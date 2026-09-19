"""A15：每一列都追得回來。

`source_count ≥ 1`，而且用 `entity_id` 查 timeline 至少查得到一筆 `source_url` 非空的事件。
沒有出處的列不是「證據薄」，是**沒有證據**——那種列混在四千列裡完全看不出來。
"""
from __future__ import annotations

import sys

from evdb.store import Store

from . import arg_parser, catalog_rows, home_of, report


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.provenance").parse_args(argv)
    home = home_of(ns)
    rows = catalog_rows(home, ns.rules)
    problems: list[str] = []
    checked = 0
    with Store(home, read_only=True) as store:
        with_url: set[str] = set()
        for ev in store.all_events():
            if not (ev.source_url or "").strip():
                continue
            with_url.add(ev.entity_id)
            for r in ev.related:
                with_url.add(r["entity_id"])
        for row in rows:
            checked += 1
            if int(row.get("source_count") or 0) < 1:
                problems.append(f"{row['entity_id']}：source_count = 0")
            elif row["entity_id"] not in with_url:
                problems.append(f"{row['entity_id']}：timeline 上沒有任何 source_url 非空的事件")
    return report("A15 provenance", not problems,
                  {"rows": checked, "rows_without_provenance": len(problems)}, problems)


if __name__ == "__main__":
    sys.exit(main())
