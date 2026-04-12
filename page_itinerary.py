# page_itinerary.py
# 行程排程頁面：建立旅程、新增地點、點卡片編輯

import streamlit as st
import datetime
import re
from datetime import date, timedelta
import db
import itinerary
from page_ai_suggest import page_ai_suggest

# ── 分類選項 ──
CATEGORIES = {
    "restaurant": "🍽️ 餐廳",
    "hotel":      "🏨 住宿",
    "attraction": "🏛️ 景點",
    "shopping":   "🛍️ 購物",
    "transport":  "🚆 交通",
    "other":      "📌 其他",
}


# ════════════════════════════════════════
#  主入口
# ════════════════════════════════════════

def page_itinerary():
    user = st.session_state["user"]
    state = st.session_state

    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("返回", key="back", use_container_width=True):
            state.pop("current_trip_id", None)
            state["page"] = "home"
            st.rerun()

    if "current_trip_id" not in state:
        _page_trip_list(user)
    else:
        _page_trip_detail(state["current_trip_id"])


# ════════════════════════════════════════
#  旅程列表頁
# ════════════════════════════════════════

def _page_trip_list(user):
    st.markdown("""
    <div style="padding:1rem 0 1.2rem;">
        <div style="font-size:24px;font-weight:600;">🗺️ 我的旅程</div>
    </div>
    """, unsafe_allow_html=True)

    if st.checkbox("＋ 新增旅程", key="show_new_trip"):
        with st.form("form_new_trip"):
            trip_name = st.text_input("旅程名稱", placeholder="例：2026 沖繩 5 天")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("出發日期", value=date.today())
            with col2:
                end_date = st.date_input("結束日期", value=date.today() + timedelta(days=4))
            trip_notes = st.text_area("備註（選填）", height=80)
            submitted = st.form_submit_button("建立旅程", use_container_width=True)

            if submitted:
                if not trip_name.strip():
                    st.error("請輸入旅程名稱")
                elif end_date < start_date:
                    st.error("結束日期不能早於出發日期")
                else:
                    db.create_trip(
                        user, trip_name.strip(),
                        str(start_date), str(end_date), trip_notes
                    )
                    st.success(f"「{trip_name}」已建立！")
                    st.rerun()

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

    trips = db.get_trips(user)
    if not trips:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0;color:#A8A298;font-style:italic;">
            還沒有旅程，勾選上方「新增旅程」開始規劃吧 ✈️
        </div>
        """, unsafe_allow_html=True)
        return

    for trip in trips:
        s = date.fromisoformat(trip["start_date"])
        e = date.fromisoformat(trip["end_date"])
        days = (e - s).days + 1
        item_count = len(db.get_all_items(trip["id"]))

        col_info, col_btn, col_del = st.columns([5, 2, 1])
        with col_info:
            st.markdown(f"""
            <div class="scout-card" style="margin-bottom:0.5rem;">
                <div style="font-size:17px;font-weight:600;color:#3C3830;">{trip['name']}</div>
                <div style="font-size:13px;color:#A8A298;margin-top:4px;">
                    {trip['start_date']} ～ {trip['end_date']}　·　{days} 天　·　{item_count} 個行程
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            if st.button("開啟", key=f"open_{trip['id']}", use_container_width=True):
                st.session_state["current_trip_id"] = trip["id"]
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{trip['id']}", use_container_width=True,
                         help="刪除此旅程"):
                db.delete_trip(trip["id"])
                st.rerun()


# ════════════════════════════════════════
#  行程詳細頁
# ════════════════════════════════════════

