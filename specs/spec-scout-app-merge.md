# Spec — 合併 BuyList ＋ Scout 確認清單為單一雙 Tab App

> **用途**：交給 Stanley（Claude Code）執行的 SSOT。
> **需求來源**：Chia，2026-07-25——「整理成一個，分兩個 Tab，看怎麼連線」，並確認：不要 demo 模式，直接是能用的正式版。
> **狀態**：**v2 — blocker 已解除、可動工**。

---

## 0. Meta
- **Appetite（時間預算）**：**一個週末（2–3 天）**（Stanley，2026-08-01 拍板）。
- **Status**：done（2026-08-01 落地，commit `0d3a00a`；最小旅程管理 `efa0878` 補完前置條件）
- **Date**：v1 2026-07-25（Chia）／**v2 2026-08-01（Stanley，補實原碼調查 + 擴大範圍）**

### 0.1 v2 相對 v1 的變更（為什麼改）

v1 是在**沒有 checklist 現行原碼**的情況下寫的，§0.1 列為 BLOCKED。2026-08-01 已取得原碼（`witsper-stanley/scout-checklist`，private，最後 push 2026-07-26），跑完 v1 §5 要求的步驟 1–3，結果**推翻了 v1 的數項假設**：

| v1 假設 | 實際 | 影響 |
|---|---|---|
| checklist 是單檔 app | **三檔**：`index.html`(2 KB) + `app.js`(33 KB) + `styles.css`(13 KB) + gitignored `config.js` | 合併後的檔案結構改採多檔（見 §5.2），不再是「單檔塞單檔」 |
| 部署在 GitHub Pages | **部署在 Netlify**（有 `netlify.toml`） | v1 §10 R3「部署位置未定」直接消失：兩邊都已在 Netlify |
| 前端直接呼叫 Gemini | **已有 Netlify Function** `netlify/functions/ai-parse.js`，金鑰在 Netlify 環境變數 | 金鑰外露問題 checklist 已解；buylist 可照抄（見 §6.3） |
| 用 supabase-js | **完全沒用**，直接 `fetch` 打 PostgREST，無 Realtime（手動「↻ 重新整理」） | v1 §5.1-4「雙 supabase client」不成立，零衝突 |
| CSS 配色可能整套衝突（R2 待決） | 兩邊本來就都是 Scout CIS 米色系，**只有 3 個變數真衝突** | R2 收掉，不需要「配色統一」工程 |

**v2 新增的範圍**（Stanley，2026-08-01）：

1. **Streamlit 退役** —— 見 §4.2。連帶必須補最小旅程管理（§6.2），否則沒有任何地方能開新旅程。
2. **buylist 的 AI 貼連結帶入在公開站復活**（§6.3），沿用 checklist 已驗證的 Function proxy 模式。

**v1 已定、v2 不動的**：§4 三條關鍵決策（不合併資料庫、拿掉 demo、只動介面層）維持原判。

---

## 1. Problem Statement

購物清單（buylist）與行程確認清單（scout-checklist）是兩個分開的網頁 app，各自一個網址、各自一個 Netlify 站。同時 Scout 主 app（Streamlit）還是第三套東西，功能與 checklist 重疊、且從未部署。想整理成**一個網址、頂部兩個 Tab**，一次看兩件事。

**這次是純介面整併（Stanley 2026-08-01 拍板的「A. 介面」）** —— 不做跨模組資料打通。

## 2. Primary User + JTBD
- **User**：Chia / Stanley，手機與桌面瀏覽器都要能開。
- **JTBD**：當我要規劃行程或管理待買清單時，我想要在同一個網址切換兩個 Tab，這樣不用記兩個網址、兩個書籤。

## 3. Success Criteria
- 一個網址、頂部兩個 Tab（購物／行程），各自完整運作，功能不因合併而減損。
- 各自連各自原本的後端，資料**不合併**。
- 拿掉 `?demo=1` 範例模式。
- 手機瀏覽器打開可用（至少不破版）。
- **合併後 Streamlit 不再是任何功能的唯一入口**（可安全凍結）。

## 4. 關鍵決策（寫死，勿重新討論）

