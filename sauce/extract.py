"""抽取層：觀察 → 結構化欄位，以及評論正文 → 評語。

這是整條線上唯一會呼叫模型的地方，也是唯一會被 A12 檢查「不吃降級輸出」的地方。

## 兩個任務，兩種難度

- `sauce-product-parse`：商品標題 → 品牌／產品／規格。機械性、每筆規則一樣，用便宜那層。
- `sauce-review-verdict`：評論正文 → 對每一款醬的立場與代表句。要判斷語氣、要挑句子，
  用判斷力較強的那層。

兩個都 `degraded_ok=False`：模型被換掉就中止、一筆都不寫（A12）。
prompt 版本沒對那個模型驗過，輸出就不能算數。

## 為什麼原文要一路帶到驗證器

抽取的產出必須能回頭跟來源對上：
- 產品：折疊後的 `brand_key` / `product_key` 必須是**來源標題折疊後的連續詞串**（A10 第二層）；
- 評論：`quote` 必須是**正文的子字串**（A25）、`score_raw` 必須逐字保留（A26）。

所以驗證器拿得到原文，而且驗證失敗的那一筆不會變成事件——
不是「標記為可疑」，是根本不寫進去。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from evdb.home import Home, now_iso
from evdb.schema import Event, IngestPath, Precision
from evdb.spool import Spool
from evdb.store import Store

from . import contract
from .names import contains_key, fold, normalize_whitespace
from .scores import SCALES
from .sources import outlet_web

PROMPTS = Path(__file__).resolve().parent / "prompts"
RUNS = Path(__file__).resolve().parent.parent / "state" / "llm-runs"

TASK_PRODUCT = "sauce-product-parse"
TASK_VERDICT = "sauce-review-verdict"

#: 一篇評論送進模型的正文上限。太長的文章切到這裡為止，並把這件事記在事件裡——
#: 「我們只看了前面這一段」跟「這篇只有這麼多」不是同一件事。
BODY_CHARS = 12000

#: 食譜不是評測。白名單上的站有一大半是食譜站，而網址比對只看得出「這一頁講辣醬」，
#: 看不出「這一頁在評辣醬」。第一次冷啟動的 20 筆裡有 12 筆是食譜，
#: 而食譜頁上的 4.5 顆星是**讀者評分**——那是 user rating，照規格根本不該進庫（A20 的精神）。
_RECIPE = re.compile(
    r"/recipes?/|/recipe-|\brecipes?\b|how to make|\bfor two\b|\bmake[- ]ahead\b"
    r"|\bskillet\b|\bslow[- ]cooker\b|\bgrilled\b|\bbraised\b|\bkebabs?\b"
    r"|\bsalad\b|\bsoup\b|\btacos?\b|\bnoodles?\b|\bpopcorn\b|\bguacamole\b"
    r"|\bmarinade\b|\bpoached\b|\broasted\b|\bglaze\b|\bdrumsticks?\b", re.I)

#: 反過來，標題長這樣的幾乎一定是評測。**這一張先看**：
#: 「The Best Hot Sauce for Wings」是評測，不是雞翅食譜。
_REVIEWISH = re.compile(
    r"\bbest\b|\branked?\b|\breview\b|taste test|we tried|we tested|\btasting\b"
    r"|\bvs\.?\b|\btop \d+\b|\bworst\b|tried every|\bbrands?\b", re.I)


def looks_like_review(title: str, url: str) -> bool:
    """這一篇是評測還是食譜。評測型的標題優先，其餘看網址與標題有沒有食譜的痕跡。"""
    blob = f"{title} {url}"
    if _REVIEWISH.search(title or ""):
        return True
    return not _RECIPE.search(blob)


def _stratify(items: list[dict[str, Any]], key: str = "outlet") -> list[dict[str, Any]]:
    """跨 outlet 輪流取。取前 N 筆會拿到同一家的前 N 篇——
    第一次冷啟動的 20 筆全部來自 America's Test Kitchen，就是這樣來的。"""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        buckets.setdefault(str(item.get(key) or ""), []).append(item)
    order = sorted(buckets)
    out: list[dict[str, Any]] = []
    i = 0
    while any(buckets[k] for k in order):
        for k in order:
            if buckets[k]:
                out.append(buckets[k].pop(0))
        i += 1
    return out


