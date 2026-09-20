"""A44–A46：辣度五層，不得塌成一個數字。

三件事一起驗：

- **A44**：`sauce_catalog` 有五層的欄位，而且**沒有**叫 `heat_shu` 或 `scoville` 的欄位。
  那種欄位一旦出現，下游就會拿它當事實排序——而那個數字沒有人量過。
- **A45**：`heat_ceiling_shu` 等於宣告辣椒中最辣品種的文獻上限；
  有萃取物的列必須是 `unbounded`（萃取物可以把任何東西拉到任意辣度）。
- **A46**：`heat_rank_ci_high ≥ heat_rank_ci_low`；排序事實 < 2 筆的列不給 `heat_rank`。
"""
from __future__ import annotations

import sys

from ..heat import UNBOUNDED, ceiling_for, pepper_ceilings
from . import arg_parser, catalog_rows, home_of, report

REQUIRED = ("shu_lab", "heat_ceiling_shu", "has_capsaicin_extract", "heat_rank",
            "heat_rank_ci_low", "heat_rank_ci_high", "heat_shu_claims",
            "heat_shu_disagreement", "heat_band_label", "brand_line_rank")
FORBIDDEN = ("heat_shu", "scoville")


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.heat_layers").parse_args(argv)
    rows = catalog_rows(home_of(ns), ns.rules)
    if not rows:
        return report("A44-A46 heat_layers", False, {}, ["視圖是空的"])
    columns = set(rows[0])
    problems: list[str] = []

    for col in REQUIRED:
        if col not in columns:
            problems.append(f"A44：視圖缺欄位 {col}")
    for col in FORBIDDEN:
        if col in columns:
            problems.append(f"A44：視圖不得有欄位 {col}——辣度不可以塌成一個數字")

    table = pepper_ceilings()
    checked = with_ceiling = ranked = 0
    for row in rows:
        checked += 1
        peppers = [p for p in str(row.get("peppers") or "").split("|") if p]
        has_extract = str(row.get("has_capsaicin_extract") or "").lower() in ("true", "1")
        expected, _ = ceiling_for(peppers, has_extract, table)
        actual = str(row.get("heat_ceiling_shu") or "")
        if has_extract and actual != UNBOUNDED:
            problems.append(f"A45：{row['entity_id']} 有萃取物，上界應為 {UNBOUNDED}，實際 {actual!r}")
        elif not has_extract and str(expected) != actual:
            problems.append(f"A45：{row['entity_id']} 上界應為 {expected!r}，實際 {actual!r}")
        if actual:
            with_ceiling += 1

        rank = str(row.get("heat_rank") or "")
        if rank:
            ranked += 1
            try:
                lo = int(row.get("heat_rank_ci_low") or 0)
                hi = int(row.get("heat_rank_ci_high") or 0)
            except ValueError:
                problems.append(f"A46：{row['entity_id']} 的信賴區間不是整數")
                continue
            if hi < lo:
                problems.append(f"A46：{row['entity_id']} 的 ci_high {hi} < ci_low {lo}")
            try:
                if int(row.get("heat_rank_facts") or 0) < 2:
                    problems.append(
                        f"A46：{row['entity_id']} 只有 {row.get('heat_rank_facts')} 筆排序事實卻給了 rank")
            except ValueError:
                pass
    return report("A44-A46 heat_layers", not problems,
                  {"rows": checked, "with_ceiling": with_ceiling, "ranked": ranked,
                   "required_columns_present": [c for c in REQUIRED if c in columns],
                   "forbidden_columns_present": [c for c in FORBIDDEN if c in columns]},
                  problems)


if __name__ == "__main__":
    sys.exit(main())