### 4.1 v1 既有（Chia 已確認）
- **不合併資料庫**。購物繼續連 Stanley 的 Supabase（`kdmmjlaajqxjmiahfvos`）；行程繼續連 Chia 的 Supabase（`uarkccyqcqvgxukjcrey`）。理由：兩者無共用資料表、無跨表查詢；Stanley 對 Chia 的專案沒後台權限；合併只有遷移成本、沒有功能收益。未來若真有「這趟行程要買的東西」需求，用**情境標籤**（`tag` 欄位，已實作）表達，不合併資料庫。
- **拿掉 demo 模式**。移除 `app.js` 的 `?demo=1` 分支與假資料，一律接真實 Supabase。
- **合併只動介面層**：一個外殼＋兩個 Tab，各自的 JS/CSS 作用域隔離，不重寫兩邊既有業務邏輯。

### 4.2 v2 新增（Stanley 2026-08-01 拍板）
- **導覽形態＝頂部雙 Tab**，不做首頁卡片選單。理由：兩邊各自內部已有 tab（buylist：買物清單／辣醬庫；checklist：確認清單／行程表／時間軸），外面再包首頁會變三層導覽，而最外層只有兩個選項，在手機上是純負擔。
- **Streamlit 退役**。`app.py` 及其相依（`page_itinerary.py` / `page_ai_suggest.py` / `page_shopping.py` / `itinerary.py` / `db.py` / `ai.py`）停止開發。**不刪檔**（本週末只標作廢），但合併版做完後它不再是任何功能的唯一入口。
  - 資料零風險：Streamlit 早已從 SQLite 遷到 Supabase（`db.py` 用 `create_client`），與 checklist 共用同一個資料庫、同一張 `itinerary_items`。根目錄 `scout.db` 是遷移後的死檔案（20 KB，最後寫入 2026-04-04）。
- **合併後的落點＝Scout repo 的 `web/` 資料夾**。理由：Scout 是 private、buylist 的落點決策（`BUYLIST_STATE.md` §4）本來就是「不開新 repo」；把 checklist 併進來後 `witsper-stanley/scout-checklist` repo 可退役，從三個 repo 收斂成一個。
- **部署＝Netlify 接 Git 自動部署**（base directory `web/`），取代 buylist 現行的手動 drag-and-drop。理由：手動部署已經造成過版本漂移（`BUYLIST_STATE.md` §6.3 記著「公開站目前是舊版、沒有辣醬 tab」）。

## 5. Scope & Interfaces

### 5.1 兩邊的實際技術現況（2026-08-01 實測）

| | **buylist** | **checklist** |
|---|---|---|
| 檔案 | 單檔 `buylist/index.html`，584 行 / 42 KB，HTML+CSS+JS 全內聯 | `index.html`(骨架) + `app.js`(33 KB) + `styles.css`(13 KB) + gitignored `config.js` |
| JS 封裝 | 已包 IIFE `"use strict"` | **未包**，滿地 top-level（`app`/`curTrip`/`curItems`/`currentView`/`TRIP_CTX`…） |
| Supabase | supabase-js（CDN jsdelivr）+ **Realtime** `postgres_changes` | **不載 supabase-js**，直接 `fetch` 打 PostgREST；**無 Realtime**，手動「↻ 重新整理」 |
| 專案 | `kdmmjlaajqxjmiahfvos`（Stanley 的），key 寫死在 index.html | `uarkccyqcqvgxukjcrey`（Chia 的），key 寫死在 `app.js`，`window.SCOUT_CONFIG` 可覆蓋 |
| 身分 | 無，`localStorage.buylist_me` 只記「誰加的」 | **`?trip=<trip_id>` 即存取憑證** |
| AI | Gemini 直呼前端，金鑰在 gitignored `config.js`；**公開站偵測無金鑰→隱藏功能** | **Netlify Function proxy** `/.netlify/functions/ai-parse`，金鑰在 Netlify 環境變數 |
| DOM helper | 全域 `$(id)`、`setStatus()` | `document.getElementById` 直用 |

### 5.2 衝突清單（v1 §5 步驟 1–3 的產出）

> **⚠️ v2.1 更正（2026-08-01，實作時發現）**：本節初版只比對了 CSS **變數**，漏了 CSS **class 名稱**——
> 那才是大宗。兩邊都用 `.card`、`.status`、`.empty`、`.title` 這些通用 class，而且樣式**完全不同**
> （buylist 的 `.card` 是 18px 圓角＋陰影的白盒，checklist 的 `.card` 是 14px 圓角、無陰影的項目卡）。
> 逐個改名要動幾十處、容易漏。**改用作用域前綴一次解決**，見下表。

