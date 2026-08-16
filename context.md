---
# PROJECT DNA — 會被覆寫，但很少改動。只在專案定位本身改變時更新。
project_name: "Scout"
created_at: "2026-04-04"
last_updated: "2026-08-01"
current_version: "v0.0.0"
current_phase: "轉型中——Streamlit 退役、合併為單一靜態雙 Tab web app"
primary_owner: "Stanley / 珈欣（Chia）"
tech_stack:
  language: "JavaScript（vanilla，無 build）；Python 僅存於待退役的 Streamlit"
  ui_framework: "無框架（原生 HTML/CSS/JS）；Streamlit 待退役"
  styling: "Custom CSS（Scout CIS 米色系、Noto Sans TC、手機優先）"
  backend: "無自有後端；瀏覽器直打 Supabase PostgREST + Netlify Functions（AI proxy）"
  database: "Supabase（PostgreSQL）×2 專案：uarkccyqcqvgxukjcrey（行程，Chia）／kdmmjlaajqxjmiahfvos（購物，Stanley）"
  hosting: "Netlify"
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

**目前在哪：** 轉型中。專案在 2026-04～07 分裂成三套並存的東西（Streamlit app、buylist 靜態 app、scout-checklist 靜態 app），現正收斂成**單一靜態雙 Tab web app**，Streamlit 退役。
**本週焦點：** 收斂已完成——合併版雙 Tab app 已上線。新增了 MCP server（ADR-016），程式完成但 AC-1~4 待真實環境驗收。下一個要決定的是「AI 生成行程」要不要補（Streamlit 退役後唯一沒有替代品的缺口）。

### 2.2 MoSCoW 範疇

> 原「第一版」的模組式範疇（餐廳／旅館模組等）是 Streamlit 時代的規劃，隨 ADR-010 退役而失效。以下是收斂後的實際範疇。

**Must（合併版）**
- [x] 購物 — 待買清單（buylist，13+ 欄、預算爆表、2×2 矩陣、篩選排序、匯出 md、Realtime 同步）
- [x] 購物 — 辣醬庫
- [x] 購物 — 貼連結 AI 帶入（本機可用；公開站待改 Function proxy）
- [x] 行程 — 確認清單兩軸儀表板
- [x] 行程 — 行程表 / 時間軸（拖曳改時間）
- [x] 行程 — AI 匯入行程（Netlify Function proxy，金鑰不外露）
- [x] **合併成單一雙 Tab app**（`spec-scout-app-merge.md` v2）— commit `0d3a00a`
- [x] **最小旅程管理**（建立旅程／切換旅程／手動新增項目）— commit `efa0878`
- [x] **行程項目的編輯／跨天移動／刪除項目／刪除旅程** — commit `e2ba895`，補回 Streamlit 退役造成的功能倒退
- [x] **兩 Tab 視覺統一 ＋ 匯出 Google 日曆／Maps** — 見 ADR-015 與 `ACCEPTANCE.md`
- [ ] **Netlify 接 Git 自動部署**（取代手動 drag-and-drop）

**Should**
- [ ] 手機介面像素級優化（現版能用但偏桌面）
- [ ] 行程 Tab 補 Realtime（目前只有購物 Tab 有，兩邊行為不一致）

**Could**
- [ ] 救回 Streamlit 的「AI 生成行程」（多輪問答 → Gemini 產出整份行程）
- [ ] 行程項目的上移↑／下移↓ 排序 — **刻意不做**：時間軸已能拖曳改時間，目的重疊（`spec-itinerary-restore-edit-delete.md` §4 Could）

**Won't（明確不做）**
- 自動爬蟲（由使用者主動貼連結）
- 合併兩個 Supabase 專案（ADR-012）
- 帳號系統（網址即存取，已接受風險）
- PWA / 離線

### 2.3 進度指標

- **完成度：** 合併版雙 Tab app 已上線；行程側的功能倒退已補齊；兩 Tab 視覺統一與匯出已完成。`specs/` 無待執行規格。
- **最接近的里程碑：** 由 Chia 決定「AI 生成行程」做不做（要做需另開 spec）

---

## 3. 技術架構

> 描述當前的技術決策與系統結構。重大變動時覆寫。每一次變動必須在第 4 章有對應的 ADR。

### 3.1 技術棧

> ⚠️ 本專案目前**同時存在兩套技術棧**：已上線的靜態 web app（購物＋行程），與待退役的 Streamlit app。下表以前者為主。

| 層次 | 選擇 | 對應 ADR |
|------|------|----------|
| 語言（Language） | JavaScript（vanilla，無 build）；Python 僅存於待退役的 Streamlit | ADR-002、ADR-010 |
| UI 框架 | **無框架**，原生 HTML/CSS/JS | ADR-010 |
| 樣式 | Custom CSS（Scout CIS 米色系，見 `scout_cis.html`）、手機優先 | ADR-010 |
| 狀態管理 | 模組內區域變數 + `localStorage`（記住 tab／使用者／旅程） | ADR-010 |
| 後端框架 | **無自有後端**。瀏覽器直打 Supabase PostgREST；AI 呼叫走 Netlify Functions | ADR-007、ADR-011 |
| 資料庫 | **Supabase（PostgreSQL）× 2 個專案**（見 §3.3） | ADR-007、ADR-012 |
| ORM | 無（buylist 用 supabase-js；checklist 直接 `fetch` 打 PostgREST） | ADR-007 |
| 即時同步 | Supabase Realtime `postgres_changes`（**僅購物側**；行程側是手動重新整理） | — |
| AI 後端 | Google Gemini。行程側已走 Netlify Function proxy（金鑰在環境變數）；購物側仍在前端 `config.js`，待改 | ADR-005、ADR-011 |
| 身份驗證 | 無。購物：網址即存取；行程：`?trip=<trip_id>` 即憑證 | ADR-006、ADR-013 |
| 建置工具 | 無 | ADR-010 |
| 測試 | 無（`tests/test_itinerary.py` 只涵蓋待退役的 Streamlit 邏輯） | TBD |
| 部署 | **Netlify**（購物：`shoppingtool.netlify.app`，手動 drop；行程：另一站，Git 連動 + Functions） | ADR-011 |

### 3.2 資料夾結構

