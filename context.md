---
# PROJECT DNA — 會被覆寫，但很少改動。只在專案定位本身改變時更新。
project_name: "Scout"
created_at: "2026-04-04"
last_updated: "2026-04-18 16:53"
current_version: "v0.0.0"
current_phase: "開發中"
primary_owner: "Stanley / 珈欣（Chia）"
tech_stack:
  language: "Python"
  ui_framework: "Streamlit"
  styling: "Custom CSS（Noto Sans TC、綠色主題、手機優先）"
  backend: "Streamlit（Python）"
  database: "SQLite（scout.db）"
  hosting: "TBD"
repo_url: "https://github.com/witsper-stanley/Scout.git"
---

# Context — 專案脈絡完整紀錄

> 這份文件是本專案的**唯一事實來源（Single Source of Truth）**。
> 任何人（包括 AI）在沒有其他檔案的情況下讀完此文件，應該能完整理解：
> 這個專案是什麼、為誰而做、目前進度到哪、做過哪些決策、為什麼這樣做、目前卡在哪裡。
>
> **客觀事實原則：** 本文件只記錄「客觀可見事實」（落地的檔案、git 紀錄、對話中明確的決策）。不記錄腦中想法、未決策的探索、或對使用者意圖的猜測。

---

## 0. AI 操作手冊 — 給維護這份文件的 Claude Code 看

**⚠️ 每一個新 session 的 Claude Code，開始工作前必須完整讀完本章節。**

### 0.1 你的角色

你是這份 `context.md` 的**自動維護者**。使用者不會手動更新這份檔案——完全由你（以及未來每個 session 的你）維護。使用者的唯一 input 是與你對話、做出決策、開發程式碼。

### 0.2 客觀事實原則（Objective Facts Principle）

**最重要的哲學:**

> 只記錄「客觀可見事實」。如果一件事沒有以任何形式落地（檔案、對話、commit、設定），就當它不存在。不要猜測、不要假設、不要補完使用者腦中的想法。

具體界線：
- ✅ 記錄：檔案系統中可見的、git history 中可見的、對話中明確表達並做出決策的
- ❌ 不記錄：使用者腦中的想法但沒落地的、討論過但只是探索沒做決策的、對使用者意圖的猜測

當欄位反推或得知不出來 → 標記 `TBD（待實際開發中出現時補充）`，不要猜測補完。

**關鍵邊界案例：** 對話中使用者明確表達並做出決策（例如「我決定用 SQLite」）**算事實**，即使還沒寫進程式碼。因為它已離開使用者的腦、進入可見的對話紀錄、且代表「為什麼這樣做」。這種情境必須記錄為 ADR。純探索（例如「要不要用 SQLite 呢？」但最後沒做決策）**不算**。

### 0.3 檔案結構的兩種區塊類型

本檔案有兩種區塊，行為完全不同，**絕對不可搞混**:

**🔄 覆寫型區塊** — 永遠反映當前狀態，舊內容會被直接覆寫
- 第 0 章：AI 操作手冊（除非使用者明確要求修改規則，否則不動）
- 檔案開頭的 YAML frontmatter
- 第 1 章：專案 DNA
- 第 2 章：當前狀態快照
- 第 3 章：技術架構
- 第 6 章：未解問題與已知限制

**➕ 只增型區塊** — 只新增、不刪改，保留歷史脈絡
- 第 4 章：決策紀錄（ADR）
- 第 5 章：開發日誌

### 0.4 什麼時候要更新這份文件

你**不需要**在每次對話結尾都更新。只在偵測到以下「重要事件」時更新：

**必須觸發更新的事件:**
1. 使用者做出任何技術決策（選了某個框架、某個架構、某個資料模型）
2. 使用者改變了已做過的決策（在 ADR 建立 superseding 紀錄）
3. 完成一個 MoSCoW 裡的 Must 或 Should 項目
4. 遇到卡關超過 30 分鐘的問題（不論後來是否解決）
5. 發現一個影響後續工作的新限制、新需求、或新假設
6. 對話中討論了「為什麼這樣做而不是那樣做」的權衡（trade-off）
7. 新增或移除任何相依套件（dependency）
8. 環境設定、部署設定發生變化

**不需要觸發更新的情況:**
- 單純的 code review 和語法修正
- 執行 CLI 命令、查看檔案內容
- 問概念問題、討論但尚未做決策
- 臭蟲（bug）修復且不影響架構
- 使用者明確說「這次不用記」

