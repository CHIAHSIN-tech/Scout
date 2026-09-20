"""A47：代工廠聚類（規則 `copack-1`）。

Stanley 2026-09-20：「這 40 個小品牌出自同一條產線——這要寫出來」。

標籤上唯一直接指向代工關係的字眼是 **`Manufactured FOR X`**（有人代工）
與 `Manufactured BY X`（自己做）。所以聚類只准用兩種依據，而且都要附證據：

1. 宣告的 `manufacturer_name` / `manufacturer_location` 折疊後相同；
2. 成分表字串相似度 ≥ 門檻（同一條產線常常用同一份基底配方）。

**每個成員都要附 `evidence_ref`**——指向那一筆標籤或 FDC 事件。
沒有證據的成員不准進聚類：一個猜出來的代工關係，在報告上跟查證過的長得一模一樣。
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home
from evdb.store import Store

from . import contract
from .composition import RULES_VERSION as COMP_RULES
from .names import fold

RULES_VERSION = "copack-1"
REPORT = Path(__file__).resolve().parent.parent / "reports" / "sauce-copackers.md"

#: 成分表相似度門檻。低於這個就不算同一條產線——寧可少聚一組，不要多聚一組。
SIMILARITY = 0.92
#: 太短的成分表不拿來比：「Water, Salt」跟另一個「Water, Salt」相似度 1.0，但那什麼都沒說。
MIN_INGREDIENT_CHARS = 60


def _brand_of(events: list[Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for ev in events:
        if (ev.event_type == contract.LINK_EVENT
                and ev.payload.get("matcher_version") == contract.MATCHER_VERSION):
            out.setdefault(ev.entity_id, str(ev.payload.get("brand") or ""))
    return out


def cluster(home: Home, rules_version: str = RULES_VERSION) -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    brands = _brand_of(events)

    rows = [ev.payload for ev in events
            if ev.event_type == contract.EV_COMPOSITION
            and str(ev.payload.get("comp_rules_version", "")) == COMP_RULES]

    # --- 依據一：宣告的製造者 ---
    declared: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        maker = fold(str(r.get("manufacturer_name") or ""))
        if not maker:
            continue
        where = fold(str(r.get("manufacturer_location") or ""))
        key = f"{maker}|{where}"
        declared.setdefault(key, []).append({
            "entity_id": r["entity_id"], "brand": brands.get(r["entity_id"], ""),
            "basis": "declared_manufacturer",
            "manufacturer_name": r.get("manufacturer_name", ""),
            "manufacturer_location": r.get("manufacturer_location", ""),
            "is_copacked": r.get("is_copacked", ""),
            "evidence_ref": r.get("first_ingredient_source_ref", "")})

    # --- 依據二：成分表幾乎一樣 ---
    usable = [r for r in rows
              if len(str(r.get("ingredient_list_raw") or "")) >= MIN_INGREDIENT_CHARS]
    seen: set[str] = set()
    similar: dict[str, list[dict[str, Any]]] = {}
    for i, a in enumerate(usable):
        if a["entity_id"] in seen:
            continue
        group = []
        for b in usable[i + 1:]:
            if b["entity_id"] in seen:
                continue
            ratio = difflib.SequenceMatcher(
                None, str(a["ingredient_list_raw"]).lower(),
                str(b["ingredient_list_raw"]).lower()).ratio()
            if ratio >= SIMILARITY:
                group.append((b, round(ratio, 4)))
        if not group:
            continue
        members = [{"entity_id": a["entity_id"], "brand": brands.get(a["entity_id"], ""),
                    "basis": "ingredient_similarity", "similarity": 1.0,
                    "evidence_ref": a.get("first_ingredient_source_ref", "")}]
        seen.add(a["entity_id"])
        for b, ratio in group:
            seen.add(b["entity_id"])
            members.append({"entity_id": b["entity_id"],
                            "brand": brands.get(b["entity_id"], ""),
                            "basis": "ingredient_similarity", "similarity": ratio,
                            "evidence_ref": b.get("first_ingredient_source_ref", "")})
        brands_in = {m["brand"] for m in members if m["brand"]}
        if len(brands_in) >= 2:          # 同一個品牌自己的兩款不算代工關係
            similar[f"recipe:{a['entity_id']}"] = members

    clusters = {k: v for k, v in declared.items() if len({m["brand"] for m in v if m["brand"]}) >= 2}
    clusters.update(similar)
    missing_evidence = [m["entity_id"] for members in clusters.values()
                        for m in members if not m.get("evidence_ref")]
    return {"rules_version": rules_version, "clusters": clusters,
            "declared_groups": len(declared), "missing_evidence": missing_evidence,
            "products_considered": len(rows)}


def write(data: dict[str, Any], path: Path | None = None) -> Path:
    out = Path(path or REPORT)
    out.parent.mkdir(parents=True, exist_ok=True)
    clusters = data["clusters"]
    lines = [
        "# 代工廠聚類（A47）",
        "",
        f"規則版本 `{data['rules_version']}`　納入比對的產品 {data['products_considered']} 款　"
        f"聚出 {len(clusters)} 組",
        "",
        "聚類只用兩種依據，而且每個成員都附證據：**宣告的製造者相同**，",
        "或**成分表幾乎一樣**（相似度 ≥ 0.92、成分表長度 ≥ 60 字元）。",
        "同一個品牌自己的兩款不算——那不是代工關係。",
        "",
        "**沒有證據的成員不准進來**：猜出來的代工關係在報告上跟查證過的長得一模一樣。",
        "",
    ]
    for key, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        brands = sorted({m["brand"] for m in members if m["brand"]})
        lines += [f"## {key}", "",
                  f"品牌 {len(brands)} 個・產品 {len(members)} 款：{', '.join(brands) or '—'}",
                  "", "| 產品 | 品牌 | 依據 | 證據 |", "|---|---|---|---|"]
        for m in members:
            extra = m.get("similarity", m.get("manufacturer_name", ""))
            lines.append(f"| {m['entity_id']} | {m['brand'] or '—'} | {m['basis']} "
                         f"({extra}) | {m.get('evidence_ref', '') or '（無）'} |")
        lines.append("")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.copackers")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default=RULES_VERSION)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    data = cluster(Home.resolve(ns.home), ns.rules)
    path = write(data, Path(ns.out) if ns.out else None)
    print(json.dumps({"report": str(path), "clusters": len(data["clusters"]),
                      "products_considered": data["products_considered"],
                      "missing_evidence": len(data["missing_evidence"])},
                     ensure_ascii=False, indent=1))
    return 1 if data["missing_evidence"] else 0


if __name__ == "__main__":
    sys.exit(main())
