import streamlit as st
from db import init_db

st.set_page_config(
    page_title="Scout",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2.5rem; padding-bottom: 2.5rem; max-width: 640px; }
html, body, [class*="css"], * {
    font-family: 'Noto Sans TC', sans-serif !important;
    color: #3C3830;
}
.stApp { background-color: #F5F0EA; }

/* ── Logo ── */
.scout-header { text-align: center; padding: 2.5rem 0 1.5rem; }
.scout-logo {
    display: inline-flex; align-items: center; justify-content: center;
    width: 64px; height: 64px; border: 2px solid #3D6B54; border-radius: 50%;
    margin-bottom: 1rem; font-size: 1.8rem;
}
.scout-title  { font-size: 38px; font-weight: 600; color: #3C3830; margin-bottom: 0.4rem; font-family: Georgia, 'Noto Serif TC', serif !important; }
.scout-tagline { font-size: 20px; font-style: italic; color: #6B6558; line-height: 1.7; font-family: Georgia, 'Noto Serif TC', serif !important; }
.scout-label  { font-size: 14px; letter-spacing: 0.08em; text-transform: uppercase; color: #A8A298; margin-top: 0.6rem; font-family: Georgia, 'Noto Serif TC', serif !important; }

/* ── 一般卡片 ── */
.scout-card {
    background: #FFFFFF; border: 0.5px solid #C2DDD1;
    border-radius: 16px; padding: 28px; margin-bottom: 1rem;
}
hr { border: none; border-top: 0.5px solid #DCD8D0; margin: 1.2rem 0; }

/* ══════════════════════════════════════
   全域按鈕基礎（進入、登出、返回）
══════════════════════════════════════ */
.stButton > button {
    display: flex !important; align-items: center !important;
    justify-content: space-between !important; gap: 10px !important;
    padding: 8px 8px 8px 20px !important;
    background: #3D6B54 !important; border: none !important;
    border-radius: 100px !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 15px !important; font-weight: 400 !important;
    transition: background 0.15s !important;
    box-shadow: none !important; width: 100%;
    color: #FFFFFF !important;
}
.stButton > button * { color: #FFFFFF !important; }
.stButton > button:hover { background: #2A4D3A !important; }
.stButton > button::after {
    content: "↗"; display: inline-flex; align-items: center; justify-content: center;
    min-width: 28px; width: 28px; height: 28px; border-radius: 50%;
    background: #EAF2ED; color: #3D6B54 !important; font-size: 13px; flex-shrink: 0;
}

/* ── Secondary（登出 & 返回）── */
.btn-secondary .stButton > button { background: #EAF2ED !important; }
.btn-secondary .stButton > button,
.btn-secondary .stButton > button * { color: #3D6B54 !important; }
.btn-secondary .stButton > button::after { content: "→"; background: #3D6B54; color: #EAF2ED !important; }
.btn-secondary .stButton > button:hover { background: #C2DDD1 !important; }

/* ══════════════════════════════════════
   分類卡片：type="primary" 按鈕
══════════════════════════════════════ */
button[kind="primary"] {
    background: #EAF2ED !important;
    border: 1.5px solid #C2DDD1 !important;
    border-radius: 24px !important;
    height: 260px !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 16px !important;
    padding: 32px 20px !important;
    color: #5C8C72 !important;
    transition: background 0.2s, border-color 0.2s, transform 0.15s, color 0.2s !important;
    box-shadow: none !important;
}
button[kind="primary"] * { color: #5C8C72 !important; }
button[kind="primary"]::after { display: none !important; }

/* emoji */
button[kind="primary"] p:first-of-type {
    font-size: 64px !important; line-height: 1 !important; margin: 0 !important;
}
/* label */
button[kind="primary"] p:last-of-type {
    font-size: 20px !important; font-weight: 700 !important; margin: 0 !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    color: #5C8C72 !important;
}

/* Hover：深綠 */
button[kind="primary"]:hover {
    background: #3D6B54 !important;
    border-color: #3D6B54 !important;
    transform: translateY(-4px) !important;
    box-shadow: 0 8px 24px rgba(61,107,84,0.18) !important;
}
button[kind="primary"]:hover,
button[kind="primary"]:hover * { color: #EAF2ED !important; }
button[kind="primary"]:active { transform: scale(0.97) !important; }

/* ── Selectbox ── */
.stSelectbox label { font-size: 13px !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; color: #A8A298 !important; }
.stSelectbox > div > div {
    border: 1.5px solid #B8D4C4 !important; border-radius: 100px !important;
    background: #FFFFFF !important; font-size: 14px !important; padding: 2px 8px !important; color: #3C3830 !important;
}
div[data-baseweb="popover"] * { font-family: 'Noto Sans TC', sans-serif !important; font-size: 14px !important; }

/* ── 歡迎語 ── */
.welcome-greeting { font-size: 30px; font-weight: 500; color: #3C3830; line-height: 1.3; margin-bottom: 0.2rem; font-family: Georgia, 'Noto Serif TC', serif !important; }
.welcome-sub { font-size: 18px; color: #A8A298; font-style: italic; font-family: Georgia, 'Noto Serif TC', serif !important; }
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
    if st.button("進入", use_container_width=True):
        st.session_state["user"] = username
        st.rerun()

def home():
    user = st.session_state["user"]
    st.markdown(f"""
    <div style="padding: 1rem 0 1.5rem;">
        <div class="welcome-greeting">嗨，{user} 👋</div>
        <div class="welcome-sub">今天想探索什麼？</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    categories = [
        (col1, "shop",  "shopping",   "購物", "🛍️"),
        (col2, "food",  "restaurant", "餐廳", "🍽️"),
        (col3, "hotel", "hotel",      "旅館", "🏨"),
    ]
    for col, key, page, label, icon in categories:
        with col:
            if st.button(f"{icon}\n\n**{label}**", key=key, use_container_width=True):
                st.session_state["page"] = page
                st.rerun()

    st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([2, 1.5, 2])
    with col_m:
        st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
        if st.button("登出", key="logout", use_container_width=True):
            del st.session_state["user"]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def page_with_back(emoji, title, note):
    col_back, _ = st.columns([1, 4])
    with col_back:
        st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
        if st.button("返回", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="scout-card" style="margin-top:0.8rem;">
        <div style="font-size:28px;margin-bottom:0.6rem;">{emoji}</div>
        <div style="font-size:22px;font-weight:500;color:#3C3830;margin-bottom:0.4rem;">{title}</div>
        <div style="font-size:14px;font-style:italic;color:#6B6558;">{note}</div>
    </div>
    """, unsafe_allow_html=True)

def page_shopping():  page_with_back("🛍️", "購物", "購物模組開發中…")
def page_restaurant(): page_with_back("🍽️", "餐廳", "餐廳模組開發中…")
def page_hotel():     page_with_back("🏨", "旅館", "旅館模組開發中…")

if "user" not in st.session_state:
    login()
else:
    page = st.session_state.get("page", "home")
    if page == "shopping":    page_shopping()
    elif page == "restaurant": page_restaurant()
    elif page == "hotel":     page_hotel()
    else:                     home()
