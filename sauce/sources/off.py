"""Open Food Facts：補 FDC 漏掉的進口與小廠。

FDC 收的是廠商自己報給 USDA 的品牌食品，所以進口品與沒報的小廠會整片不見。
OFF 是群眾維護的，涵蓋面不同、一樣帶 barcode，兩邊用 GTIN 就接得起來。

## 為什麼走全量匯出而不是 search API

原本走 `world.openfoodfacts.org/api/v2/search`，那樣只要抓幾百筆。
但 OFF 的 robots.txt 對一般代理人寫著 `Disallow: /api`（實測 2026-09-19），
所以那條路不能走——**不繞過 robots 是硬規則，不是偏好**。

OFF 自己公開一份全量匯出（`static.openfoodfacts.org/data/…products.csv.gz`，約 1.3 GB），
那份不在 robots 的禁止清單上，而且它本來就是給人下載的。代價是要下載並串流過濾整份檔案；
好處是這一次抓完就有完整母體，不必對同一個站發幾百次請求。

檔案是 **TSV**（分隔字元是 tab，不是逗號），而且有些列的欄位數不齊——
用 csv 模組逐列讀、壞的列跳過並計數，不讓一列壞資料中斷整份檔案。
"""
from __future__ import annotations

import csv
import gzip
import io
import sys
from pathlib import Path
from typing import Any, Iterator

from evdb.schema import Event

from .. import harvest
from ..net import Fetcher
from . import filters

SOURCE = "off"
EXPORT_URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
EXPORT_NAME = "en.openfoodfacts.org.products.csv.gz"

#: 只收美國買得到的（NON_GOALS 寫死的邊界）
US_TOKENS = ("united states", "en:united-states", "usa")

#: 這些分類本身就等於「這是一款辣醬」，名字看不出來也照收。
NARROW_CATEGORY_TOKENS = ("hot-sauces", "hot sauces", "chili-sauces", "chili sauces",
                          "pepper-sauces", "sriracha", "harissa", "sambal", "chili-oils")

FIELDS = ("code", "product_name", "brands", "categories_en", "countries_en", "quantity",
          "labels_en", "last_modified_t", "url")


def download(fetcher: Fetcher, snapshot: harvest.Snapshot) -> dict[str, Any]:
    dest = snapshot.dir_for(SOURCE) / EXPORT_NAME
    if not dest.exists():
        for cached in sorted(snapshot.root.parent.glob(f"snapshot-*/{SOURCE}/{EXPORT_NAME}")):
            if cached.stat().st_size > 100_000_000:
                return {"ok": True, "bytes": cached.stat().st_size, "added": 0,
                        "path": str(cached), "reason": "reused_cached_download"}
    return fetcher.download(EXPORT_URL, dest)


def _rows(path: Path) -> Iterator[dict[str, str]]:
    """串流讀 gzip TSV。整份檔案不進記憶體（解開後十幾 GB）。"""
    csv.field_size_limit(10_000_000)
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in reader:
            yield row


def _is_us(row: dict[str, str]) -> bool:
    blob = (row.get("countries_en") or "").lower()
    return any(t in blob for t in US_TOKENS)


def _narrow(row: dict[str, str]) -> bool:
    blob = (row.get("categories_en") or "").lower()
    return any(t in blob for t in NARROW_CATEGORY_TOKENS)


def harvest_export(path: Path, observed_at: str, limit: int | None = None,
                   log: Any = None) -> dict[str, Any]:
    events: list[Event] = []
    scanned = us_rows = bad = 0
    try:
        for row in _rows(path):
            scanned += 1
            if scanned % 500_000 == 0 and log:
                print(f"    off scanned={scanned:,} kept={len(events):,}", file=log, flush=True)
            try:
                if not _is_us(row):
                    continue
                us_rows += 1
                code = (row.get("code") or "").strip()
                title = (row.get("product_name") or "").strip()
                if not code or not title:
                    continue
                categories = (row.get("categories_en") or "").strip()
                if not (_narrow(row) or filters.keep(title, "", categories)):
                    continue
                # OFF 的 `brands` 是**逗號串起來的多值欄位**
                # （"Secret Aardvark Trading Co,Secret Aardvark"）。整串當品牌會讓
                # 同一款醬在不同筆之間折出不同的鍵，最後在總表上變成好幾列。取第一個。
                brand = (row.get("brands") or "").split(",")[0].strip()
                events.append(harvest.product_event(
                    source=SOURCE, key=code, title=title, brand=brand,
                    url=(row.get("url") or f"https://world.openfoodfacts.org/product/{code}"),
                    observed_at=observed_at, gtin=code,
                    us_availability="retail_listing",
                    payload={"brands_all": (row.get("brands") or "")[:200],
                             "categories_en": categories[:400],
                             "countries_en": (row.get("countries_en") or "")[:200],
                             "quantity": (row.get("quantity") or "")[:80],
                             "labels_en": (row.get("labels_en") or "")[:200],
                             "last_modified_t": (row.get("last_modified_t") or ""),
                             "export": path.name, "filter_version": filters.VERSION}))
                if limit and len(events) >= limit:
                    break
            except Exception:
                bad += 1
    except (OSError, EOFError) as exc:
        return {"source": SOURCE, "events": events, "kept": len(events),
                "scanned": scanned, "us_rows": us_rows, "bad_rows": bad,
                "reason": f"{type(exc).__name__}: {exc}"}
    return {"source": SOURCE, "events": events, "kept": len(events), "scanned": scanned,
            "us_rows": us_rows, "bad_rows": bad, "reason": ""}


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                limit: int | None = None, log: Any = None) -> dict[str, Any]:
    got = download(fetcher, snapshot)
    if not got["ok"]:
        return {"source": SOURCE, "events": [], "kept": 0, "reason": got["reason"],
                "download": got}
    if log:
        print(f"  off export {got['bytes']:,} bytes -> {got['path']}", file=log, flush=True)
    out = harvest_export(Path(got["path"]), observed_at, limit, log)
    out["download"] = got
    if log:
        print(f"  off scanned={out['scanned']:,} us={out['us_rows']:,} kept={out['kept']:,} "
              f"bad={out['bad_rows']}", file=log, flush=True)
    return out
