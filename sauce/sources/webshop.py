"""第三條抓取路徑：既不是 Shopify 也不是 WooCommerce 的店。

## 為什麼要有這一條（見 DECISIONS D17）

先前把一批產品標成「買不到」，Stanley 要求逐款單獨搜。搜完的結果是
**六成以上其實買得到**——問題不在資料，在抓取端：我們只會講 Shopify 的
`/products.json` 與 Woo 的 Store API 兩種話。用搜尋找到的 13 間店裡，
**9 間兩種都不是**，於是它們連「這間店存在」都沒有被記下來——
`storefronts.py` 的 `_inspect_store` 認不出平台就回 `platform=""`，整筆丟掉。

所以這裡要修的其實是兩件事，而第二件比第一件重要：

1. 讀得到那些店的商品（能讀多少算多少）；
2. **讀不到的時候，要把「讀不到」記下來**。今天的行為是靜靜地什麼都不留，
   於是「我們沒去過」跟「那裡沒有辣醬」在資料上長得一模一樣。

## 讀法：只讀站方自己宣告的結構化資料

依序試三種，一種都沒有就記 `structured=none` 並停手：

1. **JSON-LD**（`<script type="application/ld+json">` 裡的 `@type: Product`）——
   schema.org 的標準寫法，BigCommerce／Squarespace／多數自訂購物車都會輸出。
2. **microdata**（`itemprop="price"` 那一組）。
3. **OpenGraph 的商品欄位**（`product:price:amount`）。

**不做的事**：不自己猜 HTML 裡哪一段是價錢。價錢猜錯比沒有價錢糟——
一個猜出來的 `$12.99` 在表上跟站方自己宣告的長得一模一樣。
猜不到就留空，`us_availability` 記 `retail_listing`（有貨架、沒價錢），
這在 D18 已經談定是可以接受的。
"""
from __future__ import annotations

import html
import json
import re
from typing import Any, Iterable
from urllib.parse import urlsplit

from evdb.schema import Event

from .. import admit, harvest
from ..net import Fetcher
from . import filters

SOURCE = "webshop"

#: sitemap 裡長得像商品頁的網址
_PRODUCT_PATH = re.compile(r"/(?:products?|shop|store|item|p)/[^/]+/?$", re.I)

#: 明顯不是商品頁的。用排除法是因為**有的店根本沒有 `/products/` 這種路徑**——
#: hotsauceworld.com 的商品頁是 `/hsw1133ca.html`，用正面表列會整站漏掉。
#: 所以第一輪先照正面表列找；一個都找不到時才退回這份排除清單，
#: 留下的網址一樣要過辣醬過濾器才會變成事件。
_NOT_A_PRODUCT = re.compile(
    r"/(?:cart|checkout|account|login|register|search|blog|news|press|about|contact|"
    r"faq|policies|policy|terms|privacy|shipping|returns|wholesale|gift[-_]?card|"
    r"collections?|categor|tag|author|feed|sitemap)\b", re.I)
_NOT_A_PAGE = re.compile(r"\.(?:jpg|jpeg|png|gif|webp|svg|pdf|css|js|zip|xml)$", re.I)
MAX_PRODUCT_URLS = 120      # 一間店最多看幾頁商品
MAX_SITEMAP_URLS = 4000     # 一份 sitemap 最多展開幾個網址

