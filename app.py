import streamlit as st
from db import init_db

st.set_page_config(
    page_title="Scout",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 初始化資料庫
init_db()


# --- 登入 ---
def login():
    st.markdown(
        "<h1 style='text-align:center;'>🔍 Scout</h1>"
        "<p style='text-align:center;color:gray;'>個人生活研究助理</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    username = st.text_input("使用者名稱").strip().lower()
    password = st.text_input("密碼", type="password")

    if st.button("登入", use_container_width=True):
        passwords = st.secrets.get("passwords", {})
        if username in passwords and passwords[username] == password:
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("帳號或密碼錯誤")


# --- 主頁 ---
def home():
    user = st.session_state["user"]

    # 側邊欄
    with st.sidebar:
        st.write(f"👤 **{user.capitalize()}**")
        if st.button("登出"):
            del st.session_state["user"]
            st.rerun()

    st.markdown(
        "<h2 style='text-align:center;'>🔍 Scout</h2>",
        unsafe_allow_html=True,
    )
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            "<div style='text-align:center'>"
            "<h1>🛍️</h1>"
            "<p><b>購物</b></p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("進入", key="shop", use_container_width=True):
            st.session_state["page"] = "shopping"
            st.rerun()

    with col2:
        st.markdown(
            "<div style='text-align:center'>"
            "<h1>🍽️</h1>"
            "<p><b>餐廳</b></p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("進入", key="food", use_container_width=True):
            st.session_state["page"] = "restaurant"
            st.rerun()

    with col3:
        st.markdown(
            "<div style='text-align:center'>"
            "<h1>🏨</h1>"
            "<p><b>旅館</b></p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("進入", key="hotel", use_container_width=True):
            st.session_state["page"] = "hotel"
            st.rerun()


# --- 模組 placeholder ---
def page_shopping():
    if st.button("← 返回首頁"):
        st.session_state["page"] = "home"
        st.rerun()
    st.header("🛍️ 購物")
    st.info("購物模組開發中...")


def page_restaurant():
    if st.button("← 返回首頁"):
        st.session_state["page"] = "home"
        st.rerun()
    st.header("🍽️ 餐廳")
    st.info("餐廳模組開發中...")


def page_hotel():
    if st.button("← 返回首頁"):
        st.session_state["page"] = "home"
        st.rerun()
    st.header("🏨 旅館")
    st.info("旅館模組開發中...")


# --- 路由 ---
if "user" not in st.session_state:
    login()
else:
    page = st.session_state.get("page", "home")
    if page == "shopping":
        page_shopping()
    elif page == "restaurant":
        page_restaurant()
    elif page == "hotel":
        page_hotel()
    else:
        home()
