"""A11：排程檢查器只報不改。

規格要求五類衝突各至少一個案例：
    1. 鎖定項目被要求移動
    2. 候選點營業時間不覆蓋該時段
    3. 交通時間吃掉指定停留時長
    4. 21:00 後跨區移動且最後一站不在旅館步行範圍
    5. sunset_locked 項目抵達晚於日落前 60 分

外加本檔最重要的一條：**呼叫前後 trip.json 的 sha256 完全相同**。
這支工具的整個價值建立在「它不會自己刪、不會自己搬」上面，
所以那件事要有測試，不能只有註解。
"""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from scout_mcp.travel.schedule import check_schedule


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def kinds(result) -> set[str]:
    return {c["kind"] for c in result["conflicts"]}


BASE = {
    "schema_version": 1,
    "trip": {
        "title": "測試", "country": "kr", "city": "Seoul",
        "start_date": "2026-09-21", "end_date": "2026-09-23",
        "page_slug": "2026-09-kr-seoul-aaa111",
    },
    "lodging": [{"name": "旅館", "station": "Chungmuro"}],
    "days": [{"day": 1}, {"day": 2, "sunset": "18:30"}, {"day": 3}],
    "places": [],
    "events": [],
    "legs": [],
}


def trip(**over):
    t = copy.deepcopy(BASE)
    t.update(copy.deepcopy(over))
    return t


# ── 1. 鎖定不可動 ──

def test_locked_item_cannot_be_moved():
    t = trip(events=[
        {"id": "e1", "day": 1, "time": "12:30", "title": "已訂的午餐", "locked": True},
    ])
    r = check_schedule(t, [{"event_id": "e1", "to_day": 2, "to_time": "13:00"}])
    assert "locked" in kinds(r)
    c = next(c for c in r["conflicts"] if c["kind"] == "locked")
    assert c["options"], "衝突一定要附上『要犧牲什麼』的選項"
    assert any("取消" in o or "改期" in o for o in c["options"])


def test_sunset_locked_item_also_cannot_be_moved():
    t = trip(events=[
        {"id": "e1", "day": 2, "time": "17:00", "title": "看夕陽", "sunset_locked": True},
    ])
    r = check_schedule(t, [{"event_id": "e1", "to_time": "19:00"}])
    assert "locked" in kinds(r)


def test_moving_an_unlocked_item_is_allowed():
    t = trip(events=[{"id": "e1", "day": 1, "time": "12:30", "title": "隨便吃"}])
    r = check_schedule(t, [{"event_id": "e1", "to_day": 2, "to_time": "13:00"}])
    assert "locked" not in kinds(r)


# ── 2. 營業時間 ──

def test_hours_do_not_cover_the_slot():
    t = trip(
        places=[{
            "id": "p1", "name": "只開中午的店",
            "hours": {"sources": [{"value": "11:30–14:00"}]},
        }],
        events=[{"id": "e1", "day": 1, "time": "19:00", "dur_min": 60,
                 "title": "晚餐", "place_id": "p1"}],
    )
    r = check_schedule(t)
    assert "hours" in kinds(r)
    c = next(c for c in r["conflicts"] if c["kind"] == "hours")
    assert "11:30" in c["what"], "訊息要講得出店幾點開，不能只說『時間不對』"


def test_closed_day_is_a_conflict():
    t = trip(
        places=[{
            "id": "p1", "name": "週一公休的店",
            # 2026-09-21 是週一
            "hours": {"sources": [{"value": "11:00–21:00", "closed_days": ["mon"]}]},
        }],
        events=[{"id": "e1", "day": 1, "time": "12:00", "dur_min": 60,
                 "title": "午餐", "place_id": "p1"}],
    )
    r = check_schedule(t)
    assert "hours" in kinds(r)
    assert "公休" in next(c for c in r["conflicts"] if c["kind"] == "hours")["what"]


def test_unverified_hours_is_not_a_pass():
    """查不到不等於沒問題——它進 unverified，不是靜悄悄地通過。"""
    t = trip(
        places=[{"id": "p1", "name": "沒查過的店", "hours": {"sources": []}}],
        events=[{"id": "e1", "day": 1, "time": "12:00", "dur_min": 60,
                 "title": "午餐", "place_id": "p1"}],
    )
    r = check_schedule(t)
    assert "hours" not in kinds(r)
    assert any(u["kind"] == "hours_unknown" for u in r["unverified"])
    assert "無法保證" in r["summary"]


# ── 3. 交通時間吃掉停留時長 ──

