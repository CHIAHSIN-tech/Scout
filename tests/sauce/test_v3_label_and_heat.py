"""v3 的純函式：成分推導、辣度五層、標籤照片網址、趨勢比較。

這一整檔**不碰網路、不碰模型、不碰 store**。理由跟 v3 的核心界線是同一條：
成分與辣度的欄位是規則算出來的，所以它們**測得起來**——
同樣的輸入永遠得到同樣的輸出。如果哪天這些欄位變得要靠模型才算得出來，
這一檔就會開始隨機失敗，那正是我們要的警報。
"""
from __future__ import annotations

import pytest

from sauce import composition, heat, heatrank, labelread, trend, validate
from sauce.sources import off_image

REAL_LABEL = ("INGREDIENTS: Water, Habanero Peppers, Distilled Vinegar, Carrots, "
              "Onion, Lime Juice, Garlic, Salt, Xanthan Gum. CONTAINS: None.")


# --- 成分推導 -----------------------------------------------------------------

def test_split_keeps_parenthesised_commas_as_one_item():
    items = composition.split_ingredients("Water, spices (cumin, oregano), Salt")
    assert items == ["Water", "spices (cumin, oregano)", "Salt"]


def test_derive_fields_is_pure():
    assert composition.derive_fields(REAL_LABEL) == composition.derive_fields(REAL_LABEL)


def test_derive_fields_reads_the_label_not_the_marketing():
    f = composition.derive_fields(REAL_LABEL)
    assert f["first_ingredient"] == "Water"
    assert f["water_first"] is True
    assert f["pepper_ordinal"] == 2          # 辣椒排第二 → 含量在水之後
    assert f["acidifier"]
    assert f["has_capsaicin_extract"] is False


def test_extract_is_flagged_because_it_makes_the_ceiling_meaningless():
    f = composition.derive_fields("Vinegar, Capsicum Extract, Salt")
    assert f["has_capsaicin_extract"] is True
    ceiling, basis = heat.ceiling_for(f["peppers"], f["has_capsaicin_extract"])
    assert ceiling == heat.UNBOUNDED and basis == []


def test_made_for_means_copacked_made_by_does_not():
    assert composition.derive_manufacturer(
        "Manufactured for Tiny Sauce Co, Austin TX")["is_copacked"] == "true"
    assert composition.derive_manufacturer(
        "Manufactured by Tiny Sauce Co, Austin TX")["is_copacked"] == "false"
    assert composition.derive_manufacturer("no such sentence") == {
        "manufacturer_name": "", "manufacturer_location": "", "is_copacked": ""}


@pytest.mark.parametrize("text, expected", [
    ("Habanero Hot Sauce", False),            # 這是商品標題，不是成分表
    ("Hot", False),
    (REAL_LABEL, True),
    ("Water, Vinegar, Salt, Garlic", True),
])
def test_only_things_that_look_like_a_list_are_parsed_as_one(text, expected):
    assert composition.looks_like_ingredients(text) is expected


# --- 辣度五層 -----------------------------------------------------------------

def test_unknown_ceiling_is_empty_not_zero():
    """留空＝不知道，0＝不辣。兩者在欄位上長得一樣，但一個是缺口一個是事實。"""
    ceiling, basis = heat.ceiling_for(["fictional pepper"], False, {"habanero": 350_000})
    assert ceiling == "" and basis == []


def test_ceiling_takes_the_hottest_declared_pepper():
    table = {"jalapeno": 8_000, "habanero": 350_000}
    ceiling, basis = heat.ceiling_for(["Jalapeno Peppers", "Habanero"], False, table)
    assert ceiling == 350_000 and basis == ["habanero", "jalapeno"]


def test_band_label_prefers_the_longer_hotter_phrase():
    assert heat.band_label("Our Extra Hot Sauce") == "extra hot"
    assert heat.band_label("Our Hot Sauce") == "hot"
    assert heat.band_label("Plain Sauce") == ""


def test_conflicting_shu_claims_are_all_kept():
    claims = heat.claims_in("rated 100,000 SHU by us but 50,000 scoville elsewhere",
                            "outlet", "2026-09-20T00:00:00Z")
    assert sorted(c["shu"] for c in claims) == [50_000, 100_000]
    assert {c["source"] for c in claims} == {"outlet"}


# --- 排序 ---------------------------------------------------------------------

PAIRS = [("c", "b", "lineup:1"), ("b", "a", "lineup:1"), ("c", "a", "lineup:1")]


def test_bradley_terry_orders_by_wins():
    strength = heatrank.bradley_terry(PAIRS)
    assert strength["c"] > strength["b"] > strength["a"]


