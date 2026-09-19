"""A8：產品規模。distinct 產品 ≥ 4,000、distinct 品牌 ≥ 800。

門檻不是為了好看。這份總表要回答的是「我還沒吃過的有哪些」，
而母體如果只有幾百款，查不到就跟「這款不存在」長得一模一樣——**漏收事後完全看不出來**。
所以規模是驗收條件，不是附註。
"""
from __future__ import annotations

import sys

from . import arg_parser, catalog_rows, home_of, report

MIN_PRODUCTS = 4000
MIN_BRANDS = 800


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.scale").parse_args(argv)
    rows = catalog_rows(home_of(ns), ns.rules)
    products = {r["entity_id"] for r in rows}
    brands = {r["brand_key"] for r in rows if r.get("brand_key")}
    problems = []
    if len(products) < MIN_PRODUCTS:
        problems.append(f"產品 {len(products)} < {MIN_PRODUCTS}")
    if len(brands) < MIN_BRANDS:
        problems.append(f"品牌 {len(brands)} < {MIN_BRANDS}")
    return report("A8 scale", not problems,
                  {"products": len(products), "brands": len(brands),
                   "min_products": MIN_PRODUCTS, "min_brands": MIN_BRANDS}, problems)


if __name__ == "__main__":
    sys.exit(main())
