"""Wikipedia：老牌與已經下架的品項在這裡還查得到。

零售端一旦下架，Shopify 與 FDC 就看不到它了；但「這款曾經存在」對語料庫是有意義的，
所以名單類來源要留著。產出一律是 `sauce.observation.mention`——只有名字，沒有可購性。

**只抓 `/wiki/` 底下的條目頁。** Wikimedia 的 robots.txt 對一般代理人擋掉 `/w/` 與 `/api/`
（實測 2026-09-19），所以 Action API 與 SPARQL 都不能用；能用的是條目頁本身，
而條列型條目（List of…、Category:…）剛好就是我們要的那份名單。

## 三種頁要用三種讀法

一開始三種都用「抓內文所有連結」處理，結果是：清單頁抓到 627 筆，裡面有
`Monmouth County`、`Mexico City`、`FD&C Red 40`——因為表格的第二、三欄是產地與辣椒品種。
**那種列會通過所有結構檢查、也會讓總表的列數變好看，但它們不是辣醬。**

- `table_rows`：`List of hot sauces` 這種表格條目。**每一列的第一格**才是產品名，
  其餘欄位是產地、辣椒、Scoville。只取第一格。
- `category`：`Category:` 頁。`mw-pages` 區塊裡的每一個連結都是該分類的成員，全收。
- `prose`：`Hot sauce` 這種散文條目。什麼都連，所以要過名稱規則。
"""
from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import unquote, urljoin

from evdb.schema import Event

from .. import harvest
from ..net import Fetcher
from . import filters

SOURCE = "wikipedia"
BASE = "https://en.wikipedia.org"

TABLE_ROWS, CATEGORY, PROSE = "table_rows", "category", "prose"

#: (條目路徑, 讀法)
PAGES: tuple[tuple[str, str], ...] = (
    ("/wiki/List_of_hot_sauces", TABLE_ROWS),
    ("/wiki/Category:Hot_sauces", CATEGORY),
    ("/wiki/Category:Chili_sauces", CATEGORY),
    ("/wiki/Category:Hot_sauce_brands", CATEGORY),
    ("/wiki/Hot_sauce", PROSE),
    ("/wiki/Chili_sauce", PROSE),
    ("/wiki/List_of_chili_pepper_cultivars", PROSE),
)

#: 條目頁裡不算產品的連結（導覽、維護、分類本身）
SKIP_PREFIXES = ("Wikipedia:", "Help:", "Portal:", "Template:", "Special:", "File:",
                 "Talk:", "User:", "Category:", "Main_Page")

#: Wikipedia 出過三種 HTML，三種都要認：舊版 `/wiki/X`、Parsoid `./X`、
#: Parsoid 絕對網址 `https://en.wikipedia.org/wiki/X`（`List of hot sauces` 是最後這種）。
_LINK = re.compile(
    rb'<a\b[^>]*href="(?:https?://en\.wikipedia\.org)?(?:/wiki/|\./)([^"#?]+)"'
    rb'[^>]*?(?:title="([^"]*)")?[^>]*>(.*?)</a>', re.I | re.S)
_ROW = re.compile(rb"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL = re.compile(rb"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.I | re.S)
_TAGS = re.compile(rb"<[^>]+>")
_CONTENT = re.compile(rb'<div[^>]+id="(?:mw-content-text|mw-pages)"(.*)', re.I | re.S)
_REF = re.compile(r"\[\s*\d+\s*\]")


def _body(page_bytes: bytes) -> bytes:
    """只看內文區塊，不看側邊欄與頁尾——否則每一頁都會收到一堆導覽連結。"""
    m = _CONTENT.search(page_bytes)
    return m.group(1) if m else page_bytes


def _clean_text(raw: bytes) -> str:
    text = html.unescape(_TAGS.sub(b" ", raw).decode("utf-8", "replace"))
    return _REF.sub("", re.sub(r"\s+", " ", text)).strip()


def _link_name(m: "re.Match[bytes]") -> tuple[str, str, str]:
    page = m.group(1).decode("utf-8", "replace")
    title = html.unescape((m.group(2) or b"").decode("utf-8", "replace").strip())
    text = _clean_text(m.group(3))
    name = title or text or unquote(page.rsplit("/", 1)[-1]).replace("_", " ")
    return page, re.sub(r"\s+", " ", name).strip(), text


def _rows_mode(body: bytes) -> list[tuple[str, str, str]]:
    """表格條目：每一列的第一格是產品名，其餘欄位（產地、辣椒、Scoville）當附註。"""
    out: list[tuple[str, str, str]] = []
    for row in _ROW.finditer(body):
        cells = _CELL.findall(row.group(1))
        if not cells:
            continue
        name = _clean_text(cells[0])
        low = name.lower()
        if not name or low in ("name", "brand", "sauce") or "sauce name" in low:
            continue        # 表頭列也是 <tr>，但它不是產品
        link = _LINK.search(cells[0])
        page = link.group(1).decode("utf-8", "replace") if link else ""
        note = " | ".join(_clean_text(c) for c in cells[1:4] if _clean_text(c))
        out.append((page, name, note))
    return out


def _category_mode(body: bytes) -> list[tuple[str, str, str]]:
    return [(p, n, t) for p, n, t in (_link_name(m) for m in _LINK.finditer(body))
            if not p.startswith(SKIP_PREFIXES)]


def _prose_mode(body: bytes) -> list[tuple[str, str, str]]:
    return [(p, n, t) for p, n, t in _category_mode(body) if filters.keep(n)]


MODES = {TABLE_ROWS: _rows_mode, CATEGORY: _category_mode, PROSE: _prose_mode}


def to_events(path: str, mode: str, page_bytes: bytes, observed_at: str) -> list[Event]:
    out: list[Event] = []
    seen: set[str] = set()
    for page, name, note in MODES[mode](_body(page_bytes)):
        key = page or name.replace(" ", "_")
        if key in seen or not (3 <= len(name) <= 120):
            continue
        seen.add(key)
        out.append(harvest.mention_event(
            source=SOURCE, key=key, name=name,
            url=urljoin(BASE, "/wiki/" + page) if page else urljoin(BASE, path),
            observed_at=observed_at,
            payload={"listed_on": path, "listing_mode": mode, "row_note": note,
                     "has_own_article": bool(page)}))
    return out


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                pages: tuple[tuple[str, str], ...] = PAGES,
                log: Any = None) -> dict[str, Any]:
    events: list[Event] = []
    got_pages = []
    for path, mode in pages:
        got = fetcher.get(urljoin(BASE, path))
        if not got.ok:
            got_pages.append({"page": path, "status": got.status, "reason": got.reason,
                              "kept": 0})
            if log:
                print(f"  wikipedia {path:<38} SKIP {got.reason}", file=log, flush=True)
            continue
        snapshot.write(SOURCE, path.removeprefix("/wiki/").replace(":", "_") + ".html",
                       got.body)
        found = to_events(path, mode, got.body, observed_at)
        events.extend(found)
        got_pages.append({"page": path, "status": got.status, "reason": "", "kept": len(found)})
        if log:
            print(f"  wikipedia {path:<38} kept={len(found)}", file=log, flush=True)
    return {"source": SOURCE, "pages": got_pages, "events": events, "kept": len(events),
            "reason": ""}
