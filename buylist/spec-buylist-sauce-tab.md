# Spec — 辣醬庫（Hot Sauce Library）作為 buylist 的一個 Tab

> **用途**：交給 Stanley（Claude Code）執行的 SSOT。
> **來源 & 重要變更**：原 `specs/spec-hot-sauce-library.md`（Vue 3 + Vite 獨立 app）。
> **2026-07-26 Stanley 拍板：改成「buylist 的附加功能、一個 tab」**，不開新 app、不用 Vue。
> **本 spec supersede 原 Vue spec 的架構部分**（技術棧、獨立 repo、獨立部署全部作廢）；功能意圖沿用。
> **維護**：完工後更新 `buylist/BUYLIST_STATE.md`。

---

## 0. Meta
- **Appetite**：中。買物清單之外的第二個資料域，塞進同一個單檔 app，靠頂層 tab 切換。
- **Status**：draft
- **Date**：2026-07-26

## 1. Problem Statement
Chia 買/吃過很多辣椒醬，資訊散落（備忘錄、相簿、購物紀錄），想再買時找不到連結、也不記得好不好吃。想要一個**兩人共用、可即時協作編輯**的辣醬庫，快速查「之前評分多少、值不值得回購」。

## 2. Primary User + JTBD
- **User**：Chia（主要）+ Stanley，手機為主，桌面偶爾。
- **JTBD**：當我想起或看到一款辣醬，我想要快速查到它的評分與購買連結，這樣我能決定要不要（再）買。

## 3. 為什麼併進 buylist（而非獨立 app）
- 沿用 buylist 現成的：Supabase（Stanley 個人專案 `kdmmjlaajqxjmiahfvos`）、即時同步、單檔 vanilla HTML、CIS 配色、無帳號共用、已公開部署（shoppingtool.netlify.app）。
- 使用情境相近（都是「買不買 / 值不值得回購」的決策），兩人同一個入口。
- 原 spec 假設「buylist = Firebase + Vue」已過時（buylist 實為 Supabase + 單檔 vanilla），照舊 spec 會走錯路。

## 4. MoSCoW
- **Must（MVP）**
  - 頂層 tab：「🛒 買物清單」⇄「🌶️ 辣醬庫」，切換顯示對應內容；預設買物清單。
  - 新表 `sauces`：名稱、連結、4 個評分（辣度/香氣/CP值/回購度，各 1–5）、誰加的、建立時間。
  - 新增辣醬：名稱（必填）＋連結＋4 個評分（星級選擇器）。4 個評分皆必填才能存。
  - 列表：卡片顯示名稱、4 評分、連結；**預設按「回購度」由高到低排序**。
  - 刪除辣醬（比照 buylist：可直接刪）。
  - 即時同步：新增/改/刪，另一台 ≤ 數秒看到（Supabase Realtime，`sauces` 另一個 channel）。
  - 關鍵字搜尋（名稱包含即顯示）。
  - 手機優先，390px 無橫向捲動。
- **Should（之後，不擋 MVP）**
  - 編輯評分/欄位（改回購度後即時重排）。
  - 圖片上傳（Supabase Storage）、價格、購買日期、情境/地區標籤。
- **Won't（這版不做）**
  - 帳號系統、留言/按讚、版本歷史、進階篩選、社群分享、電商整合。
  - 每個辣醬庫獨立 libraryId（原 spec 第 6 loop）——這版就一個共用庫，同 buylist。

## 5. Scope & Interfaces
- **涉及檔案**：
  - `buylist/buylist-schema.sql`：新增 `sauces` 表 + RLS 全開 + realtime（比照 `buylist_items`）。Supabase `kdmmjlaajqxjmiahfvos` 執行 DDL。
  - `buylist/index.html`：頂層 tab bar；包一層現有買物清單 UI；新增辣醬 UI（表單＋列表＋搜尋）；`sauces` 的載入/新增/刪除/搜尋/排序；第二個 Realtime channel。
- **既有 pattern 對照**：
  - Supabase client、`setStatus`、`esc`、`me`(`added_by`)、CIS 樣式全部重用。
  - 即時訂閱比照現有 `buylist-all` channel，另開 `sauces` 訂閱 → 重載辣醬列表。
  - 缺欄位容錯、RLS 全開、無登入：同 buylist。
- **明確 out of scope**：不動買物清單既有邏輯（加總/篩選/排序/匯出/實付…）；辣醬與買物是兩個獨立資料域，互不影響。

## 6. Acceptance Criteria（初始全 failing）
- [ ] **AC-1**：頂部有「買物清單 / 辣醬庫」兩個 tab，預設買物清單；點「辣醬庫」→ 顯示辣醬 UI、隱藏買物 UI（反之亦然）。
- [ ] **AC-2**：辣醬 tab 新增「Frank's RedHot」＋連結＋辣度4/香氣4/CP值5/回購度5 → 存檔 → 列表出現該卡片，顯示名稱與評分。
- [ ] **AC-3**：任一評分未選 → 無法存，狀態列紅字提示。
- [ ] **AC-4**：列表預設按回購度由高到低；新增一筆回購度 5 的會排在回購度 3 的上面。
- [ ] **AC-5**：搜尋框輸入關鍵字 → 只顯示名稱包含該字的辣醬。
- [ ] **AC-6**：刪除一筆 → 從列表消失。
- [ ] **AC-7**：另一台（Realtime）新增/刪除辣醬 ≤ 數秒同步；重整後資料仍在。
- [ ] **AC-8**：切到辣醬 tab 不影響買物清單資料與加總；切回買物清單一切如常。
- [ ] **AC-9**：手機寬（≤390px）辣醬列表無橫向捲動。

## 7. Build Order（一次一件事）
1. **schema**：`sauces` 表 + RLS + realtime，Supabase 執行 DDL。
2. **tab 骨架**：頂層 tab bar，包現有買物 UI 成一區、新增空的辣醬區，切換顯示 → 驗 AC-1、AC-8。
3. **辣醬 CRUD**：載入+排序（回購度）、新增表單（4 星＋驗證）、刪除、狀態列 → 驗 AC-2~AC-4、AC-6。
4. **搜尋 + 即時**：關鍵字過濾、`sauces` Realtime 訂閱 → 驗 AC-5、AC-7、AC-9。

## 8. End-to-End Verification
開 buylist → 切「辣醬庫」→ 新增「Frank's RedHot」(4/4/5/5) 與「某醬」(回購度3) → 確認回購度高的在上 → 搜尋名稱只剩對應 → 刪一筆消失 → 重整後在 → 切回「買物清單」資料與加總不受影響。

## 10. Open Questions / Risks
- **R1（DDL blocker）**：上線前先在 Supabase 跑 `sauces` DDL（同 buylist 加欄位的坑；且該專案免費方案會自動暫停，見 memory `buylist-supabase-pause`）。
- **R2（單檔變大）**：買物 + 辣醬塞同一 index.html，JS 會變長；用清楚的區塊註解分隔兩個資料域，不強行抽象（DRY 三次原則）。
- **R3（編輯）**：MVP 先做新增/刪除；改評分要「刪掉重加」還是做編輯，列 Should，先不擋。
