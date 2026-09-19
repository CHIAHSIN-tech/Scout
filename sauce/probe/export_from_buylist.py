"""把 buylist 的 `sauces` 表匯出成召回率清單的一部分。**唯讀。**

    python -m sauce.probe.export_from_buylist --out sauce/probe/from-buylist.csv

這張表是 Chia 與 Stanley 自己手打的、他們真的買過吃過的辣醬。它之所以適合當召回率的基準，
正是因為**它跟這個專案的抓取設定完全無關**——它早就存在，而且不是從任何一個我們去抓的
來源長出來的。用它來問「我們的總表收得到嗎」才有意義。

## 只讀，而且只讀這一張表

- 只發 GET，整支程式裡沒有任何寫入路徑（A34 用 git grep 驗這個目錄）。
- 金鑰從本機的 `.mcp.json` 讀（那個檔已被 .gitignore 擋住），**不寫進程式、不進版控**。
- 讀到的欄位只有名稱與連結；評分那幾欄不取——這裡要的是「有哪些名字」，不是「他們給幾分」。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from sauce.net import Fetcher   # noqa: E402

MCP_CONFIG = REPO / ".mcp.json"
TABLE = "sauces"


def credentials(path: Path | None = None) -> tuple[str, str]:
    """(base_url, anon_key)。找不到就回空字串，讓呼叫端講清楚是缺設定而不是沒資料。"""
    p = Path(path or MCP_CONFIG)
    if not p.exists():
        return "", ""
    blob = p.read_text(encoding="utf-8")
    try:
        data = json.loads(blob)
    except ValueError:
        return "", ""

    #: 用欄名配對，不用值的形狀。Supabase 換過金鑰格式（舊的是 JWT、新的是
    #: `sb_publishable_…`），靠「長得像 JWT」去認會在換格式那天安靜失效。
    pairs: list[tuple[str, str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for name, value in node.items():
                if isinstance(value, str) and name.upper().endswith("_URL") \
                        and "supabase" in value:
                    prefix = name[: -len("_URL")]
                    key_name = f"{prefix}_KEY"
                    if isinstance(node.get(key_name), str):
                        pairs.append((prefix, value.rstrip("/"), node[key_name]))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    if not pairs:
        return "", ""
    # `sauces` 表在 buylist 那個專案；名字裡有 BUYLIST 的優先。
    pairs.sort(key=lambda p: 0 if "BUYLIST" in p[0].upper() else 1)
    return pairs[0][1], pairs[0][2]


def fetch_rows(base_url: str, key: str, limit: int = 1000) -> list[dict[str, Any]]:
    url = f"{base_url}/rest/v1/{TABLE}?select=name,url&limit={limit}"
    got = Fetcher().get(url, accept="application/json",
                        extra_headers={"apikey": key, "Authorization": f"Bearer {key}"})
    if not got.ok:
        return []
    try:
        data = json.loads(got.body.decode("utf-8", "replace"))
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.probe.export_from_buylist")
    ap.add_argument("--out", default=str(Path(__file__).parent / "from-buylist.csv"))
    ap.add_argument("--config", default=None)
    ns = ap.parse_args(argv)

    base_url, key = credentials(Path(ns.config) if ns.config else None)
    if not base_url or not key:
        print(json.dumps({"ok": False,
                          "reason": "找不到 Supabase 設定（.mcp.json）；這是缺設定，不是表是空的"},
                         ensure_ascii=False, indent=1))
        return 1
    rows = fetch_rows(base_url, key)
    out = Path(ns.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "brand", "origin", "note"],
                           lineterminator="\n")
        w.writeheader()
        for row in rows:
            name = str(row.get("name") or "").strip()
            if name:
                w.writerow({"name": name, "brand": "", "origin": "supabase_sauces",
                            "note": str(row.get("url") or "")[:200]})
    print(json.dumps({"ok": bool(rows), "rows": len(rows), "out": str(out)},
                     ensure_ascii=False, indent=1))
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