def _page_trip_detail(trip_id):
    trip = db.get_trip(trip_id)
    if not trip:
        st.error("找不到此旅程")
        st.session_state.pop("current_trip_id", None)
        st.rerun()

    s = date.fromisoformat(trip["start_date"])
    e = date.fromisoformat(trip["end_date"])
    total_days = (e - s).days + 1

    st.markdown(f"""
    <div style="padding:0.5rem 0 1rem;">
        <div style="font-size:22px;font-weight:600;">{trip['name']}</div>
        <div style="font-size:13px;color:#A8A298;">
            {trip['start_date']} ～ {trip['end_date']}　·　{total_days} 天
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_timeline, tab_add, tab_ai = st.tabs(["📅 時間軸", "＋ 新增行程", "✨ AI 建議"])

    with tab_timeline:
        _tab_timeline(trip_id, total_days, s)

    with tab_add:
        _tab_add_item(trip_id, total_days, s)

    with tab_ai:
        page_ai_suggest(trip_id)


# ════════════════════════════════════════
#  Tab 1：時間軸
# ════════════════════════════════════════

def _tab_timeline(trip_id, total_days, start_date):
    day_options = {
        f"Day {d}  ({(start_date + timedelta(days=d-1)).strftime('%m/%d')})": d
        for d in range(1, total_days + 1)
    }
    selected_label = st.selectbox("選擇日期", list(day_options.keys()),
                                  label_visibility="collapsed")
    selected_day = day_options[selected_label]

    items = db.get_items_by_day(trip_id, selected_day)

    if not items:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0;color:#A8A298;font-style:italic;">
            這天還沒有行程，到「新增行程」頁面加入吧
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

    # ── 順序調整區（↑ ↓ 按鈕）──
    st.markdown(
        '<div style="font-size:13px;color:#A8A298;margin-bottom:0.6rem;">'
        '調整順序後自動重新計算時間</div>',
        unsafe_allow_html=True
    )

    for idx, item in enumerate(items):
        col_up, col_down, col_label = st.columns([1, 1, 8])

        with col_up:
            if idx > 0:
                if st.button("↑", key=f"up_{item['id']}", use_container_width=True):
                    new_order = [i["id"] for i in items]
                    new_order[idx], new_order[idx - 1] = new_order[idx - 1], new_order[idx]
                    itinerary.apply_reorder(trip_id, selected_day, new_order)
                    st.rerun()
            else:
                st.markdown("　")

        with col_down:
            if idx < len(items) - 1:
                if st.button("↓", key=f"down_{item['id']}", use_container_width=True):
                    new_order = [i["id"] for i in items]
                    new_order[idx], new_order[idx + 1] = new_order[idx + 1], new_order[idx]
                    itinerary.apply_reorder(trip_id, selected_day, new_order)
                    st.rerun()
            else:
                st.markdown("　")

        with col_label:
            st.markdown(
                f'<div style="padding:6px 0;font-size:14px;">'
                f'<span style="color:#3D6B54;font-weight:600;">{item["start_time"]}</span>'
                f'　{item["name"]}'
                f'<span style="color:#A8A298;font-size:12px;">　{item["duration_minutes"]} 分</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── 時間軸卡片 ──
    for item in items:
        end_min = (itinerary.time_str_to_minutes(item["start_time"])
                   + item["duration_minutes"])
        end_time = itinerary.minutes_to_time_str(end_min)
        cat_label = CATEGORIES.get(item["category"], "📌 其他")

        booking_html = (
            f'<div style="font-size:12px;color:#A8A298;margin-top:2px;">📋 {item["booking_ref"]}</div>'
            if item["booking_ref"] else ""
        )
        notes_html = (
            f'<div style="font-size:12px;color:#A8A298;margin-top:3px;">{item["notes"]}</div>'
            if item["notes"] else ""
        )
        duration_html = (
            f'<div style="font-size:11px;color:#C2DDD1;margin-top:6px;">'
            f'⏱ {item["duration_minutes"]} 分鐘</div>'
        )

        edit_key = f"editing_{item['id']}"
        is_editing = st.session_state.get(edit_key, False)

        col_time, col_card, col_actions = st.columns([2, 6, 1])

        with col_time:
            st.markdown(f"""
            <div style="text-align:right;padding-top:6px;">
                <div style="font-size:15px;font-weight:600;color:#3D6B54;">{item['start_time']}</div>
                <div style="font-size:11px;color:#A8A298;">→ {end_time}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_card:
            if not is_editing:
                st.markdown(f"""
                <div class="scout-card" style="padding:14px 18px;margin-bottom:0.2rem;">
                    <div style="font-size:11px;color:#A8A298;margin-bottom:2px;">{cat_label}</div>
                    <div style="font-size:16px;font-weight:600;">{item['name']}</div>
                    <div style="font-size:12px;color:#6B6558;">{item['location']}</div>
                    {booking_html}{notes_html}{duration_html}
                </div>
                """, unsafe_allow_html=True)
            else:
                with st.container(border=True):
                    new_name = st.text_input(
                        "名稱", value=item["name"],
                        key=f"e_name_{item['id']}"
                    )
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        new_time_str = st.text_input(
                            "開始時間（HH:MM）",
                            value=item["start_time"],
                            key=f"e_time_{item['id']}"
                        )
                    with col_e2:
                        new_duration = st.number_input(
                            "停留時間（分鐘）",
                            min_value=15, max_value=480,
                            value=item["duration_minutes"], step=15,
                            key=f"e_dur_{item['id']}"
                        )
                    new_category = st.selectbox(
                        "分類",
                        list(CATEGORIES.keys()),
                        index=list(CATEGORIES.keys()).index(item["category"])
                              if item["category"] in CATEGORIES else 0,
                        format_func=lambda k: CATEGORIES[k],
                        key=f"e_cat_{item['id']}"
                    )
                    new_location = st.text_input(
                        "地點 / 店名", value=item["location"],
                        key=f"e_loc_{item['id']}"
                    )
                    # ── 修改一：編輯模式地址欄位名稱 ──
                    new_address = st.text_input(
                        "地址 / Google Map", value=item["address"],
                        key=f"e_addr_{item['id']}"
                    )
                    new_booking = st.text_input(
                        "預約編號", value=item["booking_ref"],
                        key=f"e_book_{item['id']}"
                    )
                    new_notes = st.text_area(
                        "備註", value=item["notes"], height=80,
                        key=f"e_notes_{item['id']}"
                    )

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("✅ 儲存", use_container_width=True,
                                     key=f"save_{item['id']}"):
                            t = new_time_str.strip()
                            if not re.match(r"^\d{2}:\d{2}$", t):
                                st.error("時間格式錯誤，請輸入 HH:MM，例如 09:30")
                            else:
                                h, m = map(int, t.split(":"))
                                if not (0 <= h <= 23 and 0 <= m <= 59):
                                    st.error("時間超出範圍，請輸入 00:00 ~ 23:59")
                                else:
                                    conn = db.get_conn()
                                    conn.execute("""
                                        UPDATE itinerary_items
                                        SET name=?, category=?, start_time=?,
                                            duration_minutes=?, location=?, address=?,
                                            booking_ref=?, notes=?
                                        WHERE id=?
                                    """, (
                                        new_name.strip(), new_category, t,
                                        int(new_duration),
                                        new_location.strip(),
                                        new_address.strip(),
                                        new_booking.strip(),
                                        new_notes.strip(),
                                        item["id"]
                                    ))
                                    conn.commit()
                                    conn.close()
                                    db.log_adjustment(
                                        trip_id, f"編輯：{item['name']}",
                                        [{"id": item["id"], "start_time": t}]
                                    )
                                    st.session_state[edit_key] = False
                                    st.success("已儲存")
                                    st.rerun()
                    with col_cancel:
                        if st.button("✕ 取消", use_container_width=True,
                                     key=f"cancel_edit_{item['id']}"):
                            st.session_state[edit_key] = False
                            st.rerun()

        with col_actions:
            if not is_editing:
                if st.button("✕", key=f"del_item_{item['id']}",
                             help="刪除此行程",
                             use_container_width=True):
                    db.delete_item(item["id"])
                    st.rerun()
                st.markdown('<div style="height:0.3rem"></div>', unsafe_allow_html=True)
                if st.button("✏️", key=f"edit_btn_{item['id']}",
                             help="編輯此行程",
                             use_container_width=True):
                    st.session_state[edit_key] = True
                    st.rerun()


# ════════════════════════════════════════
#  Tab 2：新增行程項目
# ════════════════════════════════════════

def _tab_add_item(trip_id, total_days, start_date):
    # ── 修改二：加上 clear_on_submit=True ──
    with st.form("form_add_item", clear_on_submit=True):
        name = st.text_input("名稱", placeholder="例：海膽蓋飯 根本")
        col1, col2 = st.columns(2)
        with col1:
            day_options = {
                f"Day {d}  ({(start_date + timedelta(days=d-1)).strftime('%m/%d')})": d
                for d in range(1, total_days + 1)
            }
            day_label = st.selectbox("第幾天", list(day_options.keys()))
            day_number = day_options[day_label]
        with col2:
            category = st.selectbox("分類", list(CATEGORIES.keys()),
                                    format_func=lambda k: CATEGORIES[k])
        col3, col4 = st.columns(2)
        with col3:
            new_time_input = st.text_input("開始時間（HH:MM）", value="09:00")
        with col4:
            duration = st.number_input("停留時間（分鐘）", min_value=15,
                                       max_value=480, value=60, step=15)
        location    = st.text_input("地點 / 店名", placeholder="例：金澤市場")
        # ── 修改三：新增模式地址欄位名稱 ──
        address     = st.text_input("地址 / Google Map（選填）")
        booking_ref = st.text_input("預約編號（選填）", placeholder="例：CONF-12345")
        notes       = st.text_area("備註（選填）", height=80)

        submitted = st.form_submit_button("新增到行程", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("請輸入名稱")
            else:
                t = new_time_input.strip()
                if not re.match(r"^\d{2}:\d{2}$", t):
                    st.error("時間格式錯誤，請輸入 HH:MM，例如 09:30")
                else:
                    h, m = map(int, t.split(":"))
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        st.error("時間超出範圍，請輸入 00:00 ~ 23:59")
                    else:
                        db.add_item(
                            trip_id=trip_id,
                            day_number=day_number,
                            name=name.strip(),
                            start_time=t,
                            duration_minutes=int(duration),
                            category=category,
                            location=location.strip(),
                            address=address.strip(),
                            booking_ref=booking_ref.strip(),
                            notes=notes.strip(),
                        )
                        st.success(f"「{name}」已加入 Day {day_number}！")
                        st.rerun()