import json
import streamlit as st
import db
from ai import ai_generate

CATEGORIES = ["", "服飾", "3C", "美妝保養", "食品飲料", "生活用品", "書籍文具", "其他"]
CATEGORY_EMOJI = {
    "服飾": "👔", "3C": "💻", "美妝保養": "💄",
    "食品飲料": "🍱", "生活用品": "🏠", "書籍文具": "📚", "其他": "🛍️", "": "🛍️"
}


def _analyse_url(url: str) -> dict:
    """把商品連結送給 Gemini，要求回傳結構化 JSON"""
    prompt = f"""你是一個購物助理，幫使用者從商品頁面連結擷取資訊。

請根據以下 URL 推測或擷取商品資訊，回傳 **純 JSON**，不要包含 markdown code block：
{{
  "name": "商品名稱",
  "category": "服飾 | 3C | 美妝保養 | 食品飲料 | 生活用品 | 書籍文具 | 其他",
  "estimated_price": 數字（新台幣，不確定則填 0）,
  "notes": "備註（品牌、顏色、規格等，不確定則空字串）"
}}

URL：{url}"""

    try:
        from google.genai import types
        resp = ai_generate(
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        raw = resp.text.strip()
        # 移除可能的 markdown 包裝
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return {}


def page_shopping():
    user = st.session_state.get("user", "")

    # 返回按鈕
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("返回", key="back", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("""
    <div style="padding: 0.8rem 0 1rem;">
        <div style="font-size:24px;font-weight:600;color:#3C3830;">🛍️ 購物清單</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 區塊一：貼連結自動分析 ──
    with st.expander("🔗 貼連結，讓 AI 幫你填資料", expanded=False):
        url_input = st.text_input("商品連結", placeholder="https://...", label_visibility="collapsed",
                                  key="shop_url_input")
        if st.button("分析連結", key="btn_analyse_url", use_container_width=True):
            if url_input.strip():
                with st.spinner("AI 分析中…"):
                    result = _analyse_url(url_input.strip())
                if result:
                    st.session_state["shop_prefill"] = result
                    st.success("分析完成！請在下方確認並儲存。")
                else:
                    st.warning("無法解析，請手動填寫。")
            else:
                st.warning("請先輸入連結。")

    # ── 區塊二：新增表單（prefill 或手動）──
    prefill = st.session_state.get("shop_prefill", {})
    with st.expander("＋ 新增待買項目", expanded=bool(prefill)):
        with st.form("form_add_wish", clear_on_submit=True):
            name = st.text_input("商品名稱 *", value=prefill.get("name", ""))
            col_cat, col_price = st.columns(2)
            with col_cat:
                cat_default = prefill.get("category", "")
                cat_idx = CATEGORIES.index(cat_default) if cat_default in CATEGORIES else 0
                category = st.selectbox("分類", CATEGORIES, index=cat_idx)
            with col_price:
                price = st.number_input("預估價格（NT$）", min_value=0.0, step=1.0,
                                        value=float(prefill.get("estimated_price", 0)))
            notes = st.text_input("備註", value=prefill.get("notes", ""))
            submitted = st.form_submit_button("儲存", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("商品名稱不能為空。")
                else:
                    db.add_wishlist_item(user, name.strip(), category, price, notes.strip())
                    st.session_state.pop("shop_prefill", None)
                    st.success("已加入清單！")
                    st.rerun()

    # ── 區塊三：待買清單 ──
    items = db.get_wishlist(user)
    pending = [i for i in items if i["status"] == "pending"]
    purchased = [i for i in items if i["status"] == "purchased"]

    st.markdown(f"""
    <div style="font-size:13px;letter-spacing:0.08em;text-transform:uppercase;
         color:#A8A298;margin:1.2rem 0 0.6rem;">
        待買（{len(pending)} 件）
    </div>
    """, unsafe_allow_html=True)

    if not pending:
        st.markdown('<div style="color:#A8A298;font-size:14px;padding:0.5rem 0;">清單是空的，趕快加幾樣吧 ✨</div>',
                    unsafe_allow_html=True)
    else:
        for item in pending:
            _render_item(item)

    if purchased:
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:13px;letter-spacing:0.08em;text-transform:uppercase;
             color:#A8A298;margin-bottom:0.6rem;">
            已買（{len(purchased)} 件）
        </div>
        """, unsafe_allow_html=True)
        for item in purchased:
            _render_item(item)


def _render_item(item):
    emoji = CATEGORY_EMOJI.get(item["category"], "🛍️")
    is_purchased = item["status"] == "purchased"
    name_style = "text-decoration:line-through;color:#A8A298;" if is_purchased else "color:#3C3830;"
    price_text = f"NT$ {int(item['estimated_price']):,}" if item["estimated_price"] else ""

    col_info, col_check, col_del = st.columns([6, 1, 1])
    with col_info:
        st.markdown(f"""
        <div style="padding:10px 0;">
            <div style="font-size:15px;font-weight:500;{name_style}">{emoji} {item['name']}</div>
            <div style="font-size:12px;color:#A8A298;margin-top:2px;">
                {item['category'] or '未分類'}{' ・ ' + price_text if price_text else ''}
                {' ・ ' + item['notes'] if item['notes'] else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_check:
        toggle_label = "↩" if is_purchased else "✓"
        toggle_key = f"toggle_{item['id']}"
        if st.button(toggle_label, key=toggle_key, use_container_width=True):
            new_status = "pending" if is_purchased else "purchased"
            db.update_wishlist_status(item["id"], new_status)
            st.rerun()
    with col_del:
        if st.button("✕", key=f"del_wish_{item['id']}", use_container_width=True):
            db.delete_wishlist_item(item["id"])
            st.rerun()
