"""A48：每次執行輸出到自己的目錄，而且不覆寫既有的 run。

驗兩件事：
1. 最新的 run 目錄有 `sauce_catalog-v1.csv` 與 `sauce_reviews-v1.csv`；
2. **既有的 run 目錄沒有被動過**——用 mtime 比對，比最新 run 的 manifest 還新的舊檔案就是被覆寫了。

第二條是重點。覆寫掉上一次的輸出，不會有任何錯誤訊息，只會讓趨勢永遠算不出來。
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..export import OUT, runs
from . import arg_parser, report

REQUIRED = ("sauce_catalog-v1.csv", "sauce_reviews-v1.csv")


def main(argv: list[str] | None = None) -> int:
    ap = arg_parser("python -m sauce.checks.run_dirs", rules=False)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    root = Path(ns.out or OUT)
    found = runs(root)
    problems: list[str] = []
    if not found:
        return report("A48 run_dirs", False, {"runs": []},
                      [f"{root} 底下沒有任何 run 目錄"])

    latest = found[-1]
    latest_manifest = root / latest / "manifest.json"
    for name in REQUIRED:
        if not (root / latest / name).exists():
            problems.append(f"最新的 run `{latest}` 缺 {name}")

    cutoff = latest_manifest.stat().st_mtime
    for older in found[:-1]:
        for path in sorted((root / older).glob("*")):
            if path.stat().st_mtime >= cutoff:
                problems.append(f"舊的 run `{older}` 的 {path.name} 在這次執行時被動過")
    return report("A48 run_dirs", not problems,
                  {"runs": found, "latest": latest,
                   "files_in_latest": sorted(p.name for p in (root / latest).glob("*"))},
                  problems)


if __name__ == "__main__":
    sys.exit(main())