def _bridge() -> Any:
    """llm-bridge 是隔壁的本機套件，不是 pip 相依。找不到就講清楚，不要假裝可用。"""
    root = Path(r"C:\Users\luke_\Desktop\AI\2-local-only\llm-bridge")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import llm_bridge

    return llm_bridge


# ---------------------------------------------------------------- 產品標題解析

def product_items(store: Store, limit: int | None = None) -> list[dict[str, Any]]:
    """還沒被解析過的產品／提及觀察。已經有 parsed 事件的不重跑（冪等）。"""
    done = {ev.payload.get("observation_event_id")
            for ev in store.all_events() if ev.event_type == contract.EV_PARSED}
    items: list[dict[str, Any]] = []
    for ev in store.all_events():
        if ev.event_type not in (contract.EV_PRODUCT, contract.EV_MENTION):
            continue
        if ev.event_id in done:
            continue
        title = str(ev.payload.get("title") or ev.payload.get("name") or "").strip()
        if not title:
            continue
        items.append({
            "event_id": ev.event_id, "source": ev.source, "entity_id": ev.entity_id,
            "raw_title": title, "raw_brand": str(ev.payload.get("brand") or ""),
            "raw_url": ev.source_url or "",
            "us_availability": str(ev.payload.get("us_availability") or "unknown"),
            "input": json.dumps({"title": title,
                                 "brand_hint": str(ev.payload.get("brand") or "")},
                                ensure_ascii=False),
        })
        if limit and len(items) >= limit:
            break
    return items


def validate_product(out: dict[str, Any], item: dict[str, Any]) -> str | None:
    """任務不變式（A10 第二層）。模型不得憑空造字。"""
    source_text = f"{item['raw_title']} {item['raw_brand']}"
    brand, product = str(out.get("brand") or ""), str(out.get("product") or "")
    if not product.strip():
        return "product 是空的"
    if brand.strip() and not contains_key(source_text, fold(brand)):
        return f"brand {brand!r} 折疊後不是來源字串的連續詞串"
    if not contains_key(source_text, fold(product)):
        return f"product {product!r} 折疊後不是來源字串的連續詞串"
    variant = str(out.get("variant") or "")
    if variant.strip() and fold(variant) == fold(product):
        return "variant 不可以等於 product"
    shu = out.get("heat_shu")
    if shu not in (None, "", 0):
        try:
            if int(shu) <= 0:
                return "heat_shu 要是正整數或空的"
        except (TypeError, ValueError):
            return f"heat_shu {shu!r} 不是整數"
    return None


def product_events(items: list[dict[str, Any]], outputs: list[dict[str, Any]],
                   model_id: str, prompt_version: str, observed_at: str) -> list[Event]:
    out: list[Event] = []
    for item, parsed in zip(items, outputs):
        if parsed is None:
            continue
        out.append(Event(
            entity_type="sauce_extraction",
            entity_id=item["entity_id"],
            event_type=contract.EV_PARSED,
            observed_at=observed_at, source=item["source"],
            source_record_id=item["event_id"], source_url=item["raw_url"] or None,
            ingest_path=IngestPath.SDK.value,
            payload={"observation_event_id": item["event_id"],
                     "raw_title": item["raw_title"], "raw_brand": item["raw_brand"],
                     "brand": parsed.get("brand", ""), "product": parsed.get("product", ""),
                     "variant": parsed.get("variant", ""),
                     "heat_shu": parsed.get("heat_shu") or "",
                     "heat_basis": parsed.get("heat_basis", ""),
                     "us_availability": item["us_availability"],
                     "evidence_url": item["raw_url"],
                     "confidence": parsed.get("confidence", ""),
                     "model_id": model_id, "prompt_version": prompt_version}))
    return out