def test_travel_time_eats_the_dwell():
    t = trip(
        places=[{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
        events=[
            {"id": "e1", "day": 1, "time": "15:00", "dur_min": 120, "min_dur_min": 120,
             "title": "逛 A", "place_id": "a"},
            {"id": "e2", "day": 1, "time": "16:30", "title": "吃 B", "place_id": "b"},
        ],
        legs=[{"from": "a", "to": "b", "min": 40}],
    )
    r = check_schedule(t)
    assert "dwell" in kinds(r)
    c = next(c for c in r["conflicts"] if c["kind"] == "dwell")
    # 間隔 90 分 − 交通 40 分 = 50 分可用，短少 70 分
    assert "50 分" in c["what"] and "120 分" in c["what"]
    assert any("70 分" in o for o in c["options"]), "選項要講得出要挪多少，不是『再調整一下』"


def test_enough_time_is_not_a_conflict():
    t = trip(
        places=[{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
        events=[
            {"id": "e1", "day": 1, "time": "15:00", "min_dur_min": 30, "title": "逛 A", "place_id": "a"},
            {"id": "e2", "day": 1, "time": "16:30", "title": "吃 B", "place_id": "b"},
        ],
        legs=[{"from": "a", "to": "b", "min": 40}],
    )
    assert "dwell" not in kinds(check_schedule(t))


# ── 4. 夜間動線 ──

def test_late_cross_district_move_far_from_hotel():
    t = trip(
        places=[
            {"id": "a", "name": "A", "area": "城東區",
             "location": {"station": "Seongsu", "walk_min": 5}},
            {"id": "b", "name": "B", "area": "江南區",
             "location": {"station": "Gangnam", "walk_min": 8}},
        ],
        events=[
            {"id": "e1", "day": 1, "time": "19:00", "title": "逛 A", "place_id": "a"},
            {"id": "e2", "day": 1, "time": "21:30", "title": "宵夜 B", "place_id": "b"},
        ],
    )
    r = check_schedule(t)
    assert "night" in kinds(r)
    c = next(c for c in r["conflicts"] if c["kind"] == "night")
    assert "城東區" in c["what"] and "江南區" in c["what"]


def test_late_move_back_to_hotel_area_is_fine():
    t = trip(
        places=[
            {"id": "a", "name": "A", "area": "城東區", "location": {"station": "Seongsu"}},
            {"id": "b", "name": "B", "area": "中區",
             "location": {"station": "Chungmuro", "walk_min": 4}},
        ],
        events=[
            {"id": "e1", "day": 1, "time": "19:00", "title": "逛 A", "place_id": "a"},
            {"id": "e2", "day": 1, "time": "21:30", "title": "回旅館附近吃", "place_id": "b"},
        ],
    )
    assert "night" not in kinds(check_schedule(t))


# ── 5. 日落 ──

def test_sunset_locked_arriving_too_late():
    t = trip(events=[
        {"id": "e1", "day": 2, "time": "18:00", "title": "看夕陽", "sunset_locked": True},
    ])
    r = check_schedule(t)
    assert "sunset" in kinds(r)
    c = next(c for c in r["conflicts"] if c["kind"] == "sunset")
    assert "17:30" in c["what"], "要講得出最晚幾點要到"


def test_sunset_locked_arriving_in_time():
    t = trip(events=[
        {"id": "e1", "day": 2, "time": "17:20", "title": "看夕陽", "sunset_locked": True},
    ])
    assert "sunset" not in kinds(check_schedule(t))


def test_sunset_without_recorded_time_is_unverified():
    t = trip(events=[
        {"id": "e1", "day": 1, "time": "18:00", "title": "看夕陽", "sunset_locked": True},
    ])
    r = check_schedule(t)
    assert "sunset" not in kinds(r)
    assert any(u["kind"] == "sunset_unknown" for u in r["unverified"])


# ── 最重要的一條：它不會改任何東西 ──

@pytest.mark.parametrize("moves", [
    None,
    [{"event_id": "e1", "to_day": 3, "to_time": "09:00"}],
    [{"event_id": "不存在", "to_day": 2}],
])
def test_check_never_mutates_the_trip(moves):
    t = trip(
        places=[{"id": "p1", "name": "店", "hours": {"sources": [{"value": "11:30–14:00"}]}}],
        events=[
            {"id": "e1", "day": 1, "time": "19:00", "dur_min": 60, "title": "晚餐",
             "place_id": "p1", "locked": True},
            {"id": "e2", "day": 2, "time": "18:00", "title": "看夕陽", "sunset_locked": True},
        ],
    )
    before = sha(t)
    check_schedule(t, moves)
    assert sha(t) == before, "check_schedule 改動了 trip——它只能回報"


def test_every_conflict_offers_options():
    """沒有選項的衝突等於『你自己想辦法』，那不是這支工具的用途。"""
    t = trip(
        places=[{"id": "p1", "name": "店", "hours": {"sources": [{"value": "11:30–14:00"}]}}],
        events=[
            {"id": "e1", "day": 1, "time": "19:00", "dur_min": 60, "title": "晚餐",
             "place_id": "p1", "locked": True},
            {"id": "e2", "day": 2, "time": "18:00", "title": "看夕陽", "sunset_locked": True},
        ],
    )
    r = check_schedule(t, [{"event_id": "e1", "to_day": 2}])
    assert r["conflicts"]
    for c in r["conflicts"]:
        assert c["options"] and all(isinstance(o, str) and o for o in c["options"])
        assert c["what"]


def test_all_five_conflict_classes_are_reachable_in_one_trip():
    """五類一起出現時不會互相蓋掉——實際行程就是同時撞很多條。"""
    t = trip(
        places=[
            {"id": "a", "name": "A", "area": "城東區",
             "hours": {"sources": [{"value": "11:30–14:00"}]},
             "location": {"station": "Seongsu", "walk_min": 5}},
            {"id": "b", "name": "B", "area": "江南區",
             "hours": {"sources": [{"value": "10:00–23:59"}]},
             "location": {"station": "Gangnam", "walk_min": 9}},
        ],
        events=[
            # e1 是 locked，所以那個 move 會被擋下來，它仍然停在 15:00——
            # dwell 必須用「擋下來之後的樣子」來算，min_dur_min 才要設 200。
            {"id": "e1", "day": 2, "time": "15:00", "dur_min": 60, "min_dur_min": 200,
             "title": "逛 A", "place_id": "a", "locked": True},
            {"id": "e2", "day": 2, "time": "18:40", "title": "看夕陽", "place_id": "b",
             "sunset_locked": True},
            {"id": "e3", "day": 2, "time": "21:40", "title": "宵夜回城東", "place_id": "a"},
        ],
        legs=[{"from": "a", "to": "b", "min": 40}],
    )
    r = check_schedule(t, [{"event_id": "e1", "to_time": "16:00"}])
    assert {"locked", "hours", "dwell", "night", "sunset"} <= kinds(r), kinds(r)
    assert r["ok"] is False