### 0.5 如何判斷內容該寫在哪個區塊

| 內容類型 | 寫入區塊 |
|---------|---------|
| 專案名稱、使用者、成功標準變更 | 第 1 章（覆寫） |
| MoSCoW 分類、目前進度 | 第 2 章（覆寫） |
| 技術棧、資料夾結構、資料模型 | 第 3 章（覆寫） |
| 「為什麼選 A 不選 B」的決策 | 第 4 章（只增 ADR） |
| 開發過程、每日進度、卡關紀錄 | 第 5 章（只增日誌） |
| 已知 bug、技術債、暫緩事項 | 第 6 章（覆寫） |

**決定原則：** 如果這個資訊「被覆寫後就永遠消失會造成損失」，它屬於只增型。如果「永遠只有當前值是重要的」，它屬於覆寫型。

### 0.6 完整記錄分歧與轉折

使用者明確要求：**決策過程中的分歧、被拒絕的方案、轉折都要完整記錄**，因為這是最難還原的脈絡。

具體做法：
- 在 ADR 的「考慮過的選項」區塊，列出所有被認真討論過的方案，包含被拒絕的
- 寫明為什麼拒絕某個方案（而不是只寫為什麼選擇最終方案）
- 如果使用者和你（AI）曾經意見不同，記錄雙方的論點
- 如果決策後來被推翻，用 superseding 機制連結新舊 ADR

### 0.7 ADR 格式規範

每一則 ADR 使用以下格式，**嚴格遵守**:

```markdown
### ADR-[編號]: [決策標題]

- **日期:** YYYY-MM-DD
- **狀態:** Proposed | Accepted | Superseded by ADR-XXX | Deprecated | Pre-existing (reverse-engineered)
- **相關方:** 使用者 / Claude Code / 外部文件引用

**情境（Context）:**
[當時面臨什麼問題？背景是什麼？為什麼這個決策現在必須做？]

**考慮過的選項:**
1. **[選項 A]** — [描述]
   - 優點：[...]
   - 缺點：[...]
   - 為什麼沒選：[...]（如果最終選了，寫「最終採用」）
2. **[選項 B]** — [描述]
   - ...

**決策:**
[選了哪個？誰做的決定？決定的關鍵理由是什麼？]

**預期後果:**
- 正面：[...]
- 負面：[...]
- 需要後續處理的事項：[...]

**分歧與轉折紀錄:**
[若決策過程有爭論、使用者曾經偏好別的方案、中途改過主意，都記在這裡。如無則寫「無」。]
```

**特殊 ADR 類型——Pre-existing Decision：** 當反推出既有技術決策但無法得知當初的決策理由時，建立簡化版 ADR：
- 狀態標為 `Pre-existing (reverse-engineered)`
- 情境、考慮過的選項、分歧紀錄皆填 `無紀錄（此決策在 context.md 建立前已存在）`
- 決策欄位只寫事實
- 這種 ADR 的目的是讓後續決策能引用，不是還原不存在的歷史

### 0.8 開發日誌格式規範

日誌**倒序排列**（最新在最上面）。每則日誌格式：

```markdown
### [YYYY-MM-DD HH:MM] [簡短標題]

**類型:** 決策 | 進度 | 卡關 | 學習 | 重構 | 其他
**關聯 ADR:** ADR-XXX（若無則省略）
**關聯 MoSCoW:** [Must/Should/Could 的哪個項目]（若無則省略）

[2-5 句話描述發生了什麼、為什麼、結果如何。保持簡短，不要潤飾，用當下語氣。]
```

### 0.9 壓縮機制

當第 5 章開發日誌超過 100 則，或使用者明確要求壓縮時：
1. 將最舊的 1/3 日誌抽出來
2. 為這批日誌產出「時期摘要」，保留：重要決策（保留 ADR 引用）、完成的功能、學到的教訓
3. 刪除原始日誌，放「時期摘要」到第 5 章的 Archive 子區塊
4. 在 commit message 註明壓縮範圍，原始內容保留在 git history

**絕對不要壓縮 ADR**——決策紀錄是專案最珍貴的資產。

### 0.10 矛盾偵測

每次更新時檢查：
- 新資訊是否和第 1-3 章當前狀態矛盾？如果是，問使用者要覆蓋還是建立新 ADR
- 新 ADR 是否和舊 ADR 衝突？如果是，舊 ADR 必須標記為 Superseded

