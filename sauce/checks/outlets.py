"""A21：outlet 白名單可稽核。

每個 `sauce.review.published` 的 outlet 都要在 `fixtures/sauce/outlets.csv` 上；
名單每一列要有准入依據與**證據網址**，而且至少 40 列。

准入是人做的判斷，但判斷結果是資料——半年後重跑時要能逐列檢討「當初憑什麼收它」。
沒有 evidence_url 的列等於沒有判斷過。
"""
from __future__ import annotations

import sys

from .. import outlets as outlets_module
from ..contract import EV_REVIEW
from . import arg_parser, events, home_of, report

MIN_OUTLETS = 40


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.outlets", rules=False).parse_args(argv)
    rows = outlets_module.load()
    problems = list(outlets_module.check())
    if len(rows) < MIN_OUTLETS:
        problems.append(f"白名單只有 {len(rows)} 列，少於 {MIN_OUTLETS}")
    known = {r["outlet"] for r in rows} | {r["outlet_key"] for r in rows}
    seen: dict[str, int] = {}
    for ev in events(home_of(ns)):
        if ev.event_type != EV_REVIEW:
            continue
        outlet = str(ev.payload.get("outlet") or "")
        seen[outlet] = seen.get(outlet, 0) + 1
        if outlet not in known and outlets_module.outlet_key(outlet) not in known:
            problems.append(f"{ev.event_id}：outlet {outlet!r} 不在白名單上")
    return report("A21 outlets", not problems,
                  {"whitelist_rows": len(rows), "min_rows": MIN_OUTLETS,
                   "outlets_seen": len(seen)}, problems)


if __name__ == "__main__":
    sys.exit(main())
