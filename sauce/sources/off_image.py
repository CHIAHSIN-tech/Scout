"""Open Food Facts 的標籤照片：成分表與營養標示那兩面。

Stanley 2026-09-20：「成分／營養——我們要用照片上的 Label 來看，最准」。
OFF 的貢獻者**專門拍背標**，所以 `image_ingredients_url` 與 `image_nutrition_url`
這兩欄就是我們要的東西：實物包裝上的那一行字，不是廠商網站上的行銷文案。

## 授權（動手之前先確認過，見 DECISIONS D20）

OFF 的**照片**是 CC BY-SA 3.0（與資料庫的 ODbL 不同）：要署名、衍生同條款分享。
站方另提醒照片授權不涵蓋包裝上的商標與設計。

本專案的用法：照片只落地在 `<HOME>/raw/`，**不進版控、不進 view、不重新散布**，
只拿來給模型判讀。每個事件都帶 `licence_note` 把這件事寫在資料裡，
而不是只寫在某份文件上——半年後看到那張圖的人，要能從事件本身知道它的授權。

## 不走 API

OFF 的 robots.txt 擋掉 `/api`（見 `sources/off.py`）。所幸全量匯出的 CSV 就有這兩個欄位，
所以一次都不用打 API；圖片本身在 `images.openfoodfacts.org`，該主機的 robots 允許。
"""
from __future__ import annotations

import csv
import gzip
import re
from pathlib import Path
from typing import Any, Iterator

from evdb.schema import Event, IngestPath

from .. import contract, harvest
from ..net import Fetcher
from . import filters, off

SOURCE = "off_image"
LICENCE = "CC BY-SA 3.0 (Open Food Facts photo); packaging trademarks/designs may carry third-party rights"

#: 每款最多幾張（Q10）：成分、營養各一，正面一張
PANELS = (("ingredients", "image_ingredients_url"),
          ("nutrition", "image_nutrition_url"),
          ("front", "image_url"))
MAX_PER_PRODUCT = 3

#: 實際跑的時候只抓這兩面。**正面照拿不出任何欄位**——
#: `composition` 讀的是成分表、`label_lexicon` 只驗成分面板，正面印的是行銷字。
#: 為什麼這件事要特別寫出來：第一批 25 張裡有 13 張是正面、11 張營養、
#: **成分只有 1 張**。正面照吃掉了一半的請求，換回來的是零個欄位。
#: 這台主機一張圖要 25 秒，所以「抓了但用不到」不是浪費一點點，是把整批拖垮。
DEFAULT_PANELS = ("ingredients", "nutrition")

#: OFF 的圖檔名長這樣：`ingredients_en.9.400.jpg`。`.400.` 是縮圖，`.full.` 是原圖。
#: 成分表是小字，縮圖讀不出來——所以一律換成 full，換不到才退回原網址。
_RES = re.compile(r"\.(\d+)\.(400|200|100)\.jpg$", re.I)
_LANG = re.compile(r"/(?:ingredients|nutrition|front)_([a-z]{2})\.", re.I)


def full_resolution(url: str) -> str:
    return _RES.sub(r".\1.full.jpg", str(url or ""))


def _lang(url: str) -> str:
    m = _LANG.search(str(url or ""))
    return m.group(1).lower() if m else ""


