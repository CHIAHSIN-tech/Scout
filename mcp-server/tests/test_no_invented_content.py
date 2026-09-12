"""A8：頁面不含 `trip.json` 以外的店家。

參考產品那次最難發現的錯誤是「AI 沒有被明確同意就自己加了幾家店」——
人要逐條比對才看得出來。這裡把它變成結構保證：**渲染器只渲染資料，不生成內容**。

做法是渲染器把每一個店名都包在 `<span class="pn" data-place="...">` 裡，
這個測試把那些 span 全部挖出來，斷言名字集合與 id 集合都是 `places[]` 的子集合。
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from scout_mcp.travel.page import render

FIXTURE = Path(__file__).parent / "fixtures" / "trip-fixture.json"

PN_RE = re.compile(r'<span class="pn" data-place="([^"]+)">([^<]*)</span>')


@pytest.fixture
def trip():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def rendered_places(html):
    return {(m.group(1), m.group(2)) for m in PN_RE.finditer(html)}


def test_every_rendered_place_comes_from_trip_json(trip):
    html = render(trip)
    ids = {p["id"] for p in trip["places"]}
    names = {p["name"] for p in trip["places"]}
    got = rendered_places(html)
    assert got, "頁面上一個店名都沒有，這個測試就沒有在驗任何東西"
    assert {i for i, _ in got} <= ids, "頁面出現了 places 以外的 id"
    assert {n for _, n in got} <= names, "頁面出現了 places 以外的店名"


def test_removing_a_place_removes_it_from_the_page(trip):
    """刪掉資料，頁面上就不該再有它——不是靠渲染器記得，是因為它本來就只讀資料。"""
    before = rendered_places(render(trip))
    assert any(i == "gisdeun" for i, _ in before)

    t2 = copy.deepcopy(trip)
    t2["places"] = [p for p in t2["places"] if p["id"] != "gisdeun"]
    after = rendered_places(render(t2))
    assert not any(i == "gisdeun" for i, _ in after)
    assert "Gisdeun" not in render(t2)


def test_renaming_a_place_renames_it_everywhere(trip):
    """改一次 places[].name，頁面上所有「這家店」的位置一起變（A7 的同一個機制）。

    只驗 pn span：`events[].title` 是使用者自己寫的文字（「Central Reducer 下午茶時段」），
    改店名不該去動它——那是資料，不是渲染器算出來的東西。
    """
    t2 = copy.deepcopy(trip)
    for p in t2["places"]:
        if p["id"] == "central-reducer":
            p["name"] = "改名之後的店"
    html = render(t2)
    names = {n for i, n in rendered_places(html) if i == "central-reducer"}
    assert names == {"改名之後的店"}, f"還有地方印著舊店名：{names}"
    hits = [m for m in PN_RE.finditer(html) if m.group(1) == "central-reducer"]
    assert len(hits) >= 2, "時間軸與正餐表都該出現，至少兩處"


def test_event_without_place_id_renders_its_own_title_only(trip):
    """沒有 place_id 的事件不會憑空長出一家店。"""
    t2 = copy.deepcopy(trip)
    t2["events"].append({
        "id": "e9", "day": 1, "time": "21:00", "title": "回旅館休息",
    })
    html = render(t2)
    assert "回旅館休息" in html
    ids = {p["id"] for p in t2["places"]}
    assert {i for i, _ in rendered_places(html)} <= ids


def test_empty_trip_renders_nothing_invented():
    """完全沒有 places 時，頁面上不該出現任何 pn span。"""
    t = {
        "schema_version": 1,
        "trip": {"title": "空的", "country": "kr", "city": "Seoul",
                 "start_date": "2026-09-21", "end_date": "2026-09-22",
                 "page_slug": "2026-09-kr-seoul-000000"},
        "places": [], "events": [], "legs": [], "days": [],
    }
    assert rendered_places(render(t)) == set()
