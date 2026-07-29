# Spec — 合併 BuyList ＋ Scout 確認清單為單一雙 Tab App

> **用途**：交給 Stanley（Claude Code）執行的 SSOT。
> **需求來源**：Chia，2026-07-25——「整理成一個，分兩個 Tab，看怎麼連線」，並確認：不要 demo 模式，直接是能用的正式版。
> **狀態**：**部分 BLOCKED**——§5、§7 需要 checklist 現行原碼才能精確定案，見 §0.1。其餘（架構決策、衝突處理策略、AC）已可定案。

---

## 0. Meta
- **Appetite（時間預算）**：中。不是排版小改，是兩個獨立單檔 app 的合併，牽涉命名空間隔離與雙後端並存。
- **Status**：draft（部分 blocked）
- **Date**：2026-07-25

### 0.1 Blocker（動工前必須解除）
本 spec 是在**沒有 checklist 現行原碼**的情況下寫的。已知線上版是 `https://witsper-stanley.github.io/scout-checklist/`，Supabase 版（非本機 `scout-checklist/` 資料夾裡那份——那份是**舊 Firebase 版**，已停用，不可用來合併，見 §10 R1）。

**動工前必須拿到**：`witsper-stanley/scout-checklist` repo 現行 `index.html`（Supabase 版）原始碼。拿到後，先執行 §5「拿到原碼後要做的事」，把本 spec 的 TBD 處補實，再進 Build Order。

## 1. Problem Statement
現在購物清單（buylist，本機跑）和行程確認清單（scout-checklist，已上 GitHub Pages）是兩個分開的單檔 app，各自要單獨開。想整理成一個 app、用 Tab 切換，一次看兩件事。

## 2. Primary User + JTBD
- **User**：Chia / Stanley，手機與桌面瀏覽器都要能開（呼應 §4.1「上手機」決定）。
- **JTBD**：當我要規劃行程或管理待買清單時，我想要在同一個網址切換兩個 Tab，這樣不用記兩個網址、兩個書籤。

## 3. Success Criteria
- 一個網址、頂部兩個 Tab（購物／行程），各自完整運作，功能不因合併而減損。
- 各自連各自原本的後端，資料**不合併**（見 §4 決策）。
- 拿掉 `?demo=1` 範例模式，合併後就是正式可用版（見 §4 決策）。
- 手機瀏覽器打開可用（响應式，至少不破版）。

## 4. 關鍵決策（已與 Chia 確認，寫死，勿重新討論）
- **不合併資料庫**。購物繼續連 Stanley 的 Supabase 專案（`kdmmjlaajqxjmiahfvos`）；行程繼續連珈欣的 Supabase 專案（`uarkccyqcqvgxukjcrey`）。理由：兩者無共用資料表、無跨表查詢；分開後端是刻意決策（buylist 用 Stanley 自己的專案是因為他對 Scout 的 Supabase 沒後台權限）；合併資料庫只有遷移成本、沒有功能收益。若未來真出現「這趟行程要買的東西」這種跨模組需求，用**情境標籤**（`spec-buylist-context-tag.md`）之類的輕量欄位表達，不合併資料庫。
- **拿掉 demo 模式**。移除 checklist 端 `?demo=1` 的範例資料分支與相關 UI，合併版一律接真實 Supabase，不做「假資料預覽」這個狀態。
- **合併只動介面層**：一個 HTML 外殼＋兩個 Tab 面板，各自的 JS/CSS 用作用域隔離，不重寫兩邊既有的業務邏輯。

## 5. Scope & Interfaces
- **已知涉及檔案**：
  - `buylist/index.html`（391 行，現行完整原碼，已在手）——單檔 vanilla HTML/CSS/JS（IIFE `"use strict"` 包住），CSS 變數走 `:root`（`--bg`/`--card`/`--ink`/`--blue`…等 Scout CIS 命名），核心邏輯用全域 `$(id)` helper、`setStatus()`、`sb`（Supabase client 變數名）。
  - **checklist 現行 `index.html`（TBD——待 §0.1 解除 blocker 後補上實際行數/結構/變數命名）**。
- **拿到原碼後要做的事（動工第一步，非 AI 猜測）**：
  1. 讀 checklist 原碼，列出它的：Supabase client 變數名、`$` 或類似 DOM helper 名稱、`setStatus`/狀態列函式名、CSS `:root` 變數名清單、全域函式/變數清單、demo 模式的判斷與資料來源（`?demo=1` 怎麼分支）、Gemini 金鑰讀取方式。
  2. 逐一比對 buylist 的同名項目（`$`、`setStatus`、`sb`、CSS 變數如 `--card`/`--line`…），列出**衝突清單**。
  3. 用衝突清單決定實際的前綴/包裝方案（§5.1 是預設策略，若原碼結構特殊需調整）。
