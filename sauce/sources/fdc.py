"""USDA FoodData Central 的 Branded Foods 批次檔。

這是身分骨幹：它是唯一一個**帶 GTIN** 的大母體，所以比對規則第一條（GTIN 相同才合併）
有東西可以比。沒有它，整份總表就只剩下靠名字折疊的合併，那個規則自己也知道它保守。

批次檔是 zip，四百多 MB，一次數十分鐘（BOUNDS 的外部依賴表）。所以：
- 下載走 `net.Fetcher.download()`，串流寫磁碟、可續傳，不進記憶體；
- **先在本機過濾成候選列再產生事件**，不整份進庫（A9 的天花板就是為了擋這件事）；
- 過濾規則有版本（`sources.filters`），半年後重跑分得出「市場變了」與「我們改了規則」。

zip 裡要用的兩個檔：
- `food.csv`          fdc_id, data_type, description, …   ← 產品名稱在這裡
- `branded_food.csv`  fdc_id, brand_owner, brand_name, gtin_upc, branded_food_category,
                      market_country, discontinued_date, …
先掃 food.csv 把「名字看起來是辣醬」的 fdc_id 挑出來（小），再掃 branded_food.csv 補齊。
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Any, Iterator

from evdb.schema import Event, Precision

from .. import harvest
from ..net import Fetcher
from . import filters

SOURCE = "fdc"
BASE = "https://fdc.nal.usda.gov/fdc-datasets/"
#: 抓取設定定稿時的最新一版。半年重跑時換成當時的最新版並記進 DECISIONS。
DATASET = "FoodData_Central_branded_food_csv_2026-04-30.zip"

#: FDC 沒有「辣醬」這個分類，最接近的是這幾個大類。名稱過了規則還要落在這些分類裡，
#: 否則「Jalapeno Heat 洋芋片」會因為名字有 jalapeno 就被收進母體
#: （第一版真的收了兩萬六千列，其中一大半是零食與冷凍食品）。
CATEGORY_TOKENS = frozenset({"sauce", "sauces", "condiment", "condiments", "salsa",
                             "dips", "dip", "relish", "relishes", "peppers", "oils"})
#: 分類字串裡出現這些就一定不是辣醬，即使它同時有 sauce 這個詞（起司醬、義大利麵醬…）
CATEGORY_VETO = ("pepperoni", "salami", "cold cuts", "pasta", "pizza", "dessert",
                 "cheese", "gravy", "dressing")

_CAT_WORD = __import__("re").compile(r"[^a-z0-9]+")


def category_ok(category: str) -> bool:
    low = str(category or "").lower()
    if any(v in low for v in CATEGORY_VETO):
        return False
    return bool(CATEGORY_TOKENS & set(_CAT_WORD.sub(" ", low).split()))


def dataset_url(dataset: str | None = None) -> str:
    return BASE + (dataset or DATASET)


def download(fetcher: Fetcher, snapshot: harvest.Snapshot,
             dataset: str | None = None) -> dict[str, Any]:
    """下載（可續傳）。同一份批次檔在別的快照目錄下已經抓過就直接用那一份。

    檔名帶著發布日期，所以「同名」就是「同一份資料」——重抓四百多 MB 只是為了讓它
    躺在另一個資料夾裡，那不會讓結果更可信，只會多佔一份磁碟與半小時。
    """
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
    """第一趟：名字或分類看起來是辣醬的 fdc_id → {description}。"""
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


def harvest_zip(zip_path: Path, observed_at: str, limit: int | None = None) -> dict[str, Any]:
    """第二趟：把候選補上品牌、GTIN、分類，變成事件。"""
    found = candidates(zip_path, limit)
    events: list[Event] = []
    seen = 0
    with zipfile.ZipFile(zip_path) as zf:
        for row in _rows(zf, _member(zf, "branded_food.csv")):
            fdc_id = row.get("fdc_id") or ""
            meta = found.get(fdc_id)
            if meta is None:
                continue
            seen += 1
            if not category_ok(row.get("branded_food_category")):
                continue
            country = (row.get("market_country") or "").strip()
            if country and "united states" not in country.lower():
                continue          # 只收在美國買得到的（NON_GOALS 寫死的邊界）
            discontinued = (row.get("discontinued_date") or "").strip()
            brand = (row.get("brand_name") or row.get("brand_owner") or "").strip()
            events.append(harvest.product_event(
                source=SOURCE, key=fdc_id, title=meta["description"], brand=brand,
                url=f"https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients",
                observed_at=observed_at, gtin=(row.get("gtin_upc") or "").strip(),
                us_availability="discontinued" if discontinued else "retail_listing",
                payload={"brand_owner": (row.get("brand_owner") or "").strip(),
                         "subbrand_name": (row.get("subbrand_name") or "").strip(),
                         "branded_food_category": (row.get("branded_food_category") or "").strip(),
                         "package_weight": (row.get("package_weight") or "").strip(),
                         "serving_size": (row.get("serving_size") or "").strip(),
                         "serving_size_unit": (row.get("serving_size_unit") or "").strip(),
                         "market_country": country, "discontinued_date": discontinued,
                         "modified_date": (row.get("modified_date") or "").strip(),
                         "fdc_id": fdc_id, "dataset": zip_path.name,
                         "filter_version": filters.VERSION}))
    return {"source": SOURCE, "candidates": len(found), "matched": seen,
            "events": events, "kept": len(events)}


#: bulk 匯入用的欄位。欄名就是事件 payload 的鍵，所以這裡的命名等於 schema。
CSV_COLUMNS = ("source_key", "title", "brand", "gtin", "us_availability", "evidence_url",
               "brand_owner", "branded_food_category", "package_weight", "market_country",
               "discontinued_date", "modified_date", "dataset", "filter_version")


def write_candidates_csv(zip_path: Path, out_path: Path) -> dict[str, Any]:
    """候選列 → 一份 CSV，再交給 evdb 的 bulk 匯入。

    這是整條線上唯一「先落地成中間檔、再一次灌進去」的地方，也就是唯一有機會安靜掉列的地方。
    走 bulk 是為了讓 A5 驗得到 rows_in == events + rejects；自己寫迴圈產事件就沒有這個保證。
    """
    import csv as _csv

    found = candidates(zip_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_out = skipped_category = skipped_country = 0
    with zipfile.ZipFile(zip_path) as zf, \
            out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = _csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS), lineterminator="\n")
        writer.writeheader()
        for row in _rows(zf, _member(zf, "branded_food.csv")):
            fdc_id = row.get("fdc_id") or ""
            meta = found.get(fdc_id)
            if meta is None:
                continue
            if not category_ok(row.get("branded_food_category")):
                skipped_category += 1
                continue
            country = (row.get("market_country") or "").strip()
            if country and "united states" not in country.lower():
                skipped_country += 1
                continue
            discontinued = (row.get("discontinued_date") or "").strip()
            writer.writerow({
                "source_key": fdc_id, "title": meta["description"],
                "brand": (row.get("brand_name") or row.get("brand_owner") or "").strip(),
                "gtin": (row.get("gtin_upc") or "").strip(),
                "us_availability": "discontinued" if discontinued else "retail_listing",
                "evidence_url": f"https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients",
                "brand_owner": (row.get("brand_owner") or "").strip(),
                "branded_food_category": (row.get("branded_food_category") or "").strip(),
                "package_weight": (row.get("package_weight") or "").strip(),
                "market_country": country, "discontinued_date": discontinued,
                "modified_date": (row.get("modified_date") or "").strip(),
                "dataset": zip_path.name, "filter_version": filters.VERSION})
            rows_out += 1
    return {"candidates": len(found), "rows": rows_out, "path": str(out_path),
            "skipped_category": skipped_category, "skipped_country": skipped_country}


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                dataset: str | None = None, limit: int | None = None,
                log: Any = None) -> dict[str, Any]:
    got = download(fetcher, snapshot, dataset)
    if not got["ok"]:
        return {"source": SOURCE, "events": [], "kept": 0, "reason": got["reason"],
                "download": got}
    if log:
        print(f"  fdc downloaded {got['bytes']:,} bytes -> {got['path']}", file=log, flush=True)
    out = harvest_zip(Path(got["path"]), observed_at, limit)
    out["download"] = got
    out["reason"] = ""
    if log:
        print(f"  fdc candidates={out['candidates']} kept={out['kept']}", file=log, flush=True)
    return out
