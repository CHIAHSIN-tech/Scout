"""A39：判讀不得憑空造字。

照片判讀沒有「子字串」可以驗——原文是一張圖，沒有文字可以比對。
所以這一層唯一的機械守門員是**詞庫覆蓋率**：轉錄出來的成分詞，
落在 `fixtures/sauce/ingredient-lexicon.csv` 之外的比例要 ≤ 8%，
**而且所有例外逐筆列進 `reports/sauce-label-oov.md` 給人看**。

講清楚它擋得住什麼、擋不住什麼：

- **擋得住**：模型憑空生出一整串不存在的成分（那些詞會整批落在詞庫外，比例直接爆掉）。
- **擋不住**：順序錯、數字錯、漏掉一行。那三種錯誤用的都是詞庫裡的詞，覆蓋率完全正常。

所以這一條過了**不等於**判讀是對的。要看對不對只能人看樣本——
那正是 A41 要求試樣裡至少 20 筆是標籤判讀的理由。
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

from ..contract import EV_LABEL_READ
from . import REPO, arg_parser, events, home_of, report

LEXICON = REPO / "fixtures" / "sauce" / "ingredient-lexicon.csv"
OOV_REPORT = REPO / "reports" / "sauce-label-oov.md"
MAX_OOV_RATE = 0.08

#: 數字、單位、百分比不算「詞」——它們本來就不會在詞庫裡
_TOKEN = re.compile(r"[a-z][a-z'\-]{2,}")
_NOISE = {"the", "for", "are", "not", "per", "you", "our", "all", "its", "this", "that",
          "from", "into", "than", "more", "less", "made", "product", "products",
          "ingredients", "ingredient", "nutrition", "facts", "serving", "servings",
          "size", "container", "amount", "daily", "value", "calories", "total", "dietary",
          "added", "includes", "protein", "sodium", "carbohydrate", "carbohydrates",
          "sugars", "fat", "saturated", "trans", "cholesterol", "fiber", "vitamin",
          "calcium", "iron", "potassium", "net", "wt", "oz", "fl", "ml", "gluten", "free",
          "refrigerate", "opening", "after", "keep", "shake", "well", "before", "use",
          "distributed", "manufactured", "packed", "usa", "inc", "llc", "company", "co"}


def lexicon(path: Path | None = None) -> set[str]:
    p = Path(path or LEXICON)
    if not p.exists():
        return set()
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return {(r.get("term") or "").strip().lower() for r in csv.DictReader(fh)
                if (r.get("term") or "").strip()}


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(str(text or "").lower()) if t not in _NOISE]


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.label_lexicon", rules=False).parse_args(argv)
    known = lexicon()
    if not known:
        return report("A39 label_lexicon", False, {},
                      [f"詞庫不存在或是空的：{LEXICON}"])

    total = 0
    oov = Counter()
    oov_examples: dict[str, str] = {}
    reads = 0
    for ev in events(home_of(ns)):
        if ev.event_type != EV_LABEL_READ:
            continue
        if str(ev.payload.get("panel_kind") or "") != "ingredients":
            continue          # 只驗成分面板；營養面板幾乎都是數字
        reads += 1
        transcript = str(ev.payload.get("transcript") or "")
        for token in tokens(transcript):
            total += 1
            if token not in known:
                oov[token] += 1
                oov_examples.setdefault(token, str(ev.payload.get("gtin") or ev.event_id))

    rate = (sum(oov.values()) / total) if total else 0.0
    OOV_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 標籤判讀的詞庫外詞彙（A39）",
        "",
        f"成分面板判讀 {reads} 筆　詞 {total} 個　詞庫外 {sum(oov.values())} 個　"
        f"**OOV = {rate:.2%}**（門檻 {MAX_OOV_RATE:.0%}）",
        "",
        "這張表是給人看的：詞庫外不等於錯，可能只是詞庫還沒收。",
        "**但一整批沒見過的詞就是模型在造字**，那正是這條檢查要擋的。",
        "",
        "| 詞 | 出現次數 | 第一次出現在 |",
        "|---|---|---|",
    ]
    for token, count in oov.most_common():
        lines.append(f"| {token} | {count} | {oov_examples.get(token, '')} |")
    OOV_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok = rate <= MAX_OOV_RATE and reads > 0
    problems = [] if ok else [
        (f"OOV {rate:.2%} 超過門檻 {MAX_OOV_RATE:.0%}；最常見的詞庫外詞："
         f"{[t for t, _ in oov.most_common(15)]}") if reads else
        "沒有任何成分面板的判讀可以驗——0 筆不是「全部合格」，是什麼都沒驗到"]
    return report("A39 label_lexicon", ok,
                  {"ingredient_reads": reads, "tokens": total,
                   "oov_tokens": sum(oov.values()), "oov_rate": round(rate, 4),
                   "max_oov_rate": MAX_OOV_RATE, "distinct_oov": len(oov),
                   "report": str(OOV_REPORT)}, problems)


if __name__ == "__main__":
    sys.exit(main())
