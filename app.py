import streamlit as st
from db import init_db
from page_itinerary import page_itinerary
from page_shopping import page_shopping

st.set_page_config(
    page_title="Scout",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

init_db()

SVG_ENTER = 'url("data:image/svg+xml,%3Csvg width=\'13\' height=\'13\' viewBox=\'0 0 13 13\' fill=\'none\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cpath d=\'M2 11L11 2M11 2H4M11 2V9\' stroke=\'%233D6B54\' stroke-width=\'1.5\' stroke-linecap=\'round\' stroke-linejoin=\'round\'/%3E%3C/svg%3E")'
SVG_SECONDARY = 'url("data:image/svg+xml,%3Csvg width=\'13\' height=\'13\' viewBox=\'0 0 13 13\' fill=\'none\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cpath d=\'M2 6.5H11M11 6.5L7 2.5M11 6.5L7 10.5\' stroke=\'%23EAF2ED\' stroke-width=\'1.5\' stroke-linecap=\'round\' stroke-linejoin=\'round\'/%3E%3C/svg%3E")'

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 2.5rem; padding-bottom: 2.5rem; max-width: 640px; }}
html, body, [class*="css"], * {{
    font-family: 'Noto Sans TC', sans-serif !important;
    color: #3C3830;
}}
.stApp {{ background-color: #F5F0EA; }}

/* ── Logo ── */
.scout-header {{ text-align: center; padding: 2.5rem 0 1.5rem; }}
.scout-logo {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 64px; height: 64px; border: 2px solid #3D6B54; border-radius: 50%;
    margin-bottom: 1rem; font-size: 1.8rem;
}}
.scout-title {{ font-size: 38px; font-weight: 600; color: #3C3830; margin-bottom: 0.4rem;
    font-family: Georgia, 'Noto Serif TC', serif !important; }}
.scout-label {{ font-size: 14px; letter-spacing: 0.08em; text-transform: uppercase;
    color: #A8A298; margin-top: 0.6rem; font-family: Georgia, 'Noto Serif TC', serif !important; }}

/* ── 一般卡片 ── */
.scout-card {{
    background: #FFFFFF; border: 0.5px solid #C2DDD1;
    border-radius: 16px; padding: 28px; margin-bottom: 1rem;
}}
hr {{ border: none; border-top: 0.5px solid #DCD8D0; margin: 1.2rem 0; }}

/* ══════════════════════════════════
   全域按鈕基礎
══════════════════════════════════ */
.stButton > button {{
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 10px !important;
    padding: 8px 8px 8px 20px !important;
    background: #3D6B54 !important;
    border: none !important;
    border-radius: 100px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    transition: background 0.15s, transform 0.25s, box-shadow 0.25s !important;
    box-shadow: none !important;
    width: 100%;
    color: #FFFFFF !important;
}}
.stButton > button * {{ color: #FFFFFF !important; }}
.stButton > button:hover {{ background: #2A4D3A !important; }}

/* 全域箭頭 */
.stButton > button::after {{
    content: "" !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-width: 28px !important; width: 28px !important; height: 28px !important;
    border-radius: 50% !important;
    background-color: #EAF2ED !important;
    background-image: {SVG_ENTER} !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: 13px 13px !important;
    flex-shrink: 0 !important;
}}

/* ══════════════════════════════════
   分類卡片
══════════════════════════════════ */
.st-key-btn_shop .stButton > button,
.st-key-btn_food .stButton > button,
.st-key-btn_hotel .stButton > button {{
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    height: 280px !important;
    padding: 40px 16px !important;
    border-radius: 20px !important;
    border: 1.5px solid #C2DDD1 !important;
    background: #EAF2ED !important;
    box-shadow: 0 2px 8px rgba(61,107,84,0.06) !important;
    transition: background 0.25s ease, border-color 0.25s ease,
                transform 0.25s ease, box-shadow 0.25s ease !important;
}}
.st-key-btn_shop .stButton > button::after,
.st-key-btn_food .stButton > button::after,
.st-key-btn_hotel .stButton > button::after {{ display: none !important; }}
.st-key-btn_shop .stButton > button *,
.st-key-btn_food .stButton > button *,
.st-key-btn_hotel .stButton > button * {{ color: #5C8C72 !important; }}
.st-key-btn_shop .stButton > button p:first-of-type,
.st-key-btn_food .stButton > button p:first-of-type,
.st-key-btn_hotel .stButton > button p:first-of-type {{
    font-size: 64px !important; line-height: 1 !important; margin: 0 0 16px 0 !important;
}}
.st-key-btn_shop .stButton > button p:last-of-type,
.st-key-btn_food .stButton > button p:last-of-type,
.st-key-btn_hotel .stButton > button p:last-of-type {{
    font-size: 20px !important; font-weight: 700 !important;
    color: #5C8C72 !important; margin: 0 !important;
}}
.st-key-btn_shop .stButton > button:hover,
.st-key-btn_food .stButton > button:hover,
.st-key-btn_hotel .stButton > button:hover {{
    background: #3D6B54 !important; border-color: #3D6B54 !important;
    transform: translateY(-6px) !important;
    box-shadow: 0 16px 36px rgba(61,107,84,0.22) !important;
}}
.st-key-btn_shop .stButton > button:hover *,
.st-key-btn_food .stButton > button:hover *,
.st-key-btn_hotel .stButton > button:hover * {{ color: #EAF2ED !important; }}
.st-key-btn_shop .stButton > button:active,
.st-key-btn_food .stButton > button:active,
.st-key-btn_hotel .stButton > button:active {{
    transform: translateY(-2px) scale(0.98) !important;
}}

/* ══════════════════════════════════
   Secondary（登出 & 返回）
══════════════════════════════════ */
.st-key-logout .stButton > button,
.st-key-back .stButton > button {{
    background: #EAF2ED !important;
    color: #3D6B54 !important;
}}
.st-key-logout .stButton > button *,
.st-key-back .stButton > button * {{ color: #3D6B54 !important; }}
.st-key-logout .stButton > button:hover,
.st-key-back .stButton > button:hover {{ background: #C2DDD1 !important; }}
.st-key-logout .stButton > button::after,
.st-key-back .stButton > button::after {{
    background-color: #3D6B54 !important;
    background-image: {SVG_SECONDARY} !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: 13px 13px !important;
}}

/* ── Selectbox ── */
.stSelectbox label {{ font-size: 13px !important; letter-spacing: 0.08em !important;
    text-transform: uppercase !important; color: #A8A298 !important; }}
.stSelectbox > div > div {{
    border: 1.5px solid #B8D4C4 !important; border-radius: 100px !important;
    background: #FFFFFF !important; font-size: 14px !important;
    padding: 2px 8px !important; color: #3C3830 !important;
}}
div[data-baseweb="popover"] * {{ font-family: 'Noto Sans TC', sans-serif !important; font-size: 14px !important; }}

/* ── 歡迎語 ── */
.welcome-greeting {{ font-size: 30px; font-weight: 500; color: #3C3830; line-height: 1.3;
    margin-bottom: 0.2rem; font-family: Georgia, 'Noto Serif TC', serif !important; }}
.welcome-sub {{ font-size: 18px; color: #A8A298; font-style: italic;
    font-family: Georgia, 'Noto Serif TC', serif !important; }}

/* ── 上移／下移按鈕：正圓形，無箭頭 ── */
[class*="st-key-up_"] .stButton > button,
[class*="st-key-down_"] .stButton > button {{
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    min-height: 36px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    justify-content: center !important;
}}
[class*="st-key-up_"] .stButton > button::after,
[class*="st-key-down_"] .stButton > button::after {{
    display: none !important;
}}

/* ── 刪除／編輯／購物清單小按鈕：正圓形，無箭頭 ── */
[class*="st-key-del_item_"] .stButton > button,
[class*="st-key-edit_btn_"] .stButton > button,
[class*="st-key-del_wish_"] .stButton > button,
[class*="st-key-toggle_"] .stButton > button {{
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    min-height: 36px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    justify-content: center !important;
}}
[class*="st-key-del_item_"] .stButton > button::after,
[class*="st-key-edit_btn_"] .stButton > button::after,
[class*="st-key-del_wish_"] .stButton > button::after,
[class*="st-key-toggle_"] .stButton > button::after {{
    display: none !important;
}}

/* ── 旅程卡片按鈕：白底卡片風格，無箭頭 ── */
[class*="st-key-open_"] .stButton > button {{
    background: #FFFFFF !important;
    border: 0.5px solid #C2DDD1 !important;
    border-radius: 16px !important;
    padding: 16px 20px !important;
    justify-content: flex-start !important;
    text-align: left !important;
    color: #3C3830 !important;
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 4px !important;
    height: auto !important;
}}
[class*="st-key-open_"] .stButton > button * {{ color: #3C3830 !important; }}
[class*="st-key-open_"] .stButton > button:hover {{
    background: #EAF2ED !important;
    border-color: #3D6B54 !important;
}}
[class*="st-key-open_"] .stButton > button::after {{ display: none !important; }}

/* ── 新增旅程 & 行程規劃按鈕：無箭頭 ── */
.st-key-btn_new_trip .stButton > button::after,
.st-key-btn_itinerary .stButton > button::after {{
    display: none !important;
}}

/* ── 儲存／取消按鈕：無箭頭 ── */
[class*="st-key-save_"] .stButton > button::after,
[class*="st-key-cancel_edit_"] .stButton > button::after,
[class*="st-key-confirm_"] .stButton > button::after {{
    display: none !important;
}}

/* ── 返回按鈕：箭頭改為往左，放在左邊 ── */
.st-key-back .stButton > button {{
    flex-direction: row-reverse !important;
    justify-content: flex-end !important;
}}
.st-key-back .stButton > button::after {{
    background-color: #3D6B54 !important;
    background-image: url("data:image/svg+xml,%3Csvg width='13' height='13' viewBox='0 0 13 13' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 6.5H2M2 6.5L6 2.5M2 6.5L6 10.5' stroke='%23EAF2ED' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: 13px 13px !important;
}}

/* ── 進入按鈕：置中，無箭頭 ── */
.st-key-btn_login .stButton > button {{
    justify-content: center !important;
}}
.st-key-btn_login .stButton > button::after {{
    display: none !important;
}}

/* ── 登出按鈕：置中，無箭頭 ── */
.st-key-logout .stButton > button {{
    justify-content: center !important;
}}
.st-key-logout .stButton > button::after {{
    display: none !important;
}}

</style>
""", unsafe_allow_html=True)

USERS = {"Stanley": "Stanley", "珈欣": "珈欣"}


def login():
    st.markdown("""
    <div class="scout-header">
        <div class="scout-logo">🔍</div>
        <div class="scout-title">Scout</div>
        <div class="scout-label">你的生活探索夥伴</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<p style="font-size:13px;letter-spacing:0.08em;text-transform:uppercase;color:#A8A298;margin-bottom:0.4rem;text-align:center;">選擇使用者</p>', unsafe_allow_html=True)
    username = st.selectbox("選擇使用者", list(USERS.keys()), label_visibility="collapsed")
    st.markdown('<div style="height:0.8rem"></div>', unsafe_allow_html=True)
    if st.button("進入", use_container_width=True, key="btn_login"):
        st.session_state["user"] = username
        st.session_state["page"] = "home"
        st.rerun()


def home():
    user = st.session_state["user"]
    st.markdown(f"""
    <div style="padding: 1rem 0 1.5rem;">
        <div class="welcome-greeting">嗨，{user} 👋</div>
        <div class="welcome-sub">今天想探索什麼？</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:0.8rem"></div>', unsafe_allow_html=True)
    if st.button("🗺️  行程規劃", use_container_width=True, key="btn_itinerary"):
        st.session_state["page"] = "itinerary"
        st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🛍️\n\n**購物**", key="btn_shop", use_container_width=True):
            st.session_state["page"] = "shopping"
            st.rerun()
    with col2:
        if st.button("🍽️\n\n**餐廳**", key="btn_food", use_container_width=True):
            st.session_state["page"] = "restaurant"
            st.rerun()
    with col3:
        if st.button("🏨\n\n**旅館**", key="btn_hotel", use_container_width=True):
            st.session_state["page"] = "hotel"
            st.rerun()

    st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([2, 1.5, 2])
    with col_m:
        if st.button("登出", key="logout", use_container_width=True):
            del st.session_state["user"]
            st.session_state["page"] = "home"
            st.rerun()


def page_with_back(emoji, title, note):
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("返回", key="back", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()
    st.markdown(f"""
    <div class="scout-card" style="margin-top:0.8rem;">
        <div style="font-size:28px;margin-bottom:0.6rem;">{emoji}</div>
        <div style="font-size:22px;font-weight:500;color:#3C3830;margin-bottom:0.4rem;">{title}</div>
        <div style="font-size:14px;font-style:italic;color:#6B6558;">{note}</div>
    </div>
    """, unsafe_allow_html=True)


def page_restaurant(): page_with_back("🍽️", "餐廳", "餐廳模組開發中…")
def page_hotel():      page_with_back("🏨", "旅館", "旅館模組開發中…")


# ── 路由 ──
if "user" not in st.session_state:
    login()
else:
    page = st.session_state.get("page", "home")
    if page == "shopping":     page_shopping()
    elif page == "restaurant": page_restaurant()
    elif page == "hotel":      page_hotel()
    elif page == "itinerary":  page_itinerary()
    else:                      home()