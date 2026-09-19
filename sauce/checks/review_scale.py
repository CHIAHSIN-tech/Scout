"""A30：評論規模。≥1,200 篇、≥3,000 筆 verdict、≥400 款產品被評到。

覆蓋率會很低是預期內的（目錄四千款以上，有專業評論的大概一到兩成），
但**低覆蓋率與沒有語料是兩件事**。這條門檻是在確認後者沒有發生。
"""
from __future__ import annotations

import sys

from ..contract import EV_REVIEW, EV_VERDICT, LINK_EVENT, REVIEW_LINK_VERSION
from . import arg_parser, events, home_of, report

MIN_REVIEWS = 1200
MIN_VERDICTS = 3000
MIN_PRODUCTS_REVIEWED = 400


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.review_scale", rules=False).parse_args(argv)
    reviews = verdicts = 0
    products = set()
    for ev in events(home_of(ns)):
        if ev.event_type == EV_REVIEW:
            reviews += 1
        elif ev.event_type == EV_VERDICT:
            verdicts += 1
        elif (ev.event_type == LINK_EVENT
              and ev.payload.get("matcher_version") == REVIEW_LINK_VERSION):
            products.add(ev.entity_id)
    problems = []
    if reviews < MIN_REVIEWS:
        problems.append(f"評論 {reviews} < {MIN_REVIEWS}")
    if verdicts < MIN_VERDICTS:
        problems.append(f"verdict {verdicts} < {MIN_VERDICTS}")
    if len(products) < MIN_PRODUCTS_REVIEWED:
        problems.append(f"被評到的產品 {len(products)} < {MIN_PRODUCTS_REVIEWED}")
    return report("A30 review_scale", not problems,
                  {"reviews": reviews, "verdicts": verdicts,
                   "products_reviewed": len(products),
                   "thresholds": {"reviews": MIN_REVIEWS, "verdicts": MIN_VERDICTS,
                                  "products": MIN_PRODUCTS_REVIEWED}}, problems)


if __name__ == "__main__":
    sys.exit(main())
