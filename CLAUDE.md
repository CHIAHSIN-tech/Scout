# Claude Code 專案指示

> 這份檔案在每次 Claude Code session 啟動時自動被讀取。
> 它是專案層級的常駐指示，不記錄歷史（歷史與決策在 `context.md`）。

---

## 1. 每次 session 啟動的必要動作

1. 讀取專案根目錄的 `context.md`
2. 熟讀其中的第 0 章「AI 操作手冊」,理解你在本專案的維護職責
3. 讀取第 1-3 章：專案 DNA、當前狀態快照、技術架構
4. 快速掃過第 6 章「未解問題與已知限制」,避免重複建議已被排除的方案
5. 若使用者提出新請求,先判斷它是否牽涉第 4 章既有的 ADR 決策；若與舊決策衝突,主動指出並詢問使用者是要遵守舊決策還是建立 superseding ADR

## 2. context.md 的維護職責

依照 `context.md` 第 0.3 節的觸發條件判斷何時更新。更新後：
- 主動告知使用者「已更新 context.md 的 [章節/ADR/日誌]」
- 提醒使用者 commit
- 建議的 commit message 格式：`docs(context): [簡短描述]`

## 3. 開發協作原則

以下是本專案採用的開發原則,任何程式碼產出都必須遵守：

### 3.1 回答風格
- 使用者是學習中的開發者,不是純粹的程式碼產出請求者
- 在給程式碼前,先問使用者「你目前怎麼想？」或「你打算怎麼做？」
- 例外：使用者明確說「直接告訴我」或「幫我寫」時,跳過詢問

### 3.2 程式碼品質
- 每段程式碼附上簡短說明（在做什麼、為什麼這樣寫）
- 使用**繁體中文**寫註解
- 範疇（Scope）保持最小——不要寫沒被要求的額外功能
- 遵守 SOLID 原則,特別是單一職責和依賴反轉
- DRY 原則：重複三次才抽取,不要過早抽象

### 3.3 方法論守衛
主動提醒使用者對齊以下方法論：
- 提新功能／新專案 → 先完成 Problem Statement 再討論實作
- 功能清單無限擴張 → 引導做 MoSCoW 優先級排序
- 跳過設計直接問實作 → 提醒先確認 User Flow
- 問技術選擇 → 用 Appetite 思維評估,而不只是比較技術優劣

### 3.4 語言規範
- 所有回覆使用**繁體中文**
- 技術專有名詞保留英文並標註中文,例如：元件（Component）、狀態管理（State Management）

## 4. 客觀事實原則（Objective Facts Principle）

本專案的 `context.md` 只記錄「客觀可見事實」。維護檔案時嚴格遵守：

- ✅ **記錄：** 檔案系統中可見的、git history 中可見的、對話中明確表達並做出決策的
- ❌ **不記錄：** 使用者腦中的想法但沒落地的、討論過但只是探索沒做決策的、你對使用者意圖的猜測

當一個欄位反推或得知不出來時,標記為 `TBD`,不要猜測補完。

**關鍵界線：** 對話中使用者明確表達並做出決策的內容（例如「我決定用 SQLite」）**算事實**,因為它已離開使用者的腦、進入可見的對話紀錄,且代表「為什麼這樣做」。這種情境必須記錄為 ADR。

## 5. Git 紀律

- 頻繁提交,每個提交代表一個連貫的變更
- 提交訊息格式：`[類型]: [描述]`
  - `feat:` 新功能
  - `fix:` 修 bug
  - `refactor:` 重構
  - `docs:` 文件（包含 context.md 更新）
  - `chore:` 雜務（設定、相依套件）
- 重構與功能變更分開提交
- 絕不 commit `.env` 或任何機密

## 6. 與 context.md 的關係

- 本檔案（`CLAUDE.md`）：**規則**。告訴你怎麼工作。
- `context.md`：**脈絡**。告訴你本專案發生過什麼。

兩者分工明確，不要把 context.md 的內容複製到這裡，也不要把這裡的規則寫進 context.md。

---

## 資料庫 Schema

