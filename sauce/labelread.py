"""標籤照片 → 逐字轉錄（A38）。**模型只做轉錄，不做判斷。**

    python -m sauce.labelread --home .evdb [--limit N] [--panel ingredients]

這一步與 `sauce/composition.py` 的分工是整份 v3 的關鍵界線：

- **這裡**：一張圖 → 上面印了什麼字。逐字、不改寫、不補全、不翻譯、不解釋。
- **那裡**：那些字 → `fermented`／`acidifier`／`heat_ceiling_shu` 這些欄位，**純規則、沒有模型**。

混在一起，那些欄位就不可重現了——同一張圖跑兩次會得到兩個答案，
而半年後沒有人回答得出「這個 `fermented=true` 是誰說的」。

## 這一層沒有子字串可以驗

評論的引文可以驗是不是正文的子字串（A36）。標籤判讀的「原文」是一張圖，
**沒有文字可以比對**。所以機械守門員只有兩個，而且都擋不住「讀錯」：

1. A38：判讀指得到一張真的存在的照片、說得出模型與 prompt 版本；
2. A39：轉錄出的成分詞落在詞庫外的比例 ≤ 8%，例外全部列進報告給人看。

擋得住「憑空造出不存在的成分」，擋不住「順序錯、數字錯、漏了一行」。
那正是 A41 要求試樣裡至少 20 筆是標籤判讀的理由。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home, now_iso
from evdb.schema import Event, IngestPath
from evdb.spool import Spool
from evdb.store import Store

from . import contract
from .extract import PROMPTS, RUNS, _bridge, _read_outputs

TASK = "sauce-label-read"
#: 視覺模型。釘住的文字模型（nemotron）收到圖會回 HTTP 400，見 DECISIONS D19。
VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

#: 轉錄至少要這麼長才算讀到東西。太短多半是模型回「看不清楚」。
MIN_TRANSCRIPT = 12

#: **網址的語言標記會說謊。** 實測到一張網址寫 `ingredients_en` 的圖，
#: 上面印的是 `SAUCE AU PIMENT ROUGE ... Ingrédients : Vinaigre`。
#: 所以語言要從轉錄出來的字判，不能只信網址。
NON_ENGLISH = ("ingrédients", "ingredientes", "zutaten", "ingredienti",
               "ingrediënten", "składniki", "成分", "原材料")


#: 只判讀英文面板。非英文的轉錄是對的，但下游（成分詞庫、交叉驗證）全是英文的，
#: 所以那幾張判了也用不到——**而每一張要花六千多個 token**。
LANGS = ("en", "")


def label_items(store: Store, home: Home, limit: int | None = None,
                panel: str | None = None,
                langs: tuple[str, ...] = LANGS) -> list[dict[str, Any]]:
    """還沒判讀過的標籤照片。已經有 `sauce.label.read` 的不重跑（冪等）。"""
    done = {str(ev.payload.get("label_image_sha256") or "")
            for ev in store.all_events() if ev.event_type == contract.EV_LABEL_READ}
    items: list[dict[str, Any]] = []
    for ev in store.all_events():
        if ev.event_type != contract.EV_LABEL_IMAGE:
            continue
        sha = str(ev.payload.get("image_sha256") or "")
        kind = str(ev.payload.get("panel_kind") or "")
        if not sha or sha in done or not ev.raw_ref:
            continue
        if panel and kind != panel:
            continue
        if langs and str(ev.payload.get("lang") or "") not in langs:
            continue
        path = home.root / ev.raw_ref
        if not path.exists():
            continue
        items.append({
            "event_id": ev.event_id, "label_image_sha256": sha, "panel_kind": kind,
            "gtin": str(ev.payload.get("gtin") or ""),
            "product_hint": str(ev.payload.get("product_hint") or ""),
            "source_url": ev.source_url or "",
            # llm-bridge 的批次層看到 image_path 就會改送 content blocks（見 D19）
            "image_path": str(path),
            "input": json.dumps({"panel_kind": kind,
                                 "product_hint": str(ev.payload.get("product_hint") or "")},
                                ensure_ascii=False),
        })
        if limit and len(items) >= limit:
            break
    return items


#: golden 比對的門檻。自由文字不可能逐字重現，所以比的是**詞的重疊**。
GOLDEN_MIN_OVERLAP = 0.80


def transcripts_agree(value: Any, expected: Any) -> bool:
    """golden 比對：同一張圖兩次判讀的**詞**要有八成重疊，不要求一字不差。

    逐字比對在這裡是錯的門檻。實測：同樣 19 張圖重跑一次，
    逐字一致率 16%——而那 16 筆的內容其實都對，只是換了幾個標點、
    或把 `(FROM CONCENTRATE)` 寫成 `FROM CONCENTRATE`。
    用逐字當關卡，等於要求一個非決定性的模型表現得像決定性的。

    **門檻訂在詞的重疊而不是相似度**，因為我們真正在意的是「有沒有漏成分」，
    不是「字面像不像」。
    """
    if not isinstance(value, dict) or not isinstance(expected, dict):
        return value == expected
    ours = _words(str(value.get("transcript") or ""))
    theirs = _words(str(expected.get("transcript") or ""))
    if not theirs:
        return not ours
    return len(ours & theirs) / len(theirs) >= GOLDEN_MIN_OVERLAP


def _words(text: str) -> set[str]:
    import re
    return set(re.findall(r"[a-z][a-z'\-]{2,}", str(text or "").lower()))


def validate_read(out: dict[str, Any], item: dict[str, Any]) -> str | None:
    """能機械驗的只有形狀，驗不了「讀得對不對」——那一層要人看（見模組說明）。"""
    transcript = str(out.get("transcript") or "").strip()
    if len(transcript) < MIN_TRANSCRIPT:
        return f"transcript 只有 {len(transcript)} 個字元，太短"
    if out.get("panel_kind") not in ("ingredients", "nutrition", "front", "other", None, ""):
        return f"panel_kind {out.get('panel_kind')!r} 不在允許值內"
    legible = out.get("legible")
    if legible is False and transcript:
        return "宣稱看不清楚卻同時給了轉錄——兩者只能有一個"
    low = transcript.lower()
    if any(marker in low for marker in NON_ENGLISH):
        return "這張標籤不是英文的——下游的成分詞庫與交叉驗證都是英文，判了也用不到"
    return None


def read_events(items: list[dict[str, Any]], outputs: list[Any], model_id: str,
                prompt_version: str, observed_at: str) -> list[Event]:
    out: list[Event] = []
    for item, parsed in zip(items, outputs):
        if parsed is None:
            continue
        transcript = str(parsed.get("transcript") or "").strip()
        if not transcript:
            continue
        out.append(Event(
            entity_type="sauce_label_read",
            entity_id=contract.label_id(item["label_image_sha256"]),
            event_type=contract.EV_LABEL_READ,
            observed_at=observed_at, source="off_image",
            source_record_id=item["label_image_sha256"][:16],
            source_url=item["source_url"] or None,
            ingest_path=IngestPath.SDK.value,
            related=({"role": "label_image", "entity_id": contract.observation_id(
                "off_image", f"{item['gtin']}-{item['panel_kind']}")},),
            payload={"label_image_sha256": item["label_image_sha256"],
                     "label_image_event_id": item["event_id"],
                     "panel_kind": item["panel_kind"],
                     "gtin": item["gtin"], "product_hint": item["product_hint"],
                     "transcript": transcript,
                     "legible": parsed.get("legible", True),
                     "model_id": model_id, "prompt_version": prompt_version}))
    return out


def run(home: Home, limit: int | None = None, panel: str | None = None,
        model_id: str | None = None, pilot_n: int = 20, log: Any = None) -> dict[str, Any]:
    log = log or sys.stdout
    with Store(home, read_only=True) as store:
        items = label_items(store, home, limit, panel)
    if not items:
        return {"items": 0, "events": 0, "note": "沒有待判讀的標籤照片"}

    bridge = _bridge()
    result = bridge.chat_batch(items, task_type=TASK, validate=validate_read,
                               model_id=model_id or VISION_MODEL, pilot_n=pilot_n,
                               degraded_ok=False, prompts_dir=PROMPTS, runs_dir=RUNS,
                               out=log, golden_compare=transcripts_agree)
    if not result.ok:
        raise SystemExit(result.exit_code)
    records = _read_outputs(Path(result.report_dir) / "outputs.jsonl")
    report_path = Path(result.report_dir) / "report.json"
    config = json.loads(report_path.read_text(encoding="utf-8"))["config"] \
        if report_path.exists() else {}
    events = read_events(items, records, str(config.get("model_id", model_id or VISION_MODEL)),
                         str(config.get("prompt_version_hash", "")), now_iso())
    Spool(home, tag="sauce-label-reads").write(events)
    return {"items": len(items), "events": len(events),
            "model_id": config.get("model_id"), "run_dir": result.report_dir}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.labelread")
    ap.add_argument("--home", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--panel", default=None, choices=("ingredients", "nutrition", "front"))
    ap.add_argument("--model-id", default=None, help="釘住的視覺模型；換掉就中止（A16）")
    ap.add_argument("--pilot-n", type=int, default=20)
    ns = ap.parse_args(argv)
    out = run(Home.resolve(ns.home), ns.limit, ns.panel, ns.model_id, ns.pilot_n)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