```
Scout/                          ← private repo
├── buylist/                    # 【已上線】購物 app（買物清單 + 辣醬庫）
│   ├── index.html              #   單檔 584 行 / 42 KB，HTML+CSS+JS 全內聯
│   ├── config.js               #   Gemini 金鑰（gitignored）
│   ├── config.js.example
│   ├── buylist-schema.sql      #   Supabase DDL（SSOT）
│   ├── run.bat / run.command   #   本機起 http server
│   └── BUYLIST_STATE.md        #   購物側的接手文件
├── specs/                      # Chia 出的 spec ＋ 執行端修訂版（SSOT）
├── supabase_schema.sql         # 行程側 Supabase DDL（SSOT）
├── scout_cis.html              # 設計規範（配色 SSOT）
├── CLAUDE.md / context.md / CHANGELOG.md
│
├── ── 以下為待退役的 Streamlit app（ADR-010）──
├── app.py                      # 主入口、路由、全域 CSS
├── db.py                       # Supabase CRUD（已非 SQLite）
├── ai.py / itinerary.py
├── page_itinerary.py / page_ai_suggest.py / page_shopping.py
├── tests/test_itinerary.py
├── requirements.txt
├── scout.db                    # 死檔案（SQLite 時代遺留，2026-04-04 後未寫入）
└── .streamlit/{config,secrets}.toml
```

**repo 外**：`witsper-stanley/scout-checklist`（private）—— 已上線的行程 app，三檔結構（`index.html` + `app.js` 33 KB + `styles.css`）+ `netlify.toml` + `netlify/functions/ai-parse.js`。合併後併入 Scout 的 `web/`，該 repo 退役（ADR-010）。

> ⚠️ 該 repo 內另有 `buylist.html` / `buylist-schema.sql` / `BUYLIST_STATE.md` —— 是 2026-06 時代的 buylist tracer bullet 複本，早已過時，合併時刪除。

### 3.3 資料模型（Data Model）

#### 行程側 — Supabase 專案 `uarkccyqcqvgxukjcrey`（Chia 的）

DDL SSOT：`supabase_schema.sql`（冪等，可安全重跑）。Streamlit 與 scout-checklist **共用這同一份資料**。

**trips（旅程）**
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| username | TEXT | 建立者（**不叫 `user`**，避開 PostgreSQL 保留字） |
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
| day_number | INTEGER **nullable** | 第幾天；**NULL = 候選中**（尚未排入某天） |
| name | TEXT | 景點/餐廳名稱 |
| category | TEXT | restaurant/hotel/attraction/shopping/transport/other |
| start_time | TEXT **nullable** | 'HH:MM'（用 text 不用 time，避免回傳 HH:MM:SS 解析錯誤） |
| duration_minutes | INTEGER | 停留分鐘數 |
| location | TEXT | 地點/店名 |
| address | TEXT | 地址/Google Map |
| booking_ref | TEXT | 預約編號 |
| notes | TEXT | 備註 |
| source | TEXT | manual / ai |
| source_id | BIGINT | 來源項目 id |
| sort_order | INTEGER | 排序 |
| **confirm_required** | BOOLEAN | 確認清單軸一：必須確認(t) / 可以彈性(f) |
| **is_confirmed** | BOOLEAN | 確認清單軸二：已確認(t) / 未確認(f) |

**trip_adjustments（調整紀錄）**
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| trip_id | INTEGER FK | CASCADE 刪除 |
| adjusted_at | TEXT | 調整時間 |
| instruction | TEXT | 操作說明 |
| items_changed | TEXT | JSON 陣列 |

**wishlist** — Streamlit 購物模組用；已被 buylist 的 `buylist_items` 完全取代，隨 Streamlit 退役而作廢。

#### 購物側 — Supabase 專案 `kdmmjlaajqxjmiahfvos`（Stanley 的）

DDL SSOT：`buylist/buylist-schema.sql`

- **`buylist_items`**（13+ 欄）：name / category / price / urgency（需要·想要·再看看）/ availability（台灣易·需國外·稀有）/ status（pending·bought）/ starred / quantity / tag（情境標籤）/ actual_price（實付）/ link / recurring_cost / added_by / created_at
- **`buylist_budget`**：月預算 + `last_cleared`（月初自動清上月已買的月份標記）
- **`sauces`**（辣醬庫）：name / url / spiciness / aroma / cp / repurchase / added_by / created_at

三張表皆 RLS 全開 + 啟用 Realtime。

> ⚠️ 該專案是免費方案，會自動暫停；DDL 或使用前先確認未被 pause。

### 3.4 外部服務與 API

| 服務 | 用途 | 金鑰放哪 |
|------|------|---------|
| Supabase `uarkccyqcqvgxukjcrey`（Chia 的） | 行程資料（trips / itinerary_items / trip_adjustments / wishlist） | publishable key 寫死在前端，設計上即公開 |
| Supabase `kdmmjlaajqxjmiahfvos`（Stanley 的） | 購物資料（buylist_items / buylist_budget / sauces） | 同上 |
| Google Gemini API | 行程：AI 匯入（貼文字解析）／購物：貼連結抽名稱價格／Streamlit：AI 生成行程 | 行程側在 **Netlify 環境變數**（不外露）；購物側仍在前端 `config.js`（故公開站隱藏該功能） |
| Netlify | 靜態託管 + Functions（AI proxy） | — |

### 3.5 環境變數

- **Netlify 站台環境變數**：`GEMINI_API_KEY`（必要）、`GEMINI_MODEL`（選用，預設 `gemini-2.5-flash`）
- **`buylist/config.js`**（gitignored）：`window.BUYLIST_CONFIG.GEMINI_API_KEY` / `GEMINI_MODEL`
- **`scout-checklist/config.js`**（gitignored）：`window.SCOUT_CONFIG`，可覆蓋 Supabase 連線；Gemini 金鑰已改走 Function，前端不再需要
- **`.streamlit/secrets.toml`**（gitignored，Streamlit 用）：`SUPABASE_URL` / `SUPABASE_KEY` / `GEMINI_API_KEY`

### 3.6 關鍵模式與慣例

**靜態 web app（現行）**
- **無 build step**：改完檔案重整瀏覽器就是新版；本機用 `run.bat` / `run.command` 起 http server（不用 `file://`，連雲端不可靠）
- **CSS 變數**：`:root` 定義 Scout CIS 米色系（`--bg:#F5F0EA`、`--card:#FFFFFF`…），配色 SSOT 是 `scout_cis.html`
- **DOM id 前綴**：購物側一律 `bl-`，行程側合併後一律 `ck-`（避免同頁撞名）
- **JS 隔離**：各模組包 IIFE `"use strict"`，不外洩全域
- **狀態列**：`setStatus(訊息, 'err'|'ok')` —— **失敗一律顯示紅字，不靜默失敗**
- **AI 金鑰**：走 Netlify Function proxy，前端不接觸金鑰（行程側已是，購物側待改）
- **DDL**：一律冪等（`create table if not exists` / `add column if not exists`），可安全重跑

