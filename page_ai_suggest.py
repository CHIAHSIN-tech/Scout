# page_ai_suggest.py
# AI 建議行程：多輪問答 → 生成建議 → 勾選加入時間軸

import streamlit as st
import json
import db
import itinerary

CATEGORIES = {
    "restaurant": "🍽️ 餐廳",
    "hotel":      "🏨 住宿",
    "attraction": "🏛️ 景點",
    "shopping":   "🛍️ 購物",
    "transport":  "🚆 交通",
    "other":      "📌 其他",
}

# ── 問題清單（依序問）──
QUESTIONS = [
    {"key": "destination", "label": "你們打算去哪裡旅行？",
     "placeholder": "例：沖繩、京都、首爾"},
    {"key": "days",        "label": "預計幾天幾夜？",
     "placeholder": "例：3 天 2 夜"},
    {"key": "people",      "label": "幾個人一起去？有哪些成員？",
     "placeholder": "例：2 大人 1 小孩、情侶、家庭"},
    {"key": "preference",  "label": "旅遊偏好是什麼？",
     "type": "multiselect",
     "options": ["🍜 在地美食", "🏛️ 歷史景點", "🌿 自然風景", "🛍️ 購物",
                 "♨️ 溫泉 / 泡湯", "🎌 文化體驗", "🎡 主題樂園",
                 "🍺 酒吧 / 夜生活", "☕ 咖啡廳巡禮", "🏖️ 海灘 / 戶外活動"]},
    {"key": "budget",      "label": "每人每天大約的預算是多少？",
     "placeholder": "例：3000 台幣、不限制"},
    {"key": "extra",       "label": "還有什麼特別需求或想避開的？（可跳過）",
     "placeholder": "例：不喜歡太多步行、需要親子友善、素食"},
]


def _build_suggestion_prompt(answers):
    """根據使用者的回答組合 prompt"""
    return f"""你是一位專業的旅遊規劃師。請根據以下資訊，為使用者規劃一份詳細的旅遊行程建議。

旅遊資訊：
- 目的地：{answers.get('destination', '未提供')}
- 天數：{answers.get('days', '未提供')}
- 成員：{answers.get('people', '未提供')}
- 偏好：{answers.get('preference', '未提供')}
- 預算：{answers.get('budget', '未提供')}
- 特殊需求：{answers.get('extra', '無')}

請回傳一個 JSON 陣列，每個元素代表一個行程項目，格式如下：
[
  {{
    "day": 1,
    "name": "景點或餐廳名稱",
    "category": "attraction 或 restaurant 或 shopping 或 hotel 或 transport 或 other",
    "start_time": "HH:MM",
    "duration_minutes": 90,
    "location": "所在區域或地址",
    "notes": "簡短說明或推薦原因"
  }}
]

規則：
1. 根據天數安排每天的行程，早上約 09:00 開始，合理分配時間
2. 景點大約 90-120 分鐘，餐廳 60-90 分鐘，購物 60-90 分鐘
3. 每天安排 4-6 個項目，包含早餐、午餐、晚餐和景點
4. 行程之間預留合理的移動時間
5. 只回傳 JSON 陣列，不要任何說明文字或 markdown"""


def _call_ai(prompt: str):
    """呼叫 AI，回傳建議行程清單或錯誤"""
    from ai import ai_generate
    from google.genai import types

    try:
        resp = ai_generate(
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )
        raw = resp.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        if not isinstance(result, list):
            return {"error": "AI 回傳格式不正確，請再試一次"}
        return result

    except json.JSONDecodeError:
        return {"error": "AI 回傳的格式無法解析，請再試一次"}
    except Exception as e:
        return {"error": f"AI 呼叫失敗：{str(e)}"}


