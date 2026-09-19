"""A17：召回率。這是產品層的核心關卡。

    python -m sauce.coverage --home .evdb --rules v1 --probe sauce/probe/probe-v1.csv

拿一份 held-out 的清單去問總表：這些我們知道存在的辣醬，有幾款查得到。
recall < 0.90 就 exit 1；**不論過不過都寫出 `reports/sauce-coverage.md`**，
逐筆列出命中與未命中，未命中要標明「哪一個來源階層本來應該收到它」。

## 為什麼要有這張清單

漏收一款辣醬，事後完全看不出來。總表少了 Secret Aardvark，查詢端只會回「查無此醬」，
那跟「這款不存在」長得一模一樣。沒有一份獨立的清單去問，就沒有任何辦法發現這件事。

## 清單必須是 held-out 的

`probe-v1.csv` 在抓取設定定稿**之前**由人建立，而且 `sauce/` 底下除了這支程式與清單本身
不准提到它（A18 用 git grep 驗）。一旦抓取規則看得到這份清單，它量到的就不再是召回率，
而是「我們有沒有把清單抄進規則裡」。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home

from .checks import catalog_rows
from .names import fold

REPO = Path(__file__).resolve().parent.parent
DEFAULT_LIST = REPO / "sauce" / "probe" / "probe-v1.csv"
REPORT = REPO / "reports" / "sauce-coverage.md"
MIN_RECALL = 0.90

#: 未命中時，這個來源階層本來應該收到它
EXPECTED_BY_ORIGIN = {
    "supabase_sauces": "2 長尾（shopify／woo）或 1 母體（fdc／off）",
    "shelf_photo": "1 母體（fdc／off）——貨架上的東西幾乎都有 GTIN",
    "reddit_walk": "3 名單（awards／wikipedia）或 4 提及（reddit）",
}


def load_list(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as fh:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items() if k}
                for r in csv.DictReader(fh)]


#: 產品名要對上幾成的詞才算同一款
TOKEN_OVERLAP = 0.5


def _overlap(a: list[str], b: list[str]) -> float:
    if not a:
        return 0.0
    return len(set(a) & set(b)) / len(set(a))


def evaluate(rows: list[dict[str, str]], entries: list[dict[str, str]]) -> dict[str, Any]:
    """清單的每一筆在總表裡找不找得到。

    ## 為什麼不是「鍵完全相同才算命中」

    清單寫的是「我知道有這款醬」，用的是人記得的講法（`Original Red Sauce`）；
    總表寫的是通路怎麼命名（`PEPPER SAUCE, ORIGINAL`）。要求兩者的折疊鍵完全相同，
    量到的是「我們有沒有猜中通路的用字」，不是「這款醬在不在母體裡」。

    所以分三級，而且**把級別寫進報告**，不是偷偷放寬：
    - `brand+product`：品牌與產品鍵都相同 —— 最硬。
    - `brand+overlap`：品牌相同，產品名的詞重疊 ≥ 50%。
    - `product_only`：產品鍵相同但品牌對不上（總表本來就可能缺品牌欄）。

    三級都算命中。**只在品牌與產品都對不上時才算漏收。**
    """
    by_product: dict[str, list[dict[str, str]]] = {}
    by_brand: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        by_product.setdefault(r["product_key"], []).append(r)
        by_brand.setdefault(r["brand_key"], []).append(r)

    hits, misses = [], []
    for entry in entries:
        pkey = fold(entry.get("name", ""))
        bkey = fold(entry.get("brand", ""))
        ptokens = [t for t in pkey.split("-") if t]

        exact = [r for r in (by_product.get(pkey) or []) if r["brand_key"] == bkey]
        overlap: list[dict[str, str]] = []
        if not exact and bkey:
            candidates = by_brand.get(bkey) or []
            scored = [(_overlap(ptokens, [t for t in r["product_key"].split("-") if t]), r)
                      for r in candidates]
            overlap = [r for s, r in sorted(scored, key=lambda x: -x[0])
                       if s >= TOKEN_OVERLAP]
        product_only = by_product.get(pkey) or []

        match, how = (exact, "brand+product") if exact else \
                     (overlap, "brand+overlap") if overlap else \
                     (product_only, "product_only") if product_only else ([], "")
        if match:
            hits.append({**entry, "entity_id": match[0]["entity_id"], "matched_on": how,
                         "matched_product": match[0].get("product", ""),
                         "sources": match[0].get("sources", "")})
        else:
            misses.append({**entry,
                           "brand_in_catalog": bool(by_brand.get(bkey)),
                           "expected_from": EXPECTED_BY_ORIGIN.get(entry.get("origin", ""),
                                                                   "（來源不明）")})
    total = len(entries)
    by_level: dict[str, int] = {}
    for h in hits:
        by_level[h["matched_on"]] = by_level.get(h["matched_on"], 0) + 1
    return {"total": total, "hits": hits, "misses": misses, "by_level": by_level,
            "recall": round(len(hits) / total, 4) if total else 0.0}


def write_report(result: dict[str, Any], rules: str, path: Path | None = None) -> Path:
    out = Path(path or REPORT)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 產品召回率（A17）",
        "",
        f"規則版本 `{rules}`　清單 {result['total']} 筆　命中 {len(result['hits'])} 筆　"
        f"**recall = {result['recall']}**（門檻 {MIN_RECALL}）",
        "",
        "清單是 held-out 的：它在抓取設定定稿之前建立，抓取端看不到它（A18）。",
        "",
        "## 未命中",
        "",
        "漏收一款辣醬，事後完全看不出來——查不到與不存在長得一模一樣。",
        "所以每一筆未命中都要寫出「本來哪一個來源階層應該收到它」，那才是要修的地方。",
        "",
        "| 名稱 | 品牌 | 品牌在總表裡？ | 清單來源 | 本來應該由誰收到 |",
        "|---|---|---|---|---|",
    ]
    for m in result["misses"]:
        lines.append(f"| {m.get('name', '')} | {m.get('brand', '') or '—'} | "
                     f"{'有' if m.get('brand_in_catalog') else '沒有'} | "
                     f"{m.get('origin', '')} | {m['expected_from']} |")
    lines += ["", "「品牌在總表裡＝有」的那幾筆，漏的是**這一款**，不是這個品牌——",
              "多半是通路只上架了同品牌的其他口味。「沒有」才是整個品牌都沒收到。",
              "", "## 命中", "",
              f"比對級別分佈：{result['by_level']}",
              "",
              "| 名稱 | 品牌 | 比對方式 | 對到的產品名 | 來源 |", "|---|---|---|---|---|"]
    for h in result["hits"]:
        lines.append(f"| {h.get('name', '')} | {h.get('brand', '') or '—'} | "
                     f"{h['matched_on']} | {h.get('matched_product', '')} | "
                     f"{h.get('sources', '')} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.coverage")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--probe", default=None, help="held-out 清單 CSV")
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    entries = load_list(Path(ns.probe) if ns.probe else DEFAULT_LIST)
    rows = catalog_rows(Home.resolve(ns.home), ns.rules)
    result = evaluate(rows, entries)
    report_path = write_report(result, ns.rules, Path(ns.out) if ns.out else None)
    ok = result["recall"] >= MIN_RECALL
    print(json.dumps({"check": "A17 coverage", "ok": ok, "recall": result["recall"],
                      "min_recall": MIN_RECALL, "list_entries": result["total"],
                      "hits": len(result["hits"]), "misses": len(result["misses"]),
                      "by_level": result["by_level"],
                      "report": str(report_path),
                      "missed": [m.get("name") for m in result["misses"]][:20]},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
