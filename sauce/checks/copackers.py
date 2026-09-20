"""A47：代工聚類的每個成員都附得出證據。

`sauce.copackers` 產出的每一組都要滿足三件事：

1. **至少兩個品牌**。同一個品牌的兩款出自同一條產線是廢話，不是發現。
2. **每個成員都有 `evidence_ref`**，指得到那一筆標籤或 FDC 事件。
3. **依據只有兩種**：宣告的製造者相同，或成分表相似度 ≥ 門檻。

第 2 條是這一整條線的重點。一個**猜**出來的代工關係，在報告上跟**查證過**的
長得一模一樣——而這份報告的用途正是「這 40 個小牌其實是同一家做的」這種說法，
沒有證據就講出去，錯的成本落在被點名的品牌身上。

**這條檢查不驗聚類是不是對的。** 成分表相似不等於同一家代工（配方可以互抄），
宣告的製造者相同也可能只是同一個經銷商。它驗的是「說得出憑什麼」。
"""
from __future__ import annotations

import sys

from evdb.home import Home

from .. import copackers as cop
from . import arg_parser, home_of, report

MIN_BRANDS = 2


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.copackers", rules=False).parse_args(argv)
    home: Home = home_of(ns)
    data = cop.cluster(home)
    clusters = data["clusters"]

    problems: list[str] = []
    for key, members in sorted(clusters.items()):
        brands = {m.get("brand") for m in members if m.get("brand")}
        if len(brands) < MIN_BRANDS:
            problems.append(f"{key}：只有 {len(brands)} 個品牌，不構成代工關係")
        for m in members:
            if not m.get("evidence_ref"):
                problems.append(f"{key} / {m.get('entity_id')}：沒有 evidence_ref")
            if m.get("basis") not in ("declared_manufacturer", "ingredient_similarity"):
                problems.append(f"{key} / {m.get('entity_id')}：依據 "
                                f"{m.get('basis')!r} 不在允許值內")
    for entry in data.get("missing_evidence", []):
        problems.append(f"缺證據：{entry}")

    members_total = sum(len(v) for v in clusters.values())
    return report("A47 copackers", not problems,
                  {"clusters": len(clusters), "members": members_total,
                   "products_considered": data["products_considered"],
                   "rules_version": data["rules_version"],
                   "min_brands_per_cluster": MIN_BRANDS}, problems[:20])


if __name__ == "__main__":
    sys.exit(main())