### 0.11 Git 紀律

每次更新 `context.md`，提醒使用者一次：「我已更新 context.md，記得 commit。」
建議 commit message 格式：`docs(context): [簡短描述]`

---

## 1. 專案 DNA

> 這個專案的本質。很少改動。當這一章改變，通常代表專案定位本身改變了。

### 1.1 問題陳述（Problem Statement）

**我們在解決什麼問題？**
旅遊規劃分散且繁瑣——行程、購物清單、餐廳、旅館資訊各在不同地方管理，缺乏整合工具。Scout 嘗試提供一個手機友好的整合平台，讓使用者能規劃行程、管理待購清單、記錄餐廳與旅館資訊。

**為什麼這個問題值得解決？**
TBD（待實際開發中出現時補充）

### 1.2 主要使用者（Primary User）

- **Stanley**：主要手機使用者，負責整體架構與 AI 分析功能
- **珈欣（Chia）**：負責各模組的新增/編輯/刪除畫面

### 1.3 JTBD 陳述（Jobs To Be Done）

TBD（待實際開發中出現時補充）

### 1.4 成功標準

TBD（待實際開發中出現時補充）

### 1.5 時間預算（Appetite）

TBD（待實際開發中出現時補充）

---

## 2. 當前狀態快照

> 這一章永遠反映「現在」。每次有重要進度都會被覆寫。想看歷史請看第 5 章日誌。

### 2.1 當前階段

**目前在哪：** 開發中（第一版）
**本週焦點：** 購物模組 — 待買清單完成，下一步購物模組預算追蹤

### 2.2 MoSCoW 範疇

**Must（第一版）**
- [x] 基本框架 + 登入（Stanley / 珈欣 下拉選使用者）
- [x] 行程規劃模組（時間軸 + AI 建議）
- [x] 購物模組 — 待買清單
- [ ] 購物模組 — 預算追蹤
- [ ] 貼連結自動分析（AI 核心功能）

**Should（第二版）**
- [ ] 餐廳模組
- [ ] 旅館模組
- [ ] 手機介面優化

**Could（第三版）**
- [ ] 統計報表
- [ ] 擱置原因記錄

**Won't（明確不做）**
- 自動爬蟲（由使用者主動貼連結）

### 2.3 進度指標

- **完成度：** 第一版約 60%（3/5 Must 項目完成）
- **剩餘時間預算：** TBD
- **最接近的里程碑：** 購物模組 — 預算追蹤

---

## 3. 技術架構

> 描述當前的技術決策與系統結構。重大變動時覆寫。每一次變動必須在第 4 章有對應的 ADR。

### 3.1 技術棧

| 層次 | 選擇 | 對應 ADR |
|------|------|----------|
| 語言（Language） | Python | ADR-002 |
| UI 框架 | Streamlit | ADR-003 |
| 樣式 | Custom CSS（Noto Sans TC、綠色主題） | ADR-003 |
| 元件庫 | Streamlit 內建 | ADR-003 |
| 狀態管理 | `st.session_state` | ADR-003 |
| 後端框架 | Streamlit（Python） | ADR-003 |
| 資料庫 | SQLite（scout.db） | ADR-004 |
| ORM | 無（直接使用 `sqlite3`） | ADR-004 |
| AI 後端 | Google Gemini（`google-genai`） | ADR-005 |
| 身份驗證 | 無（下拉選使用者，無密碼） | ADR-006 |
| 建置工具 | 無（直接 `streamlit run app.py`） | — |
| 測試 | 無 | TBD |
| 部署 | TBD | TBD |

### 3.2 資料夾結構

```
Scout/
├── app.py                  # 主入口，路由 + 全域 CSS
├── db.py                   # 資料庫 CRUD（trips / itinerary / wishlist / budget）
├── ai.py                   # Gemini API 封裝
├── itinerary.py            # 行程邏輯（時間計算、排序）
├── page_itinerary.py       # 行程規劃頁面 UI
├── page_ai_suggest.py      # AI 建議 Tab UI
├── page_shopping.py        # 購物清單頁面 UI（待買清單 + 連結分析）
├── requirements.txt        # streamlit, google-genai
├── scout.db                # SQLite 資料庫（未 commit）
├── scout_cis.html          # 設計規範文件
├── test_gemini.py          # Gemini API 測試腳本
├── .streamlit/
│   ├── config.toml         # Streamlit 伺服器設定
│   └── secrets.toml        # API 金鑰（未 commit）
├── CLAUDE.md               # Claude Code 規則
└── context.md              # 本檔案
```

