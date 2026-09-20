"""A51：出處連結只收彙整型，而且每一筆都指得到一篇真的文章。

Stanley 2026-09-20：「我們要留的不是 review 的文字，是要留 links」、
「only keeps aggregated reviews」。

驗四件事：

1. 每一筆都有 `url` 與 `article_title`——一個沒有標題的連結，
   半年後沒有人知道該不該點它。
2. `sauces_in_article` ≥ 門檻：這是「彙整型」唯一的判準。
3. 出處**不是**自己賣辣醬的站。店家商品頁的「相關商品」側欄一頁就能對上十幾個名字，
   看起來跟一篇評了十幾款的評比一模一樣。
4. 只收當前規則版本。被新規則淘汰掉的關聯還留在庫裡（只追加），混進來就看不出差別。

**這條驗不到「那篇文章真的評了這款醬」**——它只驗那篇文章裡出現過這款醬的名字。
一篇提到 20 款、只認真評 5 款的文章，另外 15 款一樣會掛上連結。
要分辨那個差別得讀正文，而讀正文正是這一版刻意拿掉的東西。
"""
from __future__ import annotations

import sys

from ..contract import EV_REFERENCE
from ..references import MIN_SAUCES_PER_ARTICLE, RULES_VERSION, selling_hosts
from . import arg_parser, events, home_of, report

REQUIRED = ("url", "article_title", "sauces_in_article", "ref_rules_version")


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.references", rules=False).parse_args(argv)
    selling = selling_hosts()
    problems: list[str] = []
    checked = stale = 0
    articles: set[str] = set()
    sauces: set[str] = set()
    for ev in events(home_of(ns)):
        if ev.event_type != EV_REFERENCE:
            continue
        payload = ev.payload
        if str(payload.get("ref_rules_version") or "") != RULES_VERSION:
            stale += 1
            continue
        checked += 1
        sauces.add(ev.entity_id)
        url = str(payload.get("url") or "")
        articles.add(url)
        missing = [k for k in REQUIRED if not payload.get(k)]
        if missing:
            problems.append(f"{ev.entity_id}：缺 {missing}")
            continue
        if int(payload.get("sauces_in_article") or 0) < MIN_SAUCES_PER_ARTICLE:
            problems.append(f"{url}：只對上 {payload.get('sauces_in_article')} 個名字，"
                            f"不到彙整型的門檻 {MIN_SAUCES_PER_ARTICLE}")
        host = url.split("//")[-1].split("/")[0].lower().removeprefix("www.")
        if host in selling:
            problems.append(f"{url}：{host} 自己賣辣醬，它的商品頁不算評比")
    if not checked:
        problems.append("一筆出處連結都沒有——先跑 python -m sauce.references")
    return report("A51 references", not problems,
                  {"references": checked, "stale_version_ignored": stale,
                   "articles": len(articles), "sauces_with_reference": len(sauces),
                   "min_sauces_per_article": MIN_SAUCES_PER_ARTICLE,
                   "rules_version": RULES_VERSION}, problems[:20])


if __name__ == "__main__":
    sys.exit(main())
