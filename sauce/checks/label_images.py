"""A37：標籤照片落地、雜湊對得上、而且不進版控。

照片是第三方的影像（OFF 的貢獻者拍的，CC BY-SA 3.0），包裝上還可能有商標與設計的權利。
所以它只能待在 `<HOME>/raw/`：**不進版控、不進 view、不重新散布**。

雜湊那一條跟評論正文（A35）是同一個道理：日後所有的判讀都可以重跑，
前提是原始那一份沒有被動過。雜湊對不上代表原始層已經漂移，
而漂移之後任何重跑都是在另一份資料上做的。
"""
from __future__ import annotations

import hashlib
import subprocess
import sys

from ..contract import EV_LABEL_IMAGE
from . import REPO, arg_parser, events, home_of, report

PANEL_KINDS = {"ingredients", "nutrition", "front", "other"}
REQUIRED = ("panel_kind", "source", "source_url", "resolution", "image_sha256",
            "licence_note")


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.label_images", rules=False).parse_args(argv)
    home = home_of(ns)
    problems: list[str] = []
    checked = 0
    by_panel: dict[str, int] = {}
    for ev in events(home):
        if ev.event_type != EV_LABEL_IMAGE:
            continue
        checked += 1
        missing = [k for k in REQUIRED if k not in ev.payload]
        if missing:
            problems.append(f"{ev.event_id}：缺鍵 {missing}")
            continue
        panel = str(ev.payload.get("panel_kind"))
        by_panel[panel] = by_panel.get(panel, 0) + 1
        if panel not in PANEL_KINDS:
            problems.append(f"{ev.event_id}：panel_kind={panel!r} 不在允許值內")
        if not (ev.raw_ref or "").strip():
            problems.append(f"{ev.event_id}：raw_ref 是空的（圖片沒有落地）")
            continue
        path = home.root / ev.raw_ref
        if not path.exists():
            problems.append(f"{ev.event_id}：raw_ref 指到不存在的檔案 {ev.raw_ref}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != str(ev.payload["image_sha256"]):
            problems.append(f"{ev.event_id}：圖片 sha256 與 payload 記的不一致")

    try:
        tracked = subprocess.run(["git", "ls-files", "sauce/"], cwd=REPO, check=False,
                                 capture_output=True, text=True).stdout.splitlines()
    except OSError:
        tracked = []
    for line in tracked:
        if "raw/" in line:
            problems.append(f"圖片或正文進了版控：{line}")

    return report("A37 label_images", not problems,
                  {"label_images": checked, "by_panel": by_panel,
                   "tracked_files": len(tracked)}, problems)


if __name__ == "__main__":
    sys.exit(main())
