"""USDA FoodData Central 的 Branded Foods 批次檔。

這是身分骨幹：它是唯一一個**帶 GTIN** 的大母體，所以比對規則第一條（GTIN 相同才合併）
有東西可以比。它同時也是**成分與營養的第二來源**——第一來源是實物標籤照片（v3）。

批次檔是 zip，四百多 MB，一次數十分鐘（BOUNDS 的外部依賴表）。所以：
- 下載走 `net.Fetcher.download()`，串流寫磁碟、可續傳，不進記憶體；
- **先在本機過濾成候選列再產生事件**，不整份進庫（A9 的天花板就是為了擋這件事）；
- 過濾規則有版本（`sources.filters`），半年後重跑分得出「市場變了」與「我們改了規則」。

## v3：欄位要抓完整（A10）

zip 裡用到四張表：

- `food.csv`          fdc_id, data_type, description      ← 產品名稱
- `branded_food.csv`  品牌、GTIN、成分表、份量、分類、資料來源、三個日期…
- `food_nutrient.csv` **1.5 GB**，fdc_id × nutrient_id × amount（每 100 g）
- `nutrient.csv`      nutrient_id → 名稱與單位

`food_nutrient.csv` 只掃一遍，而且只留「候選 fdc_id × 我們要的那幾個 nutrient_id」——
整份讀進記憶體會直接吃掉幾個 GB。

**每 100 g 與每份兩組都存**（A10）。每份是算出來的（`per_100g × 份量 ÷ 100`），
所以它帶著 `serving_basis` 說明是怎麼來的——**算出來的數字不可以長得像量出來的**。
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Iterator

from evdb.schema import Event, IngestPath

from .. import harvest
from ..net import Fetcher
from . import filters

SOURCE = "fdc"
BASE = "https://fdc.nal.usda.gov/fdc-datasets/"
#: 抓取設定定稿時的最新一版。半年重跑時換成當時的最新版並記進 DECISIONS。
DATASET = "FoodData_Central_branded_food_csv_2026-04-30.zip"

#: FDC 沒有「辣醬」這個分類，最接近的是這幾個大類。
CATEGORY_TOKENS = frozenset({"sauce", "sauces", "condiment", "condiments", "salsa",
                             "dips", "dip", "relish", "relishes", "peppers", "oils"})
#: 分類字串裡出現這些就一定不是辣醬（起司醬、義大利麵醬…）
CATEGORY_VETO = ("pepperoni", "salami", "cold cuts", "pasta", "pizza", "dessert",
                 "cheese", "gravy", "dressing")

#: 要留的營養素（FDC 的 nutrient_id 是固定的）。只留這幾個，不是全收——
#: `food_nutrient.csv` 有一億多列，全收會直接撞到 A9 的事件天花板。
NUTRIENTS: dict[str, str] = {
    "1008": "calories_kcal", "1003": "protein_g", "1004": "fat_g",
    "1258": "saturated_fat_g", "1005": "carbs_g", "2000": "sugars_g",
    "1079": "fiber_g", "1093": "sodium_mg", "1253": "cholesterol_mg",
}

#: A10 要求這些鍵一定要在（值可以是空的）
REQUIRED_KEYS = ("fdc_id", "gtin_upc", "brand_owner", "ingredients", "serving_size",
                 "serving_size_unit", "household_serving_fulltext",
                 "branded_food_category", "market_country", "data_source",
                 "modified_date", "available_date", "discontinued_date", "nutrients")

import re as _re

_CAT_WORD = _re.compile(r"[^a-z0-9]+")


def dataset_url(dataset: str | None = None) -> str:
    return BASE + (dataset or DATASET)


def category_ok(category: str) -> bool:
    low = str(category or "").lower()
    if any(v in low for v in CATEGORY_VETO):
        return False
    return bool(CATEGORY_TOKENS & set(_CAT_WORD.sub(" ", low).split()))


def download(fetcher: Fetcher, snapshot: harvest.Snapshot,
             dataset: str | None = None) -> dict[str, Any]:
    """下載（可續傳）。同一份批次檔在別的快照目錄下已經抓過就直接用那一份。"""
    name = dataset or DATASET
    dest = snapshot.dir_for(SOURCE) / name
    if not dest.exists():
        for cached in sorted(snapshot.root.parent.glob(f"snapshot-*/{SOURCE}/{name}")):
            if cached.stat().st_size > 1_000_000:
                return {"ok": True, "status": 200, "bytes": cached.stat().st_size,
                        "added": 0, "path": str(cached), "reason": "reused_cached_download",
                        "dataset": name}
    got = fetcher.download(dataset_url(name), dest)
    got["dataset"] = name
    return got


def _rows(zf: zipfile.ZipFile, member: str) -> Iterator[dict[str, str]]:
    """zip 裡的一張 CSV，一列一列吐出來。整份檔不進記憶體。"""
    with zf.open(member) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
            for row in csv.DictReader(text):
                yield row


def _member(zf: zipfile.ZipFile, name: str) -> str:
    for n in zf.namelist():
        if n.rsplit("/", 1)[-1].lower() == name:
            return n
    raise KeyError(f"{name} not in {zf.filename}")


def candidates(zip_path: Path, limit: int | None = None) -> dict[str, dict[str, str]]:
    """第一趟：名字看起來是辣醬的 fdc_id → {description}。"""
    out: dict[str, dict[str, str]] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for row in _rows(zf, _member(zf, "food.csv")):
            if row.get("data_type") != "branded_food":
                continue
            desc = (row.get("description") or "").strip()
            if desc and filters.keep(desc):
                out[row["fdc_id"]] = {"description": desc,
                                      "publication_date": row.get("publication_date", "")}
                if limit and len(out) >= limit:
                    break
    return out


def nutrients_for(zip_path: Path, wanted: set[str],
                  log: Any = None) -> dict[str, dict[str, float]]:
    """第二趟：`food_nutrient.csv` 只掃一遍，只留候選 × 我們要的營養素。

    這張表 1.5 GB、一億多列。**不建索引、不進 DataFrame**——單向串流，
    命中才留。留下來的是 `fdc_id → {欄位名: 每 100 g 的量}`。
    """
    out: dict[str, dict[str, float]] = {}
    scanned = 0
    with zipfile.ZipFile(zip_path) as zf:
        for row in _rows(zf, _member(zf, "food_nutrient.csv")):
            scanned += 1
            if log and scanned % 20_000_000 == 0:
                print(f"    fdc nutrients scanned={scanned:,} hits={len(out):,}",
                      file=log, flush=True)
            fdc_id = row.get("fdc_id")
            if fdc_id not in wanted:
                continue
            field = NUTRIENTS.get(str(row.get("nutrient_id") or ""))
            if not field:
                continue
            try:
                out.setdefault(fdc_id, {})[field] = float(row.get("amount") or 0)
            except (TypeError, ValueError):
                continue
    return out


def _per_serving(per_100g: dict[str, float], serving_size: str,
                 unit: str) -> tuple[dict[str, float], str]:
    """每份 = 每 100 g × 份量 ÷ 100。單位不是 g／ml 就算不出來，回空 dict。

    **算出來的數字要說得出是算的。** 第二個回傳值就是那句話，會存進事件裡。
    """
    try:
        size = float(serving_size)
    except (TypeError, ValueError):
        return {}, "no_serving_size"
    if size <= 0 or str(unit or "").lower() not in ("g", "ml", "grm", "mlt"):
        return {}, f"unsupported_unit:{unit}"
    factor = size / 100.0
    return ({k: round(v * factor, 4) for k, v in per_100g.items()},
            f"computed_from_per_100g x {size}{unit}/100")


def to_event(row: dict[str, str], description: str, per_100g: dict[str, float],
             observed_at: str, dataset: str) -> Event:
    fdc_id = row.get("fdc_id") or ""
    per_serv, basis = _per_serving(per_100g, row.get("serving_size", ""),
                                   row.get("serving_size_unit", ""))
    discontinued = (row.get("discontinued_date") or "").strip()
    payload = {
        "title": description,
        "brand": (row.get("brand_name") or row.get("brand_owner") or "").strip(),
        "source_key": fdc_id,
        "us_availability": "discontinued" if discontinued else "retail_listing",
        "gtin": (row.get("gtin_upc") or "").strip(),
        "evidence_url": f"https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients",
        # ---- A10 要求的欄位，值可空、鍵不可缺 ----
        "fdc_id": fdc_id,
        "gtin_upc": (row.get("gtin_upc") or "").strip(),
        "brand_owner": (row.get("brand_owner") or "").strip(),
        "brand_name": (row.get("brand_name") or "").strip(),
        "subbrand_name": (row.get("subbrand_name") or "").strip(),
        "ingredients": (row.get("ingredients") or "").strip(),
        "serving_size": (row.get("serving_size") or "").strip(),
        "serving_size_unit": (row.get("serving_size_unit") or "").strip(),
        "household_serving_fulltext": (row.get("household_serving_fulltext") or "").strip(),
        "branded_food_category": (row.get("branded_food_category") or "").strip(),
        "market_country": (row.get("market_country") or "").strip(),
        "data_source": (row.get("data_source") or "").strip(),
        "modified_date": (row.get("modified_date") or "").strip(),
        "available_date": (row.get("available_date") or "").strip(),
        "discontinued_date": discontinued,
        "package_weight": (row.get("package_weight") or "").strip(),
        "trade_channel": (row.get("trade_channel") or "").strip(),
        "not_a_significant_source_of": (row.get("not_a_significant_source_of") or "").strip(),
        "nutrients": {"per_100g": per_100g, "per_serving": per_serv,
                      "per_serving_basis": basis,
                      "nutrient_ids": sorted(NUTRIENTS)},
        "dataset": dataset,
        "filter_version": filters.VERSION,
    }
    return Event(
        entity_type="sauce_observation",
        entity_id=harvest.contract.observation_id(SOURCE, fdc_id),
        event_type=harvest.contract.EV_PRODUCT,
        observed_at=observed_at, source=SOURCE,
        source_record_id=fdc_id,
        source_url=payload["evidence_url"],
        ingest_path=IngestPath.BULK.value, payload=payload)


def harvest_zip(zip_path: Path, observed_at: str, limit: int | None = None,
                log: Any = None, accounting_csv: Path | None = None) -> dict[str, Any]:
    """候選 → 事件。同時寫一份 `candidates.csv` 當守恆的帳（A5）。"""
    found = candidates(zip_path, limit)
    if log:
        print(f"    fdc candidates={len(found):,}，開始掃營養表（1.5 GB，只掃一遍）",
              file=log, flush=True)
    nutrients = nutrients_for(zip_path, set(found), log)

    events: list[Event] = []
    rows_in = skipped_category = skipped_country = 0
    account: list[dict[str, str]] = []
    with zipfile.ZipFile(zip_path) as zf:
        for row in _rows(zf, _member(zf, "branded_food.csv")):
            fdc_id = row.get("fdc_id") or ""
            meta = found.get(fdc_id)
            if meta is None:
                continue
            rows_in += 1
            if not category_ok(row.get("branded_food_category")):
                skipped_category += 1
                account.append({"fdc_id": fdc_id, "outcome": "skipped_category"})
                continue
            country = (row.get("market_country") or "").strip()
            if country and "united states" not in country.lower():
                skipped_country += 1
                account.append({"fdc_id": fdc_id, "outcome": "skipped_country"})
                continue
            events.append(to_event(row, meta["description"], nutrients.get(fdc_id, {}),
                                   observed_at, zip_path.name))
            account.append({"fdc_id": fdc_id, "outcome": "event"})

    if accounting_csv:
        accounting_csv.parent.mkdir(parents=True, exist_ok=True)
        with accounting_csv.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["fdc_id", "outcome"], lineterminator="\n")
            w.writeheader()
            w.writerows(account)

    with_nutrients = sum(1 for e in events if e.payload["nutrients"]["per_100g"])
    return {"source": SOURCE, "candidates": len(found), "rows_in": rows_in,
            "events": events, "kept": len(events),
            "skipped_category": skipped_category, "skipped_country": skipped_country,
            "with_nutrients": with_nutrients,
            "accounting_csv": str(accounting_csv) if accounting_csv else "", "reason": ""}


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                dataset: str | None = None, limit: int | None = None,
                log: Any = None) -> dict[str, Any]:
    got = download(fetcher, snapshot, dataset)
    if not got["ok"]:
        return {"source": SOURCE, "events": [], "kept": 0, "reason": got["reason"],
                "download": got}
    if log:
        print(f"  fdc dataset {got['bytes']:,} bytes -> {got['path']}", file=log, flush=True)
    out = harvest_zip(Path(got["path"]), observed_at, limit, log,
                      snapshot.dir_for(SOURCE) / "candidates.csv")
    out["download"] = got
    if log:
        print(f"  fdc candidates={out['candidates']} kept={out['kept']} "
              f"with_nutrients={out['with_nutrients']}", file=log, flush=True)
    return out
