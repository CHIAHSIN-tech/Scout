"""A30：評論規模。≥1,200 篇文章、≥30 篇彙整型評比、≥150 款醬有出處連結。

覆蓋率會很低是預期內的（目錄七千款以上，被專業評比點名的是少數），
但**低覆蓋率與沒有語料是兩件事**。這條門檻是在確認後者沒有發生。

## 2026-09-20 換過門檻

原本數的是 verdict（≥3,000 筆）。評論那條線改成只存連結之後（D27），
verdict 不再存在，所以門檻改數**彙整型文章篇數**與**有出處的醬**。

數字是照實際產出訂的，不是照期望訂的：目前 54 篇、212 款。
門檻放在 30／150，留一點下滑空間——**門檻的用途是抓「整批沒抓到」，
不是抓「比上次少了幾篇」**。後者是 `sauce.trend` 的事。
"""
from __future__ import annotations

import sys

from ..contract import (EV_REFERENCE, EV_REVIEW, EV_VERDICT, LINK_EVENT,
                        REVIEW_LINK_VERSION)
from ..references import RULES_VERSION as REF_RULES_VERSION
from . import arg_parser, events, home_of, report

MIN_REVIEWS = 1200
MIN_ROUNDUPS = 30
MIN_SAUCES_WITH_REFERENCE = 150
MIN_VERDICTS = 0          # 保留欄位：verdict 已經不產了（D27）
MIN_PRODUCTS_REVIEWED = 400


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.review_scale", rules=False).parse_args(argv)
    reviews = verdicts = 0
    products: set[str] = set()
    roundups: set[str] = set()
    sauces_with_reference: set[str] = set()
    for ev in events(home_of(ns)):
        if ev.event_type == EV_REVIEW:
            reviews += 1
        elif ev.event_type == EV_VERDICT:
            verdicts += 1
        elif ev.event_type == EV_REFERENCE:
            if str(ev.payload.get("ref_rules_version") or "") != REF_RULES_VERSION:
                continue          # 舊規則版本的關聯還在庫裡，不算進規模
            roundups.add(str(ev.payload.get("url") or ""))
            sauces_with_reference.add(ev.entity_id)
        elif (ev.event_type == LINK_EVENT
              and ev.payload.get("matcher_version") == REVIEW_LINK_VERSION):
            products.add(ev.entity_id)
    problems = []
    if reviews < MIN_REVIEWS:
        problems.append(f"評論文章 {reviews} < {MIN_REVIEWS}")
    if len(roundups) < MIN_ROUNDUPS:
        problems.append(f"彙整型評比 {len(roundups)} < {MIN_ROUNDUPS}")
    if len(sauces_with_reference) < MIN_SAUCES_WITH_REFERENCE:
        problems.append(f"有出處連結的醬 {len(sauces_with_reference)} "
                        f"< {MIN_SAUCES_WITH_REFERENCE}")
    return report("A30 review_scale", not problems,
                  {"reviews": reviews, "verdicts": verdicts,
                   "roundups": len(roundups),
                   "sauces_with_reference": len(sauces_with_reference),
                   "products_reviewed": len(products),
                   "thresholds": {"reviews": MIN_REVIEWS, "roundups": MIN_ROUNDUPS,
                                  "sauces_with_reference": MIN_SAUCES_WITH_REFERENCE}},
                  problems)


if __name__ == "__main__":
    sys.exit(main())
