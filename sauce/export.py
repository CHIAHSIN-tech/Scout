"""把視圖輸出到**這次執行自己的目錄**（A44）。

    python -m sauce.export --home .evdb --rules v1 [--run-date 2026-09-20]

半年跑一次、每次覆寫同一個檔，等於每次都把上一次抹掉——那樣任何時間序列分析
（新品偵測、配方變更、消失的產品）都算不出來，而且**看不出來算不出來**：
檔案在、欄位在、數字也很合理，只是沒有昨天可以比。

所以每次執行寫進 `sauce/out/<run_date>/`，**既有的 run 目錄一個位元組都不動**。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

from evdb.home import Home

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "sauce" / "out"

VIEWS = {"sauce_catalog": "sauce_views_build",
         "sauce_reviews": "sauce_views_reviews",
         "sauce_buyable": "sauce_views_buyable"}


def run(home: Home, rules: str = "v1", run_date: str | None = None,
        out_root: Path | None = None) -> dict[str, Any]:
    stamp = run_date or date.today().isoformat()
    target = Path(out_root or OUT) / stamp
    target.mkdir(parents=True, exist_ok=True)
    written: dict[str, Any] = {}
    for name, view_dir in VIEWS.items():
        src = home.views / view_dir / rules / "rows.csv"
        if not src.exists():
            written[name] = {"ok": False, "reason": f"視圖還沒產生：{src}"}
            continue
        dst = target / f"{name}-{rules}.csv"
        shutil.copyfile(src, dst)
        written[name] = {"ok": True, "path": str(dst), "bytes": dst.stat().st_size}
    (target / "manifest.json").write_text(
        json.dumps({"run_date": stamp, "rules_version": rules,
                    "views": {k: v.get("path", "") for k, v in written.items()}},
                   ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"run_date": stamp, "dir": str(target), "views": written}


def runs(out_root: Path | None = None) -> list[str]:
    root = Path(out_root or OUT)
    return sorted(p.name for p in root.iterdir()
                  if p.is_dir() and (p / "manifest.json").exists()) if root.exists() else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.export")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--run-date", default=None)
    ns = ap.parse_args(argv)
    out = run(Home.resolve(ns.home), ns.rules, ns.run_date)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
