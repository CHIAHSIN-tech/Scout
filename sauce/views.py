"""兩張衍生視圖：產品總表與評論表。

視圖只讀事件、不回頭問來源；規則版本不同就是不同的輸出目錄，舊版不覆寫。
同一份事件跑兩次，`rows_sha256` 必須一樣（A31）——所以這裡不准有任何依賴讀取順序、
時間戳或字典雜湊的東西，排序一律顯式。

    evdb --home .evdb derive sauce.views:build   --rules v1     # sauce_catalog
    evdb --home .evdb derive sauce.views:reviews --rules v1     # sauce_reviews

## 視圖是索引，不是語料本身

`quote` 是視圖裡唯一的長文字欄位，上限 500 字元（A28）。要看全文就拿 `review_id`
去 raw store 取。把正文放進視圖等於把第三方的著作一起放進每一份可分享的輸出，
那是一個「所有功能都正常」也看不出來的外流面。
"""
from __future__ import annotations

from typing import Any, Iterable

from evdb.schema import Event

from . import contract
from .names import VERSION as NAMES_VERSION

CATALOG_VIEW = "sauce_catalog"
REVIEWS_VIEW = "sauce_reviews"

#: 視圖裡的引文上限（A28）
QUOTE_MAX = 500

#: `duplicate_of_candidates` 最多列幾個鄰居（完整清單可由視圖重算）
DUPLICATE_SAMPLE = 5


def _availability(current: str, candidate: str) -> str:
    rank = contract.AVAILABILITY_RANK
    return candidate if rank.get(candidate, 0) > rank.get(current, 0) else current