### 3.3 資料模型（Data Model）

**trips（旅程）**
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| user | TEXT | 使用者名稱 |
| name | TEXT | 旅程名稱 |
| start_date | TEXT | 出發日期 |
| end_date | TEXT | 結束日期 |
| notes | TEXT | 備註 |
| created_at | TEXT | 建立時間 |

**itinerary_items（行程項目）**
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

**trip_adjustments（調整紀錄）**
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| trip_id | INTEGER FK | CASCADE 刪除 |
| adjusted_at | TEXT | 調整時間 |
| instruction | TEXT | 操作說明 |
| items_changed | TEXT | JSON 陣列 |

**wishlist / budget** — 表格已建立，wishlist CRUD 已實作（UI 完成），budget UI 尚未實作

### 3.4 外部服務與 API

| 服務 | 用途 |
|------|------|
| Google Gemini API | AI 行程建議生成（page_ai_suggest.py） |

### 3.5 環境變數

從 `.streamlit/secrets.toml`（未 commit）讀取：
- `GEMINI_API_KEY`（反推自 ai.py 使用 `genai.Client`）

### 3.6 關鍵模式與慣例

- **路由：** `st.session_state["page"]` 控制頁面切換，`app.py` 最底部 if/elif 分派
- **資料庫：** 每次操作開新連線，用完關閉（非連線池）
- **AI 呼叫：** 各頁面自組 prompt，`ai.py` 只負責呼叫 API + 自動重試
- **按鈕 key 命名：** `st-key-[name]` 對應 CSS 選擇器，讓樣式精準覆蓋

---

## 4. 架構決策紀錄（ADR）

> **只增不改。** 每一個重要決策一則。被推翻的決策不要刪除，改標記為 `Superseded`。

<!-- ADR_INSERTION_POINT -->

### ADR-001: 採用 context.md 作為專案脈絡單一事實來源

- **日期：** 2026-04-18
- **狀態：** Accepted
- **相關方：** 使用者 / Claude Code

**情境（Context）:**
使用者希望有一份自動維護的文件，讓任何新 session 的 AI 能在零先驗知識下完整理解本專案的脈絡。此決策為本文件系統建立的起點。

**考慮過的選項:**
1. **多個分散的文件（README + CHANGELOG + ADR 資料夾）** — 業界主流
   - 優點：每個檔案職責單一
   - 缺點：分享時必須打包多個檔案，AI 讀取需要多次 context switch
   - 為什麼沒選：違反使用者「單一檔案可完整分享」的核心需求
2. **單一 context.md，由使用者手動維護**
   - 優點：完全可控
   - 缺點：維護摩擦力高，容易廢棄
   - 為什麼沒選：使用者明確表示不想手動輸入
3. **單一 context.md，由 AI 自動維護** — 最終採用

**決策:**
採用選項 3。在檔案開頭放完整 AI 操作手冊，區分覆寫型與只增型區塊。採用「客觀事實原則」，只記錄可見事實，不猜測。

**預期後果:**
- 正面：零維護負擔、脈絡完整、分享方便
- 負面：AI 可能偶爾誤判區塊歸屬，需定期抽查；檔案長期會很長
- 需要後續處理的事項：日誌超過 100 則時啟動壓縮機制

**分歧與轉折紀錄:**
此決策為啟動設計，無分歧紀錄。

---

### ADR-002: 採用 Python 作為主要語言

- **日期：** 2026-04-04
- **狀態：** Pre-existing (reverse-engineered)
- **相關方：** 無紀錄

**情境（Context）:**
無紀錄（此決策在 context.md 建立前已存在）

**考慮過的選項:**
無紀錄（此決策在 context.md 建立前已存在）

**決策:**
採用 Python 作為唯一語言。所有程式碼（後端邏輯、資料庫、AI 呼叫、UI）皆以 Python 撰寫。

**預期後果:**
- 正面：與 Streamlit、google-genai、sqlite3 原生整合
- 負面：無
- 需要後續處理的事項：無

**分歧與轉折紀錄:**
無紀錄（此決策在 context.md 建立前已存在）

---

### ADR-003: 採用 Streamlit 作為 UI 與應用框架

- **日期：** 2026-04-04
- **狀態：** Pre-existing (reverse-engineered)
- **相關方：** 無紀錄

