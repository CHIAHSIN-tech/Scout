import streamlit as st
from supabase import create_client, Client

# ── 建立 Supabase 連線 ──
# 從 secrets.toml 讀取 URL 和 Key，建立全域 client
# @st.cache_resource 確保整個 app 只建立一次連線，不會每次操作都重新連
@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def init_db():
    # Supabase 版本不需要 init_db，表格已在 Supabase 介面建好
    # 保留這個函式是為了讓 app.py 不需要修改
    pass


# ── Trips CRUD ──

def create_trip(username, name, start_date, end_date, notes=""):
    """建立新旅程，回傳新旅程的 id"""
    sb = get_client()
    # .insert() 新增一筆資料，.execute() 送出請求
    res = sb.table("trips").insert({
        "username": username,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "notes": notes,
    }).execute()
    # res.data 是一個 list，第一筆就是剛新增的資料
    return res.data[0]["id"]


def get_trips(username):
    """取得某使用者的所有旅程，按開始日期排序"""
    sb = get_client()
    # .select("*") 選取所有欄位
    # .eq("username", username) 等同於 WHERE username = username
    # .order() 等同於 ORDER BY
    res = sb.table("trips")\
        .select("*")\
        .eq("username", username)\
        .order("start_date", desc=True)\
        .execute()
    return res.data


def get_trip(trip_id):
    """取得單一旅程"""
    sb = get_client()
    res = sb.table("trips")\
        .select("*")\
        .eq("id", trip_id)\
        .execute()
    # 找不到就回傳 None，找到就回傳第一筆
    return res.data[0] if res.data else None


def delete_trip(trip_id):
    """刪除旅程（行程項目會因 CASCADE 一起刪除）"""
    sb = get_client()
    sb.table("trips").delete().eq("id", trip_id).execute()


# ── Itinerary Items CRUD ──

def get_items_by_day(trip_id, day_number):
    """取得某天的所有行程項目，按 start_time 排序"""
    sb = get_client()
    res = sb.table("itinerary_items")\
        .select("*")\
        .eq("trip_id", trip_id)\
        .eq("day_number", day_number)\
        .order("start_time")\
        .order("sort_order")\
        .execute()
    return res.data


def get_all_items(trip_id):
    """取得一趟旅程的所有行程項目，按天和時間排序"""
    sb = get_client()
    res = sb.table("itinerary_items")\
        .select("*")\
        .eq("trip_id", trip_id)\
        .order("day_number")\
        .order("start_time")\
        .order("sort_order")\
        .execute()
    return res.data


def add_item(trip_id, day_number, name, start_time, duration_minutes=60,
             category="other", location="", address="",
             booking_ref="", notes="", source="manual", source_id=None):
    """新增一個行程項目，回傳新項目的 id"""
    sb = get_client()

    # 先查當天最大的 sort_order，新項目排在最後
    existing = sb.table("itinerary_items")\
        .select("sort_order")\
        .eq("trip_id", trip_id)\
        .eq("day_number", day_number)\
        .order("sort_order", desc=True)\
        .limit(1)\
        .execute()

    # 如果當天沒有項目，從 0 開始；否則最大值 +1
    max_order = existing.data[0]["sort_order"] if existing.data else -1

    res = sb.table("itinerary_items").insert({
        "trip_id": trip_id,
        "day_number": day_number,
        "name": name,
        "category": category,
        "start_time": start_time,
        "duration_minutes": duration_minutes,
        "location": location,
        "address": address,
        "booking_ref": booking_ref,
        "notes": notes,
        "source": source,
        "source_id": source_id,
        "sort_order": max_order + 1,
    }).execute()
    return res.data[0]["id"]


def update_item_time(item_id, new_start_time):
    """更新單一項目的開始時間"""
    sb = get_client()
    # .update() 等同於 UPDATE SET，.eq() 指定要更新哪一筆
    sb.table("itinerary_items")\
        .update({"start_time": new_start_time})\
        .eq("id", item_id)\
        .execute()


def update_items_bulk(updates: list[dict]):
    """
    批次更新多個項目的時間，用於串聯調整。
    updates 格式：[{"id": 3, "start_time": "11:00"}, ...]
    """
    sb = get_client()
    # Supabase 沒有原生批次 update，逐筆更新
    # 筆數少（通常一天不超過 10 筆），效能可接受
    for u in updates:
        sb.table("itinerary_items")\
            .update({"start_time": u["start_time"]})\
            .eq("id", u["id"])\
            .execute()


def delete_item(item_id):
    """刪除單一行程項目"""
    sb = get_client()
    sb.table("itinerary_items").delete().eq("id", item_id).execute()


def log_adjustment(trip_id, instruction, items_changed: list):
    """記錄一次調整歷史"""
    import json
    sb = get_client()
    sb.table("trip_adjustments").insert({
        "trip_id": trip_id,
        "instruction": instruction,
        # Supabase 不支援直接存 list，轉成 JSON 字串存
        "items_changed": json.dumps(items_changed, ensure_ascii=False),
    }).execute()
