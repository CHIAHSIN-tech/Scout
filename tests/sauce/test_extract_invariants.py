"""抽取層的驗證器：模型輸出過不了這幾關就不會變成事件。

不是「標記為可疑」，是根本不寫進去。這幾條擋的是語料庫最致命、也最看不出來的失敗：
一句**聽起來像**那篇評論會說的話——讀起來正常、結構檢查全過、掛在正確的產品上，
而它從來沒有被寫過。
"""
from __future__ import annotations

from sauce.extract import validate_product, validate_verdicts

ITEM = {"raw_title": "Secret Aardvark Habanero Hot Sauce 8oz",
        "raw_brand": "Secret Aardvark Trading Co."}

BODY = ("We tried twelve bottles this month. Secret Aardvark Habanero is the one we kept "
        "reaching for: it is tangy, carroty and genuinely hot without wrecking the dish. "
        "Melinda's Original Habanero was thinner and sweeter than we remembered.")
REVIEW_ITEM = {"body": BODY}


def verdict(**kw):
    base = {"sauce_name_raw": "Secret Aardvark Habanero", "stance": "positive",
            "quote": "it is tangy, carroty and genuinely hot without wrecking the dish",
            "score_raw": "", "score_scale": "none"}
    base.update(kw)
    return {"verdicts": [base]}


# ---- 產品 -------------------------------------------------------------------

def test_product_accepts_names_that_come_from_the_source():
    assert validate_product({"brand": "Secret Aardvark", "product": "Habanero"}, ITEM) is None


def test_product_rejects_invented_brand():
    err = validate_product({"brand": "Tabasco", "product": "Habanero"}, ITEM)
    assert err and "brand" in err


def test_product_rejects_invented_product():
    err = validate_product({"brand": "Secret Aardvark", "product": "Ghost Reaper"}, ITEM)
    assert err and "product" in err


def test_product_rejects_empty_product():
    assert validate_product({"brand": "Secret Aardvark", "product": "  "}, ITEM)


def test_variant_must_differ_from_product():
    err = validate_product({"brand": "Secret Aardvark", "product": "Habanero",
                            "variant": "habanero"}, ITEM)
    assert err and "variant" in err


def test_heat_shu_must_be_a_positive_integer_or_empty():
    assert validate_product({"brand": "", "product": "Habanero", "heat_shu": ""}, ITEM) is None
    assert validate_product({"brand": "", "product": "Habanero", "heat_shu": 3600}, ITEM) is None
    assert validate_product({"brand": "", "product": "Habanero", "heat_shu": -1}, ITEM)
    assert validate_product({"brand": "", "product": "Habanero", "heat_shu": "hot"}, ITEM)


# ---- 評語 -------------------------------------------------------------------

def test_verdict_accepts_a_real_quote():
    assert validate_verdicts(verdict(), REVIEW_ITEM) is None


def test_verdict_rejects_a_paraphrase():
    """一句改寫過的話讀起來完全正常，所以只能靠「是不是子字串」擋。"""
    err = validate_verdicts(verdict(quote="the reviewer found it tangy and quite hot indeed"),
                            REVIEW_ITEM)
    assert err and "子字串" in err


def test_verdict_rejects_a_name_that_is_not_in_the_article():
    err = validate_verdicts(verdict(sauce_name_raw="Cholula Original"), REVIEW_ITEM)
    assert err and "不在正文" in err


def test_verdict_rejects_too_short_or_too_long_quotes():
    assert validate_verdicts(verdict(quote="it is hot"), REVIEW_ITEM)
    assert validate_verdicts(verdict(quote="x" * 501), REVIEW_ITEM)


def test_verdict_rejects_unknown_stance():
    assert validate_verdicts(verdict(stance="loved_it"), REVIEW_ITEM)


def test_verdict_requires_score_raw_when_there_is_a_scale():
    err = validate_verdicts(verdict(score_scale="out_of_10", score_raw=""), REVIEW_ITEM)
    assert err and "score_raw" in err


def test_verdict_rejects_unknown_scale():
    assert validate_verdicts(verdict(score_scale="thumbs"), REVIEW_ITEM)


def test_verdicts_must_be_a_list():
    assert validate_verdicts({"verdicts": {"stance": "positive"}}, REVIEW_ITEM)