# ---------------------------------------------------------------- 評論評語抽取

def review_items(store: Store, home: Home, limit: int | None = None) -> list[dict[str, Any]]:
    done = {ev.payload.get("review_id")
            for ev in store.all_events() if ev.event_type == contract.EV_VERDICT}
    items: list[dict[str, Any]] = []
    skipped_recipe = 0
    for ev in store.all_events():
        if ev.event_type != contract.EV_REVIEW:
            continue
        review_id = str(ev.payload.get("review_id") or "")
        if not review_id or review_id in done or not ev.raw_ref:
            continue
        path = home.root / ev.raw_ref
        if not path.exists():
            continue
        body = normalize_whitespace(path.read_text(encoding="utf-8", errors="replace"))
        if len(body) < 400:
            continue
        if not looks_like_review(str(ev.payload.get("title") or ""), ev.source_url or ""):
            skipped_recipe += 1
            continue
        items.append({
            "event_id": ev.event_id, "review_id": review_id,
            "review_entity_id": ev.entity_id,
            "outlet": str(ev.payload.get("outlet") or ""),
            "url": ev.source_url or "", "body": body,
            "truncated": len(body) > BODY_CHARS,
            "input": json.dumps({"title": str(ev.payload.get("title") or ""),
                                 "body": body[:BODY_CHARS]}, ensure_ascii=False),
        })
    items = _stratify(items)
    if limit:
        items = items[:limit]
    return items


def validate_verdicts(out: dict[str, Any], item: dict[str, Any]) -> str | None:
    """A25／A26 的前置關卡：引文必須是正文的子字串，原生分數必須逐字。"""
    verdicts = out.get("verdicts")
    if not isinstance(verdicts, list):
        return "verdicts 要是陣列"
    body = normalize_whitespace(item["body"])[:BODY_CHARS]
    for i, v in enumerate(verdicts):
        if not isinstance(v, dict):
            return f"verdicts[{i}] 不是物件"
        name = normalize_whitespace(str(v.get("sauce_name_raw") or ""))
        if not name:
            return f"verdicts[{i}] 缺 sauce_name_raw"
        if name.lower() not in body.lower():
            return f"verdicts[{i}] 的 sauce_name_raw {name!r} 不在正文裡"
        if v.get("stance") not in contract.STANCE:
            return f"verdicts[{i}] 的 stance {v.get('stance')!r} 不在允許值內"
        quote = normalize_whitespace(str(v.get("quote") or ""))
        if not (20 <= len(quote) <= 500):
            return f"verdicts[{i}] 的 quote 長度 {len(quote)} 不在 20–500 之間"
        if quote not in body:
            return f"verdicts[{i}] 的 quote 不是正文的子字串（不可以改寫）"
        scale = str(v.get("score_scale") or "none")
        if scale not in SCALES:
            return f"verdicts[{i}] 的 score_scale {scale!r} 不在允許值內"
        if scale != "none" and not str(v.get("score_raw") or "").strip():
            return f"verdicts[{i}] 有 score_scale 卻沒有 score_raw"
    return None


