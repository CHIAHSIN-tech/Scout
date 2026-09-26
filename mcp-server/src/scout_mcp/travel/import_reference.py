"""把參考產品的 `rest.json` 轉成 `places[]`（規格 A17）。

這支的價值不在「以後每趟都會用到」——它是**schema 的壓力測試**。
39 家真實餐廳是現成的、有雜訊的、欄位形狀不一致的資料；能無損吃下它，
就代表 schema 不是照著理想狀況設計的。

**一個欄位都不准靜默丟掉。** 對不上 schema 的一律進 `extra{}`，
所以轉完之後 `chef_bio`、`chef_sources`、`alert`、`area` 都還找得到。

    python -m scout_mcp.travel.import_reference <rest.json> --out <places.json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .schema import PLACE_FIELDS, validate_places

# rest.json 裡直接對得上 places 同名欄位的
_SAME_NAME = ("alert", "notes", "sources", "area", "district")
# 已經被明確處理掉的來源欄位；其餘一律掃進 extra{}
_HANDLED = {
    "id", "name", "name_ko", "cuisine", "address", "district", "area",
    "price_band", "hours", "reservation", "alert", "catchtable_url",
    "gmaps_url", "sources", "notes",
}
_PLACE_KEYS = {name for name, _, _ in PLACE_FIELDS}


def _split_cuisine(raw: str) -> list[str]:
    """`"中式義式融合（퓨전음식・차이니즈 이탈리안）"` → ["中式義式融合", "퓨전음식", "차이니즈 이탈리안"]。

    原字串一定會留在 `extra.cuisine_raw`，所以這裡切壞了也不會掉資料。
    """
    parts = re.split(r"[（(]|[)）]|[、,／/・]|\s*\|\s*", raw or "")
    return [p.strip() for p in parts if p and p.strip()]


def convert_one(r: dict) -> dict:
    """一筆 rest.json 紀錄 → 一個 place。"""
    place: dict = {"id": r["id"], "name": r["name"], "kind": "meal"}

    # 韓文店名。rest.json 用字串 "unknown" 當「查不到」的哨符——
    # 那不是店名，不能寫進 name_local；但也不丟掉，原樣留在 extra。
    name_ko = r.get("name_ko")
    if name_ko and name_ko != "unknown":
        place["name_local"] = name_ko

    raw_cuisine = r.get("cuisine")
    if raw_cuisine:
        place["cuisine"] = _split_cuisine(raw_cuisine)

    for k in _SAME_NAME:
        if r.get(k) is not None:
            place[k] = r[k]

    pb = r.get("price_band") or {}
    if pb:
        place["price_band"] = {
            "band": pb.get("band"),
            "note": pb.get("value"),
            "source": pb.get("source"),
        }

    # hours：來源包成一筆 sources[0]。**沒有 fetched_at 就不寫 fetched_at**——
    # rest.json 沒有記查證日期，捏一個日期會讓「這筆多新」變成假資訊。
    h = r.get("hours") or {}
    src = {"value": h.get("value")}
    if h.get("closed_days") is not None:
        src["closed_days"] = h["closed_days"]
    if h.get("source"):
        src["url"] = h["source"]
    place["hours"] = {"sources": [src] if h.get("value") else []}

    rv = r.get("reservation") or {}
    if rv:
        reservation = {
            "required": True,
            "done": False,
            "difficulty": rv.get("difficulty"),
            "rule": rv.get("rule"),
        }
        # catchtable_url 與 reservation.source 可能是同一個東西的兩種寫法。
        # 訂位入口優先給 catchtable；兩者不同時，另一個進 sources[]，不覆蓋。
        ct = r.get("catchtable_url")
        rs = rv.get("source")
        reservation["url"] = ct or rs
        place["reservation"] = reservation
        if ct and rs and ct != rs:
            place.setdefault("sources", [])
            if rs not in place["sources"]:
                place["sources"] = [*place["sources"], rs]

    location = {}
    if r.get("address"):
        location["address"] = r["address"]
    if r.get("gmaps_url"):
        location["map_url"] = r["gmaps_url"]
    if location:
        place["location"] = location

    # 剩下的全部進 extra{}：seed_no、chef_* 五個欄位、以及任何未來新增的欄位。
    extra = {k: v for k, v in r.items() if k not in _HANDLED}
    if raw_cuisine:
        extra["cuisine_raw"] = raw_cuisine
    if name_ko == "unknown":
        extra["name_ko_raw"] = name_ko
    if extra:
        place["extra"] = extra

    return place


def convert(rows: list[dict]) -> list[dict]:
    return [convert_one(r) for r in rows]


def unmapped_keys(rows: list[dict], places: list[dict]) -> set[str]:
    """來源有、但轉完之後在 places 與 extra 裡都找不到的欄位名。應該永遠是空集合。"""
    lost: set[str] = set()
    for r, p in zip(rows, places, strict=True):
        extra = p.get("extra") or {}
        for k in r:
            if k in _PLACE_KEYS or k in extra or k in _HANDLED:
                continue
            lost.add(k)
    return lost


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="rest.json → places[]")
    ap.add_argument("source", help="rest.json 的路徑")
    ap.add_argument("--out", required=True, help="輸出的 places.json 路徑")
    args = ap.parse_args(argv)

    rows = json.loads(Path(args.source).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        print("來源必須是陣列", file=sys.stderr)
        return 2

    places = convert(rows)
    lost = unmapped_keys(rows, places)
    if lost:
        print(f"有欄位沒有落點，會被靜默丟掉：{sorted(lost)}", file=sys.stderr)
        return 1

    errs = validate_places(places)
    if errs:
        for e in errs[:20]:
            print(e, file=sys.stderr)
        print(f"共 {len(errs)} 項結構錯誤", file=sys.stderr)
        return 1

    Path(args.out).write_text(
        json.dumps(places, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"轉出 {len(places)} 筆 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
