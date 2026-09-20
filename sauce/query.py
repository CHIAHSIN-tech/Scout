"""A35：真人實際會做的那件事。

    python -m sauce.query "Secret Aardvark"
    python -m sauce.query "Secret Aardvark" --reviews
    python -m sauce.query "zzzz-not-a-sauce"          # 0 列，exit 0（查無不是錯誤）

朋友說某款醬很好吃 → 查總表 → 看懂的人怎麼講 → 決定買不買。這支程式就是那條路徑。

查不到回 0 列而且 exit 0，是刻意的：**「查無此醬」不是程式出錯**。
把它當成錯誤會讓呼叫端分不出「沒有這款」與「查詢壞了」。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home

from .checks import catalog_rows, reviews_rows
from .names import fold, tokens

URL_FIELDS = ("evidence_url",)

#: `--composition` 要印的欄位。每一個都另外印「這是誰說的」——
#: 一個沒有出處的成分欄位，跟讀過實物標籤的長得一模一樣。
COMPOSITION_FIELDS = (
    "first_ingredient", "water_first", "ingredient_count", "peppers", "pepper_ordinal",
    "pepper_form", "acidifier", "fermented", "thickener", "oil_type", "sweetener",
    "preservative", "colorant", "umami_adds", "allergens", "has_capsaicin_extract",
    "manufacturer_name", "manufacturer_location", "is_copacked",
    "sodium_per_100g", "sugar_per_100g", "calories_per_100g", "fat_per_100g",
    "carbs_per_100g", "protein_per_100g",
    "organic_certified", "non_gmo_verified", "kosher", "gluten_free_claim", "vegan_claim",
    "composition_disagreement", "comp_rules_version")

#: `--heat` 要印的五層。**沒有一個叫 heat_shu**——那個數字沒有人量過。
HEAT_FIELDS = (
    "shu_lab", "lab_method", "tested_on", "coa_url",
    "heat_ceiling_shu", "heat_ceiling_basis", "has_capsaicin_extract",
    "heat_rank", "heat_rank_ci_low", "heat_rank_ci_high", "heat_rank_facts",
    "heat_shu_claims", "heat_shu_claim_count", "heat_shu_disagreement",
    "heat_band_label", "brand_line_rank", "heat_rules_version")


def _score(row: dict[str, str], needle: str) -> tuple[int, int]:
    """比對強度。完全相同 > 前綴 > 包含；同分時來源多的排前面。"""
    key = f"{row.get('brand_key', '')} {row.get('product_key', '')}"
    product = row.get("product_key", "")
    if needle == product or needle == f"{row.get('brand_key', '')}-{product}":
        rank = 3
    elif product.startswith(needle) or key.startswith(needle):
        rank = 2
    elif needle in key:
        rank = 1
    else:
        rank = 0
    return rank, int(row.get("source_count") or 0)


def search(rows: list[dict[str, str]], text: str, all_matches: bool = False
           ) -> list[dict[str, str]]:
    """預設回**一列**：最像的那一列。

    比對規則刻意保守，所以同一款醬在總表上可能有好幾列（不同條碼、品牌欄寫法不一樣）。
    那是資料層正確的樣子——**過度合併事後看不出來，所以寧可不合併**。
    但查詢端不該把這個內部狀態丟給人：問一個名字就該得到一個答案，
    其餘長得像的列在 `duplicate_of_candidates` 欄位裡看得到，
    指令列也會在下面提一行「另外還有幾列長得很像」。
    """
    found = _search_all(rows, text)
    return found if all_matches else found[:1]


def _search_all(rows: list[dict[str, str]], text: str) -> list[dict[str, str]]:
    needle = fold(text)
    if not needle:
        return []
    scored = [(s, r) for r in rows if (s := _score(r, needle))[0] > 0]
    if not scored:
        # 退一步：逐詞比對（"aardvark" 也該找得到 "Secret Aardvark Habanero"）
        words = tokens(needle)
        scored = [((1, int(r.get("source_count") or 0)), r) for r in rows
                  if all(w in f"{r.get('brand_key', '')}-{r.get('product_key', '')}"
                         for w in words)]
    best = max((s[0] for s, _ in scored), default=0)
    return [r for s, r in sorted(scored, key=lambda x: (-x[0][0], -x[0][1], x[1]["entity_id"]))
            if s[0] == best]


def verdicts_for(rows: list[dict[str, str]], entity_id: str) -> list[dict[str, str]]:
    found = [r for r in rows if r.get("sauce_entity_id") == entity_id]
    return sorted(found, key=lambda r: (r.get("published_at") or "", r.get("verdict_id") or ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.query")
    ap.add_argument("text")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--reviews", action="store_true", help="一併列出這款醬的所有評語")
    ap.add_argument("--composition", action="store_true",
                    help="列出結構化成分／營養，以及每個欄位是誰說的")
    ap.add_argument("--heat", action="store_true",
                    help="列出辣度五層（含互相矛盾的宣稱）")
    ap.add_argument("--references", action="store_true",
                    help="列出評過這款醬的彙整型文章連結")
    ap.add_argument("--all", action="store_true", help="列出所有長得像的列，不只最像的那一列")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    home = Home.resolve(ns.home)
    all_rows = catalog_rows(home, ns.rules)
    hits = search(all_rows, ns.text, all_matches=ns.all)
    near = len(_search_all(all_rows, ns.text)) - len(hits)

    payload: dict[str, Any] = {"query": ns.text, "rows": len(hits),
                               "similar_rows_not_shown": near, "results": []}
    for row in hits:
        item = {k: row.get(k, "") for k in
                ("entity_id", "brand", "product", "variant", "gtin", "heat_shu",
                 "us_availability", "evidence_url", "sources", "source_count",
                 "corroboration", "duplicate_candidate", "review_count", "review_outlets")}
        if ns.composition:
            item["composition"] = {k: row.get(k, "") for k in COMPOSITION_FIELDS}
            item["composition_sources"] = {
                k: row.get(f"{k}_source", "") for k in COMPOSITION_FIELDS
                if row.get(f"{k}_source")}
        if ns.heat:
            item["heat"] = {k: row.get(k, "") for k in HEAT_FIELDS}
        if ns.references:
            item["references"] = [
                r for r in (row.get("references") or "").split(" | ") if r]
            item["reference_outlets"] = row.get("reference_outlets", "")
        if ns.reviews:
            item["verdicts"] = [
                {k: v.get(k, "") for k in ("outlet", "published_at", "stance", "score_raw",
                                           "quote", "url")}
                for v in verdicts_for(reviews_rows(home, ns.rules), row["entity_id"])]
        payload["results"].append(item)

    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0

    if not hits:
        print(f'查無「{ns.text}」（0 列）')
        return 0
    for item in payload["results"]:
        print(f"{item['brand']} — {item['product']}"
              + (f" [{item['variant']}]" if item["variant"] else ""))
        print(f"  entity_id      {item['entity_id']}")
        print(f"  可購性         {item['us_availability']}")
        print(f"  出處           {item['evidence_url'] or '（無）'}")
        print(f"  來源           {item['sources']}（{item['source_count']} 個，"
              f"{item['corroboration']}）")
        if item.get("gtin"):
            print(f"  GTIN           {item['gtin']}")
        if item.get("heat_shu"):
            print(f"  標榜 SHU       {item['heat_shu']}")
        if item.get("duplicate_candidate") in ("True", "true", True):
            print("  ⚠ 這一列有長得很像的鄰居（duplicate_candidate），沒有合併")
        if ns.composition:
            comp = item.get("composition") or {}
            print("  成分／營養")
            for key, value in comp.items():
                if value in ("", None, "False", False):
                    continue
                src = (item.get("composition_sources") or {}).get(key, "")
                print(f"    {key:<26} {value}" + (f"   ← {src}" if src else ""))
            if not any(v not in ("", None, "False", False) for v in comp.values()):
                print("    （沒有成分資料——沒有標籤照片也沒有 FDC 的成分表）")
        if ns.heat:
            heat = item.get("heat") or {}
            print("  辣度（五層並存，沒有單一 SHU）")
            for key, value in heat.items():
                if value in ("", None):
                    continue
                print(f"    {key:<26} {value}")
            if heat.get("heat_ceiling_shu") == "unbounded":
                print("    ⚠ 含辣椒萃取物，上界無意義——萃取物可以拉到任意辣度")
            if not heat.get("heat_rank"):
                print("    （沒有 heat_rank：排序事實少於兩筆，不給點估計）")
        if ns.references:
            refs = item.get("references") or []
            print(f"  出處（{len(refs)} 篇彙整型評比）")
            for ref in refs:
                print(f"    {ref}")
            if not refs:
                print("    （沒有：沒有任何一篇一次評很多款的文章提到它）")
        if ns.reviews:
            verdicts = item.get("verdicts") or []
            print(f"  專業評語       {len(verdicts)} 筆")
            for v in verdicts:
                print(f"    [{v['published_at'] or '日期不明'}] {v['outlet']} · {v['stance']}"
                      + (f" · {v['score_raw']}" if v["score_raw"] else ""))
                print(f"      「{v['quote']}」")
                print(f"      {v['url']}")
        print()
    if near:
        print(f"（總表上另有 {near} 列長得很像但沒有合併；加 --all 看全部）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