def test_ranking_is_reproducible():
    """種子固定：同一份輸入跑兩次，連信賴區間都要一樣。"""
    assert heatrank.rank_with_ci(PAIRS) == heatrank.rank_with_ci(PAIRS)


def test_no_pairs_means_no_ranking_at_all():
    assert heatrank.bradley_terry([]) == {}
    assert heatrank.rank_with_ci([]) == {}


# --- 標籤照片 -----------------------------------------------------------------

def test_thumbnails_are_upgraded_to_full_because_small_print_is_unreadable():
    assert off_image.full_resolution(
        "https://images.openfoodfacts.org/x/ingredients_en.9.400.jpg"
    ).endswith("ingredients_en.9.full.jpg")


def test_already_full_urls_are_left_alone():
    url = "https://images.openfoodfacts.org/x/ingredients_en.9.full.jpg"
    assert off_image.full_resolution(url) == url


def test_label_read_rejects_a_transcript_that_says_nothing():
    assert labelread.validate_read({"transcript": "n/a"}, {}) is not None
    assert labelread.validate_read(
        {"transcript": REAL_LABEL, "panel_kind": "ingredients"}, {}) is None


def test_label_read_cannot_claim_illegible_and_still_transcribe():
    bad = {"transcript": REAL_LABEL, "panel_kind": "ingredients", "legible": False}
    assert labelread.validate_read(bad, {}) is not None


def test_validate_knows_the_panel_kinds():
    assert "front" in validate.PANEL_KINDS and "ingredients" in validate.PANEL_KINDS
    assert "heat_shu" not in validate.PANEL_KINDS


# --- 趨勢 ---------------------------------------------------------------------

def test_trend_reports_recipe_changes_not_just_counts():
    before = {"s:1": {"entity_id": "s:1", "first_ingredient": "Water", "heat_rank": "3"}}
    after = {"s:1": {"entity_id": "s:1", "first_ingredient": "Vinegar", "heat_rank": "1"},
             "s:2": {"entity_id": "s:2", "first_ingredient": "Water", "heat_rank": ""}}
    out = trend.compare(before, after)
    assert out["added"] == ["s:2"] and out["gone"] == []
    assert out["recipe_changed"][0]["fields"] == ["first_ingredient"]
    assert out["rank_changed"][0]["before"] == "3"


# --- 第三條抓取路徑（非 Shopify／非 Woo 的店）-----------------------------------

LD = (b'<html><script type="application/ld+json">{"@type":"Product",'
      b'"name":"Ghost Pepper Hot Sauce","brand":{"name":"Tiny Co"},'
      b'"gtin13":"0123456789012","offers":{"@type":"Offer","price":"11.95",'
      b'"priceCurrency":"USD","availability":"https://schema.org/InStock"}}</script></html>')
OG = (b'<html><meta property="og:title" content="Reaper Hot Sauce">'
      b'<meta property="product:price:amount" content="9.50">'
      b'<meta property="product:price:currency" content="USD"></html>')


def test_jsonld_is_read_before_the_weaker_sources():
    from sauce.sources import webshop
    got = webshop.read_product_page(LD)
    assert got["structured"] == "json-ld"
    assert got["price"] == "11.95" and got["gtin"] == "0123456789012"


def test_opengraph_is_the_fallback():
    from sauce.sources import webshop
    got = webshop.read_product_page(OG)
    assert got["structured"] == "opengraph" and got["price"] == "9.50"


def test_a_page_with_no_declared_price_is_recorded_as_none_never_guessed():
    """猜出來的價錢在表上跟站方宣告的長得一模一樣，所以寧可留空。"""
    from sauce.sources import webshop
    got = webshop.read_product_page(
        b"<html><title>Habanero Hot Sauce</title><div>Only $12.99 today!</div></html>")
    assert got["structured"] == "none"
    assert got["price"] == ""


def test_a_product_page_counts_as_a_shelf_even_without_a_stock_statement():
    from sauce.sources import webshop
    assert webshop._availability("") == "retail_listing"
    assert webshop._availability("https://schema.org/InStock") == "retail_listing"
    assert webshop._availability("https://schema.org/OutOfStock") == "unknown"


def test_non_sauce_titles_are_dropped_by_the_same_filter_as_every_other_source():
    from sauce.sources import webshop
    page = webshop.read_product_page(b"<html><title>Branded T-Shirt</title></html>")
    assert webshop.to_event("x.com", "https://x.com/products/tee", page,
                            "2026-09-20T00:00:00Z") is None
