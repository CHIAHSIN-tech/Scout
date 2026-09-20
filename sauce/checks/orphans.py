"""A27：孤兒不丟。

連不上產品的觀察**留在庫裡**，不得因為連不上就不寫入。

## 這條檢查在 2026-09-20 換過一次判準

原本的判準是「孤兒數 == 沒有 verdict 連上的評論數」——那成立的前提是
**評論是唯一會連不上的東西**。評語那條線改成只存連結之後（D27），
孤兒就有好幾種了：沒有被任何彙整型文章提到的評論、還沒對上產品的標籤照片、
名單型提及、沒比對上的店面商品。

新的判準是**每一筆孤兒都說得出是哪一種**：
總數要等於各類別加總，而且類別要全部落在已知的清單裡。
只回報一個數字不對，等於把除錯工作丟回給人——
「孤兒比預期多 557 筆」跟「這 557 筆是還沒被抽取的名單型提及」是兩種不同的處境。
"""
from __future__ import annotations

import sys

from evdb.query import orphans as core_orphans
from evdb.store import Store

from ..contract import (DOMAIN, EV_LABEL_IMAGE, EV_MENTION, EV_PRODUCT, EV_REVIEW,
                        EV_VERDICT, LINK_EVENT)
from . import arg_parser, home_of, report

#: 允許連不上的事件型別，以及為什麼：
#: - 產品觀察：名字比對不到總表上的任何一款（小廠、拼法差異）
#: - 名單型提及：只有名字沒有更多資訊，本來就不一定接得上
#: - 標籤照片：那個 GTIN 不在總表裡
#: **新的事件型別出現在孤兒裡就要在這裡登記**，否則「接不上」會被默默接受。
KNOWN_ORPHAN_TYPES = (EV_PRODUCT, EV_MENTION, EV_LABEL_IMAGE, "sauce.observation.lineup")


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

    accounted = len(unlinked) + sum(surplus.values())
    problems: list[str] = []
    if reported != accounted:
        problems.append(
            f"evdb orphans 回報 {reported}，但只解釋得了 {accounted} 筆"
            f"（沒被彙整型文章提到的評論 {len(unlinked)}＋其他 {sum(surplus.values())}）。"
            f"差額 {reported - accounted} 筆沒有歸屬——那才是真的丟了東西。"
            f"組成：{surplus}")
    unknown = [k for k in surplus if k.split(" / ")[0] not in KNOWN_ORPHAN_TYPES]
    if unknown:
        problems.append(f"出現沒見過的孤兒種類：{unknown}。"
                        "新的事件型別要嘛接得上實體，要嘛在這裡登記為什麼接不上")
    return report("A27 orphans", not problems,
                  {"orphans_reported": reported, "accounted_for": accounted,
                   "reviews_published": len(published),
                   "reviews_without_reference": len(unlinked), "verdicts": verdicts,
                   "non_review_orphans": surplus}, problems)


if __name__ == "__main__":
    sys.exit(main())
