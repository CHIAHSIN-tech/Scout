"""規則式抽取：來源本身已經把品牌與品名分開的那些，不需要模型。

FDC、OFF、Shopify 的每一筆都帶著結構化的品牌欄位（`brand_name` / `brands` / `vendor`），
品名就是標題去掉品牌之後剩下的那一段。這是**純規則、可以機械驗證**的工作，
Stanley 自己的分流標準寫得很清楚：不需要模型判斷的事就不要燒模型。
五千筆走模型是四個小時加一次人工冷啟動審查，走規則是兩秒。

模型留給真的需要判斷的地方：
- 只有一串名字、沒有品牌欄位的提及（Wikipedia 的表格、得獎名錄）；
- 評論正文 → 立場與代表句（`sauce.extract` 的 `sauce-review-verdict`）。

## 產出仍然是 `sauce.extraction.parsed`

兩種抽取器產生同一種事件，差別寫在 payload 的 `extractor` 欄位裡；
`model_id` 記的是「這一筆是誰抽的」——模型抽的就是模型 id，規則抽的就是規則版本。
A10 第一層要的是「每一筆都說得出它是哪個版本產生的」，這一點兩邊都做得到，
而把規則假裝成模型（或反過來）才是真的失去可追溯性。
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from evdb.home import now_iso
from evdb.schema import Event, IngestPath

from . import contract
from .names import contains_key, fold, normalize_whitespace

#: 版本 2：多帶價格、幣別、購買連結、是否有貨（Stanley 2026-09-19 的硬條件）。
#: 版本一改，同一筆觀察就會被重新抽一次——舊的 parsed 事件留著（append-only），
#: 新的帶著新版本號，視圖看得出哪一筆是誰產生的。
VERSION = "rule:sauce-structured-2"

#: 有結構化品牌欄位的來源。其餘走模型。
STRUCTURED_SOURCES = ("fdc", "off", "shopify", "woo")

#: 規格／包裝：這些是 variant，不是產品名的一部分。
_VARIANT = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:fl\s*)?(?:oz|ounce|ounces|ml|l|g|kg|lb|lbs)"
    r"|\d+\s*(?:pk|pack|ct|count|bottles?))\b", re.I)
_TRAILING_JUNK = re.compile(r"[\s,\-–—|]+$")


def _dedupe_segments(text: str) -> str:
    """FDC 的品名是逗號分段的，而且後面幾段常常只是前面那段的重複或子集。

    例：`HOT & SPICY MADRAS CURRY SAUCE, HOT & SPICY, MADRAS CURRY`
    三段講的是同一件事。全部留著會讓產品名長得像資料庫欄位而不是人話，
    而「名字讀不讀得懂」沒有任何自動檢查蓋得到（所以 A11 的試樣要人看）。

    只**丟掉**重複的段，不改寫任何一個字——留下來的仍然是來源字串的子字串。
    """
    parts = [p.strip() for p in text.split(",")]
    kept: list[str] = []
    for part in parts:
        if not part:
            continue
        low = part.lower()
        if any(low in k.lower() for k in kept):
            continue
        kept = [k for k in kept if k.lower() not in low] + [part]
    return ", ".join(kept)


def _strip_brand(title: str, brand: str) -> str:
    """把標題開頭（或結尾）的品牌名拿掉，剩下的就是產品名。拿不掉就原樣保留。"""
    if not brand.strip():
        return title
    pattern = re.compile(r"^\s*" + re.escape(brand.strip()) + r"[\s,:\-–—]*", re.I)
    stripped = pattern.sub("", title)
    if stripped.strip() and stripped != title:
        return stripped
    pattern = re.compile(r"[\s,:\-–—]*" + re.escape(brand.strip()) + r"\s*$", re.I)
    stripped = pattern.sub("", title)
    return stripped if stripped.strip() else title


def parse(title: str, brand: str) -> dict[str, str]:
    """(標題, 品牌) → {brand, product, variant}。名稱一律取自來源字串，不重寫。"""
    title = normalize_whitespace(title)
    brand = normalize_whitespace(brand)
    variants = [m.group(0) for m in _VARIANT.finditer(title)]
    product = _strip_brand(title, brand)
    for v in variants:
        product = product.replace(v, " ")
    product = _dedupe_segments(_TRAILING_JUNK.sub("", normalize_whitespace(product)))
    if not product.strip():
        product = title
    variant = " ".join(variants)[:60]
    if fold(variant) == fold(product):
        variant = ""
    return {"brand": brand, "product": product, "variant": variant}


def parsed_event(obs: Event, parsed: dict[str, str], observed_at: str) -> Event:
    return Event(
        entity_type="sauce_extraction", entity_id=obs.entity_id,
        event_type=contract.EV_PARSED, observed_at=observed_at, source=obs.source,
        source_record_id=obs.event_id, source_url=obs.source_url,
        ingest_path=IngestPath.BULK.value,
        payload={"observation_event_id": obs.event_id,
                 "raw_title": str(obs.payload.get("title") or obs.payload.get("name") or ""),
                 "raw_brand": str(obs.payload.get("brand") or ""),
                 "brand": parsed["brand"], "product": parsed["product"],
                 "variant": parsed["variant"],
                 "heat_shu": str(obs.payload.get("claimed_shu") or ""),
                 "heat_basis": "source_claim" if obs.payload.get("claimed_shu") else "",
                 "us_availability": str(obs.payload.get("us_availability") or "unknown"),
                 "evidence_url": obs.source_url or "",
                 # 「有地方在賣、而且有價錢」是 Stanley 2026-09-19 加的硬條件，
                 # 所以價格要一路帶到視圖，不能停在觀察層
                 "price": str(obs.payload.get("price") or ""),
                 "price_currency": str(obs.payload.get("price_currency") or ""),
                 "buy_url": str(obs.payload.get("buy_url") or obs.source_url or ""),
                 "in_stock": bool(obs.payload.get("in_stock")),
                 "store_domain": str(obs.payload.get("store_domain") or ""),
                 "extractor": VERSION, "confidence": "rule",
                 "model_id": VERSION, "prompt_version": VERSION})


def run(events: Iterable[Event], sources: tuple[str, ...] = STRUCTURED_SOURCES,
        observed_at: str | None = None) -> dict[str, Any]:
    """對結構化來源的觀察跑一次規則抽取。已經有 parsed 的不重跑（冪等）。"""
    events = list(events)
    observed_at = observed_at or now_iso()
    # 「抽過了」要連版本一起看：規則升版之後同一筆觀察要重抽，否則新欄位永遠補不上。
    done = {(str(ev.payload.get("observation_event_id") or ""),
             str(ev.payload.get("extractor") or ""))
            for ev in events if ev.event_type == contract.EV_PARSED}
    out: list[Event] = []
    skipped_no_key = 0
    for ev in events:
        if ev.event_type not in (contract.EV_PRODUCT, contract.EV_MENTION):
            continue
        if ev.source not in sources or (ev.event_id, VERSION) in done:
            continue
        title = str(ev.payload.get("title") or ev.payload.get("name") or "")
        brand = str(ev.payload.get("brand") or "")
        if not title.strip():
            continue
        parsed = parse(title, brand)
        source_text = f"{title} {brand}"
        # 自己驗自己：抽出來的鍵必須仍然是來源字串的連續詞串（A10 第二層的同一條規則）。
        if not contains_key(source_text, fold(parsed["product"])):
            skipped_no_key += 1
            continue
        if parsed["brand"] and not contains_key(source_text, fold(parsed["brand"])):
            parsed["brand"] = ""
        out.append(parsed_event(ev, parsed, observed_at))
    return {"events": out, "written": len(out), "skipped_no_key": skipped_no_key,
            "extractor": VERSION}