_LDJSON = re.compile(
    rb'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)
_META = re.compile(rb'<meta[^>]+>', re.I)
_ATTR = re.compile(rb'(property|name|itemprop|content)\s*=\s*["\']([^"\']*)["\']', re.I)
_ITEMPROP = re.compile(
    rb'itemprop=["\'](price|priceCurrency|availability|gtin13|gtin12|gtin14|name|brand)["\']'
    rb'[^>]*?content=["\']([^"\']*)["\']', re.I)
_TITLE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
_TAG = re.compile(rb"<[^>]+>")

_IN_STOCK = ("instock", "in_stock", "limitedavailability", "onlineonly", "preorder")


def _txt(raw: bytes) -> str:
    return html.unescape(_TAG.sub(b" ", raw or b"").decode("utf-8", "replace")).strip()


def _flatten(node: Any) -> Iterable[dict[str, Any]]:
    """JSON-LD 可以是一個物件、一個陣列，或塞在 `@graph` 裡。三種都攤平。"""
    if isinstance(node, list):
        for item in node:
            yield from _flatten(item)
    elif isinstance(node, dict):
        yield node
        for key in ("@graph", "mainEntity", "itemListElement"):
            if key in node:
                yield from _flatten(node[key])


def _is_product(node: dict[str, Any]) -> bool:
    t = node.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(str(x or "").lower() == "product" for x in types)


def _first_offer(node: dict[str, Any]) -> dict[str, Any]:
    offers = node.get("offers")
    for candidate in (_flatten(offers) if offers is not None else []):
        if isinstance(candidate, dict) and ("price" in candidate or "lowPrice" in candidate):
            return candidate
    return {}


def from_jsonld(body: bytes) -> dict[str, Any]:
    """站方自己宣告的 schema.org Product。抓不到就回空 dict。"""
    for chunk in _LDJSON.findall(body or b""):
        try:
            data = json.loads(chunk.decode("utf-8", "replace").strip())
        except ValueError:
            continue
        for node in _flatten(data):
            if not isinstance(node, dict) or not _is_product(node):
                continue
            offer = _first_offer(node)
            brand = node.get("brand")
            if isinstance(brand, dict):
                brand = brand.get("name")
            price = offer.get("price", offer.get("lowPrice", ""))
            return {
                "structured": "json-ld",
                "title": str(node.get("name") or "").strip(),
                "brand": str(brand or "").strip(),
                "description": str(node.get("description") or "")[:1000],
                "gtin": str(node.get("gtin13") or node.get("gtin12")
                            or node.get("gtin14") or node.get("gtin") or "").strip(),
                "sku": str(node.get("sku") or "").strip(),
                "price": str(price or "").strip(),
                "price_currency": str(offer.get("priceCurrency") or "").strip(),
                "availability": str(offer.get("availability") or "").strip(),
            }
    return {}


def from_microdata(body: bytes) -> dict[str, Any]:
    found = {k.decode().lower(): v.decode("utf-8", "replace")
             for k, v in _ITEMPROP.findall(body or b"")}
    if "price" not in found:
        return {}
    return {"structured": "microdata", "title": found.get("name", ""),
            "brand": found.get("brand", ""), "description": "",
            "gtin": found.get("gtin13") or found.get("gtin12") or found.get("gtin14") or "",
            "sku": "", "price": found.get("price", ""),
            "price_currency": found.get("pricecurrency", ""),
            "availability": found.get("availability", "")}


def from_opengraph(body: bytes) -> dict[str, Any]:
    props: dict[str, str] = {}
    for tag in _META.findall(body or b""):
        attrs = {k.decode().lower(): v.decode("utf-8", "replace")
                 for k, v in _ATTR.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key.startswith(("og:", "product:")):
            props[key] = attrs.get("content", "")
    if "product:price:amount" not in props:
        return {}
    return {"structured": "opengraph", "title": props.get("og:title", ""),
            "brand": props.get("product:brand", ""),
            "description": props.get("og:description", "")[:1000], "gtin": "", "sku": "",
            "price": props.get("product:price:amount", ""),
            "price_currency": props.get("product:price:currency", ""),
            "availability": props.get("product:availability", "")}


def read_product_page(body: bytes) -> dict[str, Any]:
    """三種讀法依序試。**都讀不到就回 `structured: "none"`，不猜。**"""
    for reader in (from_jsonld, from_microdata, from_opengraph):
        got = reader(body)
        if got.get("title") or got.get("price"):
            return got
    m = _TITLE.search(body or b"")
    return {"structured": "none", "title": _txt(m.group(1)) if m else "",
            "brand": "", "description": "", "gtin": "", "sku": "",
            "price": "", "price_currency": "", "availability": ""}


def product_urls(fetcher: Fetcher, origin: str) -> list[str]:
    """sitemap 裡長得像商品頁的網址。沒有 sitemap 就回空——**不爬全站**。"""
    out: list[str] = []
    seen: set[str] = set()
    for root in admit.sitemap_urls(fetcher, origin):
        got = fetcher.get(root, accept="application/xml,text/xml,*/*")
        if not got.ok:
            continue
        locs = [m.decode("utf-8", "replace") for m in admit._LOC.findall(got.body or b"")]
        # 子 sitemap 再展一層（商品常常被切成 sitemap_products_1.xml）
        for child in [u for u in locs if u.endswith(".xml")][:admit.SITEMAP_FANOUT]:
            sub = fetcher.get(child, accept="application/xml,text/xml,*/*")
            if sub.ok:
                locs += [m.decode("utf-8", "replace")
                         for m in admit._LOC.findall(sub.body or b"")]
            if len(locs) > MAX_SITEMAP_URLS:
                break
        fallback: list[str] = []
        for url in locs:
            if url.endswith(".xml") or url in seen:
                continue
            path = urlsplit(url).path
            if _PRODUCT_PATH.search(path):
                seen.add(url)
                out.append(url)
            elif (path not in ("", "/") and not _NOT_A_PRODUCT.search(path)
                  and not _NOT_A_PAGE.search(path)):
                fallback.append(url)
            if len(out) >= MAX_PRODUCT_URLS:
                return out
        if not out and fallback:
            # 平路徑的店（商品頁就是 /hsw1133ca.html）。留下的網址一樣要過辣醬過濾器。
            out = fallback[:MAX_PRODUCT_URLS]
    return out


_OUT_OF_STOCK = ("outofstock", "soldout", "discontinued", "backorder")


def _availability(raw: str) -> str:
    """站方沒講存貨狀態時，**商品頁本身就是貨架**（D18：有貨架就算數，價錢可以沒有）。

    所以三種結果：站方說有貨 → `retail_listing`；站方說沒貨 → `unknown`；
    **站方什麼都沒說 → 還是 `retail_listing`**，因為這一頁是從那間店自己的 sitemap
    走進來的，它列在架上這件事不需要再被誰確認一次。
    """
    low = str(raw or "").lower().rsplit("/", 1)[-1].replace(" ", "").replace("_", "")
    if any(tok in low for tok in _OUT_OF_STOCK):
        return "unknown"
    return "retail_listing"


def to_event(domain: str, url: str, read: dict[str, Any], observed_at: str) -> Event | None:
    title = str(read.get("title") or "").strip()
    if not title:
        return None
    verdict = filters.classify(title, "", "", str(read.get("description") or ""))
    if not verdict["keep"]:
        return None
    host = domain.replace("https://", "").replace("http://", "").strip("/").lower()
    slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
    return harvest.product_event(
        source=SOURCE, key=f"{harvest.contract.DOMAIN}-{host}-{slug}", title=title,
        brand=str(read.get("brand") or "").strip(), url=url, observed_at=observed_at,
        gtin=str(read.get("gtin") or "").strip(),
        us_availability=_availability(read.get("availability", "")),
        payload={"store_domain": host, "handle": slug,
                 "price": str(read.get("price") or ""),
                 "price_currency": str(read.get("price_currency") or ""),
                 "buy_url": url,
                 # 這一欄是這條路徑的重點：讀法說得出來，才知道這個價錢是站方宣告的
                 "structured": str(read.get("structured") or "none"),
                 "sku": str(read.get("sku") or ""),
                 "filter_reason": verdict["reason"], "filter_matched": verdict["matched"],
                 "filter_version": verdict["filter_version"]})


def harvest_store(fetcher: Fetcher, domain: str, snapshot: harvest.Snapshot,
                  observed_at: str, limit: int = MAX_PRODUCT_URLS) -> dict[str, Any]:
    origin = domain if domain.startswith("http") else f"https://{domain}"
    urls = product_urls(fetcher, origin)
    events: list[Event] = []
    by_reader: dict[str, int] = {}
    for url in urls[:limit]:
        got = fetcher.get(url, accept="text/html,*/*")
        if not got.ok:
            continue
        read = read_product_page(got.body)
        by_reader[read["structured"]] = by_reader.get(read["structured"], 0) + 1
        ev = to_event(domain, url, read, observed_at)
        if ev is not None:
            events.append(ev)
    # 「找到幾頁、讀得懂幾頁、留下幾筆」三個數字都要留：
    # 只記最後一個的話，「沒去過」跟「去過但讀不懂」會長得一樣。
    snapshot.write(SOURCE, f"{_safe(domain)}.json",
                   {"domain": domain, "product_urls": len(urls),
                    "by_reader": by_reader, "kept": len(events)})
    return {"domain": domain, "product_urls": len(urls), "by_reader": by_reader,
            "events": events, "kept": len(events)}


def _safe(domain: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "_", str(domain or "").lower())


def harvest_all(fetcher: Fetcher, domains: Iterable[str], snapshot: harvest.Snapshot,
                observed_at: str, log: Any = None) -> dict[str, Any]:
    events: list[Event] = []
    stores: list[dict[str, Any]] = []
    for domain in domains:
        got = harvest_store(fetcher, domain, snapshot, observed_at)
        events.extend(got.pop("events"))
        stores.append(got)
        if log:
            print(f"    webshop {domain}: 商品頁 {got['product_urls']}、"
                  f"留下 {got['kept']}、讀法 {got['by_reader']}", file=log, flush=True)
    unreadable = [s["domain"] for s in stores
                  if s["product_urls"] and not any(k != "none" for k in s["by_reader"])]
    return {"source": SOURCE, "events": events, "kept": len(events),
            "stores": len(stores), "unreadable_stores": unreadable, "reason": ""}
