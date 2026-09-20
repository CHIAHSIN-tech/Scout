"""成分與營養的結構化（規則 `sauce-comp-1`）。**這一步不准有任何模型。**

    python -m sauce.composition --home .evdb --rules sauce-comp-1

## 為什麼這裡不能有模型

模型負責把**照片變成文字**（`sauce/labelread.py`）。文字變成 `fermented`、`acidifier`、
`has_capsaicin_extract` 這些欄位是**規則**的工作。混在一起的代價是：

- 同一段文字跑兩次會得到兩個答案——欄位不可重現；
- 半年後沒有人回答得出「這個 `fermented=true` 是誰說的」；
- 規則錯了可以改規則重算，模型錯了只能重跑而且結果還是會飄。

A42 用 `git grep` 擋住這個檔引用任何模型相關的東西，並驗連跑兩次輸出雜湊相同。

## 三層來源，優先序固定，而且不一致時兩個值都留

1. `label_photo`——實物標籤的逐字轉錄。**最準**，因為那是包裝上真的印著的字。
2. `fdc`——廠商報給 USDA 的成分表與營養值。
3. `storefront_text`——商品頁的描述。最弱，行銷文案混在裡面。

照片與 FDC 都有值而且不一致時，**兩個值都保留**並把欄位名記進 `composition_disagreement`。
自動擇一等於替日後的分析做了一個沒有人驗證過的決定（A43）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from evdb.home import Home, now_iso
from evdb.schema import Event, IngestPath
from evdb.spool import Spool
from evdb.store import Store

from . import contract
from .names import fold

#: 版本 2：只有「長得像成分表」的文字才解析（見 looks_like_ingredients）。
#: 版本 1 把商品標題也當成分表，`first_ingredient` 會是「Habanero Hot Sauce」這種假值。
#: **同一個版本號必須對應同一套規則**，所以規則改了就換號，舊事件留著不覆寫。
RULES_VERSION = "sauce-comp-2"
OUT_DIR = Path(__file__).resolve().parent.parent / "state" / "composition"

SOURCE_PRIORITY = ("label_photo", "fdc", "storefront_text")

# ---------------------------------------------------------------- 詞表（有版本）

PEPPERS = ("habanero", "jalapeno", "jalapeño", "serrano", "cayenne", "chipotle", "ancho",
           "guajillo", "arbol", "poblano", "scorpion", "reaper", "ghost pepper",
           "bhut jolokia", "scotch bonnet", "datil", "fresno", "pequin", "piquin",
           "rocoto", "aji", "tabasco pepper", "calabrian", "aleppo", "shishito", "hatch",
           "anaheim", "pasilla", "mulato", "cascabel", "trinidad", "naga", "fatalii",
           "carolina reaper", "thai chili", "bird's eye", "red pepper", "green chile",
           "red chile", "chile pepper", "chili pepper", "peppers", "chiles", "chilies")

ACIDIFIERS = ("vinegar", "acetic acid", "citric acid", "lactic acid", "malic acid",
              "lime juice", "lemon juice", "tamarind")
FERMENT_MARKERS = ("fermented", "aged", "cultured", "culture", "koji", "brine",
                   "lacto-fermented", "mash")
THICKENERS = ("xanthan", "guar", "pectin", "starch", "arrowroot", "carrageenan",
              "cellulose", "tapioca")
OILS = ("olive oil", "canola oil", "soybean oil", "sunflower oil", "safflower oil",
        "sesame oil", "avocado oil", "coconut oil", "vegetable oil", "grapeseed oil")
SWEETENERS = ("sugar", "cane sugar", "honey", "agave", "molasses", "syrup", "fructose",
              "glucose", "dextrose", "sucralose", "stevia", "erythritol")
PRESERVATIVES = ("sodium benzoate", "potassium sorbate", "sodium citrate", "ascorbic acid",
                 "erythorbate", "edta", "calcium chloride", "bisulfite")
COLORANTS = ("caramel color", "annatto", "achiote", "red 40", "yellow 5", "turmeric",
             "paprika extract")
UMAMI = ("soy sauce", "fish sauce", "anchovy", "miso", "worcestershire", "yeast extract",
         "monosodium glutamate", "msg", "mushroom", "bonito", "kelp")
ALLERGENS = ("soy", "wheat", "milk", "egg", "fish", "shellfish", "peanut", "tree nut",
             "sesame", "gluten")
EXTRACT_MARKERS = ("oleoresin", "capsicum extract", "pepper extract", "capsaicin",
                   "chili extract", "capsaicin extract")

CLAIMS = {
    "organic_certified": ("usda organic", "certified organic", "organic"),
    "non_gmo_verified": ("non-gmo project", "non gmo", "non-gmo"),
    "kosher": ("kosher", "ou kosher", "star-k"),
    "halal": ("halal",),
    "gluten_free_claim": ("gluten free", "gluten-free"),
    "vegan_claim": ("vegan",),
}

_SPLIT = re.compile(r",(?![^(\[]*[)\]])")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MFR = re.compile(
    r"(?:manufactured|made|produced|packed|distributed|bottled)\s+(?:by|for)\s*[:\-]?\s*"
    r"([^,.;]{3,60})(?:,\s*([^.;]{3,60}))?", re.I)


def _has(text: str, needles: Iterable[str]) -> str:
    low = f" {re.sub(r'[^a-z0-9%]+', ' ', str(text or '').lower()).strip()} "
    for n in needles:
        if f" {re.sub(r'[^a-z0-9%]+', ' ', n.lower()).strip()} " in low:
            return n
    return ""


def split_ingredients(text: str) -> list[str]:
    """成分表 → 逐項。括號裡的逗號不切（`spices (cumin, oregano)` 是一項）。"""
    body = str(text or "")
    body = re.sub(r"^\s*ingredients?\s*[:\-]\s*", "", body, flags=re.I)
    body = body.split("CONTAINS")[0].split("Contains:")[0]
    parts = [p.strip(" .;·*") for p in _SPLIT.split(body)]
    return [p for p in parts if 1 < len(p) <= 120]


def derive_fields(ingredients_text: str) -> dict[str, Any]:
    """成分表原文 → 結構化欄位。純函式：同樣的輸入永遠得到同樣的輸出。"""
    items = split_ingredients(ingredients_text)
    lowered = [i.lower() for i in items]
    peppers = [i for i in items if _has(i, PEPPERS)]
    pepper_ordinal = next((n for n, i in enumerate(lowered, start=1) if _has(i, PEPPERS)), 0)
    pct = _PCT.search(ingredients_text or "")
    claims = {name: bool(_has(ingredients_text, words)) for name, words in CLAIMS.items()}
    return {
        "ingredient_list_raw": str(ingredients_text or "").strip()[:2000],
        "ingredient_count": len(items),
        "first_ingredient": items[0] if items else "",
        "water_first": bool(items) and lowered[0].startswith(("water", "filtered water")),
        "peppers": peppers,
        "pepper_count": len(peppers),
        "pepper_ordinal": pepper_ordinal,
        "pepper_form": ("mash" if _has(ingredients_text, ("mash",)) else
                        "puree" if _has(ingredients_text, ("puree", "purée")) else
                        "dried" if _has(ingredients_text, ("dried", "dehydrated", "powder"))
                        else "whole_or_unspecified" if peppers else ""),
        "pepper_pct_declared": pct.group(1) if pct else "",
        "acidifier": _has(ingredients_text, ACIDIFIERS),
        "fermented": bool(_has(ingredients_text, FERMENT_MARKERS)),
        "thickener": _has(ingredients_text, THICKENERS),
        "oil_type": _has(ingredients_text, OILS),
        "sweetener": _has(ingredients_text, SWEETENERS),
        "preservative": _has(ingredients_text, PRESERVATIVES),
        "colorant": _has(ingredients_text, COLORANTS),
        "umami_adds": _has(ingredients_text, UMAMI),
        "allergens": [a for a in ALLERGENS if _has(ingredients_text, (a,))],
        "has_capsaicin_extract": bool(_has(ingredients_text, EXTRACT_MARKERS)),
        **claims,
    }


def derive_manufacturer(text: str) -> dict[str, str]:
    """「Manufactured by X, City ST」這種句子。抓不到就留空，不猜。"""
    m = _MFR.search(str(text or ""))
    if not m:
        return {"manufacturer_name": "", "manufacturer_location": "", "is_copacked": ""}
    name = (m.group(1) or "").strip()
    where = (m.group(2) or "").strip()
    made_for = bool(re.search(r"(?:manufactured|made|produced|packed)\s+for", text or "",
                              re.I))
    return {"manufacturer_name": name[:80], "manufacturer_location": where[:80],
            # 「made FOR X」＝ 有人代工；「made BY X」＝ 自己做。
            # 這是標籤上唯一一個直接指向代工關係的字眼。
            "is_copacked": "true" if made_for else "false"}


NUTRIENT_FIELDS = {"calories_kcal": "calories_per_100g", "protein_g": "protein_per_100g",
                   "fat_g": "fat_per_100g", "carbs_g": "carbs_per_100g",
                   "sugars_g": "sugar_per_100g", "sodium_mg": "sodium_per_100g"}


def _nutrition(payload: dict[str, Any]) -> dict[str, Any]:
    nutrients = payload.get("nutrients") or {}
    per_100g = nutrients.get("per_100g") if isinstance(nutrients, dict) else {}
    out: dict[str, Any] = {}
    for src, dst in NUTRIENT_FIELDS.items():
        value = (per_100g or {}).get(src)
        out[dst] = value if isinstance(value, (int, float)) else ""
    out["declared_serving_size_g"] = payload.get("serving_size", "")
    out["household_serving_fulltext"] = payload.get("household_serving_fulltext", "")
    return out


# ---------------------------------------------------------------- 合併三層來源

def collect(events: list[Event]) -> dict[str, dict[str, Any]]:
    """每個 sauce 實體收齊三層的原始文字與營養值。"""
    obs_to_sauce: dict[str, str] = {}
    sauce_of_gtin: dict[str, str] = {}
    for ev in events:
        if ev.event_type != contract.LINK_EVENT:
            continue
        if ev.payload.get("matcher_version") != contract.MATCHER_VERSION:
            continue
        for r in ev.related:
            if r["role"] == "observation":
                obs_to_sauce[r["entity_id"]] = ev.entity_id
        gtin = str(ev.payload.get("gtin") or "")
        if gtin:
            sauce_of_gtin.setdefault(gtin, ev.entity_id)

    bundle: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.event_type == contract.EV_PRODUCT:
            sid = obs_to_sauce.get(ev.entity_id)
            if not sid:
                continue
            slot = bundle.setdefault(sid, {})
            if ev.source == "fdc":
                slot["fdc_text"] = str(ev.payload.get("ingredients") or "")
                slot["fdc_nutrition"] = _nutrition(ev.payload)
                slot["fdc_ref"] = ev.event_id
            elif ev.source in ("shopify", "woo"):
                slot.setdefault("store_text", str(ev.payload.get("title") or ""))
                slot.setdefault("store_ref", ev.event_id)
        elif ev.event_type == contract.EV_LABEL_READ:
            gtin = str(ev.payload.get("gtin") or "")
            sid = sauce_of_gtin.get(gtin)
            if not sid or str(ev.payload.get("panel_kind")) != "ingredients":
                continue
            slot = bundle.setdefault(sid, {})
            slot["label_text"] = str(ev.payload.get("transcript") or "")
            slot["label_ref"] = ev.event_id
    return bundle


def looks_like_ingredients(text: str) -> bool:
    """這段文字是不是一份成分表。

    商品標題（`Habanero Hot Sauce`）也是「文字」，但把它當成分表解析出來的
    `first_ingredient = "Habanero Hot Sauce"` 是假的——它會混在真正讀過標籤的列裡面，
    而且從欄位上看不出差別。所以門檻是**長得像清單**：有 INGREDIENTS 這個字，
    或至少兩個逗號分隔的項目。
    """
    body = str(text or "").strip()
    if len(body) < 12:
        return False
    if re.search(r"ingredients?", body, re.I):
        return True
    return len(split_ingredients(body)) >= 3


def compose(sauce_id: str, slot: dict[str, Any], rules_version: str) -> dict[str, Any]:
    """三層合併成一列。**不一致時兩個值都留**（A43）。"""
    label_text = slot.get("label_text") or ""
    fdc_text = slot.get("fdc_text") or ""
    store_text = slot.get("store_text") or ""
    # 只有長得像成分表的文字才拿來解析（見 looks_like_ingredients）
    if not looks_like_ingredients(store_text):
        store_text = ""
    if not looks_like_ingredients(fdc_text):
        fdc_text = ""

    chosen_text, source, ref = (
        (label_text, "label_photo", slot.get("label_ref", "")) if label_text.strip() else
        (fdc_text, "fdc", slot.get("fdc_ref", "")) if fdc_text.strip() else
        (store_text, "storefront_text", slot.get("store_ref", "")))

    row: dict[str, Any] = {"entity_id": sauce_id, "comp_rules_version": rules_version}
    fields = derive_fields(chosen_text)
    for key, value in fields.items():
        row[key] = value
        row[f"{key}_source"] = source if chosen_text.strip() else ""
        row[f"{key}_source_ref"] = ref if chosen_text.strip() else ""
    row.update(derive_manufacturer(chosen_text))
    nutrition = slot.get("fdc_nutrition") or {}
    for key, value in nutrition.items():
        row[key] = value
        row[f"{key}_source"] = "fdc" if value != "" else ""
        row[f"{key}_source_ref"] = slot.get("fdc_ref", "") if value != "" else ""

    # 照片與 FDC 都有成分表時才比得起來。兩邊都算一次，欄位值不同的記下來。
    disagreement: list[str] = []
    if label_text.strip() and fdc_text.strip():
        other = derive_fields(fdc_text)
        for key in fields:
            if key in ("ingredient_list_raw",):
                continue
            if fields[key] != other[key]:
                disagreement.append(key)
                row[f"{key}_fdc_value"] = other[key]     # 兩個值都留，不自動擇一
    row["composition_disagreement"] = sorted(disagreement)
    row["composition_sources_available"] = sorted(
        s for s, t in (("label_photo", label_text), ("fdc", fdc_text),
                       ("storefront_text", store_text)) if t.strip())
    return row


def to_event(row: dict[str, Any], observed_at: str) -> Event:
    return Event(
        entity_type="sauce_composition", entity_id=row["entity_id"],
        event_type=contract.EV_COMPOSITION, observed_at=observed_at, source="evdb",
        source_record_id=row["entity_id"], ingest_path=IngestPath.BULK.value,
        payload=row)


def run(home: Home, rules_version: str = RULES_VERSION,
        out_dir: Path | None = None) -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    bundle = collect(events)
    rows = [compose(sid, slot, rules_version) for sid, slot in sorted(bundle.items())]
    rows = [r for r in rows if r.get("composition_sources_available")]

    observed_at = now_iso()
    Spool(home, tag="sauce-composition").write([to_event(r, observed_at) for r in rows])

    # A42：輸出檔要決定性。排序顯式、鍵排序、不放時間戳。
    out = Path(out_dir or OUT_DIR) / rules_version
    out.mkdir(parents=True, exist_ok=True)
    path = out / "composition.jsonl"
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True, default=str) + "\n"
                   for r in rows)
    path.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    (out / "manifest.json").write_text(
        json.dumps({"rules_version": rules_version, "rows": len(rows),
                    "rows_sha256": digest}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    by_source: dict[str, int] = {}
    for r in rows:
        key = r.get("first_ingredient_source") or "(none)"
        by_source[key] = by_source.get(key, 0) + 1
    return {"rows": len(rows), "rows_sha256": digest, "path": str(path),
            "by_primary_source": by_source,
            "with_disagreement": sum(1 for r in rows if r["composition_disagreement"])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.composition")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default=RULES_VERSION)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    out = run(Home.resolve(ns.home), ns.rules, Path(ns.out) if ns.out else None)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
