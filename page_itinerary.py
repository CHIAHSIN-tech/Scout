# page_itinerary.py
# 行程排程頁面：建立旅程、新增地點、點卡片編輯

import streamlit as st
import datetime
import re
from datetime import date, timedelta
from collections import defaultdict
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

    if "show_new_trip" not in st.session_state:
        st.session_state["show_new_trip"] = False

    if st.button("＋ 新增旅程", key="btn_new_trip", use_container_width=True):
        st.session_state["show_new_trip"] = not st.session_state["show_new_trip"]
        st.rerun()

    if st.session_state["show_new_trip"]:
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
                    st.session_state["show_new_trip"] = False
                    st.rerun()

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

    trips = db.get_trips(user)
    if not trips:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0;color:#A8A298;font-style:italic;">
            還沒有旅程，點上方「新增旅程」開始規劃吧 ✈️
        </div>
        """, unsafe_allow_html=True)
        return

    for trip in trips:
        s = date.fromisoformat(trip["start_date"])
        e = date.fromisoformat(trip["end_date"])
        days = (e - s).days + 1
        all_items = db.get_all_items(trip["id"])
        sched_count = sum(1 for i in all_items if i.get("day_number") is not None)
        cand_count = len(all_items) - sched_count
        meta = f"{days} 天　·　{sched_count} 個行程"
        if cand_count:
            meta += f"　·　{cand_count} 候選"

        col_info, col_del = st.columns([7, 1])
        with col_info:
            if st.button(
                f"**{trip['name']}**\n\n{trip['start_date']} ～ {trip['end_date']}　·　{meta}",
                key=f"open_{trip['id']}",
                use_container_width=True
            ):
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

    tab_timeline, tab_candidates, tab_ai = st.tabs(
        ["📅 時間軸", "📋 候選 / 確認", "✨ AI 建議"]
    )

    with tab_timeline:
        _tab_timeline(trip_id, total_days, s)

    with tab_candidates:
        _tab_candidates(trip_id, total_days, s)

    with tab_ai:
        page_ai_suggest(trip_id)


# ════════════════════════════════════════
#  Tab 2：候選 / 確認（優先儀表板 + 候選清單）
# ════════════════════════════════════════

def _tab_candidates(trip_id, total_days, start_date):
    # ── 1. 優先儀表板：必須確認且尚未確認的項目 ──
    pending = db.get_unconfirmed_required(trip_id)
    st.markdown(
        '<div style="font-size:15px;font-weight:600;color:#3D6B54;'
        'margin:0.4rem 0 0.6rem;">🔔 優先提醒</div>',
        unsafe_allow_html=True
    )
    if pending:
        st.markdown(
            f'<div style="font-size:13px;color:#A85C32;font-weight:600;'
            f'margin-bottom:6px;">⚠️ 有 {len(pending)} 個「必須確認」項目還沒確認</div>',
            unsafe_allow_html=True
        )
        for it in pending:
            where = (f"Day {it['day_number']} {it['start_time']}"
                     if it.get("day_number") else "候選中")
            col_a, col_b = st.columns([4, 1.6])
            with col_a:
                st.markdown(
                    f'<div style="font-size:14px;padding-top:8px;">'
                    f'{CATEGORIES.get(it["category"], "📌 其他")}　{it["name"]}'
                    f'<span style="color:#A8A298;font-size:12px;">　·　{where}</span></div>',
                    unsafe_allow_html=True
                )
            with col_b:
                if st.button("✅ 標記已確認", key=f"confirm_pending_{it['id']}",
                             use_container_width=True):
                    db.set_confirmed(it["id"], True)
                    st.rerun()
    else:
        st.markdown(
            '<div style="background:#EAF2ED;border-radius:12px;padding:10px 16px;'
            'font-size:13px;color:#3D6B54;">✅ 目前沒有待確認的必訂項目</div>',
            unsafe_allow_html=True
        )

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── 2. 候選清單 ──
    st.markdown(
        '<div style="font-size:15px;font-weight:600;color:#3D6B54;margin:0.4rem 0 0.6rem;">'
        '🗂️ 候選清單'
        '<span style="font-size:12px;color:#A8A298;font-weight:400;">'
        '　還沒決定排哪天的點子</span></div>',
        unsafe_allow_html=True
    )

    # 新增候選（不需指定日期/時段）
    with st.expander("＋ 新增候選項目"):
        with st.form("form_add_candidate", clear_on_submit=True):
            c_name = st.text_input("名稱", placeholder="例：美麗海水族館、某家燒肉")
            col1, col2 = st.columns(2)
            with col1:
                c_cat = st.selectbox("分類", list(CATEGORIES.keys()),
                                     format_func=lambda k: CATEGORIES[k])
            with col2:
                c_dur = st.number_input("預估停留（分鐘）", min_value=15,
                                        max_value=480, value=60, step=15)
            c_notes = st.text_area("備註（選填）", height=70)
            c_required = st.checkbox("必須確認（需要訂位 / 預約）")
            if st.form_submit_button("加入候選", use_container_width=True):
                if not c_name.strip():
                    st.error("請輸入名稱")
                else:
                    db.add_candidate(
                        trip_id, c_name.strip(),
                        duration_minutes=int(c_dur), category=c_cat,
                        notes=c_notes.strip(), confirm_required=c_required,
                    )
                    st.success(f"「{c_name}」已加入候選")
                    st.rerun()

    candidates = db.get_candidates(trip_id)
    if not candidates:
        st.markdown(
            '<div style="text-align:center;padding:1.5rem 0;color:#A8A298;'
            'font-style:italic;">還沒有候選項目，先把想去但還沒定日期的點子丟進來吧</div>',
            unsafe_allow_html=True
        )
        return

    # 排入行程用的天數選單
    day_opts = {
        f"Day {d}  ({(start_date + timedelta(days=d-1)).strftime('%m/%d')})": d
        for d in range(1, total_days + 1)
    }

    for it in candidates:
        cat_label = CATEGORIES.get(it["category"], "📌 其他")
        required = bool(it.get("confirm_required"))
        confirmed = bool(it.get("is_confirmed"))

        # 確認徽章
        badge = ""
        if required:
            if confirmed:
                badge = ('<span style="font-size:11px;color:#3D6B54;background:#EAF2ED;'
                         'border-radius:10px;padding:1px 8px;margin-left:6px;">✅ 已確認</span>')
            else:
                badge = ('<span style="font-size:11px;color:#A85C32;background:#F6E8DD;'
                         'border-radius:10px;padding:1px 8px;margin-left:6px;">⚠️ 待確認</span>')

        with st.container(border=True):
            notes_html = (f'<div style="font-size:12px;color:#A8A298;margin-top:2px;">'
                          f'{it["notes"]}</div>' if it.get("notes") else "")
            st.markdown(
                f'<div style="font-size:11px;color:#A8A298;">{cat_label}　'
                f'<span style="color:#C2DDD1;">⏱ {it["duration_minutes"]} 分</span></div>'
                f'<div style="font-size:16px;font-weight:600;">{it["name"]}{badge}</div>'
                f'{notes_html}',
                unsafe_allow_html=True
            )

            # 排入某天某時段
            with st.expander("📅 排入行程"):
                col_d, col_t = st.columns(2)
                with col_d:
                    sched_label = st.selectbox(
                        "排到第幾天", list(day_opts.keys()),
                        key=f"cand_day_{it['id']}"
                    )
                with col_t:
                    sched_time = st.text_input(
                        "開始時間（HH:MM）", value="09:00",
                        key=f"cand_time_{it['id']}"
                    )
                if st.button("確定排入", key=f"cand_sched_{it['id']}",
                             use_container_width=True):
                    t = sched_time.strip()
                    if not itinerary.is_valid_time(t):
                        st.error("時間格式錯誤，請輸入 HH:MM，例如 09:30")
                    else:
                        db.schedule_item(it["id"], trip_id, day_opts[sched_label], t)
                        st.success(f"「{it['name']}」已排入 {sched_label}")
                        st.rerun()

            # 確認狀態快速切換 + 刪除
            col_req, col_conf, col_del = st.columns([2, 2, 1])
            with col_req:
                req_label = "取消必須確認" if required else "設為必須確認"
                if st.button(req_label, key=f"cand_req_{it['id']}",
                             use_container_width=True):
                    db.set_confirm_required(it["id"], not required)
                    st.rerun()
            with col_conf:
                if required:
                    conf_label = "改未確認" if confirmed else "標記已確認"
                    if st.button(conf_label, key=f"cand_conf_{it['id']}",
                                 use_container_width=True):
                        db.set_confirmed(it["id"], not confirmed)
                        st.rerun()
            with col_del:
                if st.button("✕", key=f"cand_del_{it['id']}",
                             help="刪除此候選", use_container_width=True):
                    db.delete_item(it["id"])
                    st.rerun()


# ════════════════════════════════════════
#  Tab 1：時間軸
# ════════════════════════════════════════

def _tab_timeline(trip_id, total_days, start_date):

    view_mode = st.radio(
        "檢視模式",
        ["單日檢視", "全覽所有天"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"view_mode_{trip_id}"
    )

    if view_mode == "單日檢視":
        day_options = {
            f"Day {d}  ({(start_date + timedelta(days=d-1)).strftime('%m/%d')})": d
            for d in range(1, total_days + 1)
        }
        selected_label = st.selectbox("選擇日期", list(day_options.keys()),
                                      label_visibility="collapsed")
        selected_day = day_options[selected_label]
        items = db.get_items_by_day(trip_id, selected_day)

        if st.checkbox("＋ 新增行程到這天", key=f"show_add_{selected_day}"):
            _tab_add_item(trip_id, total_days, start_date, default_day=selected_day)

    else:
        selected_day = None
        items = db.get_all_items(trip_id)

    if not items:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0;color:#A8A298;font-style:italic;">
            這天還沒有行程，展開上方「新增行程」加入吧
        </div>
        """, unsafe_allow_html=True)
        return

    if view_mode == "全覽所有天":
        _render_all_days(trip_id, total_days, start_date, items)
        return

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

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

    _render_items(trip_id, items)


