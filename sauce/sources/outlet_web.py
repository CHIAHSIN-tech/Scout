"""白名單內 outlet 的評論文章。這是評論層的主力來源。

## 兩件事分得很開

**這一支只負責把文章原封不動地搬回來**：正文逐字存進 raw store，事件裡只放中繼資料
與一個 sha256 指標。它不判斷作者喜不喜歡那瓶醬、不挑代表句、不給分數——
那是抽取層（`sauce.extract`）的事，而且抽取層可以重跑、可以換模型、可以改規則版本，
**原始那層永遠不動**。這是整個語料庫的核心紀律：一旦入庫時只留摘要，
所有沒被那次摘要保留的訊號就永久消失，而且事後無從察覺。

## 擋牆在前面

要抓的每一個網址都先過 `net.Fetcher.get_review()`，它在**送出請求之前**查白名單，
不在名單上直接 raise。事後稽核（A21）也會檢查，但事後發現時東西已經抓回來了，
所以真正的擋牆一定是事前那道。

## 文章從哪裡來

走 outlet 自己的 sitemap，挑網址長得像辣醬內容的那些。不用站內搜尋——
多數站的 robots.txt 明文擋掉 `/search` 與 `/?s=`，那是禁止爬，不是「沒有內容」。
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any, Iterable

from evdb.schema import Event, IngestPath, Precision

from .. import contract, harvest
from ..names import normalize_whitespace
from ..net import Fetcher
from ..outlets import OutletNotAdmitted, outlet_key

SOURCE = "outlet_web"

#: 一個 outlet 最多抓幾篇。不是技術限制，是禮貌上限——同一個站一次搬走幾千頁不合適。
MAX_ARTICLES_PER_OUTLET = 120

_SCRIPTS = re.compile(rb"<(script|style|noscript|svg|form)\b.*?</\1>", re.I | re.S)
_CHROME = re.compile(rb"<(nav|header|footer|aside)\b.*?</\1>", re.I | re.S)
_ARTICLE = re.compile(rb"<article\b[^>]*>(.*?)</article>", re.I | re.S)
_MAIN = re.compile(rb"<main\b[^>]*>(.*?)</main>", re.I | re.S)
_TAGS = re.compile(rb"<[^>]+>")
_TITLE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
_H1 = re.compile(rb"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
_HEADING = re.compile(rb"<h[23]\b[^>]*>(.*?)</h[23]>", re.I | re.S)
_LDJSON = re.compile(rb'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.I | re.S)
_META = re.compile(rb'<meta\b[^>]*?(?:property|name)="([^"]+)"[^>]*?content="([^"]*)"', re.I)
_LANG = re.compile(rb'<html\b[^>]*\blang="([^"]{2,12})"', re.I)
_PAYWALL = re.compile(rb"(paywall|subscribe to (?:read|continue)|subscriber[- ]only)", re.I)

#: 標題長這樣就是排行／彙整文；一篇裡面會有很多款醬。
_RANKING = re.compile(r"\b(ranked|ranking|best|worst|top\s*\d+|\d+\s+best)\b", re.I)
_ROUNDUP = re.compile(r"\b(we tried|we tested|taste test|tasted|every|all \d+)\b", re.I)
_GUIDE = re.compile(r"\b(guide|explained|what is|how to|everything you need)\b", re.I)


def _text(raw: bytes) -> str:
    return normalize_whitespace(html.unescape(_TAGS.sub(b" ", raw).decode("utf-8", "replace")))


def body_text(page: bytes) -> str:
    """正文。先砍掉腳本與版面框架，再優先取 <article>／<main>，都沒有才退回整頁。"""
    cleaned = _CHROME.sub(b" ", _SCRIPTS.sub(b" ", page))
    m = _ARTICLE.search(cleaned) or _MAIN.search(cleaned)
    return _text(m.group(1) if m else cleaned)


def _ld_objects(page: bytes) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in _LDJSON.finditer(page):
        try:
            data = json.loads(m.group(1).decode("utf-8", "replace"))
        except ValueError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                out.append(item)
                graph = item.get("@graph")
                if isinstance(graph, list):
                    out.extend(x for x in graph if isinstance(x, dict))
    return out


def _authors(page: bytes, metas: dict[str, str]) -> list[str]:
    names: list[str] = []
    for obj in _ld_objects(page):
        author = obj.get("author")
        for a in (author if isinstance(author, list) else [author]):
            if isinstance(a, dict) and a.get("name"):
                names.append(str(a["name"]).strip())
            elif isinstance(a, str) and a.strip():
                names.append(a.strip())
    for key in ("author", "article:author", "twitter:creator", "parsely-author"):
        if metas.get(key):
            names.append(metas[key].strip())
    seen: list[str] = []
    for n in names:
        n = normalize_whitespace(n)[:120]
        if n and n.lower() not in {"", "admin"} and n not in seen and not n.startswith("http"):
            seen.append(n)
    return seen[:6]


def _published(page: bytes, metas: dict[str, str]) -> str:
    for obj in _ld_objects(page):
        for key in ("datePublished", "dateCreated", "uploadDate"):
            if obj.get(key):
                return str(obj[key])[:25]
    for key in ("article:published_time", "datePublished", "parsely-pub-date",
                "og:published_time", "date"):
        if metas.get(key):
            return metas[key][:25]
    return ""


def _updated(page: bytes, metas: dict[str, str]) -> str:
    for obj in _ld_objects(page):
        if obj.get("dateModified"):
            return str(obj["dateModified"])[:25]
    return metas.get("article:modified_time", "")[:25]


def _metas(page: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _META.finditer(page):
        key = m.group(1).decode("utf-8", "replace").strip().lower()
        val = html.unescape(m.group(2).decode("utf-8", "replace")).strip()
        if key and val and key not in out:
            out[key] = val
    return out


def _title(page: bytes, metas: dict[str, str]) -> str:
    m = _H1.search(page)
    if m:
        text = _text(m.group(1))
        if text:
            return text[:300]
    for key in ("og:title", "twitter:title"):
        if metas.get(key):
            return normalize_whitespace(metas[key])[:300]
    m = _TITLE.search(page)
    return (_text(m.group(1))[:300] if m else "")


def article_kind(title: str, headings: int) -> str:
    """一篇評論是單品、彙整、排行還是導讀。純規則，判斷依據記在 payload 裡。"""
    if _RANKING.search(title):
        return "ranking"
    if _ROUNDUP.search(title) or headings >= 5:
        return "roundup"
    if _GUIDE.search(title):
        return "guide"
    return "single"


def disclosure(body: str) -> str:
    """揭露方式。沒寫就是 `undisclosed`——**沒寫不等於自費**，兩者不可以合併。"""
    low = body.lower()
    if "we may earn" in low or "affiliate" in low or "commission" in low:
        return "affiliate"
    if "sent us" in low or "provided samples" in low or "samples were provided" in low \
            or "free samples" in low or "pr sample" in low:
        return "samples_provided"
    if "we bought" in low or "purchased with our own" in low or "we paid for" in low:
        return "purchased"
    return "undisclosed"


def url_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def to_event(url: str, outlet_row: dict[str, str], page: bytes, raw_ref: str,
             observed_at: str) -> Event:
    """一篇評論 → `sauce.review.published`。**payload 只放中繼資料，正文在 raw store。**"""
    metas = _metas(page)
    body = body_text(page)
    blob = body.encode("utf-8")
    key = url_key(url)
    okey = outlet_row.get("outlet_key") or outlet_key(outlet_row.get("outlet", ""))
    title = _title(page, metas)
    published = _published(page, metas)
    headings = len(_HEADING.findall(page))
    payload = {
        "review_id": contract.review_id(okey, key),
        "outlet": outlet_row.get("outlet", ""), "outlet_key": okey,
        "outlet_tier": outlet_row.get("tier", ""),
        "outlet_conflict_of_interest": outlet_row.get("conflict_of_interest", ""),
        "url": url, "title": title,
        "authors": _authors(page, metas), "published_at": published,
        "updated_at": _updated(page, metas),
        "language": (_LANG.search(page).group(1).decode() if _LANG.search(page) else "en"),
        "modality": "text",
        "article_kind": article_kind(title, headings),
        "article_kind_basis": f"title_rules+headings={headings}",
        "items_reviewed_count": headings,
        "items_reviewed_basis": "h2/h3 heading count（估計值；真正的數字是連上去的 verdict 筆數）",
        "disclosure": disclosure(body),
        "body_sha256": hashlib.sha256(blob).hexdigest(),
        "body_bytes": len(blob), "body_chars": len(body),
        "paywalled": bool(_PAYWALL.search(page)),
        "retrieved_at": observed_at,
    }
    return Event(
        entity_type="sauce_review",
        entity_id=contract.observation_id(SOURCE, f"{okey}-{key}"),
        event_type=contract.EV_REVIEW,
        observed_at=observed_at, source=SOURCE,
        source_record_id=key, source_url=url,
        event_time=published[:10] or None,
        event_time_precision=Precision.DAY.value if published[:10] else Precision.UNKNOWN.value,
        published_at=published or None,
        ingest_path=IngestPath.SDK.value, raw_ref=raw_ref, payload=payload)


def harvest_outlet(fetcher: Fetcher, recorder: Any, outlet_row: dict[str, str],
                   urls: Iterable[str], snapshot: harvest.Snapshot,
                   observed_at: str) -> dict[str, Any]:
    events: list[Event] = []
    tried = blocked = 0
    reasons: dict[str, int] = {}
    for url in list(urls)[:MAX_ARTICLES_PER_OUTLET]:
        tried += 1
        try:
            got, row = fetcher.get_review(url)
        except OutletNotAdmitted:
            blocked += 1
            reasons["not_admitted"] = reasons.get("not_admitted", 0) + 1
            continue
        if not got.ok:
            reasons[got.reason or "unknown"] = reasons.get(got.reason or "unknown", 0) + 1
            continue
        body = body_text(got.body)
        if len(body) < 600:          # 太短的不是評論文章（多半是分類頁或轉址頁）
            reasons["too_short"] = reasons.get("too_short", 0) + 1
            continue
        raw_ref = recorder.store_raw(body, SOURCE, suffix=".txt")
        events.append(to_event(got.final_url or url, row, got.body, raw_ref or "", observed_at))
    snapshot.write(SOURCE, f"{outlet_row.get('outlet_key', 'outlet')}-urls.json",
                   {"outlet": outlet_row.get("outlet"), "tried": tried,
                    "kept": len(events), "reasons": reasons})
    return {"outlet": outlet_row.get("outlet"), "tried": tried, "blocked": blocked,
            "kept": len(events), "reasons": reasons, "events": events}


def harvest_all(fetcher: Fetcher, recorder: Any, plan: list[tuple[dict[str, str], list[str]]],
                snapshot: harvest.Snapshot, observed_at: str,
                log: Any = None) -> dict[str, Any]:
    outlets_done, events = [], []
    for outlet_row, urls in plan:
        try:
            got = harvest_outlet(fetcher, recorder, outlet_row, urls, snapshot, observed_at)
        except Exception as exc:
            got = {"outlet": outlet_row.get("outlet"), "tried": 0, "blocked": 0, "kept": 0,
                   "reasons": {f"{type(exc).__name__}": 1}, "events": []}
        events.extend(got.pop("events"))
        outlets_done.append(got)
        if log:
            print(f"  review {str(got['outlet']):<30} kept={got['kept']:<4} "
                  f"tried={got['tried']:<4} {got['reasons']}", file=log, flush=True)
    return {"source": SOURCE, "outlets": outlets_done, "events": events,
            "kept": len(events)}