def page_ai_suggest(trip_id: int):
    """AI 建議行程的主頁面，嵌入在行程詳細頁的 tab 內"""

    prefix = f"ai_suggest_{trip_id}"

    if f"{prefix}_q" not in st.session_state:
        st.session_state[f"{prefix}_q"] = 0
        st.session_state[f"{prefix}_answers"] = {}
        st.session_state[f"{prefix}_suggestions"] = None

    current_q = st.session_state[f"{prefix}_q"]
    answers = st.session_state[f"{prefix}_answers"]
    suggestions = st.session_state[f"{prefix}_suggestions"]

    # ════════════════════
    #  階段一：多輪問答
    # ════════════════════
    if suggestions is None:

        # 顯示已回答的問題
        for i in range(current_q):
            q = QUESTIONS[i]
            st.markdown(
                f'<div style="margin-bottom:0.3rem;">'
                f'<span style="font-size:13px;color:#A8A298;">{q["label"]}</span><br>'
                f'<span style="font-size:15px;color:#3C3830;font-weight:500;">'
                f'{answers.get(q["key"], "")}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        if current_q > 0:
            st.markdown('<hr style="margin:0.8rem 0">', unsafe_allow_html=True)

        # 顯示目前的問題
        if current_q < len(QUESTIONS):
            q = QUESTIONS[current_q]
            st.markdown(
                f'<div style="font-size:16px;font-weight:600;color:#3C3830;'
                f'margin-bottom:0.6rem;">{q["label"]}</div>',
                unsafe_allow_html=True
            )

            is_last = current_q == len(QUESTIONS) - 1
            q_type = q.get("type", "text")

            # 根據題型渲染不同的輸入元件
            if q_type == "multiselect":
                selected_opts = st.multiselect(
                    q["label"],
                    options=q.get("options", []),
                    label_visibility="collapsed",
                    key=f"{prefix}_input_{current_q}"
                )
                answer = "、".join(selected_opts) if selected_opts else ""
            else:
                answer = st.text_input(
                    q["label"],
                    placeholder=q.get("placeholder", ""),
                    label_visibility="collapsed",
                    key=f"{prefix}_input_{current_q}"
                )

            if is_last:
                col_next, col_skip = st.columns([3, 1])
            else:
                col_next = st.columns([1])[0]
                col_skip = None

            with col_next:
                btn_label = "開始生成行程 ✨" if is_last else "下一題 →"
                if st.button(btn_label, use_container_width=True,
                             key=f"{prefix}_next_{current_q}"):
                    if not answer.strip() and not is_last:
                        st.warning("請選擇或輸入回答後再繼續")
                    else:
                        answers[q["key"]] = answer.strip()
                        st.session_state[f"{prefix}_answers"] = answers

                        if is_last:
                            with st.spinner("AI 正在規劃你的行程，請稍候…"):
                                prompt = _build_suggestion_prompt(answers)
                                result = _call_ai(prompt)
                            if isinstance(result, dict) and "error" in result:
                                st.error(f"❌ {result['error']}")
                            else:
                                st.session_state[f"{prefix}_suggestions"] = result
                                st.rerun()
                        else:
                            st.session_state[f"{prefix}_q"] = current_q + 1
                            st.rerun()

            if is_last and col_skip is not None:
                with col_skip:
                    if st.button("跳過", use_container_width=True,
                                 key=f"{prefix}_skip_{current_q}"):
                        answers[q["key"]] = ""
                        st.session_state[f"{prefix}_answers"] = answers
                        with st.spinner("AI 正在規劃你的行程，請稍候…"):
                            prompt = _build_suggestion_prompt(answers)
                            result = _call_ai(prompt)
                        if isinstance(result, dict) and "error" in result:
                            st.error(f"❌ {result['error']}")
                        else:
                            st.session_state[f"{prefix}_suggestions"] = result
                            st.rerun()

        # 重新開始按鈕
        if current_q > 0:
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
            if st.button("↩ 重新開始", key=f"{prefix}_restart",
                         use_container_width=True):
                st.session_state[f"{prefix}_q"] = 0
                st.session_state[f"{prefix}_answers"] = {}
                st.session_state[f"{prefix}_suggestions"] = None
                st.rerun()

    # ════════════════════
    #  階段二：勾選並加入
    # ════════════════════
    else:
        destination = answers.get("destination", "行程")
        st.markdown(
            f'<div style="font-size:16px;font-weight:600;margin-bottom:0.8rem;">'
            f'✨ {destination} 建議行程</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="font-size:13px;color:#A8A298;margin-bottom:1rem;">'
            '勾選想加入的項目，再點「加入行程」</div>',
            unsafe_allow_html=True
        )

        # 依天分組顯示
        days_dict = {}
        for idx, item in enumerate(suggestions):
            day = item.get("day", 1)
            days_dict.setdefault(day, []).append((idx, item))

        selected_indices = st.session_state.get(f"{prefix}_selected", set())

        for day_num in sorted(days_dict.keys()):
            st.markdown(
                f'<div style="font-size:14px;font-weight:600;color:#3D6B54;'
                f'margin:0.8rem 0 0.4rem;">Day {day_num}</div>',
                unsafe_allow_html=True
            )
            for idx, item in days_dict[day_num]:
                cat_label = CATEGORIES.get(item.get("category", "other"), "📌 其他")
                checked = st.checkbox(
                    f"**{item['start_time']}**　{item['name']}　"
                    f"_{cat_label}・{item.get('duration_minutes', 60)} 分_",
                    value=(idx in selected_indices),
                    key=f"{prefix}_chk_{idx}"
                )
                if checked:
                    selected_indices.add(idx)
                else:
                    selected_indices.discard(idx)

                if item.get("notes"):
                    st.markdown(
                        f'<div style="font-size:12px;color:#A8A298;'
                        f'margin:-0.5rem 0 0.5rem 1.6rem;">{item["notes"]}</div>',
                        unsafe_allow_html=True
                    )

        st.session_state[f"{prefix}_selected"] = selected_indices

        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

        col_all, col_none = st.columns(2)
        with col_all:
            if st.button("全選", use_container_width=True, key=f"{prefix}_all"):
                st.session_state[f"{prefix}_selected"] = set(range(len(suggestions)))
                st.rerun()
        with col_none:
            if st.button("取消全選", use_container_width=True, key=f"{prefix}_none"):
                st.session_state[f"{prefix}_selected"] = set()
                st.rerun()

        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

        col_add, col_restart = st.columns([3, 1])
        with col_add:
            if st.button("＋ 加入行程", use_container_width=True,
                         key=f"{prefix}_add"):
                if not selected_indices:
                    st.warning("請至少勾選一個項目")
                else:
                    count = 0
                    for idx in sorted(selected_indices):
                        item = suggestions[idx]
                        start_time = item.get("start_time", "09:00")
                        if not itinerary.is_valid_time(start_time):
                            start_time = "09:00"
                        db.add_item(
                            trip_id=trip_id,
                            day_number=item.get("day", 1),
                            name=item.get("name", "未命名"),
                            start_time=start_time,
                            duration_minutes=item.get("duration_minutes", 60),
                            category=item.get("category", "other"),
                            location=item.get("location", ""),
                            notes=item.get("notes", ""),
                        )
                        count += 1

                    st.success(f"已加入 {count} 個行程項目！")
                    for key in [f"{prefix}_q", f"{prefix}_answers",
                                f"{prefix}_suggestions", f"{prefix}_selected"]:
                        st.session_state.pop(key, None)
                    st.rerun()

        with col_restart:
            if st.button("重來", use_container_width=True, key=f"{prefix}_restart2"):
                for key in [f"{prefix}_q", f"{prefix}_answers",
                            f"{prefix}_suggestions", f"{prefix}_selected"]:
                    st.session_state.pop(key, None)
                st.rerun()