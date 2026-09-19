"""契約本身的不變式。這些如果鬆掉，其他檢查會在錯的東西上通過。"""
from __future__ import annotations

from evdb.query import orphans as core_orphans_source

from sauce import contract


def test_link_event_matches_what_the_core_orphans_query_looks_for():
    """核心的 orphans 是硬寫 `entity.linked` 找連結的。

    這條測試存在的理由：如果哪天有人把它改成 `sauce.entity.linked`（spec 的字面），
    每一筆觀察都會變成孤兒，而**視圖照樣產得出來、列數照樣好看**，
    只有 A27 會發現——所以在這裡也釘一次。
    """
    import inspect

    source = inspect.getsource(core_orphans_source)
    assert f"'{contract.LINK_EVENT}'" in source or f'"{contract.LINK_EVENT}"' in source


def test_observation_ids_live_in_the_namespace_the_core_can_see():
    """orphans 只看得到 `src:` 開頭的實體。觀察的 id 必須落在那裡。"""
    assert contract.observation_id("fdc", "123").startswith("src:")


def test_verdicts_do_not_live_in_the_orphan_namespace():
    """verdict 用 `review:`，所以它不會被算成孤兒（A27 的等式靠這個成立）。"""
    assert not contract.review_id("sporked", "abc123").startswith("src:")


def test_every_namespace_used_by_a_template_is_registered():
    used = {contract.sauce_id("b", "p"), contract.brand_id("b"), contract.gtin_id("1" * 14),
            contract.review_id("o", "k"), contract.outlet_id("o")}
    for entity_id in used:
        assert entity_id.split(":", 1)[0] in contract.NAMESPACES


def test_ugc_sources_can_never_be_review_sources():
    assert not (contract.UGC_SOURCES & set(contract.REVIEW_SOURCES))


def test_reddit_is_a_ugc_source():
    """Stanley 2026-09-19：「I don't care what random people say about a product at all」。"""
    assert "reddit" in contract.UGC_SOURCES


def test_every_source_has_a_tier():
    for source in contract.SOURCES:
        assert source in contract.SOURCE_TIER, source


def test_availability_ranking_covers_the_whole_enum():
    for value in contract.US_AVAILABILITY:
        assert value in contract.AVAILABILITY_RANK


def test_review_event_types_are_the_only_ones_that_carry_judgement():
    assert contract.EV_MENTION not in contract.REVIEW_EVENT_TYPES
    assert contract.EV_VERDICT in contract.REVIEW_EVENT_TYPES