| 類型 | 衝突 | 實際處理 |
|---|---|---|
| **CSS class** | 大量：`.card`、`.status`、`.empty`、`.title`、`.hidden` 等通用名，兩邊樣式不同 | **不改名**。把兩邊每一條選擇器都加上作用域前綴：buylist 全部 `#panel-shop …`、checklist 全部 `#panel-trip …`。機械轉換（腳本產生），零手抄風險。 |
| **CSS 變數** | `--green`（`#5C8C72` / `#3D6B54`）、`--amber`、`--muted` 三個同名不同值 | 一併被上一列解決：原本的 `:root{…}` 改成 `#panel-shop{…}` / `#panel-trip{…}`。**CSS 變數會往下繼承**，等於自動作用域化，不需改名。已實測：同一個 `--green` 在兩個 panel 下解析出各自的值，`:root` 上則不存在。 |
| **JS 全域** | checklist 全部 top-level（`app`/`curTrip`/`curItems`/`currentView`/`TRIP_CTX`…），會污染 | **checklist 整包塞進 IIFE**。一包解決，含下一列。 |
| **`sb`** | 撞名、語意不同（checklist 是 REST fetch **函式**；buylist 是 supabase-js **client 物件**） | 被上一列的 IIFE 自動隔離，**不需改名**。 |
| **DOM id** | 實際只有 **`status` 一個**真撞。（`app` vs `appTitle`、`view` vs `view-list`／`view-matrix` 都是不同字串，不算撞。） | **buylist** 側改名：`status`→`bl-status`、`statusText`→`bl-statusText`（buylist 已大量用 `bl-` 前綴，改動最小）。checklist 側 id 全部維持原樣，`app.js` 一行不用改。 |
| **Supabase client** | 無 | checklist 不載 supabase-js，零衝突。 |
| **config** | `window.BUYLIST_CONFIG` vs `window.SCOUT_CONFIG` | 名稱不撞。第一天先原樣並存（不動已驗證的邏輯），第二天再收斂成單一 `window.SCOUT_APP_CONFIG`（§6.4）。 |

**外殼自己的樣式變數**用 `--sh-` 前綴（`shell.css`）。理由：兩個 panel 各自定義了同名的 `--bg`／`--card`／`--green`，外殼若跟著用同一批名字會被繼承關係搞混。

### 5.3 合併後的檔案結構（`web/`）

```
web/
├── index.html            # 外殼：<head> + 頂部 Tab bar + 兩個 panel 容器
├── shell.js              # Tab 切換 + localStorage 記住上次選的 Tab
├── shell.css             # 外殼樣式 + 統一的 :root CSS 變數
├── buylist.js            # 從 buylist/index.html 的 <script> 原樣搬出（已是 IIFE）
├── buylist.css           # 從 buylist/index.html 的 <style> 原樣搬出
├── checklist.js          # 從 scout-checklist/app.js 搬來，整包包 IIFE、id 加 ck- 前綴、移除 demo 分支
├── checklist.css         # 從 scout-checklist/styles.css 搬來，3 個衝突變數改名
├── config.js.example     # 雙金鑰範本（config.js 已在 .gitignore）
└── netlify/functions/
    ├── ai-parse.js       # 現成，行程 AI 匯入（原樣搬）
    └── ai-product.js     # 新增，buylist 貼連結帶入（§6.3）
```

> **為什麼拆檔而不是全部內聯**：checklist 本來就是多檔；buylist 的 CSS/JS 從 `<style>`/`<script>` 剪下貼到獨立檔是純搬移、不是重寫。合併後 `index.html` 保持可讀，也避免一個 60 KB 的巨檔。

### 5.4 明確 out of scope（本週末不做）
- 不重寫任一邊既有業務邏輯／UI／資料模型。
- 不合併 Supabase 專案。
- 不做 PWA／離線。
- 不做手機介面像素級優化（另一份 spec）。
- **不救 Streamlit 的「AI 生成行程」（多輪問答 → Gemini 產出整份行程）** —— 週末預算裝不下，見 §10 R2。
- 不刪 Streamlit 程式碼（只標作廢）。
- 不做旅程刪除、行程項目的欄位編輯／排序／跨天移動（Streamlit 有、合併版不補，見 §10 R2）。

## 6. 功能範圍

