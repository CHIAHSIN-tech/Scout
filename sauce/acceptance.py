"""把驗收表跑一遍，產生 `ACCEPTANCE-sauce-corpus.md`（逐條 PASS/FAIL ＋ 原始輸出）。

    python -m sauce.acceptance --home .evdb --rules v1

**這支程式不判斷「差不多算過了」。** 每一條的判定依據只有兩種：指令的 exit code，
或 `git grep` 有沒有輸出。跑不動的（需要兩次執行才驗得到的、需要人參與的）
一律標 `BLOCKED` 並寫出原因——**`BLOCKED` 不是 PASS**。

任何一項 FAIL 或 BLOCKED，整個 run 就是失敗，不論產出多少列。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
REPORT = REPO / "ACCEPTANCE-sauce-corpus.md"
PY = str(REPO / ".venv" / "Scripts" / "python.exe")


@dataclass
class Item:
    key: str
    title: str
    kind: str                     # "exit0" | "grep_empty" | "manual"
    command: list[str] = field(default_factory=list)
    note: str = ""


def items(home: str, rules: str) -> list[Item]:
    evdb = [PY, "-m", "evdb", "--home", home]
    def chk(name: str, *extra: str) -> list[str]:
        return [PY, "-m", f"sauce.checks.{name}", "--home", home, *extra]
    return [
        Item("A1", "乾淨環境跑得起來、測試全綠", "exit0", [PY, "-m", "pytest", "tests/sauce", "-q"]),
        Item("A2", "註冊表登記完整、全庫體檢無違規", "exit0", evdb + ["validate", "--json"]),
        Item("A3", "evdb 核心沒有被領域概念汙染", "grep_empty",
             ["git", "grep", "-niE", "sauce|scoville|capsaicin|pepper", "--",
              "evdb/"], "在 ../1-github/evdb 執行"),
        Item("A4", "evdb 工作樹沒有被這份任務改動", "grep_empty",
             ["git", "status", "--porcelain"], "在 ../1-github/evdb 執行"),
        Item("A5", "批次匯入不丟列", "exit0", chk("conservation")),
        Item("A6", "同一份快照跑兩次，事件數不變", "exit0",
             chk("idempotent", "--snapshot", "state/snapshot-20260919T082412Z")),
        Item("A7", "只追加：舊事件都還在", "exit0",
             chk("append_only", "--baseline", "state/events-20260919T082412Z.txt"),
             "第一次執行時基準就是這一輪自己；真正的證據要等下一輪"),
        Item("A8", "產品規模", "exit0", chk("scale", "--rules", rules)),
        Item("A9", "事件總數天花板", "exit0", chk("ceiling")),
        Item("A10", "抽取不變式（三層）", "exit0", [PY, "-m", "sauce.validate", "--home", home]),
        Item("A11", "首輪試樣是交付物", "exit0", [PY, "-m", "sauce.pilot", "check"]),
        Item("A12", "bridge 不吃降級輸出", "exit0", chk("degraded")),
        Item("A13", "同一個 GTIN 不出現在兩列", "exit0", chk("dupes", "--rules", rules)),
        Item("A14", "不過度合併", "exit0", chk("confusables", "--rules", rules)),
        Item("A15", "每一列可追溯", "exit0", chk("provenance", "--rules", rules)),
        Item("A16", "可購性值域與證據", "exit0", chk("availability", "--rules", rules)),
        Item("A17", "召回率", "exit0",
             [PY, "-m", "sauce.coverage", "--home", home, "--rules", rules,
              "--probe", "sauce/probe/probe-v1.csv"]),
        Item("A18", "召回率清單是 held-out 的", "grep_empty",
             ["git", "grep", "-n", "probe", "--", "sauce/", ":!sauce/coverage.py",
              ":!sauce/probe/"]),
        Item("A19", "零影音平台", "grep_empty",
             ["git", "grep", "-niE", r"youtube|youtu\.be|timedtext|yt[-_]?dlp|pytube",
              "--", "sauce/", "tests/sauce/", "fixtures/sauce/", "requirements-sauce.txt"]),
        Item("A20", "零 user review", "exit0", chk("no_ugc")),
        Item("A21", "outlet 白名單可稽核", "exit0", chk("outlets")),
        Item("A22", "白名單是抓取端的擋牆", "exit0",
             [PY, "-m", "pytest", "tests/sauce/test_outlet_gate.py", "-q"]),
        Item("A23", "不含語音轉文字、不含付費轉錄", "grep_empty",
             ["git", "grep", "-niE",
              r"whisper|deepgram|assemblyai|speech[-_]to[-_]text|transcribe",
              "--", "sauce/", "requirements-sauce.txt"]),
        Item("A24", "正文逐字保存、不進 payload", "exit0", chk("bodies")),
        Item("A25", "評語是原句", "exit0", chk("quotes")),
        Item("A26", "原生分數不被改寫", "exit0", chk("scores")),
        Item("A27", "孤兒不丟", "exit0", chk("orphans")),
        Item("A28", "版控與輸出不外流長正文", "exit0", [PY, "-m", "sauce.checks.export_safety"]),
        Item("A29", "評論覆蓋率報告", "exit0",
             [PY, "-m", "sauce.reviews_report", "--home", home, "--rules", rules]),
        Item("A30", "評論規模", "exit0", chk("review_scale")),
        Item("A31", "視圖可重算", "exit0", chk("reproducible", "--rules", rules)),
        Item("A32", "作業書可執行", "manual", note="從空的 .evdb 照 RUNBOOK 跑到底"),
        Item("A33", "沒有繞過共用 session 的直接請求", "grep_empty",
             ["git", "grep", "-nE",
              r"requests\.(get|post)\(|httpx\.(get|post)\(|urlopen\(",
              "--", "sauce/", ":!sauce/net.py"]),
        Item("A34", "沒有密鑰進版控、probe 匯出唯讀", "grep_empty",
             ["git", "grep", "-nE", r"SUPABASE_KEY|service_role|eyJ[A-Za-z0-9_-]{20,}",
              "--", "sauce/", "tests/sauce/", "fixtures/sauce/"]),
        Item("A35", "主要路徑：查得到、看得懂", "exit0",
             [PY, "-m", "sauce.query", "Secret Aardvark", "--home", home,
              "--rules", rules]),
    ]


def run_item(item: Item, cwd: Path) -> dict[str, Any]:
    if item.kind == "manual":
        return {"verdict": "BLOCKED", "output": "", "exit": None}
    where = cwd
    if "在 ../1-github/evdb 執行" in item.note:
        where = (REPO.parent / "1-github" / "evdb").resolve()
    try:
        proc = subprocess.run(item.command, cwd=where, capture_output=True, text=True,
                              timeout=1800, encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"verdict": "FAIL", "output": f"{type(exc).__name__}: {exc}", "exit": None}
    out = (proc.stdout or "") + (proc.stderr or "")
    if item.kind == "grep_empty":
        verdict = "PASS" if not out.strip() else "FAIL"
    else:
        verdict = "PASS" if proc.returncode == 0 else "FAIL"
    return {"verdict": verdict, "output": out.strip(), "exit": proc.returncode}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.acceptance")
    ap.add_argument("--home", default=".evdb")
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ns = ap.parse_args(argv)

    todo = [i for i in items(ns.home, ns.rules) if not ns.only or i.key in ns.only]
    results = []
    for item in todo:
        got = run_item(item, REPO)
        results.append({"item": item, **got})
        print(f"{item.key:<4} {got['verdict']:<8} {item.title}", flush=True)

    passed = sum(1 for r in results if r["verdict"] == "PASS")
    failed = [r for r in results if r["verdict"] == "FAIL"]
    blocked = [r for r in results if r["verdict"] == "BLOCKED"]

    lines = [
        "# 驗收表 — us-hot-sauce-corpus",
        "",
        f"`{passed}` PASS　`{len(failed)}` FAIL　`{len(blocked)}` BLOCKED（共 {len(results)} 條）",
        "",
        "**任何一項 FAIL 或 BLOCKED，整個 run 就是失敗**，不論產出多少列。",
        "`BLOCKED` 的意思是「這一條這一輪驗不到」，不是「應該會過」。",
        "",
        "| 項目 | 判定 | 內容 |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['item'].key} | {r['verdict']} | {r['item'].title} |")
    lines += ["", "---", "", "## 原始輸出", ""]
    for r in results:
        item = r["item"]
        lines += [f"### {item.key} — {item.title}", "",
                  f"**判定：{r['verdict']}**" + (f"（exit {r['exit']}）" if r["exit"] is not None
                                                 else "")]
        if item.command:
            lines += ["", "```", " ".join(item.command), "```"]
        if item.note:
            lines += ["", f"> {item.note}"]
        if r["output"]:
            body = r["output"]
            if len(body) > 4000:
                body = body[:4000] + "\n…（截斷）"
            lines += ["", "```", body, "```"]
        lines.append("")
    out = Path(ns.out or REPORT)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n報告：{out}")
    return 0 if not failed and not blocked else 1


if __name__ == "__main__":
    sys.exit(main())