def _edit_distance_le(a: str, b: str, limit: int = 2) -> bool:
    """只回答「距離是不是 ≤ limit」。不需要真的算出距離，長度差太多就直接否定。"""
    if abs(len(a) - len(b)) > limit:
        return False
    if a == b:
        return True
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (ca != cb)))
        if min(current) > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _duplicate_candidates(rows: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """可疑的重複：產品名相同但品牌不同，或整體鍵只差一兩個字元。**不合併，只標記。**"""
    out: dict[str, list[str]] = {}
    by_product: dict[str, list[str]] = {}
    by_block: dict[tuple[int, str], list[str]] = {}
    for eid, row in rows.items():
        by_product.setdefault(row["product_key"], []).append(eid)
        key = f"{row['brand_key']}|{row['product_key']}"
        by_block.setdefault((len(key) // 3, key[:3]), []).append(eid)

    def note(a: str, b: str) -> None:
        if a == b:
            return
        out.setdefault(a, [])
        if b not in out[a]:
            out[a].append(b)

    for ids in by_product.values():
        if len(ids) < 2:
            continue
        for a in ids:
            for b in ids:
                if a != b and rows[a]["brand_key"] != rows[b]["brand_key"]:
                    note(a, b)
    # 編輯距離只在同一個區塊內比。全表兩兩比是 O(n²)，而且比出來的那些跨區塊配對
    # 幾乎都是雜訊——差兩個字元的名字，前三個字元不會不一樣。
    for ids in by_block.values():
        if len(ids) < 2 or len(ids) > 200:
            continue
        for i, a in enumerate(ids):
            ka = f"{rows[a]['brand_key']}|{rows[a]['product_key']}"
            for b in ids[i + 1:]:
                kb = f"{rows[b]['brand_key']}|{rows[b]['product_key']}"
                if _edit_distance_le(ka, kb):
                    note(a, b)
                    note(b, a)
    return {k: sorted(v) for k, v in out.items()}


def build(events: list[Event], rules_version: str) -> list[dict[str, Any]]:
    """`sauce_catalog`：一列一款產品（不分瓶容量）。"""
    rows: dict[str, dict[str, Any]] = {}
    verdicts_by_sauce: dict[str, list[Event]] = {}
    seasons: dict[str, set[str]] = {}

    verdict_by_id: dict[str, Event] = {}
    for ev in events:
        if ev.event_type == contract.EV_VERDICT:
            verdict_by_id[str(ev.source_record_id or "")] = ev

    for ev in events:
        if ev.event_type != contract.LINK_EVENT:
            continue
        roles = {r["role"]: r["entity_id"] for r in ev.related}
        sid = roles.get("product") or ev.entity_id
        if ev.payload.get("matcher_version") == contract.REVIEW_LINK_VERSION:
            key = str(ev.payload.get("verdict_source_record_id") or "")
            if key in verdict_by_id:
                verdicts_by_sauce.setdefault(sid, []).append(verdict_by_id[key])
            continue

        row = rows.setdefault(sid, {
            "entity_id": sid, "brand_key": ev.payload.get("brand_key", ""),
            "brand": ev.payload.get("brand", ""),
            "product_key": ev.payload.get("product_key", ""),
            "product": ev.payload.get("product", ""),
            "variant": ev.payload.get("variant", ""), "gtin": ev.payload.get("gtin", ""),
            "heat_shu": ev.payload.get("heat_shu", ""),
            "heat_basis": ev.payload.get("heat_basis", ""),
            "us_availability": "unknown", "evidence_url": "",
            "price": "", "price_currency": "", "buy_url": "", "in_stock": False,
            "store_domain": "",
            "_sources": set(), "_tiers": set(), "_seasons": set(),
            "first_observed_at": ev.observed_at, "last_observed_at": ev.observed_at,
            "names_version": NAMES_VERSION,
            "matcher_version": ev.payload.get("matcher_version", ""),
            "prompt_version": ev.payload.get("prompt_version", ""),
        })
        row["_sources"].add(ev.source)
        row["_tiers"].add(contract.SOURCE_TIER.get(ev.source, "unknown"))
        row["first_observed_at"] = min(row["first_observed_at"], ev.observed_at)
        row["last_observed_at"] = max(row["last_observed_at"], ev.observed_at)
        for field in ("brand", "product", "variant", "gtin", "heat_shu", "heat_basis"):
            if not row[field] and ev.payload.get(field):
                row[field] = ev.payload[field]
        candidate = str(ev.payload.get("us_availability") or "unknown")
        best = _availability(row["us_availability"], candidate)
        if best != row["us_availability"]:
            row["us_availability"] = best
            row["evidence_url"] = str(ev.payload.get("evidence_url") or "")
        elif not row["evidence_url"] and ev.payload.get("evidence_url"):
            row["evidence_url"] = str(ev.payload["evidence_url"])
        # 價格：取**最低的有效報價**，並記下是哪一間店報的。
        # 同一款醬在三個貨架上有三個價錢是常態，視圖只留一個，但留的是哪一個要說得出來。
        offer = str(ev.payload.get("price") or "").strip()
        if offer:
            try:
                better = (not row["price"]) or float(offer) < float(row["price"])
            except ValueError:
                better = not row["price"]
            if better:
                row["price"] = offer
                row["price_currency"] = str(ev.payload.get("price_currency") or "")
                row["buy_url"] = str(ev.payload.get("buy_url") or "")
                row["store_domain"] = str(ev.payload.get("store_domain") or "")
            row["in_stock"] = bool(row["in_stock"] or ev.payload.get("in_stock"))
        if ev.source == "hotones":
            row["_seasons"].add(str(ev.payload.get("season") or ""))

    for ev in events:
        if ev.event_type == contract.EV_MENTION and ev.source == "hotones":
            seasons.setdefault(ev.entity_id, set()).add(str(ev.payload.get("season") or ""))

    dupes = _duplicate_candidates(rows)
    out: list[dict[str, Any]] = []
    for sid, row in rows.items():
        sources = sorted(row.pop("_sources"))
        tiers = sorted(row.pop("_tiers"))
        row_seasons = sorted(s for s in row.pop("_seasons") if s)
        verdicts = verdicts_by_sauce.get(sid, [])
        stances: dict[str, int] = {}
        outlets: set[str] = set()
        for v in verdicts:
            stances[str(v.payload.get("stance") or "")] = \
                stances.get(str(v.payload.get("stance") or ""), 0) + 1
            outlets.add(str(v.payload.get("outlet") or ""))
        row["sources"] = "|".join(sources)
        row["source_count"] = len(sources)
        row["tiers"] = "|".join(tiers)
        row["hotones_seasons"] = "|".join(row_seasons)
        near = dupes.get(sid, [])
        row["duplicate_candidate"] = sid in dupes
        row["duplicate_candidate_count"] = len(near)
        # 只列前幾個。視圖是索引不是資料——有些鍵會撞到上百個鄰居，整串寫進來會讓
        # 這一欄變成視圖裡最長的欄位（實測 776 字元，超過 A28 的 500 上限）。
        # 完整清單本來就可以從視圖自己重算，不需要存第二份。
        row["duplicate_of_candidates"] = "|".join(near[:DUPLICATE_SAMPLE])
        # 只有一個來源不代表錯，但無法判斷是真的——把這件事寫成欄位，
        # 不要在收錄階段替使用者決定（沿用 madb 的判準精神）。
        row["corroboration"] = ("multi_source" if len(sources) > 1 else
                                f"single_source:{sources[0]}" if sources else "no_source")
        row["review_count"] = len(verdicts)
        row["review_outlets"] = "|".join(sorted(o for o in outlets if o))
        row["review_stance_mix"] = "|".join(f"{k}={v}" for k, v in sorted(stances.items()) if k)
        row["rules_version"] = rules_version
        out.append(row)
    out.sort(key=lambda r: r["entity_id"])
    return out


def buyable(events: list[Event], rules_version: str) -> list[dict[str, Any]]:
    """`sauce_buyable`：**真的有地方在賣、而且有價錢**的那一份。

    Stanley 2026-09-19 的硬條件：「必須要是有地方在賣，有價錢的 Hot Sauce」。
    這跟 spec 的 NON_GOALS（「不追價格」）直接衝突，所以兩張表都留著、各自回答一個問題：

    - `sauce_catalog`（`build`）是**母體**：這個世界上有哪些辣醬。
      FDC 與 OFF 只有條碼、沒有貨架，但「這款存在過」對語料庫仍然有意義。
    - `sauce_buyable`（這一張）是**貨架**：現在去哪裡買、多少錢。
      沒有價格或沒有購買連結的列一律不在這裡。

    分成兩張而不是把母體砍掉，是因為砍掉之後就**再也回答不了「這款存不存在」**——
    而那正是漏收最難察覺的那一面。
    """
    def sellable(row: dict[str, Any]) -> bool:
        """「買得到」的判準是**有貨架**，不是有標價。

        Stanley 2026-09-20：「不需要必須有價錢，這只是買得到的驗證而已，
        如果某種原因「買得到但是沒價錢」成立的話，也是可以」。

        所以條件是「有人把它上架在賣」：有購買連結，而且可購性不是
        mention_only。價格有就存、沒有就留空——**留空跟填 0 是兩件事**。
        """
        if not str(row.get("buy_url") or "").strip():
            return False
        # 不拿「現在有沒有貨」當門檻：Hot Jawn 這一款實測就是上架、標價 $12、
        # 但當下缺貨——那仍然是「有地方在賣」。缺貨是 `in_stock` 那一欄的事。
        # 幣別不是 USD 代表那是別的國家的貨架；沒有價格則不評斷幣別。
        price = str(row.get("price") or "").strip()
        if price and str(row.get("price_currency") or "") != "USD":
            return False
        return True

    return [r for r in build(events, rules_version) if sellable(r)]


def reviews(events: list[Event], rules_version: str) -> list[dict[str, Any]]:
    """`sauce_reviews`：一列一筆 verdict。連不上產品的也留著（孤兒不丟）。"""
    published: dict[str, Event] = {}
    for ev in events:
        if ev.event_type == contract.EV_REVIEW:
            published[str(ev.payload.get("review_id") or "")] = ev

    linked: dict[str, str] = {}
    for ev in events:
        if (ev.event_type == contract.LINK_EVENT
                and ev.payload.get("matcher_version") == contract.REVIEW_LINK_VERSION):
            linked[str(ev.payload.get("verdict_source_record_id") or "")] = ev.entity_id

    names: dict[str, tuple[str, str]] = {}
    for ev in events:
        if (ev.event_type == contract.LINK_EVENT
                and ev.payload.get("matcher_version") == contract.MATCHER_VERSION):
            names.setdefault(ev.entity_id, (str(ev.payload.get("brand") or ""),
                                            str(ev.payload.get("product") or "")))

    out: list[dict[str, Any]] = []
    for ev in events:
        if ev.event_type != contract.EV_VERDICT:
            continue
        review = published.get(str(ev.payload.get("review_id") or ""))
        meta = review.payload if review else {}
        sid = linked.get(str(ev.source_record_id or ""), "")
        brand, product = names.get(sid, ("", ""))
        out.append({
            "verdict_id": str(ev.source_record_id or ""),
            "review_id": ev.payload.get("review_id", ""),
            "outlet": ev.payload.get("outlet", ""),
            "outlet_tier": meta.get("outlet_tier", ""),
            "outlet_conflict": meta.get("outlet_conflict_of_interest", ""),
            "url": ev.source_url or meta.get("url", ""),
            "published_at": meta.get("published_at", ""),
            "authors": "|".join(meta.get("authors") or []),
            "article_kind": meta.get("article_kind", ""),
            "disclosure": meta.get("disclosure", ""),
            "sauce_entity_id": sid,
            "sauce_name_raw": ev.payload.get("sauce_name_raw", ""),
            "brand": brand, "product": product,
            "stance": ev.payload.get("stance", ""),
            "score_raw": ev.payload.get("score_raw", ""),
            "score_scale": ev.payload.get("score_scale", ""),
            "score_norm": ev.payload.get("score_norm", ""),
            "rank_in_article": ev.payload.get("rank_in_article", ""),
            "of_total": ev.payload.get("of_total", ""),
            "quote": str(ev.payload.get("quote") or "")[:QUOTE_MAX],
            "descriptors": "|".join(str(d) for d in (ev.payload.get("descriptors") or [])),
            "modality": meta.get("modality", ""),
            "language": meta.get("language", ""),
            "link_rule_version": contract.REVIEW_LINK_VERSION if sid else "",
            "prompt_version": ev.payload.get("prompt_version", ""),
            "rules_version": rules_version,
        })
    out.sort(key=lambda r: (r["review_id"], r["verdict_id"]))
    return out