# ════════════════════════════════════════
#  全覽模式：依天分組顯示
# ════════════════════════════════════════

def _render_all_days(trip_id, total_days, start_date, all_items):
    days_dict = defaultdict(list)
    for item in all_items:
        days_dict[item["day_number"]].append(item)

    for day_num in range(1, total_days + 1):
        day_date = (start_date + timedelta(days=day_num - 1)).strftime("%m/%d")
        st.markdown(
            f'<div style="font-size:15px;font-weight:600;color:#3D6B54;'
            f'margin:1.2rem 0 0.6rem;">Day {day_num}'
            f'<span style="font-size:13px;color:#A8A298;font-weight:400;">'
            f'　{day_date}</span></div>',
            unsafe_allow_html=True
        )

        items = days_dict.get(day_num, [])
        if not items:
            st.markdown(
                '<div style="font-size:13px;color:#A8A298;font-style:italic;'
                'margin-bottom:0.8rem;">這天還沒有行程</div>',
                unsafe_allow_html=True
            )
            continue

        _render_items(trip_id, items)
        st.markdown('<hr style="margin:0.5rem 0">', unsafe_allow_html=True)


# ════════════════════════════════════════
#  共用：渲染行程卡片清單
# ════════════════════════════════════════

def _render_items(trip_id, items):
    # 取得旅程資訊，用於跨天移動的天數選單
    trip_info = db.get_trip(trip_id)
    if trip_info:
        trip_s = date.fromisoformat(trip_info["start_date"])
        trip_e = date.fromisoformat(trip_info["end_date"])
        total_d = (trip_e - trip_s).days + 1
        day_opts = {
            f"Day {d}  ({(trip_s + timedelta(days=d-1)).strftime('%m/%d')})": d
            for d in range(1, total_d + 1)
        }
    else:
        day_opts = {}

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
        # 確認狀態徽章：只有「必須確認」的項目才顯示
        confirm_html = ""
        if item.get("confirm_required"):
            if item.get("is_confirmed"):
                confirm_html = ('<span style="display:inline-block;font-size:11px;'
                                'color:#3D6B54;background:#EAF2ED;border-radius:10px;'
                                'padding:1px 8px;margin-top:4px;">✅ 已確認</span>')
            else:
                confirm_html = ('<span style="display:inline-block;font-size:11px;'
                                'color:#A85C32;background:#F6E8DD;border-radius:10px;'
                                'padding:1px 8px;margin-top:4px;">⚠️ 待確認</span>')

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
                    <div>{confirm_html}</div>
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

                    # ── 跨天移動：第幾天選單 ──
                    if day_opts:
                        current_day_label = next(
                            (k for k, v in day_opts.items() if v == item["day_number"]),
                            list(day_opts.keys())[0]
                        )
                        new_day_label = st.selectbox(
                            "移到第幾天",
                            list(day_opts.keys()),
                            index=list(day_opts.keys()).index(current_day_label),
                            key=f"e_day_{item['id']}"
                        )
                        new_day = day_opts[new_day_label]
                    else:
                        new_day = item["day_number"]

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

                    # ── 確認狀態兩軸 ──
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        new_required = st.checkbox(
                            "必須確認", value=bool(item.get("confirm_required")),
                            key=f"e_req_{item['id']}",
                            help="需要訂位/預約等，未確認會出現在優先提醒"
                        )
                    with col_c2:
                        new_confirmed = st.checkbox(
                            "已確認", value=bool(item.get("is_confirmed")),
                            key=f"e_conf_{item['id']}"
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
                                    # 透過 Supabase 更新（取代舊版 sqlite get_conn 寫法）
                                    db.update_item_full(item["id"], {
                                        "name": new_name.strip(),
                                        "category": new_category,
                                        "start_time": t,
                                        "duration_minutes": int(new_duration),
                                        "location": new_location.strip(),
                                        "address": new_address.strip(),
                                        "booking_ref": new_booking.strip(),
                                        "notes": new_notes.strip(),
                                        "day_number": new_day,
                                        "confirm_required": new_required,
                                        "is_confirmed": new_confirmed,
                                    })
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
#  新增行程項目
# ════════════════════════════════════════

def _tab_add_item(trip_id, total_days, start_date, default_day=1):
    with st.form(f"form_add_item_{default_day}", clear_on_submit=True):
        name = st.text_input("名稱", placeholder="例：海膽蓋飯 根本")
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("分類", list(CATEGORIES.keys()),
                                    format_func=lambda k: CATEGORIES[k])
        with col2:
            new_time_input = st.text_input("開始時間（HH:MM）", value="09:00")

        duration = st.number_input(
            "停留時間（分鐘）",
            min_value=15, max_value=480,
            value=60, step=15
        )

        location    = st.text_input("地點 / 店名", placeholder="例：金澤市場")
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
                            day_number=default_day,
                            name=name.strip(),
                            start_time=t,
                            duration_minutes=int(duration),
                            category=category,
                            location=location.strip(),
                            address=address.strip(),
                            booking_ref=booking_ref.strip(),
                            notes=notes.strip(),
                        )
                        st.success(f"「{name}」已加入 Day {default_day}！")
                        st.rerun()