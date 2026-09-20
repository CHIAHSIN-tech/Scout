"""A41：首輪試樣。**第一次執行的交付物，不是關卡。**

    python -m sauce.pilot build --home .evdb --n 60
    python -m sauce.pilot check

產生 `sauce/pilot/sample-v1.jsonl`：n ≥ 60，其中 ≥20 筆是 `sauce.label.read`，其餘是產品名，每筆帶 `model_id`、`prompt_version`、
來源 `event_id` 與空白的人工裁決欄位。

人看過並填入裁決之後，這個檔就是 `sauce.validate` 第三層的標註集，第二次執行起三層全開。

## 人在看的時候到底該看什麼

不是「模型有沒有亂編」——那一層已經有機器在驗（A10 第二層、A25）。人要看的是兩件
**沒有任何自動檢查蓋得到**的事：

- **產品那 25 筆**：這些名字唸得出來嗎？`"Original Hot Sauce 5oz 2pk Value"` 完全可以
  通過所有機器檢查（它確實是來源字串的子字串），但它不是一個人會拿來稱呼那瓶醬的說法。
- **標籤判讀那 20 筆**：把 `image_path` 那張圖打開，逐字對。這一項**連「引文是不是子字串」
  這種機器檢查都沒有**——原文是一張圖。詞庫覆蓋率（A39）只擋得住模型整批造字，
  擋不住順序錯、數字錯、漏掉一行。**人不看，這三種錯誤永遠不會被發現。**
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home
from evdb.store import Store

from . import contract

SAMPLE = Path(__file__).resolve().parent / "pilot" / "sample-v1.jsonl"
MIN_ITEMS = 60
#: **不再要求評語。** 2026-09-20 起評論那條線只存連結不存評論內容（D27），
#: 而連結是規則比對出來的、機器驗得了，不需要人審。
#: 試樣要留的是**機器驗不了**的那兩種：名字唸不唸得出來、標籤讀得對不對。
MIN_VERDICTS = 0
MIN_LABEL_READS = 20

BLANK = {"human_verdict": None, "human_note": None, "reviewer": None, "reviewed_at": None}


def _stride(items: list[Any], n: int) -> list[Any]:
    """等距抽樣。取前 n 筆會偏向同一個來源（事件是按 entity_id 排序的）。"""
    if len(items) <= n:
        return list(items)
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def build(home: Home, n: int = MIN_ITEMS, min_verdicts: int = MIN_VERDICTS,
          min_label_reads: int = MIN_LABEL_READS) -> list[dict[str, Any]]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    parsed = [ev for ev in events if ev.event_type == contract.EV_PARSED]
    verdicts = [ev for ev in events if ev.event_type == contract.EV_VERDICT]
    reads = [ev for ev in events if ev.event_type == contract.EV_LABEL_READ]
    # 判讀要附圖給人開，所以先把「這張圖的雜湊 → 原始檔位置」查表建好
    image_ref = {str(ev.payload.get("image_sha256") or ""): (ev.raw_ref or "")
                 for ev in events if ev.event_type == contract.EV_LABEL_IMAGE}

    want_verdicts = min(min_verdicts, len(verdicts))
    want_reads = min(min_label_reads, len(reads))
    want_parsed = max(n - want_verdicts - want_reads, 0)
    items: list[dict[str, Any]] = []
    for ev in _stride(parsed, want_parsed):
        items.append({
            "id": len(items) + 1, "kind": "product", "event_id": ev.event_id,
            "source": ev.source, "source_url": ev.source_url,
            "raw_title": ev.payload.get("raw_title", ""),
            "raw_brand": ev.payload.get("raw_brand", ""),
            "extracted_brand": ev.payload.get("brand", ""),
            "extracted_product": ev.payload.get("product", ""),
            "extracted_variant": ev.payload.get("variant", ""),
            "heat_shu": ev.payload.get("heat_shu", ""),
            "model_id": ev.payload.get("model_id", ""),
            "prompt_version": ev.payload.get("prompt_version", ""),
            "ask_the_reviewer": "這個名字唸得出來嗎？是人會用來稱呼這瓶醬的說法嗎？",
            **BLANK})
    for ev in _stride(verdicts, want_verdicts):
        items.append({
            "id": len(items) + 1, "kind": "verdict", "event_id": ev.event_id,
            "source": ev.source, "source_url": ev.source_url,
            "review_id": ev.payload.get("review_id", ""),
            "outlet": ev.payload.get("outlet", ""),
            "sauce_name_raw": ev.payload.get("sauce_name_raw", ""),
            "stance": ev.payload.get("stance", ""),
            "score_raw": ev.payload.get("score_raw", ""),
            "score_scale": ev.payload.get("score_scale", ""),
            "quote": ev.payload.get("quote", ""),
            "model_id": ev.payload.get("model_id", ""),
            "prompt_version": ev.payload.get("prompt_version", ""),
            "ask_the_reviewer": "這句話是那篇評論對這款醬的重點嗎？（引文出自原文已由 A25 驗過）",
            **BLANK})
    for ev in _stride(reads, want_reads):
        sha = str(ev.payload.get("label_image_sha256") or "")
        items.append({
            "id": len(items) + 1, "kind": "label_read", "event_id": ev.event_id,
            "source": ev.source, "source_url": ev.source_url,
            "label_image_sha256": sha,
            "image_path": image_ref.get(sha, ""),
            "gtin": ev.payload.get("gtin", ""),
            "product_hint": ev.payload.get("product_hint", ""),
            "panel_kind": ev.payload.get("panel_kind", ""),
            "transcript": ev.payload.get("transcript", ""),
            "model_id": ev.payload.get("model_id", ""),
            "prompt_version": ev.payload.get("prompt_version", ""),
            "ask_the_reviewer": "把 image_path 那張圖打開，逐字對：順序、數字、有沒有漏行。"
                                "（這一項沒有任何機器檢查蓋得到）",
            **BLANK})
    return items


def write(items: list[dict[str, Any]], path: Path = SAMPLE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items),
                    encoding="utf-8")
    return path


def read(path: Path = SAMPLE) -> list[dict[str, Any]]:
    if not Path(path).exists():
        return []
    return [json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def check(path: Path = SAMPLE) -> dict[str, Any]:
    """A41 只檢查「檔案在、筆數夠、欄位齊」——裁決欄位允許是空白（那是給人填的）。"""
    items = read(path)
    verdicts = [i for i in items if i.get("kind") == "verdict"]
    reads = [i for i in items if i.get("kind") == "label_read"]
    required = ("event_id", "model_id", "prompt_version", "human_verdict")
    missing = [i.get("id") for i in items if any(k not in i for k in required)]
    judged = [i for i in items if i.get("human_verdict") in ("correct", "incorrect")]
    problems = []
    if len(items) < MIN_ITEMS:
        problems.append(f"只有 {len(items)} 筆，少於 {MIN_ITEMS}")
    if len(verdicts) < MIN_VERDICTS:
        problems.append(f"verdict 只有 {len(verdicts)} 筆，少於 {MIN_VERDICTS}")
    if len(reads) < MIN_LABEL_READS:
        problems.append(f"label_read 只有 {len(reads)} 筆，少於 {MIN_LABEL_READS}")
    if missing:
        problems.append(f"這些筆缺必要欄位：{missing[:10]}")
    return {"path": str(path), "items": len(items), "verdicts": len(verdicts),
            "label_reads": len(reads),
            "judged_by_human": len(judged), "problems": problems,
            "note": "裁決欄位空白是預期的：第一次執行時這份檔案是交付物，不是關卡",
            "ok": not problems}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.pilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--home", default=None)
    b.add_argument("--n", type=int, default=MIN_ITEMS)
    sub.add_parser("check")
    ns = ap.parse_args(argv)
    if ns.cmd == "build":
        path = write(build(Home.resolve(ns.home), ns.n))
        print(json.dumps({"written": str(path), **check(path)}, ensure_ascii=False, indent=1))
        return 0
    out = check()
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
