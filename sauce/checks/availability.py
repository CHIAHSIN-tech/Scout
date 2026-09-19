"""A16：可購性的值域，以及「說得出在賣就要拿得出連結」。

`us_availability` 必須在 enum 內；值不是 `mention_only` 也不是 `unknown` 的列，
`evidence_url` 必須非空。**查得到但買不到**是這份總表最容易出現、也最難察覺的失敗：
一列寫著 retail_listing 卻沒有任何連結，讀的人沒辦法分辨那是真的在賣還是我們猜的。
"""
from __future__ import annotations

import sys

from ..contract import US_AVAILABILITY
from . import arg_parser, catalog_rows, home_of, report

NEEDS_EVIDENCE = tuple(v for v in US_AVAILABILITY if v not in ("mention_only", "unknown"))


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.availability").parse_args(argv)
    rows = catalog_rows(home_of(ns), ns.rules)
    problems: list[str] = []
    counts: dict[str, int] = {}
    for row in rows:
        value = (row.get("us_availability") or "").strip()
        counts[value] = counts.get(value, 0) + 1
        if value not in US_AVAILABILITY:
            problems.append(f"{row['entity_id']}：us_availability={value!r} 不在允許值內")
        elif value in NEEDS_EVIDENCE and not (row.get("evidence_url") or "").strip():
            problems.append(f"{row['entity_id']}：{value} 但沒有 evidence_url")
    return report("A16 availability", not problems,
                  {"rows": len(rows), "by_value": dict(sorted(counts.items()))}, problems)


if __name__ == "__main__":
    sys.exit(main())
