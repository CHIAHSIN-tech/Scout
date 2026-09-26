# Changelog

人類可讀的版本日誌（機器可讀版本是 git commit log）。重要的、協作者該知道的變動寫這裡；
typo / 純機械調整不必寫。最新在上。詳細「為什麼」在 `context.md` §4 ADR；這裡只記「動了什麼」。

## [Unreleased]

### 2026-09-13 — 旅程頁：開放街區不再被問營業時間、補回「回旅館」那一段

- **schema 新增 `kind: "area"`**（開放街區、公園、河濱這種沒有門的地點）。
  標成 area 的地點不自動發問、頁面不印「營業時間尚未查證」、排程也不檢查它的營業時間。
  首爾那趟待確認從 **19 筆降到 11 筆**，剩下的都是真的有門的地方。
- **首爾行程補上 D2／D3 的收尾**（21:30、21:40 回 Oriens）。
  頁面現在看得到「這天幾點回到旅館」，夜間動線檢查也拿得到最後一站。
- 以上兩項對應 `REVIEW.md` 首跑標成 `WRONG` 的第 12、14、25 條，現在都是 `OK`。

### 2026-09-12 — 旅程頁模組 ＋ 託管遷移至 Cloudflare Workers

- **🗺️ 旅程頁模組**：每趟旅程一份本機 `trip.json`（`context.md` ADR-019），
  MCP 新增十個工具（`create_trip_file` / `upsert_place` / `upsert_event` / `upsert_leg` /
  `upsert_open_question` / `set_trip_section` / `read_trip` / `list_trip_files` /
  `check_schedule` / `build_trip_page`）。**既有 8 個工具一字未改。**
  - `build_trip_page` 產出**自含單檔 HTML**：沒有外部 script／樣式表／字體／圖片，
    沒有 fetch，斷網打得開、可以存到手機。CSS 與示意地圖移植自
    2026/9 首爾行程 artifact 的原始檔。
  - **改一處，多處一起改**：時間軸、日標題摘要、快捷 nav、地圖文字轉乘表、正餐一覽表
    五個區塊全部由 `events` 算出來。同樣輸入建兩次位元相同。
  - `check_schedule` **只回報不修改**，五類衝突各附「要解掉它得犧牲什麼」的選項。
  - 查不到的營業時間不會變成頁面上的數字；來源打架時兩個都印、不挑一個當正確答案，
    兩種情況都自動變成一筆待確認。
  - 行程 Tab 底部新增「歷次行程表」列表（`web/trip-pages.js`），不碰 Supabase、
    不依賴 `config.js`。
- **☁️ 託管改 Cloudflare Workers（Static Assets）**（ADR-018，取代 ADR-011）。
  四支 Netlify Function 合併成一支 Worker，行為與錯誤訊息逐字等價；
  前端路徑 `/.netlify/functions/*` → `/api/*`，舊網址留一行 308 相容轉址。
  保活排程改用 `[triggers] crons`，cron 值不變。
  **選 Workers 不選 Pages 是因為 Pages 不支援 Cron Trigger。**
  ⚠️ 本次**只寫設定檔，沒有部署**；Cloudflare 後台的步驟與網址變更的影響
  寫在 `for-chia-cloudflare.md`。
- **🔑 基礎設施權限收回 Stanley**（ADR-020，取代 ADR-014）。當初把 repo 轉給 Chia 的理由
  是「她的 Netlify 接著她的 GitHub」，託管搬到 Cloudflare 之後那個理由就沒了；
  而實際分工一直是「Chia 出 spec、Stanley 執行」。
  GitHub repo、Cloudflare、行程 Supabase 都歸 Stanley，Chia 保留 repo 寫入權。
  ⚠️ **代價要講清楚：她失去部署自主權**，那正是 ADR-014 想給她的。
  文件拆成兩份：`for-chia-handover.md`（只剩三件只有她做得到的事）
  與 `runbook-cloudflare.md`（Stanley 自己做的部分）。
- ⚠️ **`trips/` 與 `web/trips/` 暫時不進版控**：repo 是公開的，而 `trip.json` 含訂位編號、
  旅館地址、班機時刻。代價是行程表目前不會跟著網站部署。見 `DECISIONS-trip-page.md`。

