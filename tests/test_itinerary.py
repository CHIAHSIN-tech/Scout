# tests/test_itinerary.py
# itinerary.py 純邏輯單元測試（時間計算、重排、串聯調整）。
#
# 重點：這些測試「不需要」Supabase / Streamlit。
# 做法是在 import itinerary 之前，先把一個假的 db 模組塞進 sys.modules，
# 這樣 itinerary.py 裡的 `import db` 會拿到假的，不會去執行真正的 db.py
# （真正的 db.py 會 import supabase / streamlit，本機不一定裝了）。
#
# 執行方式：
#   python tests/test_itinerary.py     # 內建簡易 runner，印 PASS/FAIL
#   pytest tests/test_itinerary.py     # 若有裝 pytest 也可

import os
import sys
import types

# 讓測試能找到專案根目錄的 itinerary.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 在 import itinerary 之前，先註冊假的 db 模組 ──
_fake_db = types.ModuleType("db")
sys.modules["db"] = _fake_db

import itinerary  # noqa: E402  （必須在塞完假 db 之後才 import）


# ════════════════════════════════════════
#  時間工具函式
# ════════════════════════════════════════

def test_time_str_to_minutes():
    assert itinerary.time_str_to_minutes("00:00") == 0
    assert itinerary.time_str_to_minutes("09:30") == 570
    assert itinerary.time_str_to_minutes("23:59") == 1439


def test_minutes_to_time_str():
    assert itinerary.minutes_to_time_str(0) == "00:00"
    assert itinerary.minutes_to_time_str(570) == "09:30"
    # 超過 23:59 會被夾住
    assert itinerary.minutes_to_time_str(99999) == "23:59"
    # 負數會被夾到 00:00
    assert itinerary.minutes_to_time_str(-10) == "00:00"


def test_shift_time():
    assert itinerary.shift_time("12:00", -60) == "11:00"
    assert itinerary.shift_time("09:00", 90) == "10:30"
    # 不會掉到負時間
    assert itinerary.shift_time("00:30", -120) == "00:00"


def test_is_valid_time():
    assert itinerary.is_valid_time("09:30")
    assert itinerary.is_valid_time("00:00")
    assert itinerary.is_valid_time("23:59")
    assert not itinerary.is_valid_time("24:00")
    assert not itinerary.is_valid_time("9:30")
    assert not itinerary.is_valid_time("abc")
    assert not itinerary.is_valid_time("12:60")


# ════════════════════════════════════════
#  reorder_and_recalculate：候選項目（NULL）要被排除、不能讓 min() 出錯
# ════════════════════════════════════════

def _set_day_items(items):
    """設定假 db.get_items_by_day 的回傳值"""
    _fake_db.get_items_by_day = lambda trip_id, day_number: items


def test_reorder_basic():
    # 三個已排定項目，依新順序從最早時間接排
    _set_day_items([
        {"id": 1, "start_time": "09:00", "duration_minutes": 60},
        {"id": 2, "start_time": "10:00", "duration_minutes": 30},
        {"id": 3, "start_time": "11:00", "duration_minutes": 90},
    ])
    updates = itinerary.reorder_and_recalculate(99, 1, [3, 1, 2])
    # 基準 = 最早的 09:00；接排：3(90分) → 1(60分) → 2
    assert updates == [
        {"id": 3, "start_time": "09:00", "sort_order": 0},
        {"id": 1, "start_time": "10:30", "sort_order": 1},
        {"id": 2, "start_time": "11:30", "sort_order": 2},
    ]


def test_reorder_ignores_null_start_time_items():
    # AC-2 核心：就算當天資料夾帶了一個無時段（候選殘留）的項目，min() 也不能爆，且要被略過
    _set_day_items([
        {"id": 1, "start_time": "09:00", "duration_minutes": 60},
        {"id": 2, "start_time": None,    "duration_minutes": 60},  # 無時段
        {"id": 3, "start_time": "11:00", "duration_minutes": 30},
    ])
    updates = itinerary.reorder_and_recalculate(99, 1, [1, 2, 3])
    ids = [u["id"] for u in updates]
    assert 2 not in ids                  # 無時段項目被排除
    assert ids == [1, 3]
    assert updates[0]["start_time"] == "09:00"
    assert updates[1]["start_time"] == "10:00"  # 1 停 60 分後接 3


def test_reorder_all_candidates_returns_empty():
    # 全部都是無時段 → 沒有可重算的東西，回傳空 list（不丟例外）
    _set_day_items([
        {"id": 1, "start_time": None, "duration_minutes": 60},
        {"id": 2, "start_time": None, "duration_minutes": 60},
    ])
    assert itinerary.reorder_and_recalculate(99, 1, [1, 2]) == []


def test_reorder_empty_day_returns_empty():
    _set_day_items([])
    assert itinerary.reorder_and_recalculate(99, 1, []) == []


# ════════════════════════════════════════
#  adjust_with_cascade：候選項目要被跳過、目標若是候選要報錯
# ════════════════════════════════════════

def _set_all_items(items):
    """設定假 db.get_all_items 的回傳值"""
    _fake_db.get_all_items = lambda trip_id: items


def test_cascade_shifts_selected_items():
    _set_all_items([
        {"id": 1, "start_time": "09:00"},
        {"id": 2, "start_time": "10:00"},
        {"id": 3, "start_time": "11:00"},
    ])
    # 把項目 1 從 09:00 移到 10:00（delta = +60），並讓 2、3 一起平移
    result = itinerary.adjust_with_cascade(99, 1, 1, "10:00", [2, 3])
    assert result["mode"] == "cascade"
    assert result["delta_minutes"] == 60
    updates = {u["id"]: u["start_time"] for u in result["updates"]}
    assert updates == {1: "10:00", 2: "11:00", 3: "12:00"}


def test_cascade_skips_null_start_time_candidates():
    # 候選項目（無時段）即使被勾進 cascade，也要被跳過、不能因 NULL 計算出錯
    _set_all_items([
        {"id": 1, "start_time": "09:00"},
        {"id": 2, "start_time": None},     # 候選
        {"id": 3, "start_time": "11:00"},
    ])
    result = itinerary.adjust_with_cascade(99, 1, 1, "10:00", [2, 3])
    ids = [u["id"] for u in result["updates"]]
    assert 2 not in ids                    # 候選被跳過
    assert set(ids) == {1, 3}


def test_cascade_target_is_candidate_raises():
    # 目標本身是候選（無時段）→ 不能當基準，應報錯
    _set_all_items([
        {"id": 1, "start_time": None},
        {"id": 2, "start_time": "10:00"},
    ])
    try:
        itinerary.adjust_with_cascade(99, 1, 1, "10:00", [2])
        assert False, "應該要丟 ValueError"
    except ValueError:
        pass


def test_cascade_target_not_found_raises():
    _set_all_items([{"id": 1, "start_time": "09:00"}])
    try:
        itinerary.adjust_with_cascade(99, 1, 999, "10:00", [])
        assert False, "應該要丟 ValueError"
    except ValueError:
        pass


# ════════════════════════════════════════
#  簡易 runner（不依賴 pytest）
# ════════════════════════════════════════

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}  -> {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}  -> {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed (total {len(tests)})")
    sys.exit(1 if failed else 0)
