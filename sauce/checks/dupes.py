"""A13：同一個 GTIN 不得出現在兩列。

GTIN 是這份資料裡唯一的硬識別碼。同一個條碼出現在兩列，代表比對規則第一條沒有生效——
而那在總表上看起來只是「兩款很像的醬」，不會有任何警訊。
"""
from __future__ import annotations

import sys

from . import arg_parser, catalog_rows, home_of, report


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.dupes").parse_args(argv)
    rows = catalog_rows(home_of(ns), ns.rules)
    by_gtin: dict[str, list[str]] = {}
    for r in rows:
        gtin = (r.get("gtin") or "").strip()
        if gtin:
            by_gtin.setdefault(gtin, []).append(r["entity_id"])
    bad = {g: ids for g, ids in by_gtin.items() if len(set(ids)) > 1}
    problems = [f"GTIN {g} 出現在 {len(set(ids))} 列：{sorted(set(ids))[:4]}"
                for g, ids in sorted(bad.items())]
    return report("A13 dupes", not bad,
                  {"rows": len(rows), "with_gtin": len(by_gtin),
                   "duplicated_gtins": len(bad)}, problems)


if __name__ == "__main__":
    sys.exit(main())
