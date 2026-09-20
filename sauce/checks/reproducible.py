"""A31：視圖可重算。連續 derive 兩次，`rows_sha256` 必須相同。

視圖是「規則 × 事件」的函數。兩次算出不同的雜湊，代表函數裡混進了外部狀態
（時間、隨機、字典順序），而那會讓「半年後重跑比對差異」這件事失去意義——
分不出差異是資料變了還是算法飄了。
"""
from __future__ import annotations

import json
import sys

from ..proc import run as proc_run
from . import REPO, arg_parser, home_of, report

PY = str(REPO / ".venv" / "Scripts" / "python.exe")
VIEWS = ("sauce.views:build", "sauce.views:reviews")


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.reproducible").parse_args(argv)
    home = home_of(ns)
    seen: dict[str, list[str]] = {v: [] for v in VIEWS}
    for _ in range(2):
        for view in VIEWS:
            proc = proc_run(
        [PY, "-m", "evdb", "--home", str(home.root), "derive", view,
                 "--rules", ns.rules], cwd=REPO)
            if proc.returncode:
                return report("A31 reproducible", False, {"view": view},
                              [f"derive {view} 失敗：{proc.stderr[-300:]}"])
            path = (home.views / view.replace(":", "_").replace(".", "_") / ns.rules
                    / "manifest.json")
            seen[view].append(json.loads(path.read_text(encoding="utf-8"))["rows_sha256"])
    problems = [f"{v}：兩次的 rows_sha256 不同 {h}" for v, h in seen.items()
                if len(set(h)) != 1]
    return report("A31 reproducible", not problems,
                  {v: {"rows_sha256": h[0], "runs": len(h)} for v, h in seen.items()},
                  problems)


if __name__ == "__main__":
    sys.exit(main())
