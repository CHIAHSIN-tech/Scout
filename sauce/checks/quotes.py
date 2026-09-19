"""A25：評語是原句，不是改寫。

每一筆 verdict 的 `quote` 經統一空白正規化後，必須是它那篇正文的子字串，
長度在 20–500 之間。

這一條擋的是整個語料庫最致命、也最看不出來的失敗：模型寫出一句**聽起來像**那篇評論會說的話。
它讀起來完全正常、通過所有結構檢查、掛在正確的產品上——而它從來沒有被寫過。
"""
from __future__ import annotations

import sys

from ..contract import EV_REVIEW, EV_VERDICT
from ..names import normalize_whitespace
from . import arg_parser, events, home_of, report

MIN_LEN, MAX_LEN = 20, 500


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.quotes", rules=False).parse_args(argv)
    home = home_of(ns)
    bodies: dict[str, str] = {}
    verdicts = []
    for ev in events(home):
        if ev.event_type == EV_REVIEW and ev.raw_ref:
            path = home.root / ev.raw_ref
            if path.exists():
                bodies[str(ev.payload.get("review_id") or "")] = normalize_whitespace(
                    path.read_text(encoding="utf-8", errors="replace"))
        elif ev.event_type == EV_VERDICT:
            verdicts.append(ev)

    problems = []
    for ev in verdicts:
        review_id = str(ev.payload.get("review_id") or "")
        quote = normalize_whitespace(str(ev.payload.get("quote") or ""))
        if not (MIN_LEN <= len(quote) <= MAX_LEN):
            problems.append(f"{ev.event_id}：quote 長度 {len(quote)} 不在 {MIN_LEN}–{MAX_LEN}")
            continue
        body = bodies.get(review_id)
        if body is None:
            problems.append(f"{ev.event_id}：找不到 review {review_id} 的正文，無法驗證引文")
            continue
        if quote not in body:
            problems.append(f"{ev.event_id}：quote 不是正文的子字串 —— {quote[:70]!r}")
    return report("A25 quotes", not problems,
                  {"verdicts": len(verdicts), "bodies": len(bodies)}, problems)


if __name__ == "__main__":
    sys.exit(main())