**Streamlit（待退役）**
- **路由**：`st.session_state["page"]` + `app.py` 底部 if/elif 分派
- **AI 呼叫**：各頁面自組 prompt，`ai.py` 只負責呼叫 + 503 重試
- **按鈕 key 命名**：`st-key-[name]` 對應 CSS 選擇器

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
- **狀態：** **Superseded by ADR-010**（2026-08-01，Streamlit 退役、改為靜態 web app）
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
- **狀態：** **Superseded by ADR-007**（已遷移至 Supabase；`scout.db` 為遺留死檔案）
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

### ADR-007: 資料庫從 SQLite 遷移至 Supabase（PostgreSQL）

- **日期：** 2026-06（實際日期無紀錄，反推自 `db.py` 與 `supabase_schema.sql`）
- **狀態：** Accepted — **Supersedes ADR-004**
- **相關方：** Stanley（反推自程式碼；context.md 在此期間未被維護，故當時未記錄）

**情境（Context）:**
ADR-004 當時已寫明 SQLite 的缺點：「不適合多人同時寫入；檔案式資料庫部署到雲端需額外處理」，並留下待辦「若日後部署到雲端，需評估 db 持久化方案」。當專案要讓兩人同時使用、且要有能在手機瀏覽器打開的網頁版時，這個限制變成硬阻擋——網頁前端無法讀取伺服器上的 SQLite 檔案。

**考慮過的選項:**
1. **繼續用 SQLite + 找持久化方案** — 例如 Streamlit Cloud 掛外部磁碟、或 LiteFS 之類
   - 優點：不用改資料層程式碼
   - 缺點：仍然只有 Streamlit 能存取；純前端網頁版無解
   - 為什麼沒選：擋住「靜態網頁版 + 兩人共用」這個方向
2. **Firebase** — checklist 網頁版最初的選擇
   - 為什麼沒選：見 ADR-008，最終也遷離
3. **Supabase（PostgreSQL）** — 最終採用

**決策:**
遷移至 Supabase。`db.py` 改用 `supabase.create_client()`，連線資訊從 `.streamlit/secrets.toml` 讀取。schema 以 `supabase_schema.sql` 為 SSOT，所有 DDL 寫成冪等（`create table if not exists` / `add column if not exists`），因為 Chia 已在 Supabase 介面手建部分表格，同一份必須能安全重跑。遷移時避開 PostgreSQL 保留字：`trips.user` → `trips.username`。

**預期後果:**
- 正面：資料脫離單機檔案；PostgREST 讓純靜態前端可直接讀寫，不需要自有後端；兩人共用成立
- 負面：多了一個外部相依與其可用性風險（免費方案會自動暫停）；anon key 攤在前端（見 ADR-013）
- 需要後續處理的事項：`scout.db` 成為死檔案，應刪除；context.md 的技術棧描述失效（本次 2026-08-01 才補正）

**分歧與轉折紀錄:**
此決策發生在 context.md 停止維護的期間（2026-04-18 ～ 2026-08-01），過程未被記錄，本則為事後從程式碼反推補記。**這段空窗本身是教訓**：ADR-004 已預告的風險真的發生了，但決策過程沒留下紀錄。

---

### ADR-008: 行程確認清單獨立為靜態網頁版，並從 Firebase 改為 Supabase

- **日期：** 2026-06（反推自 `witsper-stanley/scout-checklist` commit `122f55d`、`8cd65b3`）
- **狀態：** Accepted
- **相關方：** Stanley / Chia

**情境（Context）:**
「出發前哪些事還沒確認」這個需求，Streamlit 版不適合——Chia 要能在手機上隨時打開、也要能把連結分享出去。最初做成 Firebase 版（本機 `scout-checklist/` 資料夾裡那份，remote 指向 `CHIAHSIN-tech/scout-checklist`）。

**考慮過的選項:**
1. **做進 Streamlit** — 為什麼沒選：手機體驗差、要跑伺服器、無法分享連結
2. **Firebase 靜態網頁版** — 初始實作
   - 為什麼沒選：與 ADR-007 的 Supabase 方向不一致，會變成兩套後端技術
3. **Supabase 靜態網頁版** — 最終採用

**決策:**
改寫資料層 Firebase → Supabase，直接 `fetch` 打 PostgREST（**不載 supabase-js**，省一個相依）。與 Streamlit 共用同一個 Supabase 專案與同一張 `itinerary_items` 表，因此兩邊看到的是同一份資料。同步機制刻意用手動「↻ 重新整理」而非 Realtime（省成本）。舊 Firebase 版停用。

**預期後果:**
- 正面：手機可用、可分享連結、與 Streamlit 資料互通
- 負面：**版本混淆風險**——本機 `scout-checklist/` 那份舊 Firebase 版仍存在，且 remote 指向不同帳號，容易誤認為現行版（`spec-scout-app-merge.md` v1 就差點踩到）
- 需要後續處理的事項：刪除本機舊 Firebase 版

**分歧與轉折紀錄:**
無紀錄（發生在 context.md 空窗期）。

---

### ADR-009: BuyList 採單檔 vanilla HTML + Stanley 自己的 Supabase 專案

- **日期：** 2026-07-05 前後（反推自 `buylist/BUYLIST_STATE.md` §4）
- **狀態：** Accepted
- **相關方：** Chia（出 spec）/ Stanley（執行端調整）

**情境（Context）:**
Chia 的 spec（`specs/buylist-handoff.md`）原本指定 Vue + Vite + Firebase、開全新獨立專案。Stanley 在執行端做了三處調整，理由記在 `BUYLIST_STATE.md` §4。

**考慮過的選項:**
1. **Vue + Vite（spec 原案）** — 為什麼沒選：tracer bullet 不需要框架；有 build step 就不好分享
2. **Firebase（spec 原案）** — 為什麼沒選：ADR-007 已選 Supabase，統一一個後端技術，且要 SQL 查詢力、不鎖定
3. **全新獨立 repo（spec 原案）** — 為什麼沒選：Scout 是 private 且 Chia 已是協作者，不需要多開 repo
4. **單檔 vanilla HTML + Scout repo 的 `buylist/` + Supabase** — 最終採用

