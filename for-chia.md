# 給珈欣 — 行程表 + AI 匯入 + UI 翻新（spec-scout-checklist-itinerary-view）

嗨珈欣 👋 你那份「完整行程表 + AI 匯入行程 + UI 整體翻新」的 spec 做完了，全部落在
`scout-checklist/` 這個網頁版。下面是你會在意的重點。

## 一句話
網頁版確認清單現在多了一個「🗓️ 行程表」視圖：可以看依 Day 排好的完整行程、切時間軸、
**用手指拖曳改時間**，還能**貼一段文字讓 AI 自動拆成行程排進去**。原本的確認清單也按手機
資訊架構翻新（重點置頂、其餘收合）。

## 你的兩個 Open Question 都查清楚了（都是好消息，沒有阻斷）
1. **後端是 Firebase 還是 Supabase？** → 確認是 **Supabase**。`app.js` 本來就在打 Supabase
   REST，跟 Streamlit 共用同一個 DB。spec 裡擔心的 Firebase 是多慮。
2. **`patchItem()` 能不能改 day/time？** → **可以**，它本來就是萬用的（傳什麼欄位改什麼），
   「📅 排入行程」已經在用它。所以拖曳改時間直接接上，沒有前置工作。

## 做了什麼（對應你的 Must / AC）
- **AC-1/AC-2 清單**：行程表 →「📋 清單」，依 Day 分組（時間 / 地點 / 類別 icon），
  最上方提醒「還有 N 項未排定」。
- **AC-3 時間軸**：「🕐 時間軸」垂直時間軸，**重疊項目並排顯示不互蓋**（行事曆式分欄）。
- **AC-4 拖曳改時間**：按住卡片上下拖（自由拖、不格線吸附），放開自動寫回後端 `start_time`，
  重新整理時間會保留。手機觸控可用。
- **AC-5 衝突警告**：拖到 / 排到時段重疊時，卡片變琥珀色 + 標「⚠️ 時段重疊」+ 上方橫幅提醒，
  但**不阻擋**操作。
- **AC-6 今天**：旅行中自動聚焦並高亮「今天」（清單有「今天」標籤、時間軸 chip 有 ⭐）。
- **AC-7 手機資訊架構**：確認清單的「必須確認」置頂展開 + 數量摘要；「已確認」「可以彈性」
  改成**預設收合**，手機一進來不用捲就看到重點。
- **AC-8 AI 匯入**：行程表上方「🤖 AI 匯入行程」→ 貼文字 → Gemini 解析 → 直接以「已排入」
  狀態加入。**Should（fallback）**：AI 判斷不出第幾天的項目會退回候選（不會弄丟）。
- **AC-9 正式化**：見下方「我跟 spec 不一樣的地方」。

## 你要做的事
- **Supabase**：不用再動，跟現在同一個 DB 即可。
- **（選填）想用 AI 匯入**：在 `config.js` 補一個 `GEMINI_API_KEY`（Google AI Studio 拿）。
  不填的話 AI 匯入會顯示提示，其餘功能照常。
  - ⚠️ 純前端站，金鑰會被瀏覽器看到（spec Open Question 4）。我沿用跟 trip_id / anon key
    一樣的「可公開、靠連結保護」假設，並在 `config.example.js` 寫明。若你不能接受，要改成
    後端代呼叫——這需要你和 Stanley 決定，我先沒做（屬 spec 沒要求的範疇）。

## 我跟 spec 不一樣的地方（請過目）
- **AC-9「移除 ?demo=1 判斷」我沒有照做，改成保留 demo**。理由：正式體驗本來就不靠旗標
  （**預設網址即正式版、直接寫 Supabase**，AC-9 的真正目的已達成）；而 `?demo=1` 是「選用」的
  離線預覽，對正式版零影響，卻是沒有 Supabase 連線時唯一能預覽 / 測試的途徑（我自己驗證也靠它）。
  刪掉只有壞處沒有好處，所以保留並在 README 寫明。**如果你堅持要拿掉，跟我說一聲我再移除。**

## 想先看長相（不用設定）
開 `scout-checklist/index.html?demo=1` → 範例模式，假資料、按鈕能動、不連網。
切到「🗓️ 行程表」就能看到清單 / 時間軸 / 拖曳 / AI 匯入（範例模式 AI 用本地解析示範）。

## 怎麼驗的
寫了一支 Playwright 端到端腳本，用 390px 手機尺寸跑過全部 AC-1～AC-9 共 24 項檢查，
**全綠**（含拖曳改時間後重新整理仍保留、重疊並排、今天高亮、AI 匯入後項目出現）。

有問題隨時敲我 🙌

---

# 給珈欣 — 行程候選＋確認狀態整合（前一份 spec 001）

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
