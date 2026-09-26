"""trip.json 的命令列驗證器。

    python -m scout_mcp.travel.validate <trip.json>
    python -m scout_mcp.travel.validate --places <places.json>

exit 0 = 通過。錯誤一行一條印到 stderr，訊息是繁體中文、指得出是哪一筆哪個欄位。

它只是 `schema.validate_trip()` 的外殼——**驗證邏輯一份都不在這裡**，
不然 schema 改了這支就會悄悄落後。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .schema import validate_places, validate_trip


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="驗證 trip.json 的結構與不變式")
    ap.add_argument("path", help="要驗的 JSON 檔")
    ap.add_argument(
        "--places",
        action="store_true",
        help="把輸入當成 places[] 陣列驗（給 import_reference 的輸出用）",
    )
    args = ap.parse_args(argv)

    p = Path(args.path)
    if not p.exists():
        print(f"找不到檔案：{p}", file=sys.stderr)
        return 2
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"不是合法的 JSON：{exc}", file=sys.stderr)
        return 2

    errs = validate_places(data) if args.places else validate_trip(data)
    for e in errs:
        print(e, file=sys.stderr)
    if errs:
        print(f"共 {len(errs)} 項問題", file=sys.stderr)
        return 1
    print(f"{p} 通過驗證")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