**決策:**
單檔 vanilla HTML/CSS/JS（無 build），放在 private Scout repo 的 `buylist/`。後端用 **Stanley 自己的 Supabase 專案 `kdmmjlaajqxjmiahfvos`**，而非 Scout 既有的 `uarkccyqcqvgxukjcrey`——**關鍵理由：Scout 那個專案是 Chia 的，Stanley 沒有後台權限，無法自己建表改欄位。** 用 supabase-js + Realtime `postgres_changes` 達成兩人即時同步。

**預期後果:**
- 正面：零 build、好分享、Stanley 能自管 schema、即時同步達成 spec 第一 Must
- 負面：**專案內出現第二個 Supabase 專案**（見 ADR-012）；單檔隨功能長大到 584 行 / 42 KB
- 需要後續處理的事項：合併時需把單檔拆成 `.js` / `.css`（見 ADR-010）

**分歧與轉折紀錄:**
Stanley 有意識地覆寫了 spec 的三項技術指定（框架、後端、落點），理由均記在 `BUYLIST_STATE.md` §4 的「與 spec 差異 / 理由」欄。另外 spec 要求「一次一步、做完停、等 Chia 檢查」，Stanley 選擇 one-shot 全做，同樣為有意識覆寫。

---

### ADR-010: 收斂為單一靜態雙 Tab web app，Streamlit 退役

- **日期：** 2026-08-01
- **狀態：** Accepted — **Supersedes ADR-003**
- **相關方：** Stanley（拍板）/ Claude Code（調查與提案）/ Chia（原合併需求提出者，2026-07-25）

**情境（Context）:**
Stanley 提問「Scout 放 Cloudflare + Supabase 是不是過度工程，換 Netlify 會不會比較乾淨」。調查後發現：(a) 專案內根本沒有 Cloudflare，實際是 Netlify + GitHub Pages 的混合；(b) **真正的複雜度不在 infra，而在同一批需求被做了三次**——Streamlit app（從未部署）、buylist 靜態 app（Netlify）、scout-checklist 靜態 app（Netlify），三個部署位置、兩套技術棧、功能重疊。Chia 早在 2026-07-25 就提出要把後兩者合併成雙 Tab（`spec-scout-app-merge.md` v1）。

**考慮過的選項:**
1. **只做 infra 搬家（Netlify ↔ Cloudflare）** — 優點：改動小
   - 為什麼沒選：零收益。靜態單頁 app 對兩家託管商功能等價，搬家不解決任何實際問題
2. **砍掉 Supabase 改用更輕的東西** — 為什麼沒選：Supabase 正是「不用寫後端就有兩人即時同步」的原因，砍掉等於砍掉核心價值或自己寫後端，只會更複雜。用不到的功能（Auth/Storage/Edge Functions）不增加負擔
3. **保留 Streamlit 作為「管理後台」，靜態版只讀** — 優點：不用補旅程管理 UI
   - 為什麼沒選：兩套並存的維護成本正是問題本身；且 Streamlit 從未部署，要用得先本機起服務
4. **合併 buylist + checklist 為單一雙 Tab 靜態 app，Streamlit 退役** — 最終採用
5. **合併後外層做「首頁卡片選單」** — Stanley 最初的描述
   - 為什麼沒選：兩邊各自內部已有 tab，外面再包首頁＝三層導覽，而最外層只有兩個選項，手機上是純負擔。改為**頂部雙 Tab**

**決策:**
執行 `spec-scout-app-merge.md` v2。合併只動介面層（一個外殼 + 頂部雙 Tab + 作用域隔離），**不打通兩邊資料**（Stanley 明確選「A. 純介面」）。落點為 Scout repo 的 `web/`，`witsper-stanley/scout-checklist` repo 退役，三個 repo 收斂成一個。Streamlit 停止開發、不刪檔、標作廢。Appetite：一個週末。

因 checklist 的 `?trip=<trip_id>` 是唯一身分機制、而 `trip_id` 只能從 Streamlit 建立旅程取得，**退役的前置條件是補上最小旅程管理**（建立旅程／切換旅程／手動新增項目）。若不補，Streamlit 退役後將無人能開新旅程，且 Stanley 對 Chia 的 Supabase 沒後台權限、無法手動 insert。

**預期後果:**
- 正面：一個網址、一套技術、一個 repo、一個部署平台；buylist 的 AI 功能可藉 checklist 已有的 Function proxy 在公開站復活
- 負面：**Streamlit 獨有功能沒有替代品**——AI 生成行程（多輪問答）、行程項目欄位編輯／排序／跨天移動、旅程刪除。本次刻意不補（spec §5.4、R2）
- 負面：合併後一個網址外流＝兩邊資料同時外流（風險集中，見 ADR-013）
- 需要後續處理的事項：`scout.db` 刪除；`scout-checklist` repo 內過時的 buylist 複本刪除；Netlify 站台命名決定（spec R1）

**分歧與轉折紀錄:**
Stanley 的原始提問假設「Scout 放在 Cloudflare」，經查證為誤記，實際無 Cloudflare。Claude Code 指出真正的問題不在託管平台選擇而在架構分裂，Stanley 接受並將範疇從「換託管商」改為「收斂架構 + Streamlit 退役」。導覽形態上，Stanley 原本描述「首頁進去再到不同功能」，Claude Code 以「三層導覽只為兩個選項」為由建議改頂部雙 Tab，Stanley 採納。AI 生成行程是否救回一題，Stanley 未答，暫定不救（spec §5.4）。

---

### ADR-011: 部署採 Netlify，AI 金鑰以 Netlify Function 代理

- **日期：** 2026-07-26（buylist 上線）／2026-07-26（checklist 改 Function proxy，commit `9bf6a62`）
- **狀態：** Accepted
- **相關方：** Stanley

**情境（Context）:**
兩件事同時要解：(a) app 要能在手機瀏覽器打開，需要公開網址（`BUYLIST_STATE.md` §4.1 Chia 拍板「buylist 要上手機」）；(b) 前端直呼 Gemini 就得把金鑰放進前端檔案，公開部署等於金鑰外洩。

**考慮過的選項:**
1. **Cloudflare Tunnel** — 從本機 private 環境開洞出去，程式碼仍 private
   - 為什麼沒選：要求本機常開；靜態託管更簡單
