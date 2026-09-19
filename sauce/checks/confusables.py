"""A14：不過度合併。

`fixtures/sauce/confusables.csv` 是人工維護的一份「這幾組長得像但不是同一款」清單。
每一組在視圖裡都必須仍然是各自獨立的列。

為什麼要有這一份：過度合併與漏收一樣，事後完全看不出來，但它更糟——
把兩個不同品牌的同名產品併成一列之後，總表顯示「一列、兩個來源」，
看起來比實際更有佐證。漏收至少是空白；過度合併是**假的佐證**。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from ..names import fold
from . import REPO, arg_parser, catalog_rows, home_of, report

CONFUSABLES = REPO / "fixtures" / "sauce" / "confusables.csv"
MIN_GROUPS = 15


def load(path: Path | None = None) -> list[dict[str, str]]:
    p = Path(path or CONFUSABLES)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items() if k}
                for r in csv.DictReader(fh)]


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.confusables").parse_args(argv)
    rows = catalog_rows(home_of(ns), ns.rules)
    by_key = {(r["brand_key"], r["product_key"]): r["entity_id"] for r in rows}
    groups = load()
    problems = []
    if len(groups) < MIN_GROUPS:
        problems.append(f"confusables.csv 只有 {len(groups)} 組，少於 {MIN_GROUPS}")
    checked = found = 0
    for g in groups:
        checked += 1
        a = (fold(g.get("brand_a", "")), fold(g.get("product_a", "")))
        b = (fold(g.get("brand_b", "")), fold(g.get("product_b", "")))
        ida, idb = by_key.get(a), by_key.get(b)
        if ida is None and idb is None:
            continue           # 兩邊都還沒收到，這一組這次驗不到（不是錯，但也不算過）
        found += 1
        if ida is not None and ida == idb:
            problems.append(f"第 {checked} 組被併成同一列：{g.get('label', '')} -> {ida}")
    return report("A14 confusables", not problems,
                  {"groups": len(groups), "min_groups": MIN_GROUPS,
                   "groups_present_in_view": found, "catalog_rows": len(rows)}, problems)


if __name__ == "__main__":
    sys.exit(main())
