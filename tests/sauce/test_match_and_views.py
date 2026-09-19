"""比對與視圖：合併規則、不過度合併、視圖可重算。

這幾條是整份總表最容易在事後看不出來的地方——過度合併之後，總表顯示
「一列、兩個來源」，看起來比實際更有佐證。
"""
from __future__ import annotations

from evdb.schema import Event, IngestPath

from sauce import contract, match, views


def observation(source: str, key: str, title: str, brand: str = "", gtin: str = "",
                availability: str = "retail_listing") -> Event:
    payload = {"title": title, "brand": brand, "source_key": key,
               "us_availability": availability}
    if gtin:
        payload["gtin"] = gtin
    return Event(entity_type="sauce_observation",
                 entity_id=contract.observation_id(source, key),
                 event_type=contract.EV_PRODUCT, observed_at="2026-09-19T00:00:00Z",
                 source=source, source_record_id=key,
                 source_url=f"https://{source}.test/{key}",
                 ingest_path=IngestPath.BULK.value, payload=payload)


def parsed(obs: Event, brand: str, product: str, variant: str = "") -> Event:
    return Event(entity_type="sauce_extraction", entity_id=obs.entity_id,
                 event_type=contract.EV_PARSED, observed_at=obs.observed_at,
                 source=obs.source, source_record_id=obs.event_id,
                 source_url=obs.source_url, ingest_path=IngestPath.SDK.value,
                 payload={"observation_event_id": obs.event_id,
                          "raw_title": obs.payload["title"],
                          "raw_brand": obs.payload.get("brand", ""),
                          "brand": brand, "product": product, "variant": variant,
                          "us_availability": obs.payload.get("us_availability", "unknown"),
                          "evidence_url": obs.source_url,
                          "model_id": "test-model", "prompt_version": "v-test"})


def build_events(pairs: list[tuple[Event, tuple[str, str]]]) -> list[Event]:
    events: list[Event] = []
    for obs, (brand, product) in pairs:
        events.append(obs)
        events.append(parsed(obs, brand, product))
    return events + match.link_events(events)


def test_same_brand_and_product_merge_into_one_row():
    a = observation("fdc", "1", "Secret Aardvark Habanero Hot Sauce", "Secret Aardvark")
    b = observation("shopify", "2", "Secret Aardvark Habanero", "Secret Aardvark, LLC")
    events = build_events([(a, ("Secret Aardvark", "Habanero")),
                           (b, ("Secret Aardvark, LLC", "Habanero"))])
    rows = views.build(events, "v1")
    assert len(rows) == 1
    assert rows[0]["source_count"] == 2
    assert rows[0]["corroboration"] == "multi_source"


def test_unlisted_corporate_word_does_not_merge_and_that_is_on_purpose():
    """折疊只剝清單上的尾綴。`Trading` 不在清單上，所以這兩筆不合併。

    這不是漏洞，是保守規則的直接後果：**過度合併事後看不出來，而且無法還原**。
    兩列會被標成 `duplicate_candidate`，留給人判斷要不要把 `trading` 加進尾綴清單
    （加了就是換一個 `names_version`，舊視圖不覆寫）。
    """
    a = observation("fdc", "1", "Secret Aardvark Habanero Hot Sauce", "Secret Aardvark")
    b = observation("shopify", "2", "Secret Aardvark Habanero",
                    "Secret Aardvark Trading Co.")
    rows = views.build(build_events([(a, ("Secret Aardvark", "Habanero")),
                                     (b, ("Secret Aardvark Trading Co.", "Habanero"))]), "v1")
    assert len(rows) == 2
    assert all(r["duplicate_candidate"] for r in rows)


def test_same_product_different_brand_stays_separate():
    a = observation("fdc", "1", "Ghost Pepper Hot Sauce", "Alpha Foods")
    b = observation("fdc", "2", "Ghost Pepper Hot Sauce", "Beta Foods")
    events = build_events([(a, ("Alpha Foods", "Ghost Pepper")),
                           (b, ("Beta Foods", "Ghost Pepper"))])
    rows = views.build(events, "v1")
    assert len(rows) == 2
    # 沒有合併，但標記出來讓人看得到它們長得像
    assert all(r["duplicate_candidate"] for r in rows)
    assert rows[0]["duplicate_of_candidates"] == rows[1]["entity_id"]


def test_same_gtin_merges_even_with_different_names():
    a = observation("fdc", "1", "Aardvark Habanero", "Secret Aardvark", gtin="011210200005")
    b = observation("off", "2", "Habanero Sauce", "Aardvark", gtin="0011210200005")
    events = build_events([(a, ("Secret Aardvark", "Aardvark Habanero")),
                           (b, ("Aardvark", "Habanero Sauce"))])
    rows = views.build(events, "v1")
    assert len(rows) == 1, "同一個 GTIN 不得出現在兩列"


def test_canonical_id_does_not_depend_on_order():
    a = observation("fdc", "1", "X Sauce", "Alpha", gtin="011210200005")
    b = observation("off", "2", "Y Sauce", "Beta", gtin="011210200005")
    forward = views.build(build_events([(a, ("Alpha", "X Sauce")), (b, ("Beta", "Y Sauce"))]), "v1")
    backward = views.build(build_events([(b, ("Beta", "Y Sauce")), (a, ("Alpha", "X Sauce"))]), "v1")
    assert [r["entity_id"] for r in forward] == [r["entity_id"] for r in backward]


def test_availability_takes_the_strongest_and_keeps_its_evidence():
    a = observation("wikipedia", "1", "Old Sauce", "Alpha", availability="mention_only")
    b = observation("shopify", "2", "Old Sauce", "Alpha", availability="retail_listing")
    rows = views.build(build_events([(a, ("Alpha", "Old Sauce")),
                                     (b, ("Alpha", "Old Sauce"))]), "v1")
    assert rows[0]["us_availability"] == "retail_listing"
    assert rows[0]["evidence_url"].startswith("https://shopify.test/")


def test_single_source_is_labelled_not_hidden():
    a = observation("awards", "1", "Tiny Batch Sauce", "Tiny Co")
    rows = views.build(build_events([(a, ("Tiny Co", "Tiny Batch Sauce"))]), "v1")
    assert rows[0]["corroboration"].startswith("single_source:")


def test_view_is_stable_across_two_runs():
    a = observation("fdc", "1", "A Sauce", "Alpha")
    b = observation("shopify", "2", "B Sauce", "Beta")
    events = build_events([(a, ("Alpha", "A Sauce")), (b, ("Beta", "B Sauce"))])
    assert views.build(events, "v1") == views.build(list(reversed(events)), "v1")