2. **GitHub Pages** — 免費、直接從 repo 出
   - 為什麼沒選：**不能跑 serverless function**，AI 金鑰問題無解
3. **Netlify** — 最終採用

**決策:**
用 Netlify（Stanley **個人**帳號、免費方案）。金鑰問題以 Netlify Function 代理解決：`netlify/functions/ai-parse.js` 從 `process.env.GEMINI_API_KEY` 取金鑰呼叫 Gemini，前端只打 `/.netlify/functions/ai-parse`，完全不接觸金鑰。

buylist 側當時未採此法，改用權宜方案：部署版 `config.js` 帶空字串，前端偵測無金鑰就**隱藏**「🔗貼連結帶入」（commit `5f49665`）——功能在公開站不可用。ADR-010 的合併將改為與 checklist 一致的 proxy 模式。

**預期後果:**
- 正面：手機可用；Gemini 金鑰不外露；Functions 讓純靜態站也能有「一點點後端」
- 負面：buylist 目前是**手動 drag-and-drop 部署**，已造成版本漂移（公開站至今仍是舊版、沒有辣醬 tab）。合併時改為 Git 連動自動部署
- 需要後續處理的事項：⚠️ **絕不使用公司（witsper）帳號**，僅用個人帳號

**分歧與轉折紀錄:**
`BUYLIST_STATE.md` §4 原記「手機要用再改成公開網址（Cloudflare 從 private 出）」，2026-07-25 被 §4.1 supersede 為「要上手機」，最終落地是 Netlify 而非 Cloudflare。

---

### ADR-012: 不合併兩個 Supabase 專案

- **日期：** 2026-07-25
- **狀態：** Accepted
- **相關方：** Chia（確認）/ Stanley

**情境（Context）:**
合併成單一 app 後，同一頁會同時連兩個 Supabase 專案（購物連 Stanley 的、行程連 Chia 的）。直覺上「一個 app 一個資料庫」比較乾淨，是否該合併？

**考慮過的選項:**
1. **合併成一個 Supabase 專案** — 優點：概念單純
   - 缺點：兩邊無共用資料表、無跨表查詢，合併只有遷移成本、沒有功能收益；且 Stanley 對 Chia 的專案沒後台權限，合過去就失去自管 schema 的能力（這正是 ADR-009 分開的原因）
   - 為什麼沒選：純成本、零收益
2. **維持兩個專案** — 最終採用

**決策:**
不合併。若未來真出現「這趟行程要買的東西」這類跨模組需求，用**情境標籤**（`buylist_items.tag`，已實作）之類的輕量欄位表達，不合併資料庫。

**預期後果:**
- 正面：各自可獨立演進；Stanley 保有購物側的完整自管權
- 負面：兩個免費方案專案都可能自動暫停，要各自留意；合併後的 app 有兩套不同的存取模式（supabase-js + Realtime vs 裸 fetch + 手動重新整理），行為不一致
- 需要後續處理的事項：無

**分歧與轉折紀錄:**
Chia 提出合併需求時同時確認「資料不合併」，未出現分歧。

---

### ADR-013: 存取控制＝網址即憑證，不做帳號系統

- **日期：** 2026-07（反推自 `supabase_schema.sql` §6 與兩邊 README）
- **狀態：** Accepted — 延續並放大 ADR-006
- **相關方：** Stanley / Chia（均已明示接受風險）

**情境（Context）:**
ADR-006 決定 Streamlit 不做密碼登入（僅下拉選使用者），當時的前提是「信任環境、本機使用」，並留下待辦「若日後公開部署，需重新評估」。2026-07 兩個 app 都公開部署了，這個待辦到期。

**考慮過的選項:**
1. **導入 Supabase Auth** — 優點：真實存取控制
   - 為什麼沒選：兩人私用工具，登入流程的摩擦大於收益
2. **網址即憑證** — 最終採用

**決策:**
不做帳號系統。RLS 全開（`supabase_schema.sql` 用「停用 RLS + GRANT anon」的版本 A），publishable anon key 直接寫死在前端原始碼中——這在 Supabase 靜態網站是常見做法，真正的存取邊界是**網址本身**：
- 購物：知道 `shoppingtool.netlify.app` 就能讀寫全部購物資料
- 行程：知道網址**且**知道 `?trip=<trip_id>` 才能讀寫該趟旅程

**預期後果:**
- 正面：零摩擦，分享連結即分享存取權
- 負面：**連結外流 = 資料外流**，任何人可讀／寫／刪。已由 Stanley 與 Chia 明示接受（`BUYLIST_STATE.md` §4.1）
- 負面：ADR-010 合併後兩邊共用一個網址，**風險集中**——一個網址外流等於兩邊資料同時外流。合併前需再次確認接受（`spec-scout-app-merge.md` R3）
- 需要後續處理的事項：若哪天要給第三人看，需重新評估

**分歧與轉折紀錄:**
ADR-006 當時就寫明「若日後公開部署，需重新評估」。實際公開時的處理是「評估後接受風險」而非「加上保護」，屬有意識的取捨，不是遺漏。

---

### ADR-014: Scout repo 所有權轉移給 Chia，部署由她自主operate

- **日期：** 2026-08-01
- **狀態：** Accepted（等待 Chia 接受轉移請求）
- **相關方：** Stanley（拍板）/ Claude Code

**情境（Context）:**
ADR-010 的合併要接上 Netlify 自動部署時卡住：Chia 的 Netlify 帳號連的是 `CHIAHSIN-tech` 這個 GitHub 帳號，而 `Scout` 是 `witsper-stanley` 名下的 private repo，因此不出現在 Netlify 的 repo 選單裡。Stanley 明確指出**未來後台的主要使用者是 Chia**，而現行結構讓每一次基礎設施異動都必須由他授權，是所有權錯位而不只是步驟麻煩。

**考慮過的選項:**
1. **維持現狀，Stanley 安裝一次 Netlify GitHub App** — 把 App 裝到 `witsper-stanley` 並授權 `Scout`
   - 優點：改動最小；且這是一次性成本，裝完 Chia 在 Netlify 上就能自主
   - 缺點：所有權仍錯位。未來換部署平台、加任何需要 repo 授權的服務，都會再卡 Stanley 一次
   - 為什麼沒選：只解決這一次，沒解決結構
