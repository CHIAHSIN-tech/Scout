"""A6：同一份快照重放兩次，事件總數不變。

evdb 的 event_id 是內容的 SHA-256，所以「同樣的輸入產生同樣的事件」這件事是結構保證，
不是靠這支程式去維持的。它驗的是**我們有沒有在某個地方混進了會變的東西**——
時間戳、隨機數、讀取順序。任何一個混進去，第二次重放就會多出一批「新」事件。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from evdb.store import Store

from . import REPO, arg_parser, home_of, report

PY = str(REPO / ".venv" / "Scripts" / "python.exe")


def _count(home) -> int:  # noqa: ANN001
    with Store(home, read_only=True) as store:
        return store.count()


def main(argv: list[str] | None = None) -> int:
    ap = arg_parser("python -m sauce.checks.idempotent", rules=False)
    ap.add_argument("--snapshot", required=True, help="state/snapshot-<id>")
    ns = ap.parse_args(argv)
    home = home_of(ns)
    before = _count(home)
    runs = []
    for _ in range(2):
        proc = subprocess.run(
            [PY, "-m", "sauce.load", "--home", str(home.root), "--snapshot", ns.snapshot],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
        runs.append({"exit": proc.returncode, "events_after": _count(home)})
    problems = []
    if runs[0]["exit"] or runs[1]["exit"]:
        problems.append(f"重放失敗：exit {runs[0]['exit']} / {runs[1]['exit']}")
    if runs[0]["events_after"] != runs[1]["events_after"]:
        problems.append(f"第二次重放事件數從 {runs[0]['events_after']} 變成 "
                        f"{runs[1]['events_after']}：有東西不是純函數")
    return report("A6 idempotent", not problems,
                  {"events_before": before, "after_first": runs[0]["events_after"],
                   "after_second": runs[1]["events_after"], "snapshot": ns.snapshot},
                  problems)


if __name__ == "__main__":
    sys.exit(main())
