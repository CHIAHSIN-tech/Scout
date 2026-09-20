"""A45：兩次執行之間變了什麼。

    python -m sauce.trend --from 2026-09-20 --to 2027-03-20
    python -m sauce.trend                      # 不給參數就取最舊與最新兩個 run

四種變化：**新增**、**消失**、**heat_rank 變動**、**配方變更**（成分或營養欄位有差異）。

配方變更是這份東西存在的理由之一：一個品牌把 `first_ingredient` 從 habanero 換成 water，
或把 `sodium_per_100g` 調掉三成，在單一時點的表上完全看不出來——
**只有兩個時點擺在一起才看得見**。

只有一個 run 的時候回報「無法比較」並寫出空報告，**exit 0**。
第一次執行就報錯等於把正常狀態當成故障。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from .export import OUT, runs

REPORTS = Path(__file__).resolve().parent.parent / "reports"

#: 這些欄位變了就叫「配方變更」
RECIPE_FIELDS = ("first_ingredient", "ingredient_count", "peppers", "acidifier",
                 "fermented", "thickener", "sweetener", "preservative",
                 "has_capsaicin_extract", "sodium_per_100g", "sugar_per_100g",
                 "calories_per_100g", "fat_per_100g", "carbs_per_100g")


def load_run(run_date: str, rules: str = "v1",
             root: Path | None = None) -> dict[str, dict[str, str]]:
    path = Path(root or OUT) / run_date / f"sauce_catalog-{rules}.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["entity_id"]: r for r in csv.DictReader(fh)}


def compare(before: dict[str, dict[str, str]],
            after: dict[str, dict[str, str]]) -> dict[str, Any]:
    added = sorted(set(after) - set(before))
    gone = sorted(set(before) - set(after))
    recipe_changed = []
    rank_changed = []
    for key in sorted(set(before) & set(after)):
        a, b = before[key], after[key]
        diffs = [f for f in RECIPE_FIELDS if (a.get(f) or "") != (b.get(f) or "")]
        if diffs:
            recipe_changed.append({"entity_id": key, "fields": diffs,
                                   "before": {f: a.get(f, "") for f in diffs},
                                   "after": {f: b.get(f, "") for f in diffs}})
        if (a.get("heat_rank") or "") != (b.get("heat_rank") or ""):
            rank_changed.append({"entity_id": key, "before": a.get("heat_rank", ""),
                                 "after": b.get("heat_rank", "")})
    return {"added": added, "gone": gone, "recipe_changed": recipe_changed,
            "rank_changed": rank_changed}


def write(data: dict[str, Any], run_from: str, run_to: str,
          path: Path | None = None) -> Path:
    out = Path(path or REPORTS / f"sauce-trend-{run_from}-{run_to}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not run_from:
        out.write_text(
            "# 趨勢報告\n\n目前只有一個 run，沒有東西可以比。\n\n"
            "**這不是錯誤**：第一次執行本來就沒有前一次。下一輪跑完就會有內容。\n",
            encoding="utf-8")
        return out
    lines = [
        f"# 趨勢：{run_from} → {run_to}",
        "",
        f"新增 {len(data['added'])}　消失 {len(data['gone'])}　"
        f"配方變更 {len(data['recipe_changed'])}　排序變動 {len(data['rank_changed'])}",
        "",
        "「消失」不代表停產——也可能是那間店這次沒抓到。兩者在這裡分不出來，",
        "要看該列的 `sources` 與 `corroboration` 才判斷得了。",
        "",
        "## 配方變更", "",
        "| 產品 | 變了哪些欄位 | 之前 | 之後 |", "|---|---|---|---|",
    ]
    for item in data["recipe_changed"][:300]:
        lines.append(f"| {item['entity_id']} | {', '.join(item['fields'])} | "
                     f"{json.dumps(item['before'], ensure_ascii=False)} | "
                     f"{json.dumps(item['after'], ensure_ascii=False)} |")
    lines += ["", "## 新增", ""] + [f"- {k}" for k in data["added"][:300]]
    lines += ["", "## 消失", ""] + [f"- {k}" for k in data["gone"][:300]]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.trend")
    ap.add_argument("--from", dest="run_from", default=None)
    ap.add_argument("--to", dest="run_to", default=None)
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)

    available = runs()
    run_from = ns.run_from or (available[0] if len(available) >= 2 else "")
    run_to = ns.run_to or (available[-1] if available else "")
    if not run_from or run_from == run_to:
        path = write({}, "", run_to, Path(ns.out) if ns.out else
                     REPORTS / "sauce-trend-single-run.md")
        print(json.dumps({"ok": True, "runs": available,
                          "note": "只有一個 run，無法比較", "report": str(path)},
                         ensure_ascii=False, indent=1))
        return 0

    data = compare(load_run(run_from, ns.rules), load_run(run_to, ns.rules))
    path = write(data, run_from, run_to, Path(ns.out) if ns.out else None)
    print(json.dumps({"ok": True, "from": run_from, "to": run_to,
                      "added": len(data["added"]), "gone": len(data["gone"]),
                      "recipe_changed": len(data["recipe_changed"]),
                      "rank_changed": len(data["rank_changed"]),
                      "report": str(path)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
