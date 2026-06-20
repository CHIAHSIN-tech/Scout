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


def _next_sort_order(sb, trip_id, day_number):
    """查某天目前最大的 sort_order，回傳「排在最後」應使用的值（空的話 0，否則最大值 +1）"""
    existing = sb.table("itinerary_items")\
        .select("sort_order")\
        .eq("trip_id", trip_id)\
        .eq("day_number", day_number)\
        .order("sort_order", desc=True)\
        .limit(1)\
        .execute()
    return (existing.data[0]["sort_order"] + 1) if existing.data else 0


def add_item(trip_id, day_number, name, start_time, duration_minutes=60,
             category="other", location="", address="",
             booking_ref="", notes="", source="manual", source_id=None,
             confirm_required=False):
    """新增一個「已排定」行程項目（指定了某天某時段），回傳新項目的 id"""
    sb = get_client()

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
        # 排在當天最後
        "sort_order": _next_sort_order(sb, trip_id, day_number),
        "confirm_required": confirm_required,
    }).execute()
    return res.data[0]["id"]


def add_candidate(trip_id, name, duration_minutes=60, category="other",
                  location="", address="", booking_ref="", notes="",
                  source="manual", source_id=None, confirm_required=False):
    """
    新增一個「候選中」項目：不指定日期/時段（day_number / start_time 皆為 NULL）。
    對應 spec：候選中狀態支援所有項目類型（景點/住宿/餐廳），不會出現在 Day-based Kanban。
    回傳新項目的 id。
    """
    sb = get_client()
    res = sb.table("itinerary_items").insert({
        "trip_id": trip_id,
        "day_number": None,      # NULL = 候選中
        "name": name,
        "category": category,
        "start_time": None,      # 候選中無時段
        "duration_minutes": duration_minutes,
        "location": location,
        "address": address,
        "booking_ref": booking_ref,
        "notes": notes,
        "source": source,
        "source_id": source_id,
        "sort_order": 0,
        "confirm_required": confirm_required,
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


def update_items_schedule(updates: list[dict]):
    """
    批次更新項目的 start_time 與 sort_order，用於同一天的重新排序。
    updates 格式：[{"id": 3, "start_time": "11:00", "sort_order": 0}, ...]
    （取代舊版 itinerary.apply_reorder 直接用 sqlite get_conn 的寫法。）
    """
    sb = get_client()
    for u in updates:
        sb.table("itinerary_items")\
            .update({"start_time": u["start_time"], "sort_order": u["sort_order"]})\
            .eq("id", u["id"])\
            .execute()


def update_item_full(item_id, fields: dict):
    """
    更新單一項目的多個欄位（編輯畫面用）。
    fields 只放要更新的欄位，例如 name / category / start_time / day_number 等。
    （取代 page_itinerary 編輯儲存時直接用 sqlite get_conn 的寫法。）
    """
    sb = get_client()
    sb.table("itinerary_items").update(fields).eq("id", item_id).execute()


# ── 候選 / 已排定 查詢 ──

def get_candidates(trip_id):
    """取得一趟旅程的所有「候選中」項目（day_number IS NULL）"""
    sb = get_client()
    res = sb.table("itinerary_items")\
        .select("*")\
        .eq("trip_id", trip_id)\
        .is_("day_number", "null")\
        .order("id")\
        .execute()
    return res.data


def get_scheduled_items(trip_id):
    """取得一趟旅程所有「已排定」項目（day_number 不為 NULL），按天/時間排序"""
    sb = get_client()
    res = sb.table("itinerary_items")\
        .select("*")\
        .eq("trip_id", trip_id)\
        .not_.is_("day_number", "null")\
        .order("day_number")\
        .order("start_time")\
        .order("sort_order")\
        .execute()
    return res.data


def get_unconfirmed_required(trip_id):
    """
    取得「必須確認且尚未確認」的項目（優先儀表板的核心查詢）。
    對應 spec AC-3：標記為必須確認、若未確認就要被標示出來。
    候選或已排定都可能在內。
    """
    sb = get_client()
    res = sb.table("itinerary_items")\
        .select("*")\
        .eq("trip_id", trip_id)\
        .eq("confirm_required", True)\
        .eq("is_confirmed", False)\
        .order("day_number")\
        .order("start_time")\
        .execute()
    return res.data


# ── 候選 ↔ 已排定 的狀態切換 ──

def schedule_item(item_id, trip_id, day_number, start_time):
    """把一個候選項目排入某天某時段（候選中 → 已排定），排在當天最後"""
    sb = get_client()
    sb.table("itinerary_items").update({
        "day_number": day_number,
        "start_time": start_time,
        "sort_order": _next_sort_order(sb, trip_id, day_number),
    }).eq("id", item_id).execute()


def unschedule_item(item_id):
    """把一個已排定項目退回候選中（清掉日期/時段）"""
    sb = get_client()
    sb.table("itinerary_items").update({
        "day_number": None,
        "start_time": None,
        "sort_order": 0,
    }).eq("id", item_id).execute()


# ── 確認狀態（兩軸）──

def set_confirm_required(item_id, required: bool):
    """設定「必須確認 / 可以彈性」"""
    sb = get_client()
    sb.table("itinerary_items")\
        .update({"confirm_required": required})\
        .eq("id", item_id)\
        .execute()


def set_confirmed(item_id, confirmed: bool):
    """設定「已確認 / 未確認」"""
    sb = get_client()
    sb.table("itinerary_items")\
        .update({"is_confirmed": confirmed})\
        .eq("id", item_id)\
        .execute()


def delete_item(item_id):
    """刪除單一行程項目"""
    sb = get_client()
    sb.table("itinerary_items").delete().eq("id", item_id).execute()


# ── Wishlist CRUD（購物待買清單）──
# Supabase 重構時這組函式被漏掉，但 page_shopping.py 仍在呼叫，
# 導致首頁「購物」一進去就崩潰。這裡補回來，全部走 Supabase。

def add_wishlist_item(username, name, category="", estimated_price=0, notes=""):
    """新增一筆待買項目，回傳新項目的 id"""
    sb = get_client()
    res = sb.table("wishlist").insert({
        "username": username,
        "name": name,
        "category": category,
        "estimated_price": estimated_price,
        "notes": notes,
        "status": "pending",
    }).execute()
    return res.data[0]["id"]


def get_wishlist(username):
    """取得某使用者的所有待買項目（含已購買），依加入順序"""
    sb = get_client()
    res = sb.table("wishlist")\
        .select("*")\
        .eq("username", username)\
        .order("id")\
        .execute()
    return res.data


def update_wishlist_status(item_id, status):
    """更新待買項目狀態（pending / purchased）"""
    sb = get_client()
    sb.table("wishlist").update({"status": status}).eq("id", item_id).execute()


def delete_wishlist_item(item_id):
    """刪除一筆待買項目"""
    sb = get_client()
    sb.table("wishlist").delete().eq("id", item_id).execute()


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
