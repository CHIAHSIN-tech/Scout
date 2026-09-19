"""A9：事件總數天花板（800,000）。

`evdb derive` 會把全部事件讀進記憶體。這條是擋在它前面的保險絲，
**不是放寬 derive 的理由**——超過就去收緊來源端的候選過濾規則（例如 FDC 的分類閘），
不是去改 derive。給 evdb 的 streaming derive 提案記在 KNOWN_ISSUES，本任務不實作、不繞過。
"""
from __future__ import annotations

import sys

from evdb.store import Store

from . import arg_parser, home_of, report

MAX_EVENTS = 800_000


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.ceiling", rules=False).parse_args(argv)
    with Store(home_of(ns), read_only=True) as store:
        stats = store.stats()
    total = int(stats["events"])
    ok = total <= MAX_EVENTS
    problems = [] if ok else [
        f"事件總數 {total} 超過天花板 {MAX_EVENTS}；收緊來源的候選過濾規則，不要放寬 derive"]
    return report("A9 ceiling", ok,
                  {"events": total, "max_events": MAX_EVENTS,
                   "by_source": stats["by_source"]}, problems)


if __name__ == "__main__":
    sys.exit(main())
