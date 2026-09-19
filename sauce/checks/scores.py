"""A26：原生分數不被改寫。

有評分的 verdict 必須帶 `score_raw`（原文逐字，`"8.5/10"`、`"★★★★☆"`、`"Best Overall"`）
與 `score_scale`；`score_norm` 可以是空的，但只要非空就必須能由
`(score_raw, score_scale)` 用 `sauce/scores.py` 的規則重算出同一個值。

**不得只留 `score_norm`。** 一旦只剩正規化後的 0.85，就再也回答不了
「原文寫的是 8.5/10 還是四顆半星」——而那兩件事在不同 outlet 之間根本不能直接比較。
"""
from __future__ import annotations

import sys

from ..contract import EV_VERDICT
from ..scores import SCALES, normalize
from . import arg_parser, events, home_of, report


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.scores", rules=False).parse_args(argv)
    problems, checked, with_score = [], 0, 0
    for ev in events(home_of(ns)):
        if ev.event_type != EV_VERDICT:
            continue
        checked += 1
        raw = str(ev.payload.get("score_raw") or "")
        scale = str(ev.payload.get("score_scale") or "none")
        norm = ev.payload.get("score_norm")
        if scale not in SCALES:
            problems.append(f"{ev.event_id}：score_scale {scale!r} 不在允許值內")
            continue
        if scale != "none":
            with_score += 1
            if not raw.strip():
                problems.append(f"{ev.event_id}：有 score_scale 卻沒有 score_raw")
                continue
        if norm not in (None, ""):
            expected = normalize(raw, scale)
            if expected is None or abs(float(norm) - float(expected)) > 1e-9:
                problems.append(
                    f"{ev.event_id}：score_norm={norm} 無法由 ({raw!r}, {scale}) 重算出來"
                    f"（重算得到 {expected}）")
        if norm not in (None, "") and not raw.strip():
            problems.append(f"{ev.event_id}：只有 score_norm、沒有 score_raw")
    return report("A26 scores", not problems,
                  {"verdicts": checked, "with_score": with_score}, problems)


if __name__ == "__main__":
    sys.exit(main())