- **明確 out of scope**：不重寫任一邊既有業務邏輯／UI／資料模型；不合併 Supabase 專案；不做 PWA 離線（見 `BUYLIST_STATE.md §4.1`，離線是之後才談）；不改各自的 AI 功能行為（貼連結帶入 / AI 匯入行程），只搬到同一頁。

### 5.1 衝突處理策略（預設方案，供 §5 步驟 3 校對用）
兩個各自完整的單檔 app 塞進同一頁，必然撞名。預設處理方式：

1. **JS 作用域**：兩邊各自的邏輯各包一個 IIFE（buylist 本來就是），互不外洩全域變數。共用的極少數東西（例如 Tab 切換本身）另外寫一小段外殼腳本，不進任一邊的 IIFE。
2. **DOM id**：兩邊原本的 element id（如 buylist 的 `list`、`bl-name`、`f-cat`）若與 checklist 有重複，其中一邊要加前綴（建議 buylist 側加 `bl-` 前綴，因為它現有 id 已大量用 `bl-` 開頭，改動最小；checklist 側視實際命名決定）。
3. **CSS 變數**：兩邊都用 `:root` 定義顏色變數，且**很可能同名撞色**（buylist 用 Scout CIS 的 `--bg`/`--card`/`--ink`/`--blue` 等）。策略：以 Scout CIS 配色為準（buylist 已是這套），checklist 若用不同配色系統，比對後選：(a) checklist 跟著改用同一套 CIS 變數（視覺統一，改動大），或 (b) checklist 的顏色變數整體加前綴（`--ck-bg` 等）各自獨立（改動小、但兩個 Tab 視覺風格可能不一致）。**這格需要看到 checklist 原碼才能定，先列為 Open Question（§10 R2）**。
4. **雙 Supabase client**：兩個獨立變數（如 `sbBuylist` / `sbChecklist`），各自的 `createClient(...)`，各帶各自的 URL/anon key，互不干擾。
5. **雙 Gemini 設定**：合併後的 config 檔（沿用 buylist 的 gitignored `config.js` 模式）同時容納兩把金鑰／模型設定，例如：
   ```js
   window.SCOUT_APP_CONFIG = {
     BUYLIST_GEMINI_API_KEY: "...",
     BUYLIST_GEMINI_MODEL: "gemini-2.5-flash",
     CHECKLIST_GEMINI_API_KEY: "...",
     CHECKLIST_GEMINI_MODEL: "...", // 沿用 checklist 原設定
   };
   ```
   `config.js.example` 一併更新成雙金鑰範本；`.gitignore` 已擋 `config.js`，沿用即可。
6. **Tab 外殼**：頁首一個簡單的 Tab bar（購物／行程），兩個 `<div>` 面板用 `display:none/block` 或既有 `.hidden` class 切換（buylist 已有 `.hidden` 用於清單/矩陣切換，可比照），切換邏輯放外殼腳本，記住上次選的 Tab（`localStorage`，比照 buylist 現有的 `buylist_me` 存法）。
7. **demo 模式移除**：checklist 原碼中判斷 `?demo=1` 的分支與其假資料來源整段拿掉，該路徑改為必定走真實 Supabase；若原本 demo 模式承擔了「無 config 時的降級提示」，改為明確的「尚未設定」錯誤提示（比照 buylist 的 `setStatus(...,'err')` 模式），不要無聲失敗。

