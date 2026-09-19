"""Shopify 商店的公開商品端點（`/products.json`）。

獨立辣醬品牌與專賣零售幾乎都開在 Shopify 上，這是長尾的主力來源：
FDC 與 OFF 收得到有 GTIN、上架連鎖通路的產品，收不到一年做兩百瓶、只在自家網站賣的那些。

`/products.json` 是 Shopify 自己公開的端點（不是後台 API、不需要金鑰、不是繞過），
一頁最多 250 筆，用 `page` 翻頁。仍然照 robots.txt 與速率下限走（`sauce.net`）。

一間店抓不到就記下來跳過，不讓整批停下來——一個來源失效不得汙染其他來源。
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

from evdb.schema import Event, Precision

from .. import harvest
from ..net import Fetcher
from . import filters

SOURCE = "shopify"
PAGE_SIZE = 250
MAX_PAGES = 12                      # 3,000 筆／店；辣醬店沒有比這更大的
_TAG = re.compile(r"<[^>]+>")

#: **一定要帶 `currency=USD`。**
#:
#: Shopify Markets 會依「請求來源的國家」在地化價格。從台灣打過去，Heatonist 的
#: JANG 回的是 `452.00`（TWD）；帶了 `currency=USD` 才是 `14.00`。
#: 兩個數字都「是價格」，差別在事後從欄位上完全看不出來——一份宣稱美國售價的表格，
#: 裡面混著新台幣，而且只有懂得換算的人會發現。
CURRENCY = "USD"

#: B2B／整箱／周邊：有價格，但不是「一瓶辣醬多少錢」
_NOT_A_BOTTLE = re.compile(
    r"\bcase of\b|\bwholesale\b|\bbulk\b|\bb2b\b|\bgallon\b|\bholster\b|\bpallet\b", re.I)


def products_url(domain: str, page: int) -> str:
    base = domain if domain.startswith("http") else f"https://{domain}"
    return (f"{base.rstrip('/')}/products.json?limit={PAGE_SIZE}&page={page}"
            f"&currency={CURRENCY}")


def meta_url(domain: str) -> str:
    base = domain if domain.startswith("http") else f"https://{domain}"
    return f"{base.rstrip('/')}/meta.json"


def shop_meta(fetcher: Fetcher, domain: str) -> dict[str, Any]:
    """店家自己公開的 `/meta.json`：國家、幣別、店名。

    這是「這間店在美國賣東西」最便宜也最直接的證據——比用網域字尾猜準得多。
    拿不到就回空 dict，呼叫端把可購性標成 unknown，不要猜。
    """
    got = fetcher.get(meta_url(domain), accept="application/json")
    if not got.ok:
        return {}
    try:
        data = json.loads(got.body.decode("utf-8", "replace"))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def looks_like_shopify(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("products"), list)


def _text(html: str) -> str:
    return _TAG.sub(" ", str(html or ""))[:4000]


def _barcode(product: dict[str, Any]) -> str:
    for v in product.get("variants") or []:
        code = str((v or {}).get("barcode") or "").strip()
        if code:
            return code
    return ""


def _available(product: dict[str, Any]) -> bool:
    return any((v or {}).get("available") for v in product.get("variants") or [])


def _cheapest(product: dict[str, Any]) -> tuple[str, str]:
    """(價格, 那個規格的名稱)。取**最便宜的有貨規格**——那最接近「一瓶多少錢」。

    沒有價格就回空字串。**不要用 0 當「沒有價格」**：0 是一個價格
    （贈品、樣品），跟「這個欄位沒有值」是兩件事。
    """
    best: tuple[float, str, str] | None = None
    for v in product.get("variants") or []:
        raw = str((v or {}).get("price") or "").strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        name = str((v or {}).get("title") or "")
        if _NOT_A_BOTTLE.search(name):
            continue
        if best is None or value < best[0]:
            best = (value, raw, name)
    return (best[1], best[2]) if best else ("", "")


def to_events(domain: str, payload: dict[str, Any], observed_at: str,
              meta: dict[str, Any] | None = None) -> list[Event]:
    """一頁 products.json → 事件。只留通過辣醬規則的那些（理由記在 payload 裡）。"""
    base = domain if domain.startswith("http") else f"https://{domain}"
    meta = meta or {}
    currency = str(meta.get("currency") or CURRENCY)
    shop_country = str(meta.get("country") or "")
    out: list[Event] = []
    for p in payload.get("products") or []:
        title = str(p.get("title") or "").strip()
        if not title:
            continue
        if _NOT_A_BOTTLE.search(title):
            continue          # 整箱、批發、周邊：有價格但不是一瓶辣醬的價格
        verdict = filters.classify(title, p.get("product_type"), p.get("tags"),
                                   _text(p.get("body_html")))
        if not verdict["keep"]:
            continue
        handle = str(p.get("handle") or p.get("id") or "")
        url = f"{base.rstrip('/')}/products/{handle}"
        key = f"{harvest.contract.DOMAIN}-{_host(domain)}-{handle}"
        variants = [{"sku": (v or {}).get("sku"), "price": (v or {}).get("price"),
                     "title": (v or {}).get("title"), "available": (v or {}).get("available")}
                    for v in (p.get("variants") or [])[:10]]
        price, price_variant = _cheapest(p)
        out.append(harvest.product_event(
            source=SOURCE, key=key, title=title,
            brand=str(p.get("vendor") or "").strip(), url=url,
            observed_at=observed_at, gtin=_barcode(p),
            us_availability="retail_listing" if _available(p) else "unknown",
            payload={"store_domain": _host(domain), "handle": handle,
                     "product_type": p.get("product_type"), "tags": p.get("tags"),
                     "published_at": p.get("published_at"), "variants": variants,
                     "price": price, "price_currency": currency if price else "",
                     "price_variant": price_variant, "price_requested_currency": CURRENCY,
                     "buy_url": url, "in_stock": _available(p),
                     "shop_country": shop_country,
                     "filter_reason": verdict["reason"], "filter_matched": verdict["matched"],
                     "filter_version": verdict["filter_version"]}))
    return out


def _host(domain: str) -> str:
    return domain.replace("https://", "").replace("http://", "").strip("/").lower()


def harvest_store(fetcher: Fetcher, domain: str, snapshot: harvest.Snapshot,
                  observed_at: str) -> dict[str, Any]:
    """抓一間店的全部商品。回傳摘要（含失敗原因），事件放在 `events` 欄位。"""
    events: list[Event] = []
    pages = 0
    reason = ""
    meta = shop_meta(fetcher, domain)
    for page in range(1, MAX_PAGES + 1):
        got = fetcher.get(products_url(domain, page), accept="application/json")
        if not got.ok:
            reason = reason or got.reason
            break
        try:
            payload = json.loads(got.body.decode("utf-8", "replace"))
        except ValueError:
            reason = reason or "not_json"
            break
        if not looks_like_shopify(payload):
            reason = reason or "not_shopify"
            break
        items = payload.get("products") or []
        if not items:
            break
        snapshot.write(SOURCE, f"{_host(domain).replace('/', '_')}-p{page}.json", payload)
        events.extend(to_events(domain, payload, observed_at, meta))
        pages += 1
        if len(items) < PAGE_SIZE:
            break
    return {"domain": _host(domain), "pages": pages, "events": events,
            "kept": len(events), "reason": reason,
            "shop_country": meta.get("country", ""), "shop_currency": meta.get("currency", "")}


def harvest_all(fetcher: Fetcher, domains: Iterable[str], snapshot: harvest.Snapshot,
                observed_at: str, log: Any = None) -> dict[str, Any]:
    stores, events = [], []
    for domain in domains:
        try:
            got = harvest_store(fetcher, domain, snapshot, observed_at)
        except Exception as exc:              # 一間店掛掉不能讓整批停下來
            got = {"domain": _host(domain), "pages": 0, "events": [], "kept": 0,
                   "reason": f"{type(exc).__name__}: {exc}"}
        events.extend(got.pop("events"))
        stores.append(got)
        if log:
            print(f"  shopify {got['domain']:<34} kept={got['kept']:<5} "
                  f"pages={got['pages']} {got['reason']}", file=log, flush=True)
    return {"source": SOURCE, "stores": stores,
            "stores_ok": sum(1 for s in stores if s["pages"]), "events": events,
            "kept": len(events)}
