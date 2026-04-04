# Scout — Context（專案全貌文件）

> 目的：讓任何 AI 工具開新對話時，上傳這個檔案就能完整理解專案。
> 維護原則：只更新架構/概念層級的變動，bug fix 不更新。

---

## 1. 產品定位

- **名稱**：Scout — 個人生活研究助理
- **一句話描述**：貼任何連結或文字 → AI 自動整理 → 存進個人資料庫
- **使用者**：Stanley（主要）、Chia（助理/共同使用）
- **平台**：Streamlit 網頁 App，手機優先
- **目標**：讓日常購物比較、餐廳探索、旅行規劃的資料不再散落各處

---

## 2. 技術架構

| 層級 | 技術 | 說明 |
|------|------|------|
| 語言 | Python | |
| 前端 | Streamlit | layout="centered"，手機優先 |
| AI | Gemini API | google-genai SDK，model: gemini-3-flash-preview |
| 資料庫 | SQLite | 本地檔案 scout.db，WAL mode |
| 部署 | Streamlit Cloud | 免費方案 |
| 版控 | GitHub (private) | witsper-stanley/Scout |

**檔案結構**：
```
Scout/
├── app.py              # 主程式：登入、路由、各頁面 placeholder
├── ai.py               # Gemini API 封裝（ai_generate 函式）
├── db.py               # SQLite 連線 + schema 初始化
├── requirements.txt    # streamlit, google-genai
├── CLAUDE.md           # Claude Code 專用指引
├── context.md          # 本檔案
├── .gitignore
└── .streamlit/
    ├── config.toml     # theme 設定
    └── secrets.toml    # API key + 密碼（不進 git）
```

**secrets.toml 結構**：
```toml
GOOGLE_API_KEY = "..."
GEMINI_MODEL = "gemini-3-flash-preview"

[passwords]
stanley = "..."
chia = "..."
```

---

## 3. 資料結構

### wishlist（待買清單）
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| user | TEXT | 使用者名稱 |
| name | TEXT | 商品名稱 |
| category | TEXT | 分類 |
| estimated_price | REAL | 預估價格 |
| added_date | TEXT | 加入日期 |
| status | TEXT | pending / purchased / dropped |
| purchased_date | TEXT | 購買日期 |
| notes | TEXT | 備註 |

### budget（月預算）
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| user | TEXT | 使用者名稱 |
| year_month | TEXT | 格式 2026-04 |
| budget_limit | REAL | 預算上限 |
| | | UNIQUE(user, year_month) |

---

## 4. 功能模組

### 登入
- 下拉選單選使用者（stanley / chia），無密碼
- session_state 記住登入狀態
- 側邊欄顯示目前使用者 + 登出按鈕

### 首頁
- 三個模組入口：購物 / 餐廳 / 旅館
- 用 st.columns(3) 排列，各有 icon + 進入按鈕

### 購物模組（開發中）
- 待買清單：新增 / 編輯 / 刪除 / 標記已購買
- 預算追蹤：每月上限設定，超支提醒
- 衝動煞車：顯示「這個東西你想了幾天了」
- AI 分析：貼連結 → Gemini 整理型號比較、推薦結論、價格區間

### 餐廳模組（尚未開發）
### 旅館模組（尚未開發）

---

## 5. AI 指令設計

### ai.py — ai_generate()
- 封裝 `genai.Client.models.generate_content()`
- 支援 503 自動重試（最多 2 次，間隔 3 秒）
- 呼叫方式：`ai_generate(contents="...", config=types.GenerateContentConfig(temperature=0.3))`
- 各模組的 prompt 由各模組自行定義，ai.py 只負責 API 呼叫

---

## 6. 已知限制

- SQLite 不支援多人同時寫入（目前只有兩個使用者，可接受）
- Streamlit Cloud 免費方案有 resource 上限
- 不做自動爬蟲，由使用者主動貼連結
- 目前無密碼保護，僅靠選單切換使用者

---

## 7. 產品決策記錄

| 日期 | 決策 | 為什麼這樣做 | 否決的替代方案 |
|------|------|-------------|---------------|
| 2026-04-04 | AI 用 Gemini 而非 Claude API | 與既有 Interview 專案共用同一個 API key，降低成本 | Claude API — 需要另外付費 |
| 2026-04-04 | 登入用下拉選單免密碼 | 目前只有兩人使用，簡化流程優先 | 密碼驗證 — 過度設計 |
| 2026-04-04 | 資料庫用 SQLite | 免費、零設定、Streamlit Cloud 可用 | PostgreSQL — 目前規模不需要 |
| 2026-04-04 | 不做自動爬蟲 | 避免法律風險和維護成本 | 自動抓取 — 複雜且不穩定 |

---

## 8. 分工

- **Stanley**：整體架構、AI 分析功能、整合、部署
- **Chia**：各模組的新增/編輯/刪除畫面

## 9. 協作規則

- 用 Branch 開發，不直接推 main
- 一次只做一個功能
- 做完自己測試，沒問題再開 Pull Request
