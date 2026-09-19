"""實體解析：把觀察與評論連到實體。連結本身也是事件，不改寫任何既有事件。

## 兩條規則，兩種保守

**`sauce-match-1`（產品）** 只在下列任一成立時把兩筆觀察併成同一款醬：

1. 兩筆的 GTIN-14 相同；或
2. 折疊後的 `brand_key` 與 `product_key` **兩者都**完全相同。

其餘一律各自成列。`product_key` 相同但 `brand_key` 不同、或編輯距離 ≤ 2 的，
在視圖上標 `duplicate_candidate` 並把對造寫進 `duplicate_of_candidates`，**不合併**。

為什麼這麼保守：過度合併事後看不出來，而且無法還原。把兩個不同品牌的同名產品併成一列之後，
總表顯示「一列、兩個來源」，看起來比實際更有佐證——那比漏收還糟，因為漏收至少是空白，
過度合併是假的佐證。

**`sauce-reviewlink-1`（評論）** 更保守：評論裡的 `sauce_name_raw` 折疊後要與某款醬的
`product_key` 完全相同，而且品牌對得上（`brand_key` 相同，或評論正文裡出現那個品牌名），
才建立連結。連不上的**留在庫裡當孤兒**（A27），不猜、不模糊比對——
猜錯的代價是把 A 的評價掛到 B 身上，而那在庫裡看起來和正確連結一模一樣。

## 連結事件為什麼叫 `entity.linked`

evdb 核心的 `evdb orphans` 是硬寫這個字串找連結的。改成 `sauce.entity.linked`
會讓每一筆觀察都變成孤兒，A27 直接破功。見 `contract` 的模組說明。
"""
from __future__ import annotations

from typing import Any, Iterable

from evdb.home import Home
from evdb.schema import Event, IngestPath
from evdb.store import Store

from . import contract
from .names import VERSION as NAMES_VERSION
from .names import fold, gtin14, normalize_whitespace

MATCHER_VERSION = contract.MATCHER_VERSION
REVIEW_LINK_VERSION = contract.REVIEW_LINK_VERSION


class Canonical:
    """GTIN 相同的幾個 (brand, product) 併成同一個實體。

    用 union-find，代表元取字典序最小的那一個——**不是先看到的那一個**。
    先看到誰取決於事件的讀取順序，那會讓同一份事件跑兩次得到不同的視圖（A31 會抓到）。
    """

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, key: str) -> str:
        self.parent.setdefault(key, key)
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        lo, hi = (ra, rb) if ra < rb else (rb, ra)
        self.parent[hi] = lo


def parsed_rows(events: Iterable[Event]) -> list[dict[str, Any]]:
    """抽取結果 → 比對要用的欄位。名稱在這裡才折疊（抽取層存的是原字）。"""
    by_obs: dict[str, Event] = {}
    for ev in events:
        if ev.event_type in (contract.EV_PRODUCT, contract.EV_MENTION):
            by_obs[ev.event_id] = ev
    rows: list[dict[str, Any]] = []
    for ev in events:
        if ev.event_type != contract.EV_PARSED:
            continue
        brand = str(ev.payload.get("brand") or "")
        product = str(ev.payload.get("product") or "")
        bkey, pkey = fold(brand), fold(product)
        if not pkey:
            continue                     # 產品名折不出鍵的，比對層不處理（留在庫裡）
        obs = by_obs.get(str(ev.payload.get("observation_event_id") or ""))
        rows.append({
            "parsed": ev, "observation": obs,
            "observation_entity_id": obs.entity_id if obs else ev.entity_id,
            "brand": brand, "product": product, "brand_key": bkey, "product_key": pkey,
            "gtin": gtin14(str((obs.payload if obs else {}).get("gtin") or "")),
            "sauce_id": contract.sauce_id(bkey, pkey),
        })
    return rows


def canonical_ids(rows: list[dict[str, Any]]) -> dict[str, str]:
    """GTIN 把不同的 (brand, product) 併起來；其餘各自獨立。"""
    canon = Canonical()
    by_gtin: dict[str, list[str]] = {}
    for row in rows:
        canon.find(row["sauce_id"])
        if row["gtin"]:
            by_gtin.setdefault(row["gtin"], []).append(row["sauce_id"])
    for ids in by_gtin.values():
        for other in ids[1:]:
            canon.union(ids[0], other)
    return {sid: canon.find(sid) for sid in canon.parent}