### 6.1 原樣搬移
- **購物 Tab**：買物清單（新增／篩選／排序／已買沉底／星號／數量／情境標籤／實付金額／匯出 md／月預算爆表提示／2×2 矩陣）＋ 辣醬庫。Realtime 同步保留。
- **行程 Tab**：確認清單兩軸儀表板（必須確認／可以彈性 × 已確認／未確認）＋ 行程表（Day 分組）＋ 時間軸（拖曳改時間）＋ AI 匯入行程 ＋ 排入行程／退回候選。

### 6.2 新增：最小旅程管理（因 Streamlit 退役而必須補）

`?trip=<trip_id>` 目前是 checklist 唯一的身分機制，而 `trip_id` 只能從 Streamlit 建立旅程後取得。Streamlit 一退役就沒人能開新旅程，故必須補：

1. **旅程選擇器**：行程 Tab 頂部一個 `<select>`，列出 `trips`（`GET /rest/v1/trips?select=*&order=start_date.desc`）。選定後存 `localStorage.scout_trip_id`。
2. **建立旅程**：一個小表單（名稱、開始日、結束日）→ `POST /rest/v1/trips`。建立後自動選中。
3. **手動新增行程項目**：名稱、分類、第幾天（可留空＝候選）、時間（可留空）→ 沿用 `app.js` 現成的 `addItem()`（原本只給 AI 匯入用）。
4. **`?trip=` 相容**：網址帶 `?trip=N` 時**優先於** localStorage（維持既有分享連結不失效），並同步寫回 localStorage。

> 刻意不做：刪除旅程、編輯既有項目欄位、排序／跨天移動。這些留在凍結的 Streamlit 裡，真的需要時再開 spec。

### 6.3 新增：buylist 的 AI 貼連結帶入在公開站復活

現況：buylist 的 Gemini 金鑰在前端 `config.js`，公開部署時故意留空 → 偵測到無金鑰就隱藏「🔗貼連結帶入」（commit `5f49665`）。checklist 已用 Netlify Function 解掉同一題。

做法：照抄 `ai-parse.js` 寫一支 `ai-product.js`（輸入商品 URL，用 Gemini + `url_context` 抽名稱與價格，回傳原始文字），前端改打 `/.netlify/functions/ai-product`，前端不再碰金鑰、也不再需要隱藏按鈕。共用 Netlify 環境變數 `GEMINI_API_KEY`。

### 6.4 config 收斂

合併成單一 gitignored `web/config.js`：

```js
window.SCOUT_APP_CONFIG = {
  // 兩個 Supabase 都寫死在各自的 js 裡（publishable key，設計上即公開），
  // 這裡只保留需要覆蓋時的 override 用途。
  BUYLIST_SUPABASE_URL: "",
  BUYLIST_SUPABASE_ANON_KEY: "",
  CHECKLIST_SUPABASE_URL: "",
  CHECKLIST_SUPABASE_ANON_KEY: "",
};
```

Gemini 金鑰**不再進前端 config**（兩邊都走 Function + Netlify 環境變數）。`config.js.example` 一併更新。

### 6.5 新增：Supabase 保活排程（因 R6 而加，2026-08-01）

**問題**：免費方案閒置 7 天自動暫停。購物專案天天用、不會暫停；行程專案是季節性使用，已暫停過兩次，每次都要人工 un-pause。

**做法**：加一支 Netlify Scheduled Function `netlify/functions/keepalive.js`，每天打一次兩個 Supabase 的最輕量查詢（`select id limit 1`），用 API 活動把閒置計時器歸零。

- 排在同一支 function 裡打兩個專案，購物側順便保險（未來若冷卻也不會中招）。
- 用 `HEAD` 或 `select=id&limit=1`，回應體積接近零，不佔用量。
- 失敗不影響網站（排程 function 與前端無關），但要能從 Netlify function log 看出來。
- 金鑰用兩邊的 publishable anon key，本來就是公開的，放環境變數即可。

**驗證方式**：部署後隔 10 天再開行程 Tab，若不需要 un-pause 就算成功。**在確認有效之前不要拆掉手動 un-pause 這條退路。**

⚠️ **不確定性**：Supabase 判定「活動」的實際規則沒有公開到逐條保證的程度，一般理解是 API 請求即算活動。若實測十天後仍被暫停，退而求其次的選項：(a) 升級 Pro（$25/月，無自動暫停）；(b) 把行程資料併進購物那個天天有人用的專案——但那要推翻 ADR-012，且需 Chia 同意。

