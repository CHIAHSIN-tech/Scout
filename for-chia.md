# 給珈欣 — 行程候選＋確認狀態整合

嗨珈欣 👋 這次照 spec 把「候選項目＋出發前確認狀態」整套做進來了，順手也修了幾個
Supabase 遷移後遺留的崩潰。以下是你會在意的重點。

---

## 一句話
旅程項目現在可以「候選中（還沒決定哪天）」存在，並且有「必須確認/可以彈性 × 已確認/未確認」
兩軸狀態；Streamlit 和新的網頁版確認清單共用同一個 Supabase。

---

## ⚠️ 你只要做一件事：跑一次 schema

把 repo 根目錄的 **`supabase_schema.sql`** 整份貼到 Supabase SQL Editor 按 Run（用你那個專案）。
- 它是**冪等**的：你之前手建好的 `trips` / `itinerary_items` 不會被弄壞，只會：
  - 把 `day_number` / `start_time` 改成可 NULL（候選中要用）
  - 補上 `confirm_required` / `is_confirmed` 兩個欄位
  - **建出 `wishlist` 表**（見下方）
  - 加索引、把幾張表對 anon 開放（網頁版要用）

跑完 Streamlit 端和網頁版就都連得起來。

---

## 幾個你會在意的修正

1. **購物頁原本一進去就崩潰** 🐛
   Supabase 重構時 `db.py` 少了 `get_wishlist / add_wishlist_item / update_wishlist_status /
   delete_wishlist_item`，但 `page_shopping.py` 還在呼叫。我把這 4 個函式補回來（走 Supabase），
   schema 也建了 `wishlist` 表。你跑完 schema，購物頁就會動。

2. **重排、編輯儲存也會崩潰** 🐛
   `itinerary.py` 的 `apply_reorder` 和 `page_itinerary.py` 的編輯儲存還在呼叫已被移除的
   `db.get_conn()`（sqlite 時代的）。已全部改走 Supabase。

3. `requirements.txt` 少了 `supabase`，補上（不然雲端部署會掛）。

---

## 新的資料模型（你做新增/編輯/刪除畫面時會用到）

- **候選中** = `day_number IS NULL`（沒有日期/時段）。不會出現在 Day-based 時間軸。
- **確認狀態兩軸**：
  - `confirm_required`：必須確認(true) / 可以彈性(false)
  - `is_confirmed`：已確認(true) / 未確認(false)
- 「必須確認且未確認」= 優先儀表板要凸顯的「不能忘」清單。

已經幫你備好的 `db.py` 函式（直接用）：
`add_candidate`、`get_candidates`、`get_scheduled_items`、`get_unconfirmed_required`、
`schedule_item`、`unschedule_item`、`set_confirm_required`、`set_confirmed`。

---

## 想先看長相（不用設定）

- 網頁版確認清單：開 `scout-checklist/index.html?demo=1` → 範例模式，假資料、按鈕能動、不連網。
- Streamlit 端：旅程詳細頁多了「📋 候選 / 確認」分頁。

詳細的驗收步驟在 `HANDOFF_itinerary_confirm.md`。有問題隨時敲我們 🙌
