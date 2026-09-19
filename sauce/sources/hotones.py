"""每季選醬名單。**完全不經影音平台。**

名單本身就是產品 metadata：每季十款、第幾棒、標榜多少 SHU。這份資料有兩個公開的
文字來源，兩個都不是影音網站：

1. **Heatonist 的 season pack 商品頁**——每一季的十瓶裝是一件商品，商品描述就是那一季的名單；
2. **編輯型報導**——白名單內的 outlet 每季都會寫一篇，名單在文章裡。

這一支只做第一種（商品頁）。第二種走評論層的一般流程，名單會以 verdict 的形式出現。

節目本身的影片、留言、字幕一律不碰（NON_GOALS）。
"""
from __future__ import annotations

import html
import json
import re
from typing import Any

from evdb.schema import Event

from .. import harvest
from ..net import Fetcher

SOURCE = "hotones"
STORE = "heatonist.com"

_SEASON = re.compile(r"season\s*(\d+)", re.I)
_TAGS = re.compile(r"<[^>]+>")
_LIST_ITEM = re.compile(r"<li\b[^>]*>(.*?)</li>", re.I | re.S)
_SHU = re.compile(r"([\d,]{3,})\s*(?:shu|scoville)", re.I)


def _text(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", raw or ""))).strip()


def season_of(title: str) -> str:
    m = _SEASON.search(title or "")
    return f"S{m.group(1)}" if m else ""


def is_season_pack(product: dict[str, Any]) -> bool:
    blob = f"{product.get('title', '')} {product.get('product_type', '')} {product.get('tags', '')}"
    return bool(_SEASON.search(blob)) and bool(re.search(r"pack|box|set|collection", blob, re.I))


def lineup_from(product: dict[str, Any]) -> list[dict[str, Any]]:
    """商品描述裡的那份名單。抓 <li>，抓不到就退回逐行切——版面每季都會改。"""
    body = product.get("body_html") or ""
    items = [_text(x) for x in _LIST_ITEM.findall(body)]
    if len(items) < 3:
        items = [_text(x) for x in re.split(r"<br\s*/?>|</p>", body)]
    out: list[dict[str, Any]] = []
    for n, raw in enumerate([i for i in items if 3 <= len(i) <= 160], start=1):
        shu = _SHU.search(raw)
        out.append({"position": n, "text": raw,
                    "claimed_shu": shu.group(1).replace(",", "") if shu else ""})
    return out[:12]


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                store: str = STORE, log: Any = None) -> dict[str, Any]:
    from . import shopify

    events: list[Event] = []
    seasons = 0
    for page in range(1, 6):
        got = fetcher.get(shopify.products_url(store, page), accept="application/json")
        if not got.ok:
            break
        try:
            payload = json.loads(got.body.decode("utf-8", "replace"))
        except ValueError:
            break
        products = payload.get("products") or []
        if not products:
            break
        for product in products:
            if not is_season_pack(product):
                continue
            title = str(product.get("title") or "")
            season = season_of(title)
            items = lineup_from(product)
            if not season or len(items) < 3:
                continue
            seasons += 1
            handle = str(product.get("handle") or product.get("id") or "")
            url = f"https://{store}/products/{handle}"
            snapshot.write(SOURCE, f"{season}-{handle}.json".replace("/", "_"), product)
            events.append(harvest.lineup_event(
                source=SOURCE, key=f"{season}-{handle}", season=season, items=items,
                url=url, observed_at=observed_at))
            for item in items:
                events.append(harvest.mention_event(
                    source=SOURCE, key=f"{season}-{handle}-{item['position']}",
                    name=item["text"][:120], url=url, observed_at=observed_at,
                    payload={"season": season, "position": item["position"],
                             "claimed_shu": item["claimed_shu"],
                             "lineup_title": title}))
        if len(products) < shopify.PAGE_SIZE:
            break
    if log:
        print(f"  hotones seasons={seasons} kept={len(events)}", file=log, flush=True)
    return {"source": SOURCE, "seasons": seasons, "events": events, "kept": len(events),
            "reason": ""}