2. **建立 GitHub organization 共同持有** — Scout 轉進 org，兩人都是 owner
   - 優點：長期最乾淨，誰都不是瓶頸，之後加人也容易
   - 缺點：建 org 是網頁流程（Claude Code 做不到），仍需有人手動操作；比選項 3 多一步
   - 為什麼沒選：Stanley 選了更直接的選項 3
3. **轉移給 `CHIAHSIN-tech`** — 最終採用

**決策:**
把 `witsper-stanley/Scout` 轉移給 `CHIAHSIN-tech`，Stanley 降為協作者。理由：Chia 的 Netlify 已連著該 GitHub 帳號，轉移後 repo 直接出現在選單，**不需要安裝任何 GitHub App**，剩餘所有部署步驟她都能自己完成。

轉移請求已於 2026-08-01 透過 API 送出。轉移給**使用者帳號**需要對方按接受才生效，接受前 repo 仍在 `witsper-stanley` 名下。給 Chia 的操作說明寫在 `for-chia-deploy.md`。

**預期後果:**
- 正面：部署與後台操作的瓶頸從 Stanley 移除，與「Chia 是主要後台使用者」的事實一致
- 負面：Stanley 失去 repo 擁有權，日後若要取回需再走一次轉移（且需他接受）
- 負面：Stanley 依賴 Chia 保留他的協作者權限；轉移後需確認他仍有 Admin 或 Write，否則推不了程式
- 需要後續處理的事項：轉移生效後更新本機 git remote（GitHub 會自動轉址，但明確指向新位址較清楚）；`BUYLIST_STATE.md` §4「落點：private 的 Scout repo」的敘述需補註所有權已變更

**分歧與轉折紀錄:**
Claude Code 一開始把「Netlify 選單顯示 CHIAHSIN-tech」誤判為帳號混用的風險，並援引 Stanley 稍早「這個 repo 是個人的，不要跟其他東西繞在一起」的說法提出疑慮。Stanley 更正：使用 Chia 的帳號是刻意的。此更正也讓真正的問題浮現——不是帳號用錯，而是所有權與實際操作者不一致。ADR-009 當初把 buylist 放進 Scout repo 的理由之一是「Chia 是 Scout 協作者也拿得到」，該前提在本次轉移後反轉：現在是 Stanley 成為協作者。

---

<!-- 往後的 ADR 依序往下寫 -->

---

---

### ADR-015: 兩個 Tab 的顏色 token 只求「同名同值」，不抽成共用樣式層

**日期：** 2026-08-16
**狀態：** 已採納
**決策者：** Chia（2026-08-08 拍板方向）／Stanley 端執行

**背景：**
合併成雙 Tab 後，`#panel-shop` 與 `#panel-trip` 各自定義了一整套 CSS 變數（buylist.css / checklist.css 的檔頭），其中 `--muted`、`--green`、`--amber` 三個名字**在兩邊指不同顏色**（例如 `--muted` 一邊 `#6B6558`、一邊 `#A8A298`）。

真正的成本不是「看起來不像同一個 app」，而是**日後任何一次改色，改的人會以為兩邊都改到，實際只改到一半，而且不會有任何錯誤訊息**。這個缺陷會隨每次改動放大。

**選項：**
1. 把兩邊的 token 上移到 `shell.css` 成為單一來源
2. 維持兩份定義，但要求同名一律同值
3. 不處理

**決策：** 選 2。並補一支 `scripts/check-style.mjs --token-parity` 把這條規則變成可執行的檢查。
統一時**以購物 Tab 為準，不反向修改購物端**：行程端主色 `--green`（`#3D6B54`）改名 `--brand`、`--green-line` 改名 `--green`、`--sub`→`--muted`、原 `--muted`→`--faint`。字體同理全站統一 `Noto Sans TC`，襯線體移除。

**理由：**
選項 1 的改動範圍過大（兩個 app 的全部樣式規則都要重新對照命名），而它要解決的問題——「同名不同值」——選項 2 就能解決。抽共用層是更乾淨的終局，但不是現在該付的代價。

**代價 / 已知風險：**
- 兩份 token 定義仍然存在，仍可能各自漂移。**只有在有人執行 `scripts/check-style.mjs` 時才會被抓到**——目前沒有 CI、沒有 pre-commit hook。
- 同值不同名的情況（`--text` vs `--ink`）沒有處理，不構成上述缺陷，但也還在。
- `--amber` 對齊購物端色票後，當文字色對比只剩約 2.3:1，因此另立 `--warn-ink`（值取自購物端既有的 `--red`）給文字用。這不是新增顏色，是既有色票換個語意名字。

**關聯：** ADR-010（單一靜態 app、無 build step）、`specs/TASK-ui-unify-and-calendar-maps-export.md`、`DECISIONS.md`

---

### ADR-016: 新增 Python MCP server，讓 Claude 直接讀寫 Scout 資料

**日期：** 2026-08-16
**狀態：** 已採納
**決策者：** Stanley

**背景：**
兩人用 Claude 討論旅程時，Scout 的資料只存在網頁介面裡，Claude 看不到也改不了，
規劃產出要靠人工在對話與網頁之間抄寫。

**決策：** 新增 `mcp-server/`（Python + 官方 MCP SDK，stdio transport），
以純 PostgREST HTTP client 讀寫，與網頁前端走同一條 REST 路、同一把 publishable key。

**與 ADR-010 的關係（重要）：**
ADR-010 讓 Streamlit 退役、收斂成單一靜態 web app，等於把 Python 從產品面移除。
本 ADR **重新引入 Python，但只在開發工具面**——MCP server 在兩人各自的電腦上跑，
不部署、不是產品的一部分、不影響「產品是單一靜態 app」這個決策。
根目錄既有的 `requirements.txt`（Streamlit 時代）刻意不動，`mcp-server/` 自帶 pyproject。

**與 ADR-012 的關係：**
行程與購物分屬兩個 Supabase 專案且不合併，所以 MCP server 需要**四個**連線環境變數
（`SCOUT_SUPABASE_URL/KEY` ＋ `SCOUT_BUYLIST_URL/KEY`）。原規格假設只有一個專案，
執行時修正。同時發現 `supabase_schema.sql` 的 `wishlist` 表是 Streamlit 遺留，
**現行購物 Tab 讀的是另一個專案的 `buylist_items`**，購物工具因此改接後者。