## 7. Acceptance Criteria（初始全 failing）

- [ ] **AC-1**：開合併後的網址 → 頂部 Tab bar（🛒購物／🗺️行程），預設落在購物 Tab。
- [ ] **AC-2**：行程 Tab → 確認清單、行程表、時間軸、AI 匯入全部正常，接 Chia 的 Supabase，資料與獨立版一致。
- [ ] **AC-3**：購物 Tab → buylist 全部功能（含辣醬庫）正常，接 Stanley 的 Supabase，Realtime 即時同步仍在。
- [ ] **AC-4**：網址帶不帶 `?demo=1` 都一樣是正式資料，程式碼裡沒有任何假資料路徑。
- [ ] **AC-5**：兩個 Tab 樣式互不污染（在購物 Tab 操作不會改到行程 Tab 的顏色／字級，反之亦然）。
- [ ] **AC-6**：購物 Tab 新增一筆不會被行程 Tab 的邏輯或狀態列覆蓋或報錯，反之亦然。
- [ ] **AC-7**：手機瀏覽器（或桌面模擬 375px）打開 → Tab bar 可點、兩個 Tab 都不破版、不橫捲。
- [ ] **AC-8**：重整頁面 → 停留在上次選的 Tab。
- [ ] **AC-9**（新）：行程 Tab 可建立一趟新旅程（名稱＋起訖日），建立後自動選中並顯示空清單，**全程不需要 Streamlit、不需要 Supabase 後台**。
- [ ] **AC-10**（新）：旅程下拉可切換旅程，切換後清單正確重載；重整後停在同一趟旅程。
- [ ] **AC-11**（新）：網址帶 `?trip=N` 時載入該趟旅程（優先於 localStorage），既有分享連結不失效。
- [ ] **AC-12**（新）：行程 Tab 可手動新增一筆行程項目（不經 AI），留空天數時進入候選區。
- [ ] **AC-13**（新）：**公開站**的購物 Tab 上「🔗貼連結帶入」可見且可用（走 Function proxy），且前端原始碼／network 內容中不出現 Gemini 金鑰。
- [ ] **AC-14**（新）：push 到 Scout repo main → Netlify 自動部署出新版（不需手動 drag-and-drop）。

## 8. Build Order（週末 2–3 天，一次一件事）

**第一天 — ✅ 完成（2026-08-01）**
1. ✅ **搭外殼**：`web/index.html` + `shell.js` + `shell.css`，頂部雙 Tab、切換、記住上次選擇。**AC-1、AC-8 通過**。
2. ✅ **搬 buylist**：`<style>`→`buylist.css`（加 `#panel-shop` 前綴）、`<script>`→`buylist.js`（本來就是 IIFE，只改 `status`/`statusText` 兩個 id）。**AC-3、AC-6 通過**——實測連上 Supabase、Realtime「即時同步已連線」、真實資料正常渲染。
3. ✅ **搬 checklist**：`app.js`→`checklist.js`（整包包 IIFE、**移除 demo 分支**，id 全部維持原樣）、`styles.css`→`checklist.css`（加 `#panel-trip` 前綴）。**AC-4、AC-5、AC-6、AC-7 通過**。
   - ✅ **AC-2 通過**（Stanley un-pause 後補驗）：`?trip=4` 載入「沖繩 5 天（示範）」，兩軸儀表板（必須確認 2／已確認 1／可以彈性 2）、行程表（Day 1–5 分組）、時間軸（時刻表格線）三個檢視都正確渲染真實資料。同時購物 Tab 仍「即時同步已連線」、3 筆項目在——AC-6 二次確認。

**第二天**
4. ✅ **最小旅程管理**（§6.2）：旅程下拉 + 建立旅程 + 手動新增項目 + `?trip=` 相容。**AC-9～AC-12 全數通過**（2026-08-01 實測，測試資料已清除）。
   - 沒選旅程時渲染「選擇／建立旅程」畫面，不再是「網址缺少 ?trip=」的死路。
   - localStorage 存的 id 會對照旅程清單驗證，指向已刪除的旅程時自動清掉並回到選擇畫面。
   - 實作時修掉一個自己造的落差：從 localStorage 還原時原本沒把 `?trip=` 寫回網址，導致複製網址列拿不到可分享的連結。
5. **Function 收斂**：搬 `ai-parse.js`、新寫 `ai-product.js`，buylist 前端改打 proxy、拿掉「無金鑰就隱藏」的分支。驗 AC-13。
6. **config 收斂**（§6.4）。