**情境（Context）:**
無紀錄（此決策在 context.md 建立前已存在）

**考慮過的選項:**
無紀錄（此決策在 context.md 建立前已存在）

**決策:**
採用 Streamlit 作為 UI 框架與應用伺服器。路由透過 `st.session_state["page"]` 實現。樣式以 `st.markdown(..., unsafe_allow_html=True)` 注入自訂 CSS。

**預期後果:**
- 正面：快速開發、純 Python、無需前後端分離
- 負面：UI 客製化受限，手機體驗需額外 CSS 調整
- 需要後續處理的事項：手機介面優化（第二版）

**分歧與轉折紀錄:**
無紀錄（此決策在 context.md 建立前已存在）

---

### ADR-004: 採用 SQLite 作為資料庫

- **日期：** 2026-04-04
- **狀態：** Pre-existing (reverse-engineered)
- **相關方：** 無紀錄

**情境（Context）:**
無紀錄（此決策在 context.md 建立前已存在）

**考慮過的選項:**
無紀錄（此決策在 context.md 建立前已存在）

**決策:**
採用 SQLite（`scout.db`）搭配 Python 內建 `sqlite3` 模組。啟用 WAL 模式（`PRAGMA journal_mode=WAL`）與外鍵約束（`PRAGMA foreign_keys=ON`）。

**預期後果:**
- 正面：零設定、部署簡單、適合小規模個人工具
- 負面：不適合多人同時寫入；檔案式資料庫部署到雲端需額外處理
- 需要後續處理的事項：若日後部署到 Streamlit Cloud，需評估 db 持久化方案

**分歧與轉折紀錄:**
無紀錄（此決策在 context.md 建立前已存在）

---

### ADR-005: 從 Claude API 切換至 Google Gemini 作為 AI 後端

- **日期：** 2026-04-04（反推自 commit `6da3d29`）
- **狀態：** Accepted
- **相關方：** Stanley（反推自 git commit history）

**情境（Context）:**
專案初期使用 Claude API 作為 AI 後端。後來明確切換至 Google Gemini（`google-genai`）。commit message 為「Switch AI backend from Claude API to Gemini API」。

**考慮過的選項:**
1. **Claude API（Anthropic）** — 初始選擇
   - 為什麼沒選：已在 commit 中被明確替換，具體原因無紀錄
2. **Google Gemini（google-genai）** — 最終採用

**決策:**
切換至 Google Gemini，以 `genai.Client.models.generate_content()` 呼叫 API。`ai.py` 封裝重試邏輯（503 自動重試，最多 2 次，間隔 3 秒）。

**預期後果:**
- 正面：已實際運作，AI 行程建議功能可用
- 負面：切換原因未記錄，未來若需再評估 AI 供應商缺乏比較基準
- 需要後續處理的事項：無

**分歧與轉折紀錄:**
此決策為一次明確的技術切換，由 git commit 可見。切換前後的考量未記錄。

---

### ADR-006: 登入採用下拉選單，無密碼驗證

- **日期：** 2026-04-04（反推自 commit `4014833`）
- **狀態：** Accepted
- **相關方：** 無紀錄

**情境（Context）:**
commit message 為「Simplify login to username dropdown, no password」，表示曾有密碼登入，後來刻意簡化。

**考慮過的選項:**
1. **帳號 + 密碼登入** — 初始設計，後被移除
   - 為什麼沒選：刻意簡化，具體原因無紀錄
2. **下拉選單選使用者（無密碼）** — 最終採用
   - 使用者：Stanley / 珈欣

**決策:**
採用下拉選單選使用者，不做真實身份驗證。適合家庭/雙人使用的個人工具。

**預期後果:**
- 正面：開發簡單、使用方便
- 負面：無任何安全性，僅適合信任環境
- 需要後續處理的事項：若日後公開部署，需重新評估

**分歧與轉折紀錄:**
從有密碼到無密碼是一次明確簡化，由 commit message 可見。

---

<!-- 往後的 ADR 依序往下寫 -->

---

## 5. 開發日誌

> **只增不改（但會週期性壓縮舊內容）。**
> **倒序排列：最新在最上面。**

<!-- LOG_INSERTION_POINT -->

### [2026-04-18] 購物模組 — 待買清單完成

**類型：** 進度
**關聯 MoSCoW：** Must — 購物模組 — 待買清單

