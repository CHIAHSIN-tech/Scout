"""A29：評論覆蓋率報告。**這份報告不設通過門檻。**

    python -m sauce.reviews_report --home .evdb --rules v1   →  reports/sauce-reviews.md

它的作用不是把關，是把「多數產品沒有專業評論」這件事變成看得見的數字。
目錄會有四千款以上，有專業評論的大概只有一到兩成——那是預期內的結果，
但如果沒有人把它寫下來，使用者要連查三次都查不到評語才會自己發現。

四張表：
1. 每個 outlet 的評論筆數與時間跨度；
2. 被評到的產品數與佔目錄的比例；
3. 每款被評產品的 verdict 數分佈；
4. 孤兒評論清單，並標明為什麼連不上。
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

from . import contract
from .checks import catalog_rows
from .names import fold

REPORT = Path(__file__).resolve().parent.parent / "reports" / "sauce-reviews.md"


def collect(home: Home, rules: str = "v1") -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    catalog = catalog_rows(home, rules)
    product_keys = {r["product_key"] for r in catalog}

    published = [ev for ev in events if ev.event_type == contract.EV_REVIEW]
    verdicts = [ev for ev in events if ev.event_type == contract.EV_VERDICT]
    links = [ev for ev in events if ev.event_type == contract.LINK_EVENT
             and ev.payload.get("matcher_version") == contract.REVIEW_LINK_VERSION]

    linked_reviews = {r["entity_id"] for ev in links for r in ev.related
                      if r.get("role") == "review"}
    by_outlet: dict[str, dict[str, Any]] = {}
    for ev in published:
        outlet = str(ev.payload.get("outlet") or "(unknown)")
        row = by_outlet.setdefault(outlet, {"reviews": 0, "first": "", "last": "",
                                            "tier": ev.payload.get("outlet_tier", ""),
                                            "conflict": ev.payload.get(
                                                "outlet_conflict_of_interest", "")})
        row["reviews"] += 1
        when = str(ev.payload.get("published_at") or "")[:10]
        if when:
            row["first"] = min(row["first"] or when, when)
            row["last"] = max(row["last"], when)

    per_product = Counter(ev.entity_id for ev in links)
    orphans = []
    for ev in published:
        if ev.entity_id in linked_reviews:
            continue
        names = [str(v.payload.get("sauce_name_raw") or "") for v in verdicts
                 if v.payload.get("review_id") == ev.payload.get("review_id")]
        reason = ("沒有抽出任何 verdict" if not names else
                  "verdict 的產品名在目錄裡找不到完全相同的鍵"
                  if not any(fold(n) in product_keys for n in names) else
                  "產品名對得上但品牌對不上（規則要求品牌也吻合，寧可不連）")
        orphans.append({"review_id": ev.payload.get("review_id", ""),
                        "outlet": ev.payload.get("outlet", ""),
                        "url": ev.source_url or "", "verdicts": len(names),
                        "reason": reason})

    return {"catalog_rows": len(catalog), "published": len(published),
            "verdicts": len(verdicts), "links": len(links),
            "products_reviewed": len(per_product), "by_outlet": by_outlet,
            "per_product": per_product, "orphans": orphans}


def write(data: dict[str, Any], rules: str, path: Path | None = None) -> Path:
    out = Path(path or REPORT)
    out.parent.mkdir(parents=True, exist_ok=True)
    catalog = data["catalog_rows"] or 1
    share = round(100 * data["products_reviewed"] / catalog, 1)
    dist = Counter(data["per_product"].values())
    lines = [
        "# 專業評論的覆蓋率（A29）",
        "",
        f"規則版本 `{rules}`",
        "",
        "**這份報告沒有通過門檻。** 它存在的理由是把「多數產品沒有專業評論」變成看得見的數字，",
        "而不是讓人查了三次都查不到評語之後才自己發現。",
        "",
        "| 指標 | 數字 |",
        "|---|---|",
        f"| 目錄產品數 | {data['catalog_rows']} |",
        f"| 專業評論篇數 | {data['published']} |",
        f"| 評語（verdict）筆數 | {data['verdicts']} |",
        f"| 被至少一筆評語連到的產品 | {data['products_reviewed']} |",
        f"| **佔目錄比例** | **{share}%** |",
        f"| 連不上任何產品的評論（孤兒） | {len(data['orphans'])} |",
        "",
        "## 1. 每個 outlet",
        "",
        "| outlet | tier | 利益衝突 | 評論篇數 | 最早 | 最新 |",
        "|---|---|---|---|---|---|",
    ]
    for outlet, row in sorted(data["by_outlet"].items(), key=lambda kv: -kv[1]["reviews"]):
        lines.append(f"| {outlet} | {row['tier']} | {row['conflict']} | {row['reviews']} | "
                     f"{row['first'] or '—'} | {row['last'] or '—'} |")
    lines += ["", "## 2. 每款被評產品的評語數分佈", "",
              "| 評語數 | 有幾款產品 |", "|---|---|"]
    for n, count in sorted(dist.items()):
        lines.append(f"| {n} | {count} |")
    lines += ["", "## 3. 孤兒評論", "",
              "連不上產品的評論**留在庫裡**（A27）。比對規則刻意保守：",
              "產品名要完全相同、品牌也要對得上才連——猜錯的代價是把 A 的評價掛到 B 身上，",
              "而那在庫裡看起來和正確連結一模一樣。",
              "",
              "| outlet | 評語數 | 連不上的原因 | 網址 |", "|---|---|---|---|"]
    for o in data["orphans"][:300]:
        lines.append(f"| {o['outlet']} | {o['verdicts']} | {o['reason']} | {o['url']} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.reviews_report")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    home = Home.resolve(ns.home)
    data = collect(home, ns.rules)
    path = write(data, ns.rules, Path(ns.out) if ns.out else None)
    print(json.dumps({"report": str(path), "catalog_rows": data["catalog_rows"],
                      "published": data["published"], "verdicts": data["verdicts"],
                      "products_reviewed": data["products_reviewed"],
                      "orphans": len(data["orphans"]),
                      "outlets": len(data["by_outlet"])},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