**第三天（收尾，可壓縮）**
7. **Netlify 接 Git**：站台改接 Scout repo、base directory `web/`、functions directory `web/netlify/functions`、環境變數設 `GEMINI_API_KEY`。驗 AC-14。
8. **手機檢查** 375px。驗 AC-7。
9. **收拾**：`scout-checklist` repo 標退役（含裡面那份爛掉的 `buylist.html` 複本）；Scout repo 的 Streamlit 檔案標作廢；`scout.db` 刪除；更新 `context.md`、`CHANGELOG.md`、`BUYLIST_STATE.md`。

## 9. End-to-End Verification

手機與桌面各開一次合併後的網址：
1. 行程 Tab → 建一趟新旅程 → 手動加一筆 → 跑一次 AI 匯入 → 確認都寫進 Chia 的 Supabase。
2. 換一個瀏覽器開同一網址帶 `?trip=<剛建的 id>` → 看到同一趟。
3. 購物 Tab → 新增一筆 → 貼一個 iHerb 連結按「🔗貼連結帶入」→ 確認名稱價格帶入、且 devtools network 裡看不到 Gemini 金鑰。
4. 兩台裝置同開購物 Tab，一台新增 → 另一台即時出現（Realtime 沒被合併弄壞）。
5. 全站搜尋 `demo` 確認無殘留；重整停在上次 Tab；375px 不破版。

## 10. Open Questions / Risks

- **R1（Netlify 站台命名）**：現有站是 `shoppingtool.netlify.app`，合併後名字不再貼切。要沿用（省事、書籤不變）還是改名（例如 `scout-app`，但舊網址失效、要重發連結給 Chia）？**Stanley 決定。**
- **R2（Streamlit 獨有功能的去留）**：退役後這些功能沒有替代品——**AI 生成行程**（多輪問答 → Gemini 產出整份行程，`page_ai_suggest.py`）、**行程項目的欄位編輯／上下移排序／跨天移動**、**旅程刪除**。本週末**刻意不補**（§5.4）。Streamlit 程式碼保留可跑，真的需要時本機起一次；若之後常用，再開 spec 補進合併版。
- **R3（安全，沿用既有已接受的風險）**：兩個 Supabase 都是 anon key + RLS 全開攤在公開網址上，誰有網址誰能讀寫。合併不改變這件事，但把兩份資料放到同一個網址後，**一個網址外流＝兩邊資料同時外流**。Stanley／Chia 需再確認接受。
- **R4（Realtime 不對稱）**：購物 Tab 有 Realtime 即時同步，行程 Tab 沒有（手動重新整理）。合併後兩個 Tab 行為不一致，使用者可能困惑。本週末不處理；若要補，是 checklist 側加 Realtime 訂閱，非小工程。
- **R6（✅ 已解除，但根因仍在）**：2026-08-01 實測 `uarkccyqcqvgxukjcrey.supabase.co` **DNS 無法解析**，Stanley un-pause 後恢復（先短暫回 `PGRST205 schema cache` 錯誤，約一分鐘後 PostgREST 快取熱起來，四張表與資料都完好）。
  - **根因未解**：Supabase 免費方案閒置 7 天就自動暫停。行程資料庫是「規劃旅行時才用」的季節性用途，天生容易閒置——這已經是第二次（2026-07 有過一次「請 Chia un-pause」的交接，commit `67e0772`）。Stanley 明確表示每週手動 un-pause 不可接受。
  - **對策見 §6.5**（保活排程）。

- **R5（Chia 覆核）**：§4.2 這批決策（Streamlit 退役、落點改 Scout `web/`、Netlify 接 Git）都是 Stanley 的部署／整合範疇，依既有分工不需 Chia 拍板；但「Streamlit 退役」會讓 Chia 少掉建立旅程以外的編輯能力，動工前**知會一聲**。

## 11. Context Pulled
- `buylist/index.html`（584 行，現行完整原碼）、`buylist/BUYLIST_STATE.md`
- `witsper-stanley/scout-checklist` @ `9bf6a62`（`index.html` / `app.js` / `styles.css` / `netlify.toml` / `netlify/functions/ai-parse.js` / `README.md`）
- `db.py`（確認 Streamlit 已走 Supabase）、`supabase_schema.sql`
- 本檔 v1（Chia，2026-07-25）