### trips（旅程）
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| user | TEXT | 使用者名稱 |
| name | TEXT | 旅程名稱 |
| start_date | TEXT | 出發日期 |
| end_date | TEXT | 結束日期 |
| notes | TEXT | 備註 |
| created_at | TEXT | 建立時間 |

### itinerary_items（行程項目）
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| trip_id | INTEGER FK | 對應 trips.id，CASCADE 刪除 |
| day_number | INTEGER | 第幾天 |
| name | TEXT | 景點/餐廳名稱 |
| category | TEXT | restaurant/hotel/attraction/shopping/transport/other |
| start_time | TEXT | HH:MM |
| duration_minutes | INTEGER | 停留分鐘數 |
| location | TEXT | 地點/店名 |
| address | TEXT | 地址/Google Map |
| booking_ref | TEXT | 預約編號 |
| notes | TEXT | 備註 |
| source | TEXT | manual / ai |
| sort_order | INTEGER | 排序 |

### trip_adjustments（調整紀錄）
| 欄位 | 型別 | 說明 |
|------|------|------|
| trip_id | INTEGER FK | |
| adjusted_at | TEXT | 調整時間 |
| instruction | TEXT | 操作說明 |
| items_changed | TEXT | JSON 陣列 |

### wishlist / budget（保留，尚未實作 UI）

---

## 功能現況

### ✅ 已完成

**基本框架**
- 登入：下拉選單選使用者（Stanley / 珈欣），session_state 維持狀態
- 路由：home / itinerary / shopping / restaurant / hotel
- 全域樣式：Noto Sans TC、綠色主題、手機優先

**🗺️ 行程規劃模組（主力功能）**
- 旅程列表：新增、刪除旅程
- 行程詳細頁：兩個 Tab（時間軸 / AI 建議）
- 時間軸 Tab：
  - 單日檢視 / 全覽所有天 兩種模式
  - 手動新增行程項目（名稱、分類、時間、地點、預約編號、備註）
  - 行程卡片：點 ✏️ 展開編輯（含跨天移動）
  - 上移 ↑ / 下移 ↓ 調整順序，自動重算時間
  - 刪除單一行程
- AI 建議 Tab（page_ai_suggest.py）：
  - 多輪問答（目的地、天數、人數、偏好、預算、特殊需求）
  - 呼叫 Gemini 生成 JSON 行程建議
  - 依天分組顯示，勾選後加入時間軸

### 🚧 開發中 / 尚未開始
- 購物模組（UI placeholder 存在，功能未做）
- 餐廳模組（UI placeholder 存在，功能未做）
- 旅館模組（UI placeholder 存在，功能未做）
- 貼連結自動分析（AI 核心功能，所有模組共用）

---

## 模組說明

### ai.py — ai_generate()
- 封裝 `genai.Client.models.generate_content()`
- 遇到 503 自動重試（最多 2 次，間隔 3 秒）
- 各模組自行組 prompt，ai.py 只負責 API 呼叫

### itinerary.py — 行程邏輯
- `time_str_to_minutes / minutes_to_time_str`：時間格式轉換
- `shift_time`：時間平移
- `adjust_single_item / adjust_with_cascade`：單一/串聯調整（回傳預覽）
- `apply_adjustment`：寫入資料庫並記錄歷史
- `reorder_and_recalculate / apply_reorder`：重排順序並重算時間

---

## 開發順序

**第一版（進行中）**
- [x] 基本框架 + 登入
- [x] 行程規劃模組（時間軸 + AI 建議）
- [ ] 購物模組 — 待買清單
- [ ] 購物模組 — 預算追蹤
- [ ] 貼連結自動分析

**第二版**
- 餐廳模組
- 旅館模組
- 手機介面優化

**第三版**
- 統計報表
- 擱置原因記錄

---

## 重要原則

- 手機優先（Stanley 主要用手機）
- 介面要簡單，不要複雜
- 第一版先求能用，不求完美
- 不做自動爬蟲，由使用者主動貼連結
- 用 Branch 開發，不直接推到 main
- 一次只做一個功能

---

## 分工

**Stanley**：整體架構、AI 分析功能、整合、部署
**Chia**：各模組的新增/編輯/刪除畫面
