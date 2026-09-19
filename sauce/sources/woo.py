"""WooCommerce 的公開 Store API（`?rest_route=/wc/store/products`）。

不是 Shopify 的那一部分長尾在這裡。Store API 是 WooCommerce 給前端用的公開端點，
不需要金鑰、不是後台 API。規矩與 Shopify 那支相同：照 robots、照速率、抓不到就跳過。
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from evdb.schema import Event

from .. import harvest
from ..net import Fetcher
from . import filters

SOURCE = "woo"
PAGE_SIZE = 100
MAX_PAGES = 15


def products_url(domain: str, page: int) -> str:
    base = domain if domain.startswith("http") else f"https://{domain}"
    return (f"{base.rstrip('/')}/?rest_route=/wc/store/products"
            f"&per_page={PAGE_SIZE}&page={page}")


def _host(domain: str) -> str:
    return domain.replace("https://", "").replace("http://", "").strip("/").lower()


def _categories(product: dict[str, Any]) -> str:
    return " ".join(str((c or {}).get("name", "")) for c in product.get("categories") or [])


def to_events(domain: str, payload: list[dict[str, Any]], observed_at: str) -> list[Event]:
    out: list[Event] = []
    for p in payload or []:
        title = str((p or {}).get("name") or "").strip()
        if not title:
            continue
        desc = str(p.get("short_description") or p.get("description") or "")
        verdict = filters.classify(title, "", _categories(p), desc)
        if not verdict["keep"]:
            continue
        key = f"{harvest.contract.DOMAIN}-{_host(domain)}-{p.get('id')}"
        out.append(harvest.product_event(
            source=SOURCE, key=key, title=title, brand="",
            url=str(p.get("permalink") or ""), observed_at=observed_at,
            gtin=str(p.get("sku") or ""),
            us_availability="retail_listing" if p.get("is_in_stock") else "unknown",
            payload={"store_domain": _host(domain), "product_id": p.get("id"),
                     "categories": _categories(p),
                     "price": ((p.get("prices") or {}).get("price")),
                     "filter_reason": verdict["reason"], "filter_matched": verdict["matched"],
                     "filter_version": verdict["filter_version"]}))
    return out


def harvest_store(fetcher: Fetcher, domain: str, snapshot: harvest.Snapshot,
                  observed_at: str) -> dict[str, Any]:
    events: list[Event] = []
    pages, reason = 0, ""
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
        if not isinstance(payload, list) or not payload:
            break
        snapshot.write(SOURCE, f"{_host(domain).replace('/', '_')}-p{page}.json", payload)
        events.extend(to_events(domain, payload, observed_at))
        pages += 1
        if len(payload) < PAGE_SIZE:
            break
    return {"domain": _host(domain), "pages": pages, "events": events,
            "kept": len(events), "reason": reason}


def harvest_all(fetcher: Fetcher, domains: Iterable[str], snapshot: harvest.Snapshot,
                observed_at: str, log: Any = None) -> dict[str, Any]:
    stores, events = [], []
    for domain in domains:
        try:
            got = harvest_store(fetcher, domain, snapshot, observed_at)
        except Exception as exc:
            got = {"domain": _host(domain), "pages": 0, "events": [], "kept": 0,
                   "reason": f"{type(exc).__name__}: {exc}"}
        events.extend(got.pop("events"))
        stores.append(got)
        if log:
            print(f"  woo {got['domain']:<38} kept={got['kept']:<5} pages={got['pages']} "
                  f"{got['reason']}", file=log, flush=True)
    return {"source": SOURCE, "stores": stores,
            "stores_ok": sum(1 for s in stores if s["pages"]), "events": events,
            "kept": len(events)}
