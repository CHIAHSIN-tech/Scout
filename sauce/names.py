"""品牌名與產品名的比對鍵（折疊規則 `sauce-names-1`）。

抽取時名稱**原字保留**（payload 裡是來源怎麼寫就怎麼存）；只有比對的時候才折疊。
折疊刻意保守：小寫、去商標符號與標點、併空白、只剝**結尾**的通用尾綴。
不做同義詞、不猜縮寫、不翻譯。

折疊規則有版本。版本一改就是新的 view 目錄，舊目錄不覆寫（見 contract.NAMES_VERSION）。

## 為什麼要有 `contains_key`

A10 第二層要驗「模型沒有憑空造字」：折疊後的 brand_key／product_key 必須出現在
來源字串折疊後的結果裡。用純字串 `in` 會有假通過——`ard` 會命中 `aardvark`。
所以比對的單位是「連字號切出來的詞」，不是字元。
"""
from __future__ import annotations

import re
import unicodedata

VERSION = "sauce-names-1"

#: 只剝結尾的尾綴，可重複剝（"Foods Co." → 剝兩次）。
#: 「hot sauce」「sauce」放在這裡，是因為同一款醬在不同通路寫成
#: "Secret Aardvark Habanero" 與 "Secret Aardvark Habanero Hot Sauce"，不折就變成兩列。
SUFFIXES: tuple[str, ...] = (
    "hot sauce", "hotsauce", "sauce",
    "company", "companies", "foods", "food", "brands", "brand",
    "incorporated", "corporation", "limited",
    "llc", "l l c", "inc", "corp", "co", "ltd", "lp", "llp", "plc", "gmbh",
)
_SUFFIX_RE = re.compile(r"[\s,\.\-]+(?:" + "|".join(re.escape(s) for s in SUFFIXES) + r")\.?$", re.I)
_TRADEMARK = re.compile(r"[®™℗©]")
_PUNCT = re.compile(r"[^a-z0-9]+")
_LEADING_THE = re.compile(r"^the\s+", re.I)


def _strip_accents(s: str) -> str:
    """Sriracha 與 Srirācha 要折成同一個鍵；重音字母拆開後丟掉組合記號。"""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def fold(name: str) -> str:
    """任意字串 → 折疊鍵。空字串進、空字串出（呼叫端自己決定那算不算錯）。"""
    s = _TRADEMARK.sub(" ", str(name or ""))
    s = _strip_accents(s).strip()
    s = _LEADING_THE.sub("", s)
    for _ in range(3):                       # "Foods Co., Ltd." 要剝三層
        stripped = _SUFFIX_RE.sub("", s).strip(" ,.-")
        if stripped == s or not stripped:
            break
        s = stripped
    s = _PUNCT.sub("-", s.lower()).strip("-")
    return re.sub(r"-+", "-", s)


def brand_key(name: str) -> str:
    return fold(name)


def product_key(name: str) -> str:
    return fold(name)


def tokens(folded: str) -> list[str]:
    return [t for t in folded.split("-") if t]


def contains_key(haystack: str, key: str) -> bool:
    """`key`（已折疊）是不是 `haystack`（未折疊的來源字串）折疊後的**連續詞串**。

    比對單位是詞不是字元，所以 `ard` 不會命中 `aardvark`。空的 key 一律回 False——
    「什麼都沒抽到」不該算通過。
    """
    need, hay = tokens(key), tokens(fold(haystack))
    if not need or len(need) > len(hay):
        return False
    return any(hay[i:i + len(need)] == need for i in range(len(hay) - len(need) + 1))


def normalize_whitespace(text: str) -> str:
    """A25 的引文比對用：把各種空白（含不斷行空白）統一成單一半形空格。"""
    return re.sub(r"\s+", " ", str(text or "").replace(" ", " ")).strip()


def gtin14(code: str) -> str:
    """UPC-A / EAN-13 / GTIN-14 一律補零到 14 位。非數字或長度不對回空字串。"""
    digits = re.sub(r"\D", "", str(code or ""))
    if not digits or len(digits) > 14:
        return ""
    if len(digits) not in (8, 12, 13, 14):
        return ""
    return digits.rjust(14, "0")
