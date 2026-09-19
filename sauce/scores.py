"""評分的正規化規則（A26）。

原則只有一條：**原生分數逐字保存，正規化只能是附加欄位。**
`score_raw` 是評論原文怎麼寫就怎麼存（`"8.5/10"`、`"★★★★☆"`、`"Best Overall"`），
`score_norm` 是選配的 0–1 數字，而且必須能由 `(score_raw, score_scale)` 重算出同一個值——
A26 就是拿這個函式重算一次再比對。

看不懂的 scale 回 None，不猜。「看不懂」在這裡是正確答案，不是失敗：
`"Best Overall"` 本來就沒有數線可言，硬塞一個 1.0 會讓日後的分析以為它是滿分。
"""
from __future__ import annotations

import re

VERSION = "sauce-scores-1"

#: score_scale 的值域。抽取層只能回這幾種；不確定就回 "none"。
SCALES = ("out_of_5", "out_of_10", "out_of_100", "stars_5", "letter_grade", "rank", "none")

_NUM = re.compile(r"(\d+(?:\.\d+)?)")
_LETTER = {"a+": 1.0, "a": 0.95, "a-": 0.9, "b+": 0.85, "b": 0.8, "b-": 0.75,
           "c+": 0.7, "c": 0.65, "c-": 0.6, "d+": 0.55, "d": 0.5, "d-": 0.45, "f": 0.0}
_FULL_STAR, _HALF_STAR = "★", "½"


def normalize(score_raw: str, score_scale: str) -> float | None:
    """(原文, 量尺) → 0–1，或 None（算不出來）。純函式，沒有副作用、不看外部狀態。"""
    raw = str(score_raw or "").strip()
    scale = str(score_scale or "none").strip()
    if not raw or scale not in SCALES or scale == "none":
        return None

    if scale == "stars_5":
        stars = raw.count(_FULL_STAR) + 0.5 * raw.count(_HALF_STAR)
        if stars:
            return round(min(stars / 5.0, 1.0), 4)
        m = _NUM.search(raw)                      # "4.5 stars" 這種寫法
        return round(min(float(m.group(1)) / 5.0, 1.0), 4) if m else None

    if scale == "letter_grade":
        return _LETTER.get(raw.lower().replace(" ", ""))

    if scale == "rank":
        # 排名不是分數：第 1 名在 5 款裡和在 50 款裡意義不同，而那個分母不在 score_raw 裡。
        # 它在 verdict 的 rank_in_article / of_total 兩欄，所以這裡不正規化。
        return None

    denominator = {"out_of_5": 5.0, "out_of_10": 10.0, "out_of_100": 100.0}[scale]
    m = _NUM.search(raw)
    if not m:
        return None
    value = float(m.group(1))
    if value < 0 or value > denominator:
        return None
    return round(value / denominator, 4)