## 6. Acceptance Criteria（初始全 failing）
- [ ] **AC-1**：開合併後的頁面 → 看到頂部 Tab bar，預設落在某一個 Tab（購物或行程，待 Chia 定，先預設購物）。
- [ ] **AC-2**：切到「行程」Tab → checklist 原有功能（清單顯示、AI 匯入行程）正常運作，接的是珈欣的 Supabase，資料與獨立版一致。
- [ ] **AC-3**：切到「購物」Tab → buylist 原有功能（新增/篩選/排序/已買/星號/貼連結帶入）正常運作，接的是 Stanley 的 Supabase，資料與獨立版一致。
- [ ] **AC-4**：網址不帶 `?demo=1`（或帶了也無效）→ 兩個 Tab 都直接是正式資料，沒有任何假資料/範例模式路徑可觸發。
- [ ] **AC-5**：兩個 Tab 的顏色/字體/按鈕樣式互不干擾——在購物 Tab 動作不會意外改到行程 Tab 的樣式，反之亦然。
- [ ] **AC-6**：在購物 Tab 新增一筆項目，不會被行程 Tab 的邏輯/狀態列覆蓋或報錯；反之亦然（驗證 JS 作用域隔離）。
- [ ] **AC-7**：手機瀏覽器（或桌面模擬手機尺寸）打開 → Tab bar 可點、兩個 Tab 內容不破版（至少可用，非像素級優化——像素級手機優化是另一份 spec）。
- [ ] **AC-8**：重整頁面 → 停留在上次選的 Tab（若採用記住上次選擇的做法）。

## 7. Build Order（一次一件事）— 前兩步待 §0.1 解除後才能精確排
1. **拿到 checklist 原碼、跑 §5 步驟 1–3**：列出衝突清單，把本 spec §5.1 的假設換成實際校對過的方案。
2. **搭 Tab 外殼骨架**：空的雙 Tab 頁面（無實際內容），驗證 Tab 切換、記住上次選擇。
3. **搬入 buylist**：整段塞進購物 Tab，改必要的 id 前綴，接 `sbBuylist`，驗 AC-3、AC-6。
4. **搬入 checklist**：整段塞進行程 Tab，移除 demo 分支，接 `sbChecklist`，驗 AC-2、AC-4、AC-6。
5. **樣式收斂**：依 §5.1-3 的決定統一或隔離 CSS 變數，驗 AC-5。
6. **雙金鑰 config**：合併 `config.js`／`config.js.example`，驗兩邊 AI 功能正常。
7. **手機檢查**：驗 AC-7。

## 8. End-to-End Verification
手機與桌面瀏覽器各開一次合併後的網址：切到行程 Tab，跑一次 AI 匯入行程確認能寫回珈欣的 Supabase；切到購物 Tab，新增一筆、貼連結帶入一筆，確認能寫回 Stanley 的 Supabase；確認網址沒有 `?demo=1` 相關痕跡；確認兩邊樣式互不污染；重整頁面停留在上次 Tab。

## 9. Context Pulled
- `buylist/BUYLIST_STATE.md` §4／§4.1（既有技術決策、上手機 supersede 決策）
- `buylist/index.html`（現行完整原碼）
- 線上 `https://witsper-stanley.github.io/scout-checklist/?demo=1`（僅拿到渲染後文字，非原碼）
- 本機 `scout-checklist/index.html`（確認為舊 Firebase 版、不可用，見 §10 R1）

## 10. Open Questions / Risks
- **R1（版本混淆，已排除但需 Stanley 覆核）**：Chia 電腦上連著的 `scout-checklist/` 資料夾其 `index.html` 是**舊 Firebase 版**（import `firebase-app.js`/`firebase-database.js`，寫死 `firebaseConfig`），remote 也指到不同帳號（`CHIAHSIN-tech/scout-checklist`，非 `witsper-stanley`）。**這份不是合併對象**，只有 `witsper-stanley/scout-checklist` 現行部署的 Supabase 版才是。
- **R2（CSS 配色策略未定）**：§5.1-3 的兩個選項（統一用 CIS 變數 vs 各自加前綴獨立）需看到 checklist 原碼的配色系統才能決定，Stanley 執行時可直接判斷選哪個並記錄理由。
- **R3（合併後部署位置未定）**：這是**部署範疇、屬 Stanley 決定**（依分工：Stanley 負責整合/部署）。現況 checklist 部署在公開的 `witsper-stanley/scout-checklist`（GitHub Pages），buylist 在 private `Scout` repo 本機跑。合併後的單一 app 放哪個 repo、Pages 怎麼設，本 spec 不代為決定，只交付「合併後的單檔 app 原始碼」，部署由 Stanley 接手。
- **R4（安全，沿用 BUYLIST_STATE §4.1 的提醒）**：purchase Tab 一旦隨此次合併一起被公開部署，anon key＋全開 RLS 攤在網址上的風險同前次已提醒的內容，此處不重複展開，執行前请 Stanley／Chia 再次確認接受。
- **R5（Tab 預設順序）**：AC-1 先假設預設開「購物」Tab；Chia 若有偏好（例如預設開「行程」）可在動工前一併定，避免做完再調。
