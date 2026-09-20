"""標籤判讀 × 獨立成分文字的交叉驗證。

    python -m sauce.crosscheck --home .evdb        # 算一遍，寫報告
    python -m sauce.crosscheck --build-index       # 只重建參照表

Stanley 2026-09-20：「OCR 內容要跟 research results 再交叉驗證」。

## 為什麼非做不可

照片判讀是整份語料庫裡**唯一沒有原文可以比對**的一層：評語可以驗引文是不是正文的
逐字子字串（A25），標籤判讀的原文是一張圖。詞庫覆蓋率（A39）只擋得住模型整批造字，
擋不住三件事——**順序錯、數字錯、漏掉一行**。

而那三件事真的會發生。實測到的兩個例子：

- 一張 Kroger 莎莎醬的照片同時拍到營養標示與成分表（瓶身是圓的，一圈都進去了），
  模型把 `CALCIUM 10MG * POTASSIUM 10MG` 插進成分表裡，還漏掉六項。
- 一瓶「Sweet Thai Style Chili Sauce」被讀成番茄、洋蔥、香菜——那是莎莎醬的成分。

兩個都會通過形狀檢查，也都會通過詞庫覆蓋率。

## 拿什麼來比

**同一個 GTIN 在 Open Food Facts 上的 `ingredients_text`**——那是別人打字key進去的，
跟我們的照片判讀是兩條互相獨立的路徑。兩邊都錯成同一個樣子的機率很低。

比法是**詞的回收率**，不是字串相等：
- OFF 那邊的成分詞，有多少出現在我們的轉錄裡（`recall`）；
- 我們轉錄裡的詞，有多少在 OFF 那邊找得到（`precision`）。

`recall` 低 = 我們漏讀；`precision` 低 = 我們多讀了不該有的東西（例如營養數字、
或整個讀錯產品）。**兩個分開看**，因為它們對應到的是兩種不同的錯。

## 這條檢查驗不到什麼

- OFF 沒有那個 GTIN 的成分文字時（多數小廠）**完全驗不到**——覆蓋率本身要報出來，
  否則「沒驗到」會被當成「驗過了」。
- 兩邊都抄同一份廠商資料時會一起錯，而且分數會很漂亮。
- **順序**驗不到：詞的集合一樣、順序顛倒，recall 與 precision 都是 1.0。
  美國標籤的成分順序代表含量多寡，所以這個缺口是真的，只是沒有更好的機械辦法。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home
from evdb.store import Store

from . import contract, harvest
from .names import gtin14
from .sources import off

INDEX = Path(__file__).resolve().parent.parent / "state" / "crosscheck" / "off-ingredients.jsonl"
REPORT = Path(__file__).resolve().parent.parent / "reports" / "sauce-label-crosscheck.md"

#: 低於這個回收率就當成「讀錯了」，列進報告最前面給人看。
LOW_RECALL = 0.50
#: 低於這個精確率代表轉錄裡混進了不屬於成分表的東西（多半是營養標示）。
LOW_PRECISION = 0.50

#: 比對時忽略的詞：連接詞、單位、以及成分表裡到處都是的修飾語。
_STOP = {"and", "or", "the", "of", "with", "less", "than", "contains", "ingredients",
         "ingredient", "may", "each", "other", "from", "for", "added", "includes",
         "organic", "natural", "artificial", "concentrate", "powder", "extract",
         "juice", "puree", "dried", "ground", "whole", "fresh", "pure"}
_WORD = re.compile(r"[a-z][a-z'\-]{2,}")

#: 營養標示的詞。**兩邊都要濾掉**，而不是只濾我們這邊：
#: OFF 的 `ingredients_text` 有一部分是貢獻者把整張背標貼進去的，
#: 不濾的話「漏讀」清單裡會是 calories、cholesterol、daily——
#: 那不是我們漏讀，是參照本身不只有成分表。
_NUTRITION = {
    "nutrition", "facts", "serving", "servings", "size", "container", "amount",
    "amounte", "calories", "calorie", "total", "fat", "saturated", "trans", "cholesterol",
    "sodium", "carbohydrate", "carbohydrates", "carb", "fiber", "fibre", "sugars", "sugar",
    "protein", "vitamin", "calcium", "iron", "potassium", "daily", "value", "values",
    "percent", "diet", "advice", "contributes", "day", "nutrient", "nutrients", "mcg",
    "distributed", "manufactured", "packed", "refrigerate", "opening", "after", "shake",
    "well", "before", "use", "inc", "llc", "company", "usa", "net", "about", "general",
    "used", "storage", "keep", "cool", "place", "best", "product", "products"}

#: 成分表結束的地方。到這裡就停，後面是營養標示或公司地址。
_END_OF_INGREDIENTS = re.compile(
    r"(?:nutrition\s+facts|serving\s+size|amount\s*/?\s*serving|calories\s+per|"
    r"distributed\s+by|manufactured\s+(?:by|for)|refrigerate\s+after)", re.I)
_START_OF_INGREDIENTS = re.compile(r"ingredients?\s*:?", re.I)


def ingredients_only(text: str) -> str:
    """把一段文字切到成分表那一段。切不出來就原樣回傳（不猜）。"""
    body = str(text or "")
    m = _START_OF_INGREDIENTS.search(body)
    if m:
        body = body[m.end():]
    end = _END_OF_INGREDIENTS.search(body)
    if end:
        body = body[:end.start()]
    return body.strip()


def words(text: str) -> set[str]:
    return {w for w in _WORD.findall(ingredients_only(text).lower())
            if w not in _STOP and w not in _NUTRITION}


def build_index(export: Path | None = None, out: Path | None = None) -> dict[str, Any]:
    """從 OFF 全量匯出抽出 `GTIN → ingredients_text`，只留有成分文字的列。

    整份匯出是 1.27 GB，掃一遍要幾分鐘；抽出來的索引只有幾 MB，
    所以掃一次存起來，之後每次交叉驗證都讀這一份。
    """
    path = Path(export) if export else None
    if path is None:
        found = sorted(Path(harvest.STATE).glob(f"snapshot-*/off/{off.EXPORT_NAME}"))
        if not found:
            return {"rows": 0, "reason": "no_off_export"}
        path = found[0]
    dest = Path(out or INDEX)
    dest.parent.mkdir(parents=True, exist_ok=True)

    csv.field_size_limit(10_000_000)
    kept = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh, \
            dest.open("w", encoding="utf-8", newline="\n") as out_fh:
        for row in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            text = (row.get("ingredients_text") or "").strip()
            code = (row.get("code") or "").strip()
            if not text or not code:
                continue
            out_fh.write(json.dumps({"gtin": gtin14(code), "text": text[:4000]},
                                    ensure_ascii=False) + "\n")
            kept += 1
    return {"rows": kept, "path": str(dest)}


def load_index(path: Path | None = None) -> dict[str, str]:
    p = Path(path or INDEX)
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                out[row["gtin"]] = row["text"]
    return out


def agreement(transcript: str, reference: str) -> dict[str, Any]:
    """(回收率, 精確率, 兩邊各自獨有的詞)。**兩個數字分開報，因為它們是兩種錯。**"""
    ours = words(transcript)
    theirs = words(reference)
    if not theirs:
        return {"recall": None, "precision": None, "missing": [], "extra": []}
    hit = ours & theirs
    return {
        "recall": round(len(hit) / len(theirs), 3),
        "precision": round(len(hit) / len(ours), 3) if ours else 0.0,
        "missing": sorted(theirs - ours)[:12],     # 我們漏讀的
        "extra": sorted(ours - theirs)[:12],       # 我們多讀的
    }


def run(home: Home, index_path: Path | None = None) -> dict[str, Any]:
    reference = load_index(index_path)
    if not reference:
        return {"checked": 0, "reason": f"參照表不存在，先跑 --build-index（{INDEX}）"}

    with Store(home, read_only=True) as store:
        reads = [ev for ev in store.all_events()
                 if ev.event_type == contract.EV_LABEL_READ
                 and str(ev.payload.get("panel_kind") or "") == "ingredients"]

    rows: list[dict[str, Any]] = []
    no_reference = 0
    for ev in reads:
        gtin = gtin14(str(ev.payload.get("gtin") or ""))
        ref = reference.get(gtin, "")
        if not ref:
            no_reference += 1
            continue
        scored = agreement(str(ev.payload.get("transcript") or ""), ref)
        rows.append({"gtin": gtin, "hint": str(ev.payload.get("product_hint") or "")[:60],
                     "transcript": str(ev.payload.get("transcript") or "")[:400],
                     "reference": ref[:400], **scored})

    bad = [r for r in rows
           if (r["recall"] is not None and r["recall"] < LOW_RECALL)
           or (r["precision"] is not None and r["precision"] < LOW_PRECISION)]
    _write_report(rows, bad, len(reads), no_reference)

    checked = len(rows)
    return {
        "label_reads": len(reads), "cross_checked": checked,
        "no_reference": no_reference,
        "coverage": round(checked / len(reads), 3) if reads else 0.0,
        "median_recall": _median([r["recall"] for r in rows]),
        "median_precision": _median([r["precision"] for r in rows]),
        "suspect": len(bad), "report": str(REPORT),
    }


def _median(values: list[Any]) -> Any:
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return None
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else round((xs[mid - 1] + xs[mid]) / 2, 3)


def _write_report(rows: list[dict[str, Any]], bad: list[dict[str, Any]],
                  reads: int, no_reference: int) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 標籤判讀 × OFF 成分文字 交叉驗證",
        "",
        f"判讀 {reads} 筆　對得到獨立成分文字的 {len(rows)} 筆　"
        f"**沒有參照可比的 {no_reference} 筆**",
        "",
        "比的是**詞的回收率與精確率**，不是字串相等：",
        "回收率低＝我們漏讀；精確率低＝我們多讀了不該有的（多半是營養標示混進來）。",
        "",
        "**沒有參照可比的那幾筆完全沒有被驗過**，而它們在總表上跟驗過的長得一模一樣。",
        "",
        f"## 可疑的 {len(bad)} 筆（回收率 < {LOW_RECALL:.0%} 或 精確率 < {LOW_PRECISION:.0%}）",
        "",
    ]
    for r in sorted(bad, key=lambda x: (x["recall"] or 0)):
        lines += [f"### {r['hint'] or r['gtin']}",
                  "",
                  f"回收率 {r['recall']}　精確率 {r['precision']}",
                  "",
                  f"- 漏讀：{', '.join(r['missing']) or '—'}",
                  f"- 多讀：{', '.join(r['extra']) or '—'}",
                  "",
                  f"```\n我們讀到： {r['transcript'][:300]}\nOFF 的文字： {r['reference'][:300]}\n```",
                  ""]
    lines += ["## 全部", "", "| 產品 | 回收率 | 精確率 | 漏讀 |", "|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["recall"] or 0)):
        lines.append(f"| {r['hint'] or r['gtin']} | {r['recall']} | {r['precision']} | "
                     f"{', '.join(r['missing'][:5]) or '—'} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def score_pending(pending: Path, items: list[dict[str, Any]],
                  index_path: Path | None = None) -> dict[str, Any]:
    """在 promote **之前**先驗待審檔。

    冷啟動的待審檔還不是事件，所以 `run()` 看不到它——但那正是最該驗的時機：
    golden 一旦 promote，後面幾百筆都會照著它跑。
    """
    reference = load_index(index_path)
    rows: list[dict[str, Any]] = []
    no_reference = 0
    pend = [json.loads(ln) for ln in pending.read_text(encoding="utf-8").splitlines()
            if ln.strip()]
    for record, item in zip(pend, items):
        exp = record.get("expected")
        transcript = str(exp.get("transcript") or "") if isinstance(exp, dict) else ""
        gtin = gtin14(str(item.get("gtin") or ""))
        ref = reference.get(gtin, "")
        if not ref:
            no_reference += 1
            continue
        rows.append({"gtin": gtin, "hint": str(item.get("product_hint") or "")[:60],
                     "transcript": transcript[:400], "reference": ref[:400],
                     **agreement(transcript, ref)})
    bad = [r for r in rows
           if (r["recall"] is not None and r["recall"] < LOW_RECALL)
           or (r["precision"] is not None and r["precision"] < LOW_PRECISION)]
    return {"pending": len(pend), "cross_checked": len(rows),
            "no_reference": no_reference,
            "median_recall": _median([r["recall"] for r in rows]),
            "median_precision": _median([r["precision"] for r in rows]),
            "suspect": bad, "rows": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.crosscheck")
    ap.add_argument("--home", default=None)
    ap.add_argument("--build-index", action="store_true")
    ap.add_argument("--export", default=None)
    ns = ap.parse_args(argv)
    if ns.build_index:
        print(json.dumps(build_index(Path(ns.export) if ns.export else None),
                         ensure_ascii=False, indent=1))
        return 0
    print(json.dumps(run(Home.resolve(ns.home)), ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