**寫入面刻意很窄：**
沒有任何刪除工具，而且不是靠工具自律——`rest.py` 的動詞允許清單是正面表列的
`frozenset({"GET","POST","PATCH"})`，清單外的動詞在組出請求前就被擋下。
理由：agent 誤刪的是兩人真實的旅程資料，且 ADR-013 的安全姿態下沒有帳號層保護。
要刪除請到網頁介面，那裡有二次確認。

**代價 / 已知風險：**
- publishable key 在手即可全讀寫（ADR-013 既有姿態，本版不改）。「無刪除」是本 server
  的自我限制，不是資料庫層強制——任何人拿 key 直接打 REST 仍可刪。
- 四個環境變數容易對調（行程的 key 填到購物那組）。錯誤訊息有針對這點寫提示。

**關聯：** ADR-010、ADR-012、ADR-013、`specs/spec-scout-mcp-server.md`、`ACCEPTANCE-mcp-server.md`

## 5. 開發日誌

> **只增不改（但會週期性壓縮舊內容）。**
> **倒序排列：最新在最上面。**

<!-- LOG_INSERTION_POINT -->

### [2026-08-16] 新增 Scout MCP server

**類型：** 進度
**關聯 ADR：** ADR-016（新增）、ADR-010／012／013
**關聯 MoSCoW：** 工具鏈（新面向，不在原 MoSCoW 內）

`mcp-server/` 落地，八個工具（七個 Must ＋ create_trip）。commit `9e92ec9`。

偵察時撞到規格的一個錯誤前提：規格假設「與網頁前端讀寫同一個 Supabase」，
但行程與購物本來就分屬兩個專案（ADR-012），且規格指名的 `wishlist` 表是 Streamlit
遺留、現行購物 Tab 不讀它——照字面實作會做出沒人看得到的工具。已拍板改接 `buylist_items`，
環境變數從兩個變成四個。此為 ADR-016 的一部分。

**驗收狀態誠實記錄：** AC-5／AC-6／AC-7 由命令驗證通過（79 項測試，全程無網路）。
**AC-1～AC-4 尚未驗**——開發環境連不到 Supabase，且不該拿兩人的正式資料庫做寫入測試。
待在真實 Claude Code 環境跑過，做法寫在 `ACCEPTANCE-mcp-server.md`。

過程中修掉兩個「測試綠但其實錯」：fake Supabase 在 POST 丟掉 null 欄位（不忠實於真
PostgREST）；以及 insert 送出明確 null 會蓋掉資料表 DEFAULT。後者只有在 fake 修正後才浮得出來。

---

### [2026-08-16] 清掉 specs/ 裡最後兩份待執行規格

**類型：** 進度
**關聯 ADR：** ADR-015（新增）、ADR-010
**關聯 MoSCoW：** Must — 行程編輯／刪除、視覺統一＋匯出

盤點 `specs/` 後發現只有兩份真的還開著，其餘不是已實作但狀態沒改，就是早已作廢。兩份都執行完：

1. **行程 Tab 補回編輯與刪除**（`spec-itinerary-restore-edit-delete.md`，commit `e2ba895`）。
   卡片加展開式編輯表單（九個欄位＋「第幾天」＝跨天移動），新增 `deleteItem` / `deleteTrip`——
   在此之前整份 `checklist.js` **沒有任何 DELETE**。刪旅程採「先刪項目再刪旅程」，
   因為珈欣的 Supabase 有沒有設 CASCADE 無法從前端確認，先刪子表在兩種情況下都正確。
   AC-1～AC-9 以本地假後端逐條驗過（Supabase 在開發環境連不到，且不應拿正式資料庫做刪除測試）。

2. **雙 Tab 視覺統一 ＋ 匯出 Google 日曆／Maps**（`TASK-ui-unify-and-calendar-maps-export.md`）。
   見 ADR-015。新增 `web/export-formats.js`（純函式，瀏覽器與驗證腳本共用同一份實作）
   與 `scripts/` 下兩支只用 Node 內建模組的驗收腳本。A1–A10 全 PASS，無項目被砍。
   兩支腳本都反向注入違規測試過；其中抓到自己寫鬆的一條斷言（拿實作常數當預期值），已改硬寫。

**順帶清掉的文件債：** 刪除作廢的辣醬庫 Vue 規格與其 kickoff（2026-07-26 已改成 buylist 的一個 tab）；
六份早已上線卻仍標 `draft` 的規格補上 `done` 與落地 commit；`specs/README.md` 索引從只有 001 一列補齊到全部。

**產出物：** `ACCEPTANCE.md`、`DECISIONS.md`、`KNOWN_ISSUES.md`、`for-chia-itinerary-edit-delete.md`

---

### [2026-08-01] 架構調查 → 決定收斂為單一靜態 app、Streamlit 退役

**類型：** 決策
**關聯 ADR：** ADR-010（主）、ADR-007／008／009／011／012／013（補記）
**關聯 MoSCoW：** Must — 合併成單一雙 Tab app

Stanley 問「Scout 放 Cloudflare + Supabase 是不是過度工程，換 Netlify 比較乾淨？」。查證後發現前提有誤：專案裡沒有任何 Cloudflare，實際是 Netlify（buylist、checklist）+ 一個從未部署的 Streamlit。指出真正的複雜度不在託管平台，而在**同一批需求被做了三次**；Stanley 接受，把題目從「換託管商」改成「收斂架構」，並拍板 Streamlit 退役、純介面合併、頂部雙 Tab、Appetite 一個週末。

順帶解除了 `spec-scout-app-merge.md` v1 的 blocker：取得 `witsper-stanley/scout-checklist` 現行原碼，發現它跟 spec 假設差很多（三檔不是單檔、Netlify 不是 GitHub Pages、已有 Function proxy、不用 supabase-js），據此把 spec 改寫為 v2 並補上實測的命名衝突清單（只有 3 個 CSS 變數真衝突，JS 一包 IIFE 全解）。

發現的關鍵依賴：**Streamlit 是目前唯一能建立旅程的地方**，退役前必須補最小旅程管理，否則 checklist 的 `?trip=` 拿不到 id、Stanley 又沒有 Chia 的 Supabase 後台權限。

---

### [2026-04-18 ～ 2026-08-01] 時期摘要 — context.md 空窗期

**類型：** 其他

這段期間 context.md **完全未被維護**，但專案發生了根本性的架構變化。以下為事後從 git history 與程式碼反推的摘要（細節見對應 ADR）：