新增 `page_shopping.py`，包含三個區塊：① 貼連結讓 Gemini 分析商品資訊（自動填入表單）、② 手動新增待買項目（名稱、分類、價格、備註）、③ 待買 / 已買清單（支援打勾切換狀態、刪除）。同步在 `db.py` 新增 `get_wishlist`、`add_wishlist_item`、`update_wishlist_status`、`delete_wishlist_item` 四個函式。`app.py` 改從 `page_shopping.py` import，移除本地 placeholder。

---

### [2026-04-18 16:53] context.md 系統建立

**類型：** 其他
**關聯 ADR：** ADR-001

由啟動 prompt 於此時自動建立 `context.md` 與更新 `CLAUDE.md`（保留原有 Schema/功能說明，開頭附加 Claude Code 操作規則）。掃描到技術棧：Python + Streamlit + SQLite + Google Gemini。git 共 17 筆 commit，最早 2026-04-04，專案已有完整行程規劃模組。建立 Pre-existing ADR-002 至 ADR-006，記錄已存在的技術決策。

---

### [2026-04-18 ~16:00] 行程規劃 UI 優化

**類型：** 進度
**關聯 MoSCoW：** Must — 行程規劃模組

完成多項 UI 調整：旅程清單改為卡片按鈕（整合資訊與開啟功能）、新增全覽所有天模式、新增行程改為 checkbox 展開（移除獨立 Tab）、支援跨天移動行程項目、按鈕樣式統一（返回箭頭向左、登出/新增無箭頭）、AI 問卷支援 Enter 觸發下一題。

---

### [2026-04-18 ~15:00] 新增行程規劃模組核心

**類型：** 進度
**關聯 ADR：** ADR-004
**關聯 MoSCoW：** Must — 行程規劃模組

新增 `trips`、`itinerary_items`、`trip_adjustments` 資料表與完整 CRUD（db.py）。建立 `page_itinerary.py`（旅程列表 + 行程詳細頁）、`page_ai_suggest.py`（Gemini 多輪問答 + 行程建議）、`itinerary.py`（時間計算與排序邏輯）。

---

### Archive — 壓縮後的時期摘要

_(目前尚無壓縮紀錄)_

---

## 6. 未解問題與已知限制

> 這一章是**覆寫型**。反映「現在」哪些事情還懸而未決。

### 6.1 建檔時無法反推的資訊

以下項目在 context.md 建立時無法從客觀事實反推，待實際開發中出現時由 Claude Code 自動補充：

- 問題陳述的「為什麼值得解決」細節
- JTBD 陳述
- 成功標準（具體指標）
- 時間預算（Appetite）
- 本週焦點（已初步填入，待確認）
- Gemini API 的 secrets key 名稱（.streamlit/secrets.toml 未 commit）

### 6.2 待決定的技術選擇

- **部署平台：** 尚未決定（Streamlit Cloud / 自行部署？）
- **SQLite 持久化：** 部署後 scout.db 如何保存？
- **測試框架：** 目前無任何測試，是否引入？

### 6.3 已知的 Bug

_(目前尚無紀錄)_

### 6.4 技術債（Technical Debt）

- `scout.db` 在 `.gitignore` 中，部署時需要另外處理資料遷移
- 無測試覆蓋，功能修改時容易引發回歸問題

### 6.5 暫緩的想法（Parking Lot）

- 貼連結自動分析（AI 核心功能）— 所有模組共用，待購物模組完成後實作
- 手機介面優化 — 第二版

### 6.6 外部相依的風險

- Google Gemini API 依賴外部服務；503 已有重試機制，但長期穩定性未知

---

## 附錄 A：術語表（Glossary）

| 術語 | 說明 |
|------|------|
| Trip（旅程） | 一整趟旅行，有起訖日期，包含多個行程項目 |
| Itinerary Item（行程項目） | 旅程中的單一景點/餐廳/活動 |
| Day Number | 旅程的第幾天（從 1 開始） |
| sort_order | 同一天內的行程排列順序 |

---

## 附錄 B：外部參考資料

- [Google Gemini API 文件](https://ai.google.dev/docs)
- [Streamlit 文件](https://docs.streamlit.io)
- `scout_cis.html` — 專案設計規範文件（存在於 repo 根目錄）

---

*這份文件由 Claude Code 自動維護。使用者不手動編輯。*
*如發現結構問題或規則需要調整，在本檔案第 0 章更新操作手冊。*
