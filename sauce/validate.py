"""A10：抽取不變式。三層依序檢查，任一層失敗就 exit 1 並印出規則名稱。

    python -m sauce.validate --home .evdb

1. **schema**（必須 100% 通過）
   每個 `sauce.extraction.parsed` 要有 `brand`、`product`、`model_id`、`prompt_version`；
   每個 `sauce.review.verdict` 要有 `review_id`、`sauce_entity_id`、`stance`、`quote`、
   `model_id`、`prompt_version`。

2. **任務不變式**（機械可判）
   折疊後的鍵是來源字串的連續詞串、`heat_shu` 空或正整數、`us_availability` 與 `stance`
   在值域內、`variant` 不等於 `product`。

3. **與人工標註集一致**（**第二次執行起才啟用**）
   抽樣 ≥40 筆與 `sauce/pilot/sample-v1.jsonl` 的裁決比對，不一致率 > 10% 即失敗。
   第一次執行時那份標註集還沒有人看過，所以這一層會回報 skipped 而不是 pass——
   **「還沒有人驗過」與「驗過了沒問題」不可以印成同一個字。**
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home
from evdb.store import Store

from . import contract
from .names import contains_key, fold
from .scores import SCALES

PILOT = Path(__file__).resolve().parent / "pilot" / "sample-v1.jsonl"
MAX_DISAGREEMENT = 0.10
MIN_SAMPLE = 40

PARSED_REQUIRED = ("brand", "product", "model_id", "prompt_version")
VERDICT_REQUIRED = ("review_id", "sauce_entity_id", "stance", "quote", "model_id",
                    "prompt_version")


def layer_schema(events: list[Any]) -> list[str]:
    problems: list[str] = []
    for ev in events:
        if ev.event_type == contract.EV_PARSED:
            missing = [k for k in PARSED_REQUIRED if k not in ev.payload]
            if missing:
                problems.append(f"schema:parsed_required {ev.event_id} 缺 {missing}")
        elif ev.event_type == contract.EV_VERDICT:
            missing = [k for k in VERDICT_REQUIRED if k not in ev.payload]
            if missing:
                problems.append(f"schema:verdict_required {ev.event_id} 缺 {missing}")
    return problems


def layer_invariants(events: list[Any]) -> list[str]:
    problems: list[str] = []
    for ev in events:
        if ev.event_type == contract.EV_PARSED:
            source_text = f"{ev.payload.get('raw_title', '')} {ev.payload.get('raw_brand', '')}"
            brand = str(ev.payload.get("brand") or "")
            product = str(ev.payload.get("product") or "")
            if brand and not contains_key(source_text, fold(brand)):
                problems.append(f"invariant:brand_key_from_source {ev.event_id} {brand!r}")
            if not product or not contains_key(source_text, fold(product)):
                problems.append(f"invariant:product_key_from_source {ev.event_id} {product!r}")
            variant = str(ev.payload.get("variant") or "")
            if variant and fold(variant) == fold(product):
                problems.append(f"invariant:variant_not_product {ev.event_id}")
            shu = ev.payload.get("heat_shu")
            if shu not in (None, "", 0):
                try:
                    if int(shu) <= 0:
                        problems.append(f"invariant:heat_shu_positive {ev.event_id} {shu!r}")
                except (TypeError, ValueError):
                    problems.append(f"invariant:heat_shu_integer {ev.event_id} {shu!r}")
            avail = str(ev.payload.get("us_availability") or "")
            if avail and avail not in contract.US_AVAILABILITY:
                problems.append(f"invariant:us_availability_enum {ev.event_id} {avail!r}")
        elif ev.event_type == contract.EV_VERDICT:
            if ev.payload.get("stance") not in contract.STANCE:
                problems.append(f"invariant:stance_enum {ev.event_id} "
                                f"{ev.payload.get('stance')!r}")
            scale = str(ev.payload.get("score_scale") or "none")
            if scale not in SCALES:
                problems.append(f"invariant:score_scale_enum {ev.event_id} {scale!r}")
    return problems


def layer_pilot(events: list[Any], path: Path = PILOT) -> tuple[str, list[str], dict[str, Any]]:
    """回傳 (狀態, 問題, 統計)。狀態是 pass / fail / skipped。"""
    if not path.exists():
        return "skipped", [], {"reason": f"標註集還不存在：{path}"}
    items = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    judged = [i for i in items if i.get("human_verdict") in ("correct", "incorrect")]
    if len(judged) < MIN_SAMPLE:
        return "skipped", [], {"reason": f"人工裁決只有 {len(judged)} 筆，未達 {MIN_SAMPLE}；"
                                          "第一次執行時這是預期的（A11 的交付物）",
                               "items": len(items), "judged": len(judged)}
    by_id = {ev.event_id: ev for ev in events}
    disagreements: list[str] = []
    compared = 0
    for item in judged:
        ev = by_id.get(item.get("event_id"))
        if ev is None:
            continue
        compared += 1
        if item["human_verdict"] == "incorrect":
            disagreements.append(f"pilot:human_says_incorrect {ev.event_id} "
                                 f"{item.get('human_note', '')}")
    rate = len(disagreements) / compared if compared else 0.0
    stats = {"compared": compared, "disagreements": len(disagreements),
             "rate": round(rate, 4), "max_rate": MAX_DISAGREEMENT}
    if compared < MIN_SAMPLE:
        return "skipped", [], {**stats, "reason": "對得上的樣本不足"}
    return ("fail" if rate > MAX_DISAGREEMENT else "pass"), disagreements, stats


def run(home: Home) -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    schema = layer_schema(events)
    invariants = layer_invariants(events) if not schema else []
    pilot_status, pilot_problems, pilot_stats = ("skipped", [], {}) if (schema or invariants) \
        else layer_pilot(events)
    ok = not schema and not invariants and pilot_status != "fail"
    return {"events": len(events),
            "layer_1_schema": {"ok": not schema, "problems": schema[:20],
                               "total": len(schema)},
            "layer_2_invariants": {"ok": not invariants, "problems": invariants[:20],
                                   "total": len(invariants)},
            "layer_3_pilot": {"status": pilot_status, "problems": pilot_problems[:20],
                              **pilot_stats},
            "ok": ok}


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m sauce.validate")
    ap.add_argument("--home", default=None)
    ns = ap.parse_args(argv)
    out = run(Home.resolve(ns.home))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