- **資料層整個換掉**：SQLite → Supabase（ADR-007）。`db.py` 改用 `create_client`，`scout.db` 成為死檔案。
- **主力開發從 Streamlit 移到靜態網頁**：checklist 網頁版（ADR-008）、buylist（ADR-009）陸續完成並上線，功能豐富度早已超過 Streamlit 對應模組。
- **首次公開部署**：兩個 app 都上 Netlify，並用 Netlify Function 解掉 AI 金鑰外露問題（ADR-011）。
- **存取控制的待辦到期並結案**：ADR-006 留下的「公開部署需重新評估」，實際處理是評估後接受風險（ADR-013）。

**教訓：** ADR-004 已預告「檔案式資料庫部署到雲端需額外處理」，這個風險真的發生了、也真的被解決了，但**整個決策過程沒有留下紀錄**，只能事後反推。CLAUDE.md 第 1 節要求每個 session 讀 context.md——但沒有機制保證有人回寫。

---

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

### 6.1 仍然反推不出來的資訊

- 問題陳述的「為什麼值得解決」細節
- JTBD 陳述（合併 app 的 JTBD 已寫在 `spec-scout-app-merge.md` §2，但整個 Scout 的還沒有）
- 成功標準（具體指標）
- ADR-005 從 Claude API 切到 Gemini 的實際理由

### 6.2 待決定

- **Netlify 站台命名**：合併後沿用 `shoppingtool.netlify.app`（名字不再貼切但書籤不變）還是改名（舊網址失效、要重發連結給 Chia）？見 `spec-scout-app-merge.md` R1。
- **AI 生成行程要不要救**：Streamlit 的多輪問答 → Gemini 產出整份行程（`page_ai_suggest.py`），合併版沒有替代品。本週末刻意不補，之後再議。見 spec R2。
- **測試框架**：`tests/test_itinerary.py` 只涵蓋待退役的 Streamlit 邏輯，靜態 app 完全無測試。要不要引入？

### 6.3 已知的 Bug

- **公開站版本落後**：`shoppingtool.netlify.app` 仍是舊版，沒有辣醬庫 tab。成因是手動 drag-and-drop 部署造成的漂移，合併時接 Git 自動部署解決。

### 6.4 技術債（Technical Debt）

- **同一批需求做了三次**：Streamlit / buylist / checklist 三套並存，兩套技術棧、三個部署位置。ADR-010 的合併就是在還這筆債。
- **`scout.db`**：SQLite 時代的死檔案，應刪除。
- **`scout-checklist` repo 內有過時的 buylist 複本**（`buylist.html` / `buylist-schema.sql` / `BUYLIST_STATE.md`），是 2026-06 的 tracer bullet，合併時刪。
- **本機 `scout-checklist/` 資料夾是舊 Firebase 版**，remote 指向不同帳號（`CHIAHSIN-tech/scout-checklist`），極易誤認為現行版——`spec-scout-app-merge.md` v1 就差點踩到。應刪。
- **無測試覆蓋**：`tests/test_itinerary.py` 只涵蓋已退役的 Streamlit 邏輯。靜態 app 現在有兩支驗收腳本（`scripts/check-style.mjs`、`scripts/check-exports.mjs`，只用 Node 內建模組），但它們涵蓋的是樣式 token 與匯出格式，**不是**應用邏輯，而且沒有掛進任何 CI，要有人記得跑。
- **buylist 單檔已 584 行 / 42 KB**，HTML+CSS+JS 全內聯；合併時會拆成獨立 `.js` / `.css`。
- **兩邊同步機制不一致**：購物有 Realtime、行程要手動重新整理。合併後同一頁兩種行為，使用者可能困惑。
- **context.md 曾空窗四個月**（2026-04-18 ～ 2026-08-01），期間所有架構決策都是事後反推補記。沒有機制保證有人回寫。

### 6.5 暫緩的想法（Parking Lot）

- 手機介面像素級優化（現版能用但偏桌面）— 待 Chia 出 spec
- 行程側補 Realtime（消除與購物側的行為落差）— 非小工程
- 行程項目的上移↑／下移↓ 排序 — 其餘（欄位編輯／跨天移動／刪除項目／刪除旅程）已於 2026-08-16 補回；↑↓ 因與拖曳改時間目的重疊而刻意不做
- PWA / 離線 — 與「靠 Supabase 即時同步」的既有決策衝突，明確不做
- 結構化輸出（Gemini JSON schema 強制）取代現有自寫 parse — 現況實測可用，等真的抓錯再做
- 餐廳模組、旅館模組、統計報表 — Streamlit 時代的規劃，隨 ADR-010 失效，若要做得在新架構重新設計

### 6.6 外部相依的風險

- **Supabase 免費方案會自動暫停**：兩個專案都是。DDL 或使用前先確認未被 pause（購物側 `kdmmjlaajqxjmiahfvos` 已踩過）。
- **Google Gemini API**：Streamlit 端有 503 重試；靜態 app 端失敗只顯示紅字、無重試。
- **CDN 相依**：buylist 從 jsdelivr 載 supabase-js，CDN 掛掉整個購物 tab 不能用。
- **Netlify 免費方案**：Functions 有每月執行次數上限；兩人用不會碰到，但值得知道。
- **⚠️ 帳號紀律**：Netlify 與 Supabase 一律用**個人帳號**，絕不用公司（witsper）帳號。

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

**專案內文件**
- `scout_cis.html` — 設計規範／配色 SSOT
- `specs/spec-scout-app-merge.md` — 合併工程的執行 SSOT（v2）
- `buylist/BUYLIST_STATE.md` — 購物側的接手文件
- `supabase_schema.sql` / `buylist/buylist-schema.sql` — 兩側 DDL 的 SSOT

**Supabase 專案**
- 行程（Chia 的）：`uarkccyqcqvgxukjcrey`
- 購物（Stanley 的）：`kdmmjlaajqxjmiahfvos`

**線上位置**
- 購物：https://shoppingtool.netlify.app/ （⚠️ 目前是舊版，見 §6.3）
- 行程：Netlify（`witsper-stanley/scout-checklist` repo 連動）

**外部文件**
- [Google Gemini API](https://ai.google.dev/docs)
- [Supabase PostgREST](https://supabase.com/docs/guides/api)
- [Netlify Functions](https://docs.netlify.com/functions/overview/)
- [Streamlit](https://docs.streamlit.io)（待退役）

---

*這份文件由 Claude Code 自動維護。使用者不手動編輯。*
*如發現結構問題或規則需要調整，在本檔案第 0 章更新操作手冊。*
