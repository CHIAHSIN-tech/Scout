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