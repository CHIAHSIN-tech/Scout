"""每一款醬附上「哪幾篇文章一起評過它」——**存連結，不存評論內容**。

    python -m sauce.references --home .evdb --rules ref-1

Stanley 2026-09-20：「我們要留的不是 review 的文字，是要留 links……
就是每一個 Hot Sauce 的 Reference, not the review itselves」，
以及「only keeps aggregated reviews，就是一次要評論很多個 hot sauce 的那種文章」。

## 這一層跟原本的評語抽取差在哪

原本要模型讀完一篇評論、抽出「這款醬的立場、分數、代表句」。那有三個問題：

1. **代表句選得好不好沒有任何機器檢查蓋得到**（引文是不是原句驗得了，是不是重點驗不了）；
2. 它要過 llm-bridge 的冷啟動人審關卡，20 筆一輪；
3. **而且我們其實不需要它**。要回答「這款醬有誰評過」，一個連結就夠了，
   而連結本身是事實，不是判斷。

換成連結之後，**整條線一個模型都不用**：比對是折疊後的詞串比對，
彙整型的判準是「這篇提到幾款」——那本身就是一個數字，不是一個判斷。

## 只收彙整型

一次評很多款的那種文章（`The 16 Best Hot Sauces, Ranked`）才收。
判準就是**這篇在總表裡對上了幾款**：≥ `MIN_SAUCES_PER_ARTICLE` 才算。

這個判準有一個好處是它自己會解釋自己：一篇食譜提到一款辣醬，
對上 1 款，自然落榜；一篇「我們試了 32 款」對上二三十款，自然入選。
不需要看標題關鍵字，也不需要模型分類。

## 三個把假關聯擋掉的規則

- **名字不能整串都是描述詞**。`cayenne pepper`、`ghost pepper`、`black truffle`
  是辣椒與風味，不是產品名——它們會對上半個語料庫。
  所以一個鍵如果**每一個詞都落在成分／辣椒詞庫裡**，就不拿來比對。
- **網址要長得像文章**。`/product-sitemap.xml`、`/category/hot-sauce/`
  是店面的分類頁，不是有人寫的評比。
- **賣東西的站不算評比**。`saucemania.com.au`、`hotsaucedepot.com` 這些店在白名單裡
  是因為它們也寫文章，但它們的**商品頁**有「相關商品」側欄，
  一頁就能對上十幾個名字，看起來跟一篇評了十幾款的評比一模一樣。
  白名單本來就記著 `conflict_of_interest = sells_products`，直接用那一欄擋。
- **一個名字只能指向一款醬**。`buffalo wing` 在總表裡是 44 個品牌共用的品名——
  一篇只提過一次「buffalo wing sauce」的 Texas Pete 身世故事，
  會因為這一個詞同時掛上 44 款醬，看起來像一篇評了 44 款的評比。
  所以只有**唯一對得上一款**的品名才拿來比對；對上多款的要品牌一起出現才算。

而「彙整型」數的是**相異的名字**，不是相異的 entity_id。
數 entity_id 的話，上面那一個詞就足以讓任何文章看起來像評比。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from evdb.home import Home, now_iso
from evdb.schema import Event, IngestPath
from evdb.spool import Spool
from evdb.store import Store

from . import contract
from .names import fold
from .outlets import load as load_outlets

#: 規則一改就要升版：舊版的事件永遠留在庫裡（只追加），
#: 視圖只收當前版本，否則被規則淘汰掉的關聯會跟通過的混在一起。
RULES_VERSION = "ref-3"
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sauce"
LEXICON = FIXTURES / "ingredient-lexicon.csv"
PEPPERS = FIXTURES / "pepper-shu.csv"

#: 一篇要對上幾款才算「彙整型」。Stanley 要的就是這種。
MIN_SAUCES_PER_ARTICLE = 5

#: 比對鍵至少要這麼長。太短的詞串在長正文裡一定會撞上。
MIN_KEY_CHARS = 12

#: 標題短於這個字數，而且裡面就是一款醬的名字 → 那是商品頁。
PRODUCT_TITLE_WORDS = 9

#: 這種利益衝突的站不拿來當出處：它們的商品頁會偽裝成評比。
EXCLUDED_CONFLICT = "sells_products"

#: 正文只讀前面這麼多字元。評比文章的清單都在前段，後面是留言與推薦閱讀。
MAX_BODY_CHARS = 120_000

#: 不是文章的網址：店面的分類頁、sitemap、商品頁。
_NOT_AN_ARTICLE = re.compile(
    r"(?:sitemap[^/]*\.xml|/category/|/product-category/|/collections?/|/shop/|"
    r"/tag/|/page/\d+)", re.I)

#: 這些詞就算不在詞庫裡，也還是描述而不是名字。
EXTRA_GENERIC = {
    "hot", "sauce", "sauces", "spicy", "mild", "medium", "extra", "original", "classic",
    "gourmet", "style", "flavor", "flavour", "blend", "recipe", "case", "pack", "bottle",
    "wing", "wings", "bbq", "barbecue", "taco", "salsa", "chili", "chile", "chilli",
    "pepper", "peppers", "red", "green", "black", "white", "yellow", "orange", "purple",
    "sweet", "smoky", "smoked", "roasted", "fire", "fiery", "heat", "the", "and", "of",
    "buffalo", "louisiana", "original's", "brand", "co", "company", "kitchen", "farms",
    "private", "label", "variety", "assorted", "collection", "gift", "set", "sampler",
}


def generic_words(lexicon: Path | None = None, peppers: Path | None = None) -> set[str]:
    """成分詞 ＋ 辣椒品種 ＋ 一批包裝／行銷用語。**整串都由這些組成的名字不是名字。**"""
    words: set[str] = set(EXTRA_GENERIC)
    for path, column in ((lexicon or LEXICON, "term"), (peppers or PEPPERS, "pepper")):
        p = Path(path)
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                for part in fold(row.get(column, "")).split("-"):
                    if part:
                        words.add(part)
    return words


def is_distinctive(key: str, generic: set[str]) -> bool:
    """這個折疊後的鍵是不是一個「名字」。

    `carolina-reaper-hot-sauce` 每一個詞都是辣椒或包裝用語——它描述的是一類醬，
    不是某一瓶。拿它去比對會把所有提到卡羅萊納死神的文章都掛上去。
    """
    parts = [p for p in key.split("-") if p]
    if len("".join(parts)) < MIN_KEY_CHARS - 2:
        return False
    return any(p not in generic for p in parts)


def match_keys(catalog_rows: Iterable[dict[str, str]],
               generic: set[str] | None = None) -> dict[str, list[str]]:
    """折疊後的比對鍵 → entity_id。**一個鍵只准指向一款醬。**

    只靠品名比對時，`buffalo wing` 這種鍵會同時指向 44 個品牌的同名商品。
    那不是「這篇提到 44 款」，那是「這篇提到一個分類」。
    所以品名鍵只有在總表裡唯一時才留下；不唯一的要靠
    「品牌＋品名」那個鍵才對得上，而那個鍵本來就幾乎不會撞。
    """
    generic = generic_words() if generic is None else generic
    product_only: dict[str, set[str]] = defaultdict(set)
    qualified: dict[str, set[str]] = defaultdict(set)
    for row in catalog_rows:
        brand = (row.get("brand") or "").strip()
        product = (row.get("product") or "").strip()
        if not product:
            continue
        entity_id = row["entity_id"]
        key = fold(product)
        if len(key) >= MIN_KEY_CHARS and is_distinctive(key, generic):
            product_only[key].add(entity_id)
        if brand:
            key = fold(f"{brand} {product}")
            if len(key) >= MIN_KEY_CHARS and is_distinctive(key, generic):
                qualified[key].add(entity_id)

    out: dict[str, list[str]] = {k: sorted(v) for k, v in qualified.items()}
    for key, ids in product_only.items():
        # 撞名的品名不要——它描述的是一個分類，不是某一瓶
        if len(ids) == 1 and key not in out:
            out[key] = sorted(ids)
    return out


def selling_hosts(path: Path | None = None) -> set[str]:
    """白名單裡自己賣辣醬的那幾家的網域。"""
    return {str(r.get("domain") or "").split("/")[0].lower()
            for r in load_outlets(path)
            if str(r.get("conflict_of_interest") or "") == EXCLUDED_CONFLICT}


def looks_like_article(url: str, title: str,
                       table: dict[str, list[str]] | None = None,
                       selling: set[str] | None = None) -> bool:
    """網址要長得像一篇文章，而且**標題本身不能是一款醬的名字**。

    後面這一條才是真正管用的那個。`saucemania.com.au` 這種店的商品頁
    網址是平的（`/cajohns-reaper-sling-blade-hot-sauce-148ml/`），
    看網址分不出來；但它的標題就是那瓶醬的名字，而且頁面側欄的
    「相關商品」會讓它對上十幾個名字，於是一個商品頁看起來像一篇評了 12 款的評比。
    """
    title = str(title or "").strip()
    if not title:
        return False
    if _NOT_AN_ARTICLE.search(str(url or "")):
        return False
    if selling:
        host = str(url or "").split("//")[-1].split("/")[0].lower()
        if host.removeprefix("www.") in selling:
            return False
    if table:
        folded = f"-{fold(title)}-"
        short = len(title.split()) <= PRODUCT_TITLE_WORDS
        # 短標題 ＋ 裡面就是一款醬的名字 → 這是商品頁，不是評比。
        # 長度這一項不能省：`The 16 Best Hot Sauces, Ranked` 也很短，
        # 但它裡面沒有任何一款醬的名字，所以留得下來。
        if short and any(f"-{key}-" in folded for key in table):
            return False
    return True


def sauces_in(body: str, table: dict[str, list[str]]
              ) -> tuple[dict[str, list[str]], int]:
    """(對上的 entity_id → 靠哪些鍵, 相異名字數)。

    第二個數字才是「這篇評了幾款」。相異 entity_id 會被撞名的鍵灌水。
    """
    folded = f"-{fold(body[:MAX_BODY_CHARS])}-"
    found: dict[str, list[str]] = defaultdict(list)
    names = 0
    for key, ids in table.items():
        if f"-{key}-" in folded:
            names += 1
            for entity_id in ids:
                found[entity_id].append(key)
    return dict(found), names


def to_events(article: dict[str, Any], matches: dict[str, list[str]], observed_at: str,
              rules_version: str, names: int | None = None) -> list[Event]:
    total = len(matches) if names is None else names
    return [
        Event(entity_type="sauce_reference", entity_id=entity_id,
              event_type=contract.EV_REFERENCE, observed_at=observed_at, source="evdb",
              source_record_id=f"{article['review_id']}:{entity_id}",
              source_url=article["url"], ingest_path=IngestPath.BULK.value,
              related=({"role": "review", "entity_id": article["review_entity_id"]},),
              payload={"url": article["url"], "article_title": article["title"],
                       "outlet": article["outlet"],
                       "published_at": article.get("published_at", ""),
                       "sauces_in_article": total,
                       "matched_on": sorted(keys),
                       "reference_kind": "aggregated_roundup",
                       "ref_rules_version": rules_version})
        for entity_id, keys in sorted(matches.items())]


def run(home: Home, rules_version: str = RULES_VERSION,
        min_sauces: int = MIN_SAUCES_PER_ARTICLE,
        catalog: Path | None = None) -> dict[str, Any]:
    path = catalog or _latest_catalog()
    if path is None or not path.exists():
        return {"rows": 0, "reason": "找不到 catalog；先跑 sauce.export"}
    with path.open(encoding="utf-8", newline="") as fh:
        table = match_keys(list(csv.DictReader(fh)))
    selling = selling_hosts()

    with Store(home, read_only=True) as store:
        reviews = [ev for ev in store.all_events() if ev.event_type == contract.EV_REVIEW]

    observed_at = now_iso()
    events: list[Event] = []
    stats = {"articles": 0, "with_body": 0, "not_an_article": 0,
             "selling_hosts": len(selling),
             "roundups": 0, "too_few": 0, "no_match": 0}
    per_article: list[dict[str, Any]] = []
    for ev in reviews:
        stats["articles"] += 1
        title = str(ev.payload.get("title") or "")
        url = ev.source_url or ""
        if not looks_like_article(url, title, table, selling):
            stats["not_an_article"] += 1
            continue
        if not ev.raw_ref:
            continue
        body_path = home.root / ev.raw_ref
        if not body_path.exists():
            continue
        stats["with_body"] += 1
        matches, names = sauces_in(
            body_path.read_text(encoding="utf-8", errors="replace"), table)
        if not matches:
            stats["no_match"] += 1
            continue
        if names < min_sauces:
            stats["too_few"] += 1
            continue
        stats["roundups"] += 1
        article = {"review_id": str(ev.payload.get("review_id") or ev.event_id),
                   "review_entity_id": ev.entity_id, "url": url, "title": title,
                   "outlet": str(ev.payload.get("outlet") or ""),
                   "published_at": str(ev.payload.get("published_at") or "")}
        events.extend(to_events(article, matches, observed_at, rules_version, names))
        per_article.append({"url": url, "title": title, "names": names,
                            "linked_rows": len(matches)})

    Spool(home, tag="sauce-references").write(events)
    per_article.sort(key=lambda a: -a["names"])
    return {"references": len(events), "distinct_sauces": len({e.entity_id for e in events}),
            "match_keys": len(table), "min_sauces_per_article": min_sauces,
            "rules_version": rules_version, "top": per_article[:10], **stats}


def _latest_catalog() -> Path | None:
    root = Path(__file__).resolve().parent / "out"
    runs = sorted((d for d in root.glob("*") if d.is_dir()), reverse=True)
    for d in runs:
        for f in sorted(d.glob("sauce_catalog-*.csv")):
            return f
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.references")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default=RULES_VERSION)
    ap.add_argument("--min-sauces", type=int, default=MIN_SAUCES_PER_ARTICLE)
    ap.add_argument("--catalog", default=None)
    ns = ap.parse_args(argv)
    out = run(Home.resolve(ns.home), ns.rules, ns.min_sauces,
              Path(ns.catalog) if ns.catalog else None)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