### 2026-08-01 — 架構收斂：Streamlit 退役、三個 app 併成一個

- **決定把 buylist ＋ scout-checklist 合併成單一雙 Tab 靜態 app**，Streamlit 退役（`context.md` ADR-010）。
  執行 SSOT：`specs/spec-scout-app-merge.md` v2。Appetite：一個週末。
- 解除 v1 的 blocker：取得 checklist 現行原碼，發現它是**三檔結構 + 部署在 Netlify + 已有 Function proxy**，
  與 v1 假設不符，spec 據此改寫並補上實測的命名衝突清單。
- 合併會連帶補上**最小旅程管理**（建立／切換旅程、手動新增項目）——這是 Streamlit 退役的前置條件，
  因為目前只有 Streamlit 能開新旅程。
- `context.md` 補回空窗四個月的架構變化：新增 ADR-007～013，ADR-003／004 標記為 superseded。

### 2026-07 — 購物模組（buylist）

- **買物清單**：新增／刪除、價格、迫切度、取得難易、月預算與爆預算提示、「想買 N 天」冷卻期、
  2×2 決策矩陣、誰加的、備註。**Supabase Realtime 兩人即時同步**。
- **進階**：分類、狀態／分類篩選、價格／想最久排序、月初自動清上月已買、後續成本欄位、連結欄位。
- **後續批次**：已買星號收藏、全站改用 Scout CIS 米色配色、已買沉底、數量欄位、
  一次貼多行批次新增、情境標籤 ＋ 依標籤篩選、一鍵匯出 Markdown、已買填實付金額與差額。
- **🌶️ 辣醬庫**：作為 buylist 的第二個 tab（`sauces` 表），4 項星級評分、關鍵字搜尋、依回購度排序。
- **🔗 貼連結帶入**：貼商品連結 → Gemini 讀網頁抽出名稱與價格填入表單（不自動送出）。
  ⚠️ 公開站目前隱藏此功能（金鑰不放前端），合併後改走 Netlify Function proxy 復活。
- **上線**：https://shoppingtool.netlify.app/ ⚠️ 目前仍是舊版（沒有辣醬庫 tab），手動部署造成的漂移。

### 2026-06/07 — 行程確認清單（scout-checklist）網頁版

- **兩軸儀表板**：必須確認／可以彈性 × 已確認／未確認，最上面是「必須確認且未確認」。
- **行程表 / 時間軸**：Day 分組、拖曳改時間、手機收合。
- **排程**：候選卡片「📅 排入行程」（選天＋時間）、已排定「↩ 退回候選」。
- **✨ AI 匯入行程**：貼一段文字（部落格／訊息／備忘錄）→ Gemini 解析出景點／時間／分類並排入。
  金鑰走 **Netlify Function**（`ai-parse.js`），前端完全不接觸。
- 資料層從 Firebase 改寫為 Supabase，與 Streamlit 共用同一份 `itinerary_items`。
- 身分機制：網址帶 `?trip=<trip_id>`，不做帳號系統。

### 2026-06 — 資料層遷移

- **SQLite → Supabase（PostgreSQL）**。`db.py` 改用 `supabase.create_client`。
  schema SSOT：`supabase_schema.sql`（冪等，可安全重跑）。
- `itinerary_items` 新增 `confirm_required` / `is_confirmed` 兩軸欄位；
  `day_number` / `start_time` 改為可 NULL（NULL = 候選中）。
- 避開 PostgreSQL 保留字：`trips.user` → `trips.username`。
- 根目錄 `scout.db` 自此成為死檔案。

### 2026-04 — Streamlit app（⚠️ 已決定退役）

- 行程規劃模組：旅程 CRUD、時間軸（單日／全覽）、手動新增項目、卡片展開編輯（含跨天移動）、
  上下移自動重算時間、AI 建議（多輪問答 → Gemini 生成 JSON 行程 → 勾選加入）。
- 購物模組：待買清單（`wishlist`）—— 已被 buylist 完全取代。
- 基本框架：下拉選使用者登入、路由、全域 CSS（Noto Sans TC、手機優先）。

> 這套從未部署。合併完成後只有這些功能沒有替代品：**AI 生成行程**（多輪問答）、
> 行程項目的欄位編輯／排序／跨天移動、旅程刪除。程式碼保留可跑，需要時本機起一次。