def verdict_events(items: list[dict[str, Any]], outputs: list[dict[str, Any]],
                   model_id: str, prompt_version: str, observed_at: str) -> list[Event]:
    from .scores import normalize as normalize_score

    out: list[Event] = []
    for item, parsed in zip(items, outputs):
        if parsed is None:
            continue
        body = normalize_whitespace(item["body"])[:BODY_CHARS]
        for n, v in enumerate(parsed.get("verdicts") or [], start=1):
            quote = normalize_whitespace(str(v.get("quote") or ""))
            scale = str(v.get("score_scale") or "none")
            raw = str(v.get("score_raw") or "")
            # entity_id 用評論自己的正式身分（`review:` 命名空間），**不是 `src:`**。
            # 核心的 orphans 只數 `src:` 開頭的事件；讓 verdict 落在 `review:` 上，
            # 「孤兒」這個詞在這個領域裡就只剩一個意思：**沒有任何 verdict 連到產品的那些評論**，
            # 而那正是 A27 要數的東西。verdict 自己不該被數成孤兒。
            out.append(Event(
                entity_type="sauce_verdict",
                entity_id=item["review_id"],
                event_type=contract.EV_VERDICT,
                observed_at=observed_at, source=outlet_web.SOURCE,
                source_record_id=f"{item['review_id']}#{n}", source_url=item["url"] or None,
                ingest_path=IngestPath.SDK.value,
                related=({"role": "review", "entity_id": item["review_entity_id"]},),
                payload={
                    "review_id": item["review_id"], "review_event_id": item["event_id"],
                    "outlet": item["outlet"],
                    "sauce_entity_id": "", "sauce_name_raw": str(v.get("sauce_name_raw") or ""),
                    "stance": v.get("stance", ""),
                    "score_raw": raw, "score_scale": scale,
                    "score_norm": normalize_score(raw, scale),
                    "rank_in_article": v.get("rank_in_article", ""),
                    "of_total": v.get("of_total", ""),
                    "quote": quote, "quote_offset": body.find(quote), "quote_len": len(quote),
                    "descriptors": v.get("descriptors") or [],
                    "body_truncated": item["truncated"],
                    "model_id": model_id, "prompt_version": prompt_version}))
    return out


# ---------------------------------------------------------------- 執行

def _run_batch(task: str, items: list[dict[str, Any]], validate: Any,
               model_id: str | None, pilot_n: int, out: Any) -> tuple[list[Any], str, str]:
    bridge = _bridge()
    result = bridge.chat_batch(items, task_type=task, validate=validate,
                               model_id=model_id, pilot_n=pilot_n, degraded_ok=False,
                               prompts_dir=PROMPTS, runs_dir=RUNS, out=out)
    if not result.ok:
        raise SystemExit(result.exit_code)
    records = _read_outputs(Path(result.report_dir) / "outputs.jsonl")
    config = json.loads((Path(result.report_dir) / "report.json").read_text(encoding="utf-8")
                        )["config"] if (Path(result.report_dir) / "report.json").exists() else {}
    return records, str(config.get("model_id", model_id or "")), str(
        config.get("prompt_version_hash", ""))


def _read_outputs(path: Path) -> list[Any]:
    if not path.exists():
        return []
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r.get("output") if not (r.get("schema_error") or r.get("invariant_error")) else None
            for r in rows]


def run(home: Home, what: str = "all", limit: int | None = None,
        model_id: str | None = None, pilot_n: int = 20, log: Any = None) -> dict[str, Any]:
    log = log or sys.stdout
    observed_at = now_iso()
    summary: dict[str, Any] = {}
    with Store(home, read_only=True) as store:
        products = product_items(store, limit) if what in ("all", "products") else []
        reviews = review_items(store, home, limit) if what in ("all", "reviews") else []

    if products:
        records, model, version = _run_batch(TASK_PRODUCT, products, validate_product,
                                             model_id, pilot_n, log)
        events = product_events(products, records, model, version, observed_at)
        summary["products"] = {"items": len(products), "events": len(events),
                               "model_id": model, "prompt_version": version}
        Spool(home, tag="sauce-extract-products").write(events)
    if reviews:
        records, model, version = _run_batch(TASK_VERDICT, reviews, validate_verdicts,
                                             model_id, pilot_n, log)
        events = verdict_events(reviews, records, model, version, observed_at)
        summary["reviews"] = {"items": len(reviews), "events": len(events),
                              "model_id": model, "prompt_version": version}
        Spool(home, tag="sauce-extract-verdicts").write(events)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.extract")
    ap.add_argument("--home", default=None)
    ap.add_argument("--what", choices=("all", "products", "reviews"), default="all")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--model-id", default=None, help="釘住的模型 id；換掉就中止（A12）")
    ap.add_argument("--pilot-n", type=int, default=20)
    ns = ap.parse_args(argv)
    home = Home.resolve(ns.home)
    out = run(home, ns.what, ns.limit, ns.model_id, ns.pilot_n)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
