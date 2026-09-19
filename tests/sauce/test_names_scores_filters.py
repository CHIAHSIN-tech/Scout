"""折疊規則、評分正規化、辣醬判定——三個純函式層，錯了整條線都會錯。"""
from __future__ import annotations

from sauce.names import contains_key, fold, gtin14, normalize_whitespace
from sauce.scores import SCALES, normalize
from sauce.sources import filters


# ---- 折疊 -------------------------------------------------------------------

def test_fold_strips_trailing_suffixes_and_punctuation():
    assert fold("Secret Aardvark Trading Co.") == "secret-aardvark-trading"
    assert fold("Yellowbird Foods, LLC") == "yellowbird"
    assert fold("The Original Louisiana Hot Sauce") == "original-louisiana"


def test_fold_is_accent_insensitive():
    assert fold("Srirācha") == fold("Sriracha")


def test_fold_drops_trademark_marks():
    assert fold("TABASCO® Original") == fold("Tabasco Original")


def test_contains_key_matches_whole_words_only():
    assert contains_key("Secret Aardvark Habanero Hot Sauce 8oz", "secret-aardvark")
    assert contains_key("Secret Aardvark Habanero", "habanero")
    # `ard` 不可以命中 `aardvark`：比對單位是詞，不是字元
    assert not contains_key("Aardvark Sauce", "ard")
    assert not contains_key("Secret Aardvark", "")


def test_normalize_whitespace_handles_nbsp():
    assert normalize_whitespace("a  b\n\tc") == "a b c"


def test_gtin14_pads_and_rejects_junk():
    assert gtin14("011210200005") == "00011210200005"
    assert gtin14("0011210200005") == "00011210200005"
    assert gtin14("abc") == ""
    assert gtin14("123") == ""


# ---- 評分 -------------------------------------------------------------------

def test_scores_round_trip():
    assert normalize("8.5/10", "out_of_10") == 0.85
    assert normalize("4/5", "out_of_5") == 0.8
    assert normalize("★★★★½", "stars_5") == 0.9
    assert normalize("A-", "letter_grade") == 0.9


def test_scores_return_none_when_there_is_no_number_line():
    # "Best Overall" 沒有數線可言；硬塞一個 1.0 會讓分析以為它是滿分
    assert normalize("Best Overall", "none") is None
    assert normalize("1", "rank") is None
    assert normalize("11/10", "out_of_10") is None
    assert normalize("", "out_of_5") is None
    assert normalize("5", "not_a_scale") is None


def test_every_scale_is_declared():
    assert "none" in SCALES and "rank" in SCALES


# ---- 是不是一款辣醬 ---------------------------------------------------------

def test_explicit_phrases_are_kept():
    for title in ("Secret Aardvark Habanero Hot Sauce", "Huy Fong Sriracha",
                  "Lao Gan Ma Chili Crisp", "Mike's Hot Honey"):
        assert filters.keep(title), title


def test_heat_word_alone_is_not_enough():
    """辣不等於是醬。第一版只看關鍵字，收進來兩萬六千列洋芋片與冷凍食品。"""
    assert not filters.keep("Jalapeno Heat Potato Chips")
    assert not filters.keep("Pork Tenderloin with Peri Peri Seasonings")
    assert not filters.keep("Habanero Cheddar Cheese")


def test_heat_plus_sauce_word_is_enough():
    assert filters.keep("Habanero Pepper Sauce")
    assert filters.keep("Ghost Pepper Chili Oil")


def test_merchandise_is_excluded_even_with_the_right_words():
    assert not filters.keep("Hot Sauce T-Shirt")
    assert not filters.keep("Hot Sauce Gift Box")
    assert not filters.keep("Hot Sauce Advent Calendar")


def test_other_condiments_are_excluded():
    assert not filters.keep("Spicy BBQ Sauce")
    assert not filters.keep("Chipotle Mayo")
    assert not filters.keep("Jalapeno Ketchup")


def test_classify_reports_why():
    verdict = filters.classify("Hot Sauce T-Shirt")
    assert verdict["keep"] is False
    assert verdict["reason"] == "excluded"
    assert verdict["filter_version"] == filters.VERSION
