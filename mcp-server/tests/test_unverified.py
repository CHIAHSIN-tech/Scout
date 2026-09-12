"""A12／A13：查不到的事實不會變成頁面上的數字，來源衝突不被消滅。

A12  `hours.sources` 是空陣列時
     (a) 頁面不輸出該店營業時間
     (b) 建置時自動在 `open_questions[]` 產生一筆，含 what / why / check_by / source_hint

A13  `hours.sources` 有兩筆 value 不同時
     (a) 頁面同時顯示兩個值並標註衝突
     (b) 自動產生一筆 open_questions
     (c) 程式不得挑一個當「正確答案」

第三條最難測，因為「沒有挑」是一個否定。這裡的做法是：把兩個來源的順序對調再渲染一次，
如果程式偷偷挑了一個（例如取第一筆或取最新的 fetched_at），兩次的輸出裡會有一個值消失。
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from scout_mcp.travel.page import render
from scout_mcp.travel.service import derive_open_questions, merge_auto_questions

FIXTURE = Path(__file__).parent / "fixtures" / "trip-fixture.json"


@pytest.fixture
def trip():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def questions_by_id(qs):
    return {q["id"]: q for q in qs}


# ── A12：未查證 ──

def test_unverified_hours_are_not_printed(trip):
    """the-hyundai 的 hours.sources 是空陣列。"""
    html = render(trip)
    assert "營業時間尚未查證" in html
    # 沒有任何時間字串被塞在那家店的段落裡
    block = re.search(r'data-place="the-hyundai".*?(?=<section|<li class=)', html, re.S)
    assert block, "找得到 The Hyundai 的區塊"
    assert not re.search(r"\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}", block.group(0)), \
        "未查證的店不該出現任何營業時間區間"


def test_unverified_hours_generate_an_open_question(trip):
    qs = questions_by_id(derive_open_questions(trip))
    q = qs.get("auto-hours-the-hyundai")
    assert q, f"沒有為未查證的店產生待確認：{sorted(qs)}"
    for field in ("what", "why", "check_by", "source_hint"):
        assert q.get(field), f"待確認缺 {field}"
    assert q["auto"] is True


def test_auto_question_appears_on_the_page(trip):
    t = copy.deepcopy(trip)
    merge_auto_questions(t)
    html = render(t)
    assert "The Hyundai Seoul" in html
    assert "自動偵測" in html, "自動產生的待確認要標出來，人才知道哪些是程式推的"
    assert "還沒查證" in html


def test_open_air_areas_are_not_asked_about_hours(trip):
    """`kind: "area"`（開放街區、公園）沒有營業時間可查，問了也沒有答案。

    首爾首跑產生 17 筆自動待確認，其中 4 筆是「明洞商圈」「弘大、合井一帶」這種
    開放街區——規則本身沒錯，但比例不對會把真正重要的那兩筆稀釋掉
    （REVIEW.md 第 25 條）。
    """
    t = copy.deepcopy(trip)
    for p in t["places"]:
        if p["id"] == "the-hyundai":
            p["kind"] = "area"          # 假裝它是開放街區
    ids = {q["id"] for q in derive_open_questions(t)}
    assert "auto-hours-the-hyundai" not in ids


def test_open_air_areas_print_no_hours_line_at_all(trip):
    """area 連「尚未查證」都不該印——那會變成一個永遠查不完的假待辦。"""
    t = copy.deepcopy(trip)
    for p in t["places"]:
        if p["id"] == "the-hyundai":
            p["kind"] = "area"
    html = render(t)
    assert "營業時間尚未查證" not in html
    # 但它仍然要出現在頁面上，只是沒有營業時間那一行
    assert "The Hyundai Seoul" in html


def test_area_hours_are_not_checked_by_the_scheduler(trip):
    """排程檢查也不該把 area 列進 unverified。"""
    from scout_mcp.travel.schedule import check_schedule
    t = copy.deepcopy(trip)
    for p in t["places"]:
        if p["id"] == "the-hyundai":
            p["kind"] = "area"
    r = check_schedule(t)
    assert not any(u.get("place_id") == "the-hyundai" for u in r["unverified"])


def test_only_places_actually_scheduled_are_asked_about(trip):
    """候補清單上的店不會每一家都變成待確認——那會把清單淹掉。"""
    ids = {q["id"] for q in derive_open_questions(trip)}
    assert "auto-hours-gisdeun" not in ids, "queue_only 的店沒排進行程，不該自動發問"


def test_check_by_is_deterministic(trip):
    """check_by 由出發日往前推，不用「今天」——用了的話同樣輸入會建出不同的頁面。"""
    a = derive_open_questions(trip)
    b = derive_open_questions(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert a == b
    assert questions_by_id(a)["auto-hours-the-hyundai"]["check_by"] == "2026-09-18"


def test_merge_does_not_overwrite_hand_written_questions(trip):
    t = copy.deepcopy(trip)
    t["open_questions"].append({
        "id": "auto-hours-the-hyundai", "what": "人工寫的版本", "auto": False,
    })
    merge_auto_questions(t)
    hit = [q for q in t["open_questions"] if q["id"] == "auto-hours-the-hyundai"]
    assert len(hit) == 1 and hit[0]["what"] == "人工寫的版本"


# ── A13：來源衝突 ──

def test_conflicting_sources_are_both_shown(trip):
    """gwanghwamun-doughroom 有兩筆 value 不同的來源。"""
    html = render(trip)
    assert "11:30–21:00" in html
    assert "12:00–20:00" in html
    assert "來源互相矛盾" in html


def test_conflicting_sources_generate_an_open_question(trip):
    q = questions_by_id(derive_open_questions(trip)).get("auto-hours-conflict-gwanghwamun-doughroom")
    assert q, "來源打架沒有產生待確認"
    assert q["auto"] is True
    for field in ("what", "why", "check_by", "source_hint"):
        assert q.get(field), f"待確認缺 {field}"
    assert "矛盾" in q["what"]


def test_no_source_is_silently_picked(trip):
    """把兩個來源的順序對調，輸出裡兩個值都還要在。

    如果實作偷偷「取第一筆」或「取 fetched_at 最新的」，對調之後會少掉一個值。
    """
    t2 = copy.deepcopy(trip)
    for p in t2["places"]:
        if p["id"] == "gwanghwamun-doughroom":
            p["hours"]["sources"].reverse()
    html = render(t2)
    assert "11:30–21:00" in html and "12:00–20:00" in html
    # 待確認也要照樣產生，不會因為順序不同就消失
    ids = {q["id"] for q in derive_open_questions(t2)}
    assert "auto-hours-conflict-gwanghwamun-doughroom" in ids


def test_identical_sources_are_not_a_conflict(trip):
    """兩個來源講同一件事不是衝突——那只是互相佐證。"""
    t2 = copy.deepcopy(trip)
    for p in t2["places"]:
        if p["id"] == "gwanghwamun-doughroom":
            p["hours"]["sources"][1]["value"] = p["hours"]["sources"][0]["value"]
    ids = {q["id"] for q in derive_open_questions(t2)}
    assert "auto-hours-conflict-gwanghwamun-doughroom" not in ids
    assert "來源互相矛盾" not in render(t2)


def test_single_source_prints_the_value(trip):
    """查證過而且沒有打架的，就正常印出來——上面兩條不能讓正常情況也變成警告。"""
    html = render(trip)
    assert "12:00–15:00 / 17:30–21:00" in html
