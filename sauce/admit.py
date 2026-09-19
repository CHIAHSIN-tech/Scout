"""白名單准入的稽核工具：把「這站算不算專業評論來源」變成可以逐列覆核的資料。

准入是人的判斷，但判斷要有證據。這支程式替每一個候選站做三件機械的事：

1. 找出**符合准入依據的那一頁**（編輯團隊／編輯政策／評測方法），並確認它真的回 200；
2. 確認這站真的有辣醬或調味料的評測內容（用站內搜尋，不是用猜的）；
3. 把結果寫成 `fixtures/sauce/outlets-evidence.json`，人照著它填 `outlets.csv`。

它不會自己把任何一列寫進白名單——證據找不到的站就是不准入，而不是放寬規則。

    python -m sauce.admit --candidates fixtures/sauce/outlets-candidates.csv
    python -m sauce.admit --emit          # 把已有證據的候選印成 outlets.csv 的列
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from .net import Fetcher
from .outlets import CANDIDATES, FIXTURES, host_of, outlet_key, path_prefix_of

EVIDENCE = FIXTURES / "outlets-evidence.json"

#: 准入的內容門檻：至少要找得到這麼多篇辣醬／調味料相關文章
MIN_ARTICLES = 3

#: 依據 → 連結文字／網址裡的線索。順序就是優先序：方法論頁最有力，其次編輯團隊。
BASIS_HINTS: dict[str, tuple[str, ...]] = {
    "methodology_page": ("how we test", "how-we-test", "how we review", "how-we-review",
                         "testing methodology", "our testing process", "review process",
                         "how we rate", "taste test methodology", "how we evaluate",
                         "product testing", "our-methodology", "methodology"),
    "masthead": ("masthead", "editorial policy", "editorial-policy", "editorial guidelines",
                 "editorial-guidelines", "editorial standards", "editorial team",
                 "editorial-team", "our team", "our-team", "our editors", "staff",
                 "about us", "about-us", "/about"),
}

#: 首頁沒連到證據頁時，直接試這些常見路徑。順序＝證據力。
WELL_KNOWN: tuple[tuple[str, str], ...] = (
    ("methodology_page", "/how-we-test"), ("methodology_page", "/how-we-test/"),
    ("methodology_page", "/how-we-review"), ("methodology_page", "/methodology"),
    ("methodology_page", "/review-process"), ("methodology_page", "/how-we-rate"),
    ("masthead", "/about"), ("masthead", "/about/"), ("masthead", "/about-us"),
    ("masthead", "/about-us/"), ("masthead", "/masthead"), ("masthead", "/our-team"),
    ("masthead", "/editorial-policy"), ("masthead", "/editorial-guidelines"),
    ("masthead", "/staff"), ("masthead", "/about-me"), ("masthead", "/about-me/"),
)

#: 判斷「這站真的有辣醬／調味料評測」用的網址特徵。走 sitemap，不走站內搜尋——
#: 多數站的 robots.txt 明文擋掉 /search 與 /?s=，那是禁止爬，不是「沒有內容」。
CONTENT_PATTERNS = ("hot-sauce", "hotsauce", "hot_sauce", "chili-sauce", "chile-sauce",
                    "chilli-sauce", "sriracha", "tabasco", "habanero", "scoville",
                    "chili-oil", "chile-crisp", "chili-crisp", "condiment")
SITEMAP_FANOUT = 40         # 每個站最多展開幾份子 sitemap
MAX_CONTENT_URLS = 400      # 一個站最多記幾個候選文章網址

_ANCHOR = re.compile(rb'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_TAGS = re.compile(rb"<[^>]+>")


def _anchors(body: bytes, base: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in _ANCHOR.finditer(body):
        href = m.group(1).decode("utf-8", "replace").strip()
        text = _TAGS.sub(b" ", m.group(2)).decode("utf-8", "replace")
        text = re.sub(r"\s+", " ", text).strip()
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            out.append((urljoin(base, href), text))
    return out


def _pick(links: list[tuple[str, str]], host: str) -> dict[str, str]:
    """每一種依據挑一個最像的連結。只看同一個主機底下的連結。"""
    found: dict[str, str] = {}
    for basis, hints in BASIS_HINTS.items():
        for url, text in links:
            if host_of(url) != host:
                continue
            blob = f"{text.lower()} {urlsplit(url).path.lower()}"
            if any(h in blob for h in hints):
                found.setdefault(basis, url)
                break
    return found


_LOC = re.compile(rb"<loc>\s*([^<\s]+)\s*</loc>", re.I)


def sitemap_urls(fetcher: Fetcher, origin: str) -> list[str]:
    """robots.txt 宣告的 sitemap（沒宣告就試 /sitemap.xml），展開一層子 sitemap。"""
    roots: list[str] = []
    robots = fetcher.get(origin + "/robots.txt")
    if robots.ok:
        for line in robots.text.splitlines():
            if line.lower().startswith("sitemap:"):
                roots.append(line.split(":", 1)[1].strip())
    for guess in ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml"):
        if not roots:
            got = fetcher.get(origin + guess)
            if got.ok and b"<loc" in got.body:
                roots.append(got.final_url or (origin + guess))
    return roots[:6]


def _content_urls(fetcher: Fetcher, origin: str) -> dict[str, Any]:
    """走 sitemap 找辣醬相關的文章網址。這既是「有沒有內容」的證據，
    也是 N3d 之後真的要去抓的那份清單，所以一次做完、存起來。"""
    seen: list[str] = []
    for root in sitemap_urls(fetcher, origin):
        got = fetcher.get(root)
        if not got.ok:
            continue
        locs = [m.group(1).decode("utf-8", "replace") for m in _LOC.finditer(got.body)]
        pages = [u for u in locs if u.lower().endswith((".xml", ".xml.gz"))]
        seen.extend(u for u in locs if _looks_like_content(u))
        # 大站的 sitemap index 動輒上百份子檔（多半按月切）。只看前幾份會固定看到最舊的那幾個月，
        # 那正是最不可能有近年評測的地方——所以頭尾都取，中間跳過。
        picked = pages[:5] + pages[-(SITEMAP_FANOUT - 5):] if len(pages) > SITEMAP_FANOUT else pages
        for child in picked:
            sub = fetcher.get(child)
            if not sub.ok:
                continue
            seen.extend(m.group(1).decode("utf-8", "replace") for m in _LOC.finditer(sub.body)
                        if _looks_like_content(m.group(1).decode("utf-8", "replace")))
            if len(seen) >= MAX_CONTENT_URLS:
                break
        if len(seen) >= MAX_CONTENT_URLS:
            break
    uniq = sorted(dict.fromkeys(seen))
    return {"search_url": uniq[0] if uniq else "", "hits": len(uniq),
            "urls": uniq[:MAX_CONTENT_URLS]}


def _looks_like_content(url: str) -> bool:
    low = url.lower()
    return any(p in low for p in CONTENT_PATTERNS)


def _has_sauce_content(fetcher: Fetcher, origin: str) -> dict[str, Any]:
    return _content_urls(fetcher, origin)


def audit_one(fetcher: Fetcher, row: dict[str, str]) -> dict[str, Any]:
    domain = row["domain"]
    host = host_of(domain)
    prefix = path_prefix_of(domain)
    origin = f"https://{host}"
    home = fetcher.get(origin + (prefix or "/"))
    result: dict[str, Any] = {
        "outlet": row["outlet"], "domain": domain, "host": host,
        "tier": row["tier"], "conflict_of_interest": row["conflict_of_interest"],
        "home_status": home.status, "home_ok": home.ok, "home_reason": home.reason,
        "candidates": {}, "admission_basis": "", "evidence_url": "",
        "evidence_status": None, "sauce_content": {"search_url": "", "hits": 0},
    }
    if not home.ok:
        return result

    picks = _pick(_anchors(home.body, home.final_url or origin), host)
    result["candidates"] = picks
    tries: list[tuple[str, str]] = [(b, picks[b]) for b in ("methodology_page", "masthead")
                                    if picks.get(b)]
    tries += [(basis, origin + path) for basis, path in WELL_KNOWN]
    for basis, url in tries:
        got = fetcher.get(url)
        result["evidence_status"] = got.status
        if got.ok and len(got.body) > 1500:      # 空白的佔位頁不算證據
            result["admission_basis"] = basis
            result["evidence_url"] = got.final_url or url
            break
    result["sauce_content"] = _has_sauce_content(fetcher, origin)
    return result


def run(candidates: Path | None = None, out: Path | None = None,
        only: list[str] | None = None) -> dict[str, Any]:
    path = Path(candidates or CANDIDATES)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [{(k or "").strip(): (v or "").strip() for k, v in r.items() if k}
                for r in csv.DictReader(fh)]
    if only:
        rows = [r for r in rows if r["outlet"] in only or r["domain"] in only]
    fetcher = Fetcher()
    results = []
    for row in rows:
        try:
            results.append(audit_one(fetcher, row))
        except Exception as exc:           # 一個站掛掉不能讓整批停下來
            results.append({"outlet": row["outlet"], "domain": row["domain"],
                            "error": f"{type(exc).__name__}: {exc}",
                            "admission_basis": "", "evidence_url": ""})
        print(f"  {results[-1]['outlet']:<34} basis={results[-1].get('admission_basis') or '-':<18} "
              f"articles={results[-1].get('sauce_content', {}).get('hits', 0)}", flush=True)
    admitted = [r for r in results if r.get("evidence_url") and r.get("sauce_content", {}).get("hits", 0) >= MIN_ARTICLES]
    payload = {"audited": len(results), "admissible": len(admitted),
               "net_stats": fetcher.stats, "results": results}
    out_path = Path(out or EVIDENCE)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return payload


def emit(evidence: Path | None = None) -> list[dict[str, str]]:
    """把有證據的候選變成 outlets.csv 的列。沒證據的不出現——名單不湊數。"""
    data = json.loads(Path(evidence or EVIDENCE).read_text(encoding="utf-8"))
    today = date.today().isoformat()
    rows = []
    for r in data["results"]:
        if not r.get("evidence_url") or r.get("sauce_content", {}).get("hits", 0) < MIN_ARTICLES:
            continue
        rows.append({"outlet": r["outlet"], "domain": r["domain"], "admitted_on": today,
                     "admission_basis": r["admission_basis"], "evidence_url": r["evidence_url"],
                     "tier": r["tier"], "conflict_of_interest": r["conflict_of_interest"]})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.admit")
    ap.add_argument("--candidates", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--emit", action="store_true", help="把證據齊全的候選印成 outlets.csv")
    ns = ap.parse_args(argv)
    if ns.emit:
        rows = emit()
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]) if rows else
                           ["outlet", "domain", "admitted_on", "admission_basis",
                            "evidence_url", "tier", "conflict_of_interest"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        return 0
    out = run(Path(ns.candidates) if ns.candidates else None,
              Path(ns.out) if ns.out else None, ns.only)
    print(json.dumps({k: v for k, v in out.items() if k != "results"},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
