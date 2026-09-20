"""A28：版控與輸出不外流長正文。

1. `sauce/out/` 底下任何 CSV 的任何欄位 ≤ 500 字元；
2. `git ls-files sauce/` 不得出現 `raw/`（正文不進版控）。

這不是潔癖。評論正文是第三方的著作，而「所有功能都正常」的系統照樣可以在每一份
可分享的輸出裡夾帶全文——那是一個從任何一張表上都看不出來的外流面。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from ..proc import run as proc_run
from . import REPO, report

MAX_CELL = 500


def main(argv: list[str] | None = None) -> int:
    problems: list[str] = []
    checked_files = checked_cells = 0
    out_dir = REPO / "sauce" / "out"
    for path in sorted(out_dir.glob("*.csv")):
        checked_files += 1
        with path.open(encoding="utf-8", newline="") as fh:
            for lineno, row in enumerate(csv.DictReader(fh), start=2):
                for key, value in row.items():
                    checked_cells += 1
                    if value and len(value) > MAX_CELL:
                        problems.append(
                            f"{path.name}:{lineno} 欄位 {key} 長度 {len(value)} > {MAX_CELL}")
    try:
        tracked = proc_run(
        ["git", "ls-files", "sauce/"], cwd=REPO).stdout.splitlines()
    except OSError:
        tracked = []
    for line in tracked:
        if "raw/" in line:
            problems.append(f"正文進了版控：{line}")
    return report("A28 export_safety", not problems,
                  {"csv_files": checked_files, "cells": checked_cells,
                   "tracked_files": len(tracked), "max_cell": MAX_CELL}, problems)


if __name__ == "__main__":
    sys.exit(main())
