"""A27：孤兒不丟。

`evdb orphans --domain sauce` 回報的孤兒數，必須等於「沒有任何 verdict 連到任何
`sauce:` 實體」的 `sauce.review.published` 筆數。

連不上產品的評論**留在庫裡**，不得因為連不上就不寫入。這條同時驗兩件事：
沒有被安靜丟掉，而且孤兒的定義沒有被稀釋——其他種類的觀察都連得上，
所以「孤兒」在這個領域裡只剩一個意思。
"""
from __future__ import annotations

import sys

from evdb.query import orphans as core_orphans
from evdb.store import Store

from ..contract import DOMAIN, EV_REVIEW, EV_VERDICT, LINK_EVENT
from . import arg_parser, home_of, report


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.orphans", rules=False).parse_args(argv)
    home = home_of(ns)
    with Store(home, read_only=True) as store:
        reported = int(core_orphans(store, domain=DOMAIN, limit=1)["total"])
        evs = store.all_events()

    linked_reviews = set()
    for ev in evs:
        if ev.event_type != LINK_EVENT:
            continue
        for r in ev.related:
            if r.get("role") == "review":
                linked_reviews.add(r["entity_id"])
    published = [ev for ev in evs if ev.event_type == EV_REVIEW]
    unlinked = [ev for ev in published if ev.entity_id not in linked_reviews]
    verdicts = sum(1 for ev in evs if ev.event_type == EV_VERDICT)

    # 差額要說得出是誰。只回報一個數字不對，等於把除錯工作丟回給人：
    # 「孤兒比預期多 557 筆」跟「這 557 筆是還沒被抽取的名單型提及」是兩種不同的處境。
    linked_any = {r["entity_id"] for ev in evs if ev.event_type == LINK_EVENT
                  for r in ev.related}
    surplus: dict[str, int] = {}
    for ev in evs:
        if not ev.entity_id.startswith("src:") or not ev.event_type.startswith("sauce."):
            continue
        if ev.entity_id in linked_any or ev.event_type == EV_REVIEW:
            continue
        key = f"{ev.event_type} / {ev.source}"
        surplus[key] = surplus.get(key, 0) + 1

    ok = reported == len(unlinked)
    problems = [] if ok else [
        f"evdb orphans 回報 {reported}，但沒有 verdict 連上的 published 評論有 {len(unlinked)} 筆。"
        f"差額 {reported - len(unlinked)} 筆的組成：{surplus}"]
    return report("A27 orphans", ok,
                  {"orphans_reported": reported, "reviews_published": len(published),
                   "reviews_unlinked": len(unlinked), "verdicts": verdicts,
                   "non_review_orphans": surplus}, problems)


if __name__ == "__main__":
    sys.exit(main())
