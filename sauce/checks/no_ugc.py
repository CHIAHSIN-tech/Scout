"""A20：庫裡不得有任何來自使用者內容的評論事件。

Stanley 2026-09-19 講死的一句話：「I don't care what random people say about a product
at all」。所以 Reddit、零售站的評論外掛、marketplace 的星等一律**只能**產生
`sauce.observation.mention`（只有名字，沒有評語）。

這一條是擋得住的斷言，不是慣例：任何一筆 `sauce.review.*` 落在 UGC 來源集合裡就 exit 1。
"""
from __future__ import annotations

import sys

from ..contract import REVIEW_EVENT_TYPES, UGC_SOURCES
from . import arg_parser, events, home_of, report


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.no_ugc", rules=False).parse_args(argv)
    problems, review_events, ugc_events = [], 0, 0
    for ev in events(home_of(ns)):
        if ev.event_type in REVIEW_EVENT_TYPES:
            review_events += 1
            if ev.source in UGC_SOURCES:
                problems.append(f"{ev.event_id}：{ev.event_type} 來自 UGC 來源 {ev.source}")
        if ev.source in UGC_SOURCES:
            ugc_events += 1
            if ev.event_type.startswith("sauce.review"):
                problems.append(f"{ev.event_id}：UGC 來源產生了 {ev.event_type}")
    return report("A20 no_ugc", not problems,
                  {"review_events": review_events, "ugc_events": ugc_events,
                   "ugc_sources": sorted(UGC_SOURCES)}, problems)


if __name__ == "__main__":
    sys.exit(main())
