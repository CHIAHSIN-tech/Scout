"""A20：成分結構化的覆蓋率報告。**沒有通過門檻。**

    python -m sauce.composition_report --home .evdb   →  reports/sauce-composition.md

它的作用是把兩件事變成看得見的數字：

1. **多數列不是讀實物標籤來的。** 三層來源各佔多少比例——照片 / FDC / 商品頁。
2. **`composition_disagreement` 只在兩邊都有值時才算得出來。**
   只有單一來源的那幾成列**從來沒有被交叉檢查過**，而它們在表上跟被檢查過的一模一樣。
   所以報告的第一個數字就是「有幾成從未被交叉驗證」。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from evdb.home import Home
from evdb.store import Store

from . import composition as composition_module
from . import contract

REPORT = Path(__file__).resolve().parent.parent / "reports" / "sauce-composition.md"

FIELDS = ("first_ingredient", "ingredient_count", "water_first", "peppers",
          "pepper_ordinal", "pepper_form", "acidifier", "fermented", "thickener",
          "oil_type", "sweetener", "preservative", "colorant", "umami_adds",
          "allergens", "has_capsaicin_extract", "manufacturer_name",
          "sodium_per_100g", "sugar_per_100g", "calories_per_100g",
          "organic_certified", "gluten_free_claim", "vegan_claim")


def collect(home: Home) -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    # **只看目前這一版規則的產出。** 舊版本的事件留在庫裡（append-only），
    # 但把它們混進來會讓報告同時描述兩套規則——而規則升版的用意正是換掉舊的判斷。
    # 新版沒有產出的實體，就是新規則認為「這裡沒有成分表」，不該用舊值補。
    current = composition_module.RULES_VERSION
    latest = {ev.entity_id: ev.payload for ev in events
              if ev.event_type == contract.EV_COMPOSITION
              and str(ev.payload.get("comp_rules_version", "")) == current}
    rows = list(latest.values())

    by_primary = Counter(str(r.get("first_ingredient_source") or "(none)") for r in rows)
    available = Counter()
    for r in rows:
        for s in (r.get("composition_sources_available") or []):
            available[s] += 1
    crosschecked = sum(1 for r in rows
                       if "label_photo" in (r.get("composition_sources_available") or [])
                       and "fdc" in (r.get("composition_sources_available") or []))
    disagreeing = sum(1 for r in rows if r.get("composition_disagreement"))
    field_fill = {f: sum(1 for r in rows if r.get(f) not in ("", None, [], False, 0))
                  for f in FIELDS}
    disagree_fields = Counter()
    for r in rows:
        for f in (r.get("composition_disagreement") or []):
            disagree_fields[f] += 1
    return {"rows": len(rows), "by_primary": dict(by_primary), "available": dict(available),
            "crosschecked": crosschecked, "disagreeing": disagreeing,
            "field_fill": field_fill, "disagree_fields": dict(disagree_fields)}


def write(data: dict[str, Any], path: Path | None = None) -> Path:
    out = Path(path or REPORT)
    out.parent.mkdir(parents=True, exist_ok=True)
    total = data["rows"] or 1
    never = total - data["crosschecked"]
    lines = [
        "# 成分結構化的覆蓋率（A20）",
        "",
        "**這份報告沒有通過門檻。** 它的用途是把兩件看不見的事變成數字。",
        "",
        f"## 1. 有 {never} / {total} 列（**{100*never/total:.1f}%**）從來沒有被交叉驗證過",
        "",
        "`composition_disagreement` 只有在**照片與 FDC 都有成分表**時才算得出來。",
        "只有單一來源的列不是「一致」，是**沒比過**——而它在表上跟比過的一模一樣。",
        "",
        f"- 兩邊都有、比得起來的：{data['crosschecked']} 列",
        f"- 其中有欄位不一致的：{data['disagreeing']} 列",
        "",
        "## 2. 三層來源各佔多少",
        "",
        "| 來源 | 當主要來源的列數 | 有提供資料的列數 |",
        "|---|---|---|",
    ]
    for source in ("label_photo", "fdc", "storefront_text"):
        lines.append(f"| {source} | {data['by_primary'].get(source, 0)} | "
                     f"{data['available'].get(source, 0)} |")
    lines += ["", "`label_photo` 是實物標籤的逐字轉錄，**最準**；`storefront_text` 最弱。",
              "", "## 3. 各欄位的填充率", "", "| 欄位 | 有值的列數 | 比例 |", "|---|---|---|"]
    for field, count in sorted(data["field_fill"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {field} | {count} | {100*count/total:.1f}% |")
    if data["disagree_fields"]:
        lines += ["", "## 4. 哪些欄位最常不一致", "", "| 欄位 | 不一致的列數 |", "|---|---|"]
        for field, count in sorted(data["disagree_fields"].items(), key=lambda kv: -kv[1]):
            lines.append(f"| {field} | {count} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.composition_report")
    ap.add_argument("--home", default=None)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    data = collect(Home.resolve(ns.home))
    path = write(data, Path(ns.out) if ns.out else None)
    print(json.dumps({"report": str(path), "rows": data["rows"],
                      "crosschecked": data["crosschecked"],
                      "never_cross_checked": data["rows"] - data["crosschecked"],
                      "by_primary": data["by_primary"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
