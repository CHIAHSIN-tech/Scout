"""渲染器的命令列入口，只給驗收腳本用。

    python -m scout_mcp.travel.page <trip.json> <out.html>

驗收腳本是 Node（本 repo 的慣例，只用 Node 內建模組），渲染器是 Python，
中間需要一個不必起 MCP server 就能呼叫的縫。這支就是那個縫——
它不做任何渲染邏輯，只是 `render()` 的外殼。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import render


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("用法：python -m scout_mcp.travel.page <trip.json> <out.html>", file=sys.stderr)
        return 2
    trip = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    Path(args[1]).write_text(render(trip), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
