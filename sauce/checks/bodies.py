"""A24：正文逐字保存、而且不在 payload 裡。

三件事一起驗：
1. `sauce.review.published` 的 payload 正規化後 ≤ 4 KB —— 中繼資料就該只是中繼資料；
2. `raw_ref` 非空，而且指到的檔案讀得回來；
3. 那個檔的 sha256 等於 payload 裡記的 `body_sha256`。

第三點是整條線的地基：**日後所有的抽取都可以重跑，前提是原始那一份沒有被動過。**
雜湊對不上代表原始層已經漂移，而漂移之後任何重跑都是在另一份資料上做的。
"""
from __future__ import annotations

import hashlib
import sys

from evdb.schema import canonical_json

from ..contract import EV_REVIEW
from . import arg_parser, events, home_of, report

MAX_PAYLOAD_BYTES = 4096


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.bodies", rules=False).parse_args(argv)
    home = home_of(ns)
    problems, checked, total_bytes = [], 0, 0
    for ev in events(home):
        if ev.event_type != EV_REVIEW:
            continue
        checked += 1
        size = len(canonical_json(ev.payload).encode("utf-8"))
        total_bytes += size
        if size > MAX_PAYLOAD_BYTES:
            problems.append(f"{ev.event_id}：payload {size} bytes > {MAX_PAYLOAD_BYTES}")
        if not (ev.raw_ref or "").strip():
            problems.append(f"{ev.event_id}：raw_ref 是空的（正文沒有落地）")
            continue
        path = home.root / ev.raw_ref
        if not path.exists():
            problems.append(f"{ev.event_id}：raw_ref 指到不存在的檔案 {ev.raw_ref}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != str(ev.payload.get("body_sha256") or ""):
            problems.append(f"{ev.event_id}：正文 sha256 與 payload 記的不一致")
    return report("A24 bodies", not problems,
                  {"reviews": checked, "max_payload_bytes": MAX_PAYLOAD_BYTES,
                   "avg_payload_bytes": round(total_bytes / checked) if checked else 0},
                  problems)


if __name__ == "__main__":
    sys.exit(main())