def link_events(events: Iterable[Event]) -> list[Event]:
    """每筆解析過的觀察產生一筆 `entity.linked`。"""
    rows = parsed_rows(list(events))
    canon = canonical_ids(rows)
    out: list[Event] = []
    for row in rows:
        sid = canon.get(row["sauce_id"], row["sauce_id"])
        parsed: Event = row["parsed"]
        related = [{"role": "observation", "entity_id": row["observation_entity_id"]},
                   {"role": "product", "entity_id": sid}]
        if row["brand_key"]:
            related.append({"role": "brand", "entity_id": contract.brand_id(row["brand_key"])})
        if row["gtin"]:
            related.append({"role": "gtin", "entity_id": contract.gtin_id(row["gtin"])})
        out.append(Event(
            entity_type="link", entity_id=sid, event_type=contract.LINK_EVENT,
            observed_at=parsed.observed_at, source=parsed.source,
            related=tuple(related),
            event_time=parsed.event_time, event_time_precision=parsed.event_time_precision,
            published_at=parsed.published_at, source_record_id=parsed.source_record_id,
            source_url=parsed.source_url, ingest_path=IngestPath.BULK.value,
            payload={"matcher_version": MATCHER_VERSION, "names_version": NAMES_VERSION,
                     "rule": "gtin" if row["gtin"] else "brand_key+product_key",
                     "brand_key": row["brand_key"], "product_key": row["product_key"],
                     "brand": row["brand"], "product": row["product"],
                     "gtin": row["gtin"],
                     "observation_event_id": row["parsed"].payload.get("observation_event_id"),
                     "observation_type": (row["observation"].event_type
                                          if row["observation"] else ""),
                     "us_availability": parsed.payload.get("us_availability", "unknown"),
                     "evidence_url": parsed.payload.get("evidence_url", ""),
                     "heat_shu": parsed.payload.get("heat_shu", ""),
                     "heat_basis": parsed.payload.get("heat_basis", ""),
                     "variant": parsed.payload.get("variant", ""),
                     "price": parsed.payload.get("price", ""),
                     "price_currency": parsed.payload.get("price_currency", ""),
                     "buy_url": parsed.payload.get("buy_url", ""),
                     "in_stock": parsed.payload.get("in_stock", False),
                     "store_domain": parsed.payload.get("store_domain", ""),
                     "prompt_version": parsed.payload.get("prompt_version", "")}))
    return out


# ---------------------------------------------------------------- 評論 → 產品

def _product_index(events: Iterable[Event]) -> dict[str, list[tuple[str, str]]]:
    """product_key → [(sauce_id, brand_key)]，由連結事件反推（不重算比對規則）。"""
    index: dict[str, list[tuple[str, str]]] = {}
    for ev in events:
        if ev.event_type != contract.LINK_EVENT:
            continue
        pkey = str(ev.payload.get("product_key") or "")
        if not pkey:
            continue
        pair = (ev.entity_id, str(ev.payload.get("brand_key") or ""))
        bucket = index.setdefault(pkey, [])
        if pair not in bucket:
            bucket.append(pair)
    return index


def review_link_events(events: Iterable[Event], home: Home | None = None) -> list[Event]:
    """verdict → 產品。連不上就不連（孤兒留在庫裡）。"""
    events = list(events)
    index = _product_index(events)
    bodies: dict[str, str] = {}
    if home is not None:
        for ev in events:
            if ev.event_type == contract.EV_REVIEW and ev.raw_ref:
                path = home.root / ev.raw_ref
                if path.exists():
                    bodies[str(ev.payload.get("review_id") or "")] = normalize_whitespace(
                        path.read_text(encoding="utf-8", errors="replace")).lower()

    out: list[Event] = []
    for ev in events:
        if ev.event_type != contract.EV_VERDICT:
            continue
        pkey = fold(str(ev.payload.get("sauce_name_raw") or ""))
        if not pkey:
            continue
        candidates = index.get(pkey) or []
        body = bodies.get(str(ev.payload.get("review_id") or ""), "")
        chosen: list[str] = []
        for sauce_id, brand_key in candidates:
            brand_words = brand_key.replace("-", " ")
            if not brand_key or (brand_words and brand_words in body):
                chosen.append(sauce_id)
        # 只有一個候選對得上才連。兩個以上代表這個名字在不同品牌下都存在，
        # 挑哪一個都是猜——猜錯之後在庫裡跟正確連結長得一模一樣。
        if len(chosen) != 1:
            continue
        out.append(Event(
            entity_type="link", entity_id=chosen[0], event_type=contract.LINK_EVENT,
            observed_at=ev.observed_at, source=ev.source,
            related=({"role": "review", "entity_id": _review_entity(ev)},
                     {"role": "verdict", "entity_id": ev.entity_id},
                     {"role": "product", "entity_id": chosen[0]}),
            event_time=ev.event_time, event_time_precision=ev.event_time_precision,
            published_at=ev.published_at, source_record_id=ev.source_record_id,
            source_url=ev.source_url, ingest_path=IngestPath.BULK.value,
            payload={"matcher_version": REVIEW_LINK_VERSION, "names_version": NAMES_VERSION,
                     "rule": "product_key+brand_in_body",
                     "review_id": ev.payload.get("review_id"),
                     "sauce_name_raw": ev.payload.get("sauce_name_raw"),
                     "product_key": pkey, "verdict_source_record_id": ev.source_record_id}))
    return out


def _review_entity(verdict: Event) -> str:
    for r in verdict.related:
        if r.get("role") == "review":
            return r["entity_id"]
    return verdict.entity_id


def run(home: Home) -> dict[str, Any]:
    """讀 store、算連結、寫回 spool。重跑只會再產生同樣的事件（同內容＝同 id）。"""
    from evdb.spool import Spool

    with Store(home, read_only=True) as store:
        events = store.all_events()
    product_links = link_events(events)
    review_links = review_link_events(events, home)
    written = Spool(home, tag="sauce-match").write(product_links + review_links)
    return {"parsed_rows": len(parsed_rows(events)), "product_links": len(product_links),
            "review_links": len(review_links), "written": written,
            "matcher_version": MATCHER_VERSION, "review_link_version": REVIEW_LINK_VERSION}
