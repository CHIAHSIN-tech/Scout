"""A43：來源優先序與不一致留存。

每個結構化欄位都要說得出**是誰說的**（`_source`）與**憑哪一筆**（`_source_ref`）。
照片與 FDC 都有成分表時必須算出 `composition_disagreement`，而且**兩個值都留**——
自動擇一等於替日後的分析做了一個沒有人驗證過的決定。

順帶驗一件 A42 不負責、但這裡先擋住的事：
`composition_disagreement` 只有在兩邊都有值時才算得出來。
只有單一來源的那幾成列**從來沒有被交叉檢查過**，而它們看起來跟被檢查過的一模一樣。
"""
from __future__ import annotations

import sys

from ..contract import EV_COMPOSITION
from . import arg_parser, events, home_of, report

SOURCES = {"label_photo", "fdc", "storefront_text", ""}
#: 這幾個欄位一定要帶 _source / _source_ref
TRACKED = ("first_ingredient", "ingredient_count", "acidifier", "fermented",
           "has_capsaicin_extract", "peppers")


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.composition", rules=False).parse_args(argv)
    problems: list[str] = []
    checked = crosschecked = disagreeing = 0
    by_source: dict[str, int] = {}
    for ev in events(home_of(ns)):
        if ev.event_type != EV_COMPOSITION:
            continue
        checked += 1
        p = ev.payload
        available = p.get("composition_sources_available") or []
        primary = str(p.get("first_ingredient_source") or "")
        by_source[primary or "(none)"] = by_source.get(primary or "(none)", 0) + 1
        for field in TRACKED:
            if field not in p:
                problems.append(f"{ev.entity_id}：缺欄位 {field}")
                continue
            src = p.get(f"{field}_source")
            if src is None:
                problems.append(f"{ev.entity_id}：{field} 沒有 _source")
            elif str(src) not in SOURCES:
                problems.append(f"{ev.entity_id}：{field}_source={src!r} 不在允許值內")
            if f"{field}_source_ref" not in p:
                problems.append(f"{ev.entity_id}：{field} 沒有 _source_ref")
        if "composition_disagreement" not in p:
            problems.append(f"{ev.entity_id}：缺 composition_disagreement")
            continue
        if "label_photo" in available and "fdc" in available:
            crosschecked += 1
            if p["composition_disagreement"]:
                disagreeing += 1
                # 不一致時兩個值都要在：FDC 那一份存在 <field>_fdc_value
                for field in p["composition_disagreement"]:
                    if f"{field}_fdc_value" not in p:
                        problems.append(
                            f"{ev.entity_id}：{field} 標了不一致卻沒留 FDC 的那個值")
    return report("A43 composition", not problems,
                  {"composition_rows": checked, "by_primary_source": by_source,
                   "cross_checked": crosschecked, "disagreeing": disagreeing,
                   "never_cross_checked": checked - crosschecked}, problems)


if __name__ == "__main__":
    sys.exit(main())
