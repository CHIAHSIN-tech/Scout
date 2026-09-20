"""A38：每一筆判讀都回溯得到那張照片。

照片判讀沒有「子字串」可以驗——原文是一張圖，沒有文字可以比對（見 spec CHECKLIST 第 7 題）。
所以這一層能機械驗的只有兩件事：**判讀指得到一張真的存在的照片**，
以及**它說得出是哪個模型、哪一版 prompt 做的**。

這兩件驗不出「讀得對不對」，但它們擋得住最糟的那種失敗：
一筆沒有對應照片的轉錄——那就是憑空生出來的成分表，而它在庫裡跟真的長得一模一樣。
"""
from __future__ import annotations

import sys

from ..contract import EV_LABEL_IMAGE, EV_LABEL_READ
from . import arg_parser, events, home_of, report

REQUIRED = ("label_image_sha256", "model_id", "prompt_version", "transcript")


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.label_reads", rules=False).parse_args(argv)
    evs = events(home_of(ns))
    images = {str(ev.payload.get("image_sha256") or "") for ev in evs
              if ev.event_type == EV_LABEL_IMAGE}
    problems: list[str] = []
    checked = empty = 0
    for ev in evs:
        if ev.event_type != EV_LABEL_READ:
            continue
        checked += 1
        missing = [k for k in REQUIRED if k not in ev.payload]
        if missing:
            problems.append(f"{ev.event_id}：缺鍵 {missing}")
            continue
        sha = str(ev.payload.get("label_image_sha256") or "")
        if sha not in images:
            problems.append(f"{ev.event_id}：label_image_sha256={sha[:12]}… 在庫裡找不到對應的照片")
        if not str(ev.payload.get("transcript") or "").strip():
            empty += 1
    if not checked:
        # 0 筆不是「全部合格」。庫裡一筆判讀都沒有時這條檢查什麼都沒驗到，
        # 而它印出來的字會跟真的驗過一模一樣——所以這裡直接判不過。
        problems.append("庫裡沒有任何 sauce.label.read；冷啟動的待審檔還沒有人審過，"
                        "這條檢查什麼都沒驗到（不是通過）")
    return report("A38 label_reads", not problems,
                  {"label_reads": checked, "label_images": len(images),
                   "empty_transcripts": empty}, problems)


if __name__ == "__main__":
    sys.exit(main())