def rows_with_labels(export: Path, limit: int | None = None, log: Any = None,
                     panels: tuple[str, ...] | None = None) -> Iterator[dict[str, str]]:
    """全量匯出裡「美國 × 是辣醬 × 有標籤照片」的那些列。串流，整份不進記憶體。

    `panels` 同時是**篩選條件**：只要那幾面的照片，就只留有那幾面的列。
    少了這一層，掃出來的列有一半根本沒有成分照，抓了也只是多幾張正面照。
    """
    csv.field_size_limit(10_000_000)
    seen = 0
    with gzip.open(export, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if not off._is_us(row):
                continue
            title = (row.get("product_name") or "").strip()
            categories = (row.get("categories_en") or "").strip()
            if not title or not (off._narrow(row) or filters.keep(title, "", categories)):
                continue
            wanted = panels or tuple(k for k, _ in PANELS)
            if not any(row.get(field) for kind, field in PANELS if kind in wanted):
                continue
            seen += 1
            if log and seen % 200 == 0:
                print(f"    off_image 找到 {seen} 款有標籤照片", file=log, flush=True)
            yield row
            if limit and seen >= limit:
                return


def to_event(row: dict[str, str], panel_kind: str, url: str, blob: bytes,
             raw_ref: str, sha256: str, observed_at: str) -> Event:
    code = (row.get("code") or "").strip()
    return Event(
        entity_type="sauce_label_image",
        entity_id=contract.observation_id(SOURCE, f"{code}-{panel_kind}"),
        event_type=contract.EV_LABEL_IMAGE,
        observed_at=observed_at, source=SOURCE,
        source_record_id=f"{code}:{panel_kind}", source_url=url,
        ingest_path=IngestPath.SDK.value, raw_ref=raw_ref,
        payload={"image_sha256": sha256, "image_bytes": len(blob),
                 "panel_kind": panel_kind, "source": SOURCE, "source_url": url,
                 "resolution": "full" if ".full." in url else "as_published",
                 "lang": _lang(url), "gtin": code,
                 "product_hint": (row.get("product_name") or "").strip()[:120],
                 "brand_hint": (row.get("brands") or "").split(",")[0].strip()[:80],
                 "retrieved_at": observed_at, "licence_note": LICENCE})


def harvest_all(fetcher: Fetcher, recorder: Any, snapshot: harvest.Snapshot,
                observed_at: str, export: Path | None = None,
                limit_products: int | None = None, log: Any = None,
                skip_codes: set[str] | None = None, sink: Any = None,
                flush_every: int = 25,
                panels: tuple[str, ...] = DEFAULT_PANELS) -> dict[str, Any]:
    """抓標籤照片。一款最多三張；抓不到就跳過並計數，不讓一張圖擋住整批。

    這一支是整份管線裡**唯一一個跑幾小時起跳**的步驟（一張圖一次請求，還要守禮讓速）。
    所以它跟別的 harvester 不一樣，多兩個參數：

    - `skip_codes`：已經抓過的 GTIN。斷在半路重跑時不重抓。
    - `panels`：只抓用得到的那幾面（預設成分＋營養，不抓正面）。
    - `sink`：每 `flush_every` 款就把手上的事件交出去寫盤。
      **沒有這個，跑到第 900 秒被砍掉時那 147 張圖全部白抓**——圖在硬碟上，
      但沒有任何事件指得到它們。這不是最佳化，是失敗路徑。
    """
    import hashlib

    path = Path(export) if export else None
    if path is None:
        found = sorted(Path(harvest.STATE).glob(f"snapshot-*/off/{off.EXPORT_NAME}"))
        if not found:
            return {"source": SOURCE, "events": [], "kept": 0, "reason": "no_off_export"}
        path = found[0]

    events: list[Event] = []
    pending: list[Event] = []
    products = fetched = flushed = skipped = 0
    reasons: dict[str, int] = {}
    for row in rows_with_labels(path, limit_products, log, panels):
        if skip_codes and (row.get("code") or "").strip() in skip_codes:
            skipped += 1
            continue
        products += 1
        taken = 0
        for panel_kind, field in PANELS:
            if taken >= MAX_PER_PRODUCT:
                break
            if panel_kind not in panels:
                continue
            raw_url = (row.get(field) or "").strip()
            if not raw_url:
                continue
            url = full_resolution(raw_url)
            got = fetcher.get(url, accept="image/*")
            if not got.ok and url != raw_url:
                got = fetcher.get(raw_url, accept="image/*")   # full 不存在就退回原網址
                url = raw_url
            if not got.ok or not got.body:
                reasons[got.reason or "empty"] = reasons.get(got.reason or "empty", 0) + 1
                continue
            fetched += 1
            taken += 1
            sha = hashlib.sha256(got.body).hexdigest()
            raw_ref = recorder.store_raw(got.body, SOURCE, suffix=".jpg") or ""
            ev = to_event(row, panel_kind, url, got.body, raw_ref, sha, observed_at)
            events.append(ev)
            pending.append(ev)
        if sink and len(pending) >= flush_every:
            sink(pending)
            flushed += len(pending)
            pending = []
        if log and products % 50 == 0:
            print(f"    off_image products={products} images={fetched} flushed={flushed}",
                  file=log, flush=True)
    if sink and pending:
        sink(pending)
        flushed += len(pending)
        pending = []
    snapshot.write(SOURCE, "summary.json",
                   {"products": products, "images": fetched, "skipped": skipped,
                    "panels": list(panels), "reasons": reasons})
    return {"source": SOURCE, "events": [] if sink else events,
            "kept": flushed if sink else len(events),
            "products": products, "skipped": skipped, "reasons": reasons, "reason": ""}
