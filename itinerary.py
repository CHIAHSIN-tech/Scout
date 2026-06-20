# itinerary.py
# 行程排程的核心邏輯：時間計算、串聯調整、AI 自然語言解析

from datetime import datetime, timedelta
import json
import db


# ── 時間工具函式 ──

def time_str_to_minutes(time_str: str) -> int:
    """把 'HH:MM' 字串轉成從午夜算起的分鐘數，方便做加減法"""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def minutes_to_time_str(minutes: int) -> str:
    """把分鐘數轉回 'HH:MM' 字串，最大到 23:59"""
    minutes = max(0, min(minutes, 23 * 60 + 59))
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def shift_time(time_str: str, delta_minutes: int) -> str:
    """
    把一個時間字串往前或往後移動指定分鐘數。
    delta_minutes 為正數 = 往後（延後），負數 = 往前（提前）。
    範例：shift_time("12:00", -60) → "11:00"
    """
    total = time_str_to_minutes(time_str) + delta_minutes
    total = max(0, total)
    return minutes_to_time_str(total)


def is_valid_time(time_str: str) -> bool:
    """驗證時間字串格式是否正確（HH:MM，00:00 ~ 23:59）"""
    import re
    if not re.match(r"^\d{2}:\d{2}$", time_str.strip()):
        return False
    h, m = map(int, time_str.strip().split(":"))
    return 0 <= h <= 23 and 0 <= m <= 59


# ── 調整邏輯 ──

def adjust_single_item(item_id: int, new_start_time: str) -> dict:
    """
    模式一：只調整單一項目，其他行程保持原位。
    回傳預覽物件，讓 UI 顯示給使用者確認後再寫入。
    """
    return {
        "mode": "single",
        "updates": [{"id": item_id, "start_time": new_start_time}]
    }


def adjust_with_cascade(
    trip_id: int,
    day_number: int,
    target_item_id: int,
    new_start_time: str,
    cascade_item_ids: list[int]
) -> dict:
    """
    模式二：調整目標項目，並把指定的其他項目同步平移相同的時間差。
    cascade_item_ids：使用者勾選要一起移動的項目 id 清單。
    回傳預覽物件，讓 UI 顯示確認後再寫入。
    """
    all_items = db.get_all_items(trip_id)
    target = next((i for i in all_items if i["id"] == target_item_id), None)
    if not target:
        raise ValueError(f"找不到 item_id={target_item_id}")
    # 候選項目沒有時段，不能當作串聯調整的基準
    if not target.get("start_time"):
        raise ValueError("候選項目沒有時段，請先排入某天某時段再做串聯調整")

    delta = (
        time_str_to_minutes(new_start_time)
        - time_str_to_minutes(target["start_time"])
    )

    updates = [{"id": target_item_id, "start_time": new_start_time}]

    for item in all_items:
        # 只平移有時段的項目；候選項目（start_time 為 NULL）直接跳過，避免 NULL 計算出錯
        if item["id"] in cascade_item_ids and item.get("start_time"):
            shifted = shift_time(item["start_time"], delta)
            updates.append({"id": item["id"], "start_time": shifted})

    return {
        "mode": "cascade",
        "delta_minutes": delta,
        "updates": updates
    }


def apply_adjustment(preview: dict, trip_id: int, instruction: str = "手動調整"):
    """
    把預覽物件的 updates 實際寫入資料庫，並記錄調整歷史。
    UI 在使用者按下「確認」後呼叫這個函式。
    """
    db.update_items_bulk(preview["updates"])
    db.log_adjustment(trip_id, instruction, preview["updates"])


# ── 排序與時間重算 ──

def reorder_and_recalculate(trip_id: int, day_number: int, new_order_ids: list[int]) -> list[dict]:
    """
    依照新的排列順序重新計算時間。
    以這天所有項目中最早的 start_time 為基準，
    按新順序依序接排（前一個結束時間 = 下一個開始時間）。
    """
    all_items = db.get_items_by_day(trip_id, day_number)
    id_to_item = {i["id"]: i for i in all_items}

    # 只用「有開始時間」的項目來算基準；候選項目（無時段）不參與時間重算。
    # 這保護 min() 不會因為 NULL start_time 而出錯（spec AC-2）。
    scheduled = [i for i in all_items if i.get("start_time")]
    if not scheduled:
        return []

    earliest = min(time_str_to_minutes(i["start_time"]) for i in scheduled)
    cursor = earliest

    updates = []
    for order_idx, item_id in enumerate(new_order_ids):
        item = id_to_item.get(item_id)
        # 跳過不存在、或沒有時段的項目，確保候選項目不會被誤排
        if item is None or not item.get("start_time"):
            continue
        new_start = minutes_to_time_str(cursor)
        updates.append({
            "id": item_id,
            "start_time": new_start,
            "sort_order": order_idx
        })
        cursor += item.get("duration_minutes") or 0

    return updates


def apply_reorder(trip_id: int, day_number: int, new_order_ids: list[int]):
    """
    把重排結果寫入資料庫，同時更新 start_time 和 sort_order。
    透過 db.update_items_schedule 走 Supabase，不再直接用 sqlite 連線。
    """
    updates = reorder_and_recalculate(trip_id, day_number, new_order_ids)
    if not updates:
        return
    db.update_items_schedule(updates)
    db.log_adjustment(
        trip_id,
        f"重新排序 Day {day_number}",
        [{"id": u["id"], "start_time": u["start_time"]} for u in updates]
    )


