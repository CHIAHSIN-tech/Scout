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


def products_url(domain: str, page: int) -> str:
    base = domain if domain.startswith("http") else f"https://{domain}"
    return f"{base.rstrip('/')}/products.json?limit={PAGE_SIZE}&page={page}"


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


def to_events(domain: str, payload: dict[str, Any], observed_at: str) -> list[Event]:
    """一頁 products.json → 事件。只留通過辣醬規則的那些（理由記在 payload 裡）。"""
    base = domain if domain.startswith("http") else f"https://{domain}"
    out: list[Event] = []
    for p in payload.get("products") or []:
        title = str(p.get("title") or "").strip()
        if not title:
            continue
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
        out.append(harvest.product_event(
            source=SOURCE, key=key, title=title,
            brand=str(p.get("vendor") or "").strip(), url=url,
            observed_at=observed_at, gtin=_barcode(p),
            us_availability="retail_listing" if _available(p) else "unknown",
            payload={"store_domain": _host(domain), "handle": handle,
                     "product_type": p.get("product_type"), "tags": p.get("tags"),
                     "published_at": p.get("published_at"), "variants": variants,
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
        events.extend(to_events(domain, payload, observed_at))
        pages += 1
        if len(items) < PAGE_SIZE:
            break
    return {"domain": _host(domain), "pages": pages, "events": events,
            "kept": len(events), "reason": reason}


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
