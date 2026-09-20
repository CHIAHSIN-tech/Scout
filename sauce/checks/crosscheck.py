"""A50：標籤判讀要跟獨立來源對得上。

Stanley 2026-09-20：「OCR 內容要跟 research results 再交叉驗證」。

照片判讀是整份語料庫裡唯一沒有原文可比的一層。這條檢查拿**同一個 GTIN 在 OFF 上的
`ingredients_text`**（別人打字key的，跟照片判讀互相獨立）比詞的回收率與精確率。

門檻訂在中位數，不是每一筆：單筆低分經常是參照本身髒（OFF 的成分欄位有一部分是
貢獻者把整張背標貼進去的），拿單筆當關卡會擋掉正確的判讀。
中位數掉下來才代表判讀整體出了問題。

**兩個必須跟著分數一起讀的限制**：

- **覆蓋率**：OFF 沒有那個 GTIN 成分文字的那幾筆**完全沒被驗過**，
  而它們在總表上跟驗過的長得一模一樣。所以覆蓋率要跟分數一起報。
- **順序驗不到**：詞的集合一樣、順序顛倒，兩個分數都是 1.0——
  而美國標籤的成分順序代表含量由多到少。
"""
from __future__ import annotations

import sys

from .. import crosscheck
from . import arg_parser, home_of, report

MIN_MEDIAN_RECALL = 0.70
MIN_MEDIAN_PRECISION = 0.60
MIN_COVERAGE = 0.30


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.crosscheck", rules=False).parse_args(argv)
    out = crosscheck.run(home_of(ns))
    problems: list[str] = []
    if out.get("reason"):
        problems.append(str(out["reason"]))
    elif not out.get("cross_checked"):
        problems.append("一筆都沒有對得到獨立成分文字——這不是通過，是什麼都沒驗到")
    else:
        if (out.get("median_recall") or 0) < MIN_MEDIAN_RECALL:
            problems.append(f"回收率中位數 {out['median_recall']} < {MIN_MEDIAN_RECALL}"
                            "：判讀普遍漏讀")
        if (out.get("median_precision") or 0) < MIN_MEDIAN_PRECISION:
            problems.append(f"精確率中位數 {out['median_precision']} < {MIN_MEDIAN_PRECISION}"
                            "：轉錄裡混進了不屬於成分表的東西")
        if (out.get("coverage") or 0) < MIN_COVERAGE:
            problems.append(f"只有 {out['coverage']:.0%} 的判讀對得到獨立來源"
                            f"（門檻 {MIN_COVERAGE:.0%}）——其餘完全沒被驗過")
    return report("A50 crosscheck", not problems,
                  {**out, "min_median_recall": MIN_MEDIAN_RECALL,
                   "min_median_precision": MIN_MEDIAN_PRECISION,
                   "min_coverage": MIN_COVERAGE}, problems)


if __name__ == "__main__":
    sys.exit(main())
