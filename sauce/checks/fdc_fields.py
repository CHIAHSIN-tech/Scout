"""A36：FDC 的欄位要抓完整。

Stanley 2026-09-20：「我們 FDC 的資料要抓詳細」。所以驗的是**鍵在不在**，不是值有沒有填——
值可以是空的（廠商就沒報），但鍵不可以缺。這個分別很重要：
鍵缺了代表**我們沒去拿**，值空代表**那裡就沒有**，兩者在下游長得一模一樣，
但一個是我們的缺陷、一個是資料的事實。

同時驗兩件小事：
- `data_source` ∈ {GDSN, LI}（FDC 只有這兩種來源，出現別的代表解析錯欄位）
- `nutrients` 是子物件，而且 per_100g 與 per_serving 兩組都在
"""
from __future__ import annotations

import sys

from ..contract import EV_PRODUCT
from ..sources.fdc import REQUIRED_KEYS
from . import arg_parser, events, home_of, report

#: spec 寫 `data_source ∈ {GDSN, LI}`，但實測 2026-04-30 那份批次檔裡還有一筆 `Euromonitor`
#: （fdc_id=2757070）。**資料是對的，spec 的 enum 不完整**——照實放寬並記進 DECISIONS D21，
#: 不是把那一列丟掉。空字串也允許：廠商沒報就是沒報。
DATA_SOURCES = {"GDSN", "LI", "Euromonitor", ""}


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.fdc_fields", rules=False).parse_args(argv)
    problems: list[str] = []
    checked = with_nutrients = 0
    for ev in events(home_of(ns)):
        if ev.event_type != EV_PRODUCT or ev.source != "fdc":
            continue
        checked += 1
        fdc_id = str(ev.payload.get("fdc_id") or ev.source_record_id or "?")
        missing = [k for k in REQUIRED_KEYS if k not in ev.payload]
        if missing:
            problems.append(f"fdc_id={fdc_id}：缺鍵 {missing}")
            continue
        source = str(ev.payload.get("data_source") or "")
        if source not in DATA_SOURCES:
            problems.append(f"fdc_id={fdc_id}：data_source={source!r} 不在 {{GDSN, LI}}")
        nutrients = ev.payload.get("nutrients")
        if not isinstance(nutrients, dict):
            problems.append(f"fdc_id={fdc_id}：nutrients 不是子物件")
            continue
        for group in ("per_100g", "per_serving"):
            if group not in nutrients:
                problems.append(f"fdc_id={fdc_id}：nutrients 缺 {group}")
        if nutrients.get("per_100g"):
            with_nutrients += 1
    return report("A36 fdc_fields", not problems,
                  {"fdc_product_events": checked, "with_nutrient_values": with_nutrients,
                   "required_keys": list(REQUIRED_KEYS)}, problems)


if __name__ == "__main__":
    sys.exit(main())
