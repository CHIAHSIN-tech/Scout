# BuyList — Spec + 交接包（給 Stanley）

> 這一份是交給 Stanley（Claude Code 執行端）的完整交接文件：**Spec（SSOT）+ Firebase 交接資料 + 開場 Prompt**。
> ⚠️ **版控注意**：本檔的「Part 2 交接資料」含 Firebase config。若要把這份 handoff 放進 repo，**先把那段 config 移到 `.env.local`、別 commit 那段**（Firebase web apiKey 雖非機密金鑰，仍依 12-Factor 設定外部化處理）。

---

# Part 1 — Spec（status: approved）

## 0. Meta
- **Appetite（時間預算）**：不設時間上限（CHIA 決定不以時間卡範疇）。→ 範疇紀律改由 §4 的 **Won't** 把關。新點子若不在 Must/Should/Could，就進 Won't。
- **Status**：done（整個 app 完成、AC-1～AC-7 實測全綠，見 `buylist/BUYLIST_STATE.md` §5）
- **Date**：2026-06-20

## 1. Problem Statement
我和另一個人想買的東西散在各自腦袋、截圖、購物車裡，無法一起判斷「現在買划不划算（會不會爆我們的月預算）」「這東西去哪買、好不好買到」「到底是需要還是想要」。
→ 缺的不是「待買清單」，而是一份**兩人即時共用、把『想買的東西』跟『預算現實 + 取得難易 + 迫切度』擺在一起做購買決策**的清單。

## 2. Primary User + JTBD
- **User**：CHIA 與一位共用者（真人），**兩人共用同一份清單、各自在自己的裝置上即時看到與編輯**。使用情境是「日常」，不綁旅行。
- **JTBD**：
  - 當我**想到一個想買的東西**，我想要**隨手丟進共用清單並標記價格、迫切度、取得難易、本月想買還是之後再說**，這樣**兩人都能即時看到這份待決策清單**。
  - 當**我們要決定該不該買**，我想要**一眼看到「本月想買的東西加起來會不會爆預算」「這東西在哪買到」「這是需要還是衝動」「想了多久了」**，這樣就能**一起做出買 / 不買 / 之後再說的決策**。

## 3. Success Criteria
- 兩人會**真的持續用**它。
- 一人新增 / 改動，另一人裝置上**即時（數秒內）看到**，不需重整。
- 看一眼就能回答「本月再加買這項會不會爆預算」，不需心算或翻記帳 app。
- 不再發生「沒貨了才發現某個想買的東西其實很難買到」。

## 4. MoSCoW
- **Must（沒有就失敗）**
  - 兩人共用同一份清單，**即時同步**（一端改，另一端數秒內更新，免重整）。← 主軸
  - 新增 / 刪除想買物品（必填：名稱、預估價格）。
  - **迫切度（Urgency / Need vs Want）**：三選一標籤（需要 / 想要 / 再看看）。
  - **取得難易度（Accessibility）**：台灣容易 / 需國外 / 稀有難找。
  - **本月想買 / 之後再說** 標記。
  - 設定「月預算（Monthly Budget）」數字——**兩人共用一個**。
  - 自動加總**「本月想買 且 未購」的項目總價**，與月預算比較，明確顯示剩餘額度 / 超支多少（爆預算提示）。
  - 標記「已買」→ 該項移出未購總價（**不留帳**）。
  - **冷卻期（Cooling-off）**：自動記錄加入時間，顯示「想買了 N 天」（不需手動填）。
- **Should**
  - 物品可加「連結 / 備註」欄位。
  - 顯示「誰加的」。
  - 2×2 視覺化（價格高低 × 迫切度，或 × 取得難易）。
- **Could**
  - 物品分類、排序 / 篩選。
  - 月初自動把「已買」清掉重來。
  - 後續成本（耗材 / 訂閱）欄位。
- **Won't（這版明確不做——範疇紀律的防線）**
  - **真記帳系統**：不記錄每筆已購金額、不追蹤「本月實際已花」、不做結算帳本。已買 = 移出清單，不留帳。
  - 帳號登入 / 權限系統（用 Firebase 共享 database，靠網址 + 規則即可，不做註冊登入）。
  - 商品價格自動抓取 / 連結分析。
  - 限時優惠 / 降價追蹤、二手可得性。

## 5. Scope & Interfaces
- **涉及的檔案／模組**：全新獨立專案（**不動 Scout 既有檔案**）。**Vue + Vite** 建置 + **Firebase Realtime Database**（專案 `buylist-590d9`，與 Scout 隔離）作為共享資料層。
- **資料層（Firebase Realtime Database）** 建議結構：
  ```
  buylist/
    budget/ { monthlyBudget: number }          # 兩人共用一個
    items/
      {itemId}/ {
        name, price,
        urgency: "need" | "want" | "maybe",     # 迫切度
        accessibility: "tw_easy" | "overseas" | "rare",
        thisMonth: boolean,                      # 本月想買 / 之後再說
        bought: boolean,
        createdAt: <timestamp>,                  # 冷卻期計算用
        addedBy: <string>,                       # Should：誰加的
        note?, link?                             # Should
      }
  ```
  - 「本月未購總價」= sum(price) where `thisMonth === true && bought === false`。
- **明確 out of scope**：後端 server / SQL / 帳號登入註冊 / 記帳帳本 / 商品自動分析 / 降價追蹤。
  **Stanley 不得順手加上任何後端、登入系統或記帳整合。**
- **要遵循的既有 pattern**：
  - Firebase 接法參考 Scout web 端（`scout_cis.html` 已在用 Firebase Realtime Database 即時同步）。
  - UI 走 ui-ux-pro-max；元件依 Atomic Design 分層（物品列 = Molecule，清單 = Organism，預算列 = Molecule，新增表單 = Organism）。
  - **設定外部化（12-Factor Config）**：Firebase 設定走 `import.meta.env`，金鑰不進 git。

## 6. Acceptance Criteria（使用者視角、end-to-end、初始全 failing）
- [ ] **AC-1（即時同步，主軸）**：兩個瀏覽器視窗開同一份清單，A 視窗新增 / 修改 / 刪除一個物品後，B 視窗在數秒內自動反映，無需重整。
- [ ] **AC-2**：使用者新增物品（名稱、價格、迫切度、取得難易度、本月/之後）後，它出現在清單上並帶有對應標籤。
- [ ] **AC-3**：使用者設定月預算後，畫面顯示「本月未購總價」與「剩餘額度 / 超支金額」，僅加總 `thisMonth && !bought` 的項目；超過時有明確爆預算提示。
- [ ] **AC-4**：使用者把某物品標記為「已買」後，它從本月未購總價中扣除，剩餘額度更新，且系統未記錄任何已花金額帳目。
- [ ] **AC-5**：每個物品顯示取得難易度標示（台灣容易 / 需國外 / 稀有難找）與迫切度標示（需要 / 想要 / 再看看）。
- [ ] **AC-6**：每個物品顯示「想買了 N 天」，由加入時間自動計算（使用者不需手動輸入）。
- [ ] **AC-7（Should）**：使用者能在 2×2 視覺中看到所有本月未購物品依（價格 × 迫切度）分群的位置。

## 7. Build Order（一次一件事 / one feature per loop）
1. **Tracer bullet（先打通最大未知）**：Vue + Vite 專案骨架 + 連上 Firebase，能新增一個「只有名字」的物品寫進 Realtime Database，**兩個瀏覽器視窗即時同步顯示**。最薄但打通「Vue ↔ Firebase ↔ 即時同步」整條。（對應 AC-1）→ **做完此步先停下，等 CHIA 檢查。**
2. 補完新增表單（價格、迫切度、取得難易、本月/之後）+ 清單顯示 + 刪除。（AC-2、AC-5）
3. 月預算設定 + 本月未購總價加總 + 剩餘額度／爆預算提示。（AC-3）
4. 「已買」打勾 → 移出本月未購總價。（AC-4）
5. 冷卻期「想買 N 天」顯示。（AC-6）
6. （Should）2×2 視覺化、誰加的、連結/備註。（AC-7）
> 一個 loop 做一條，逐條把 failing 轉 passing。**不要一次 one-shot 整個 app。**

## 8. End-to-End Verification
**開兩個瀏覽器視窗**對同一網址：A 視窗新增 3 個物品（不同價格、不同迫切度、不同取得難易，皆設「本月想買」）→ B 視窗數秒內即時出現 → 設月預算（故意略低於總價）→ 兩邊都顯示爆預算與超支金額 → A 把其中一個標「已買」→ 兩邊本月未購總價同步下降、提示變回未爆 → 每個物品都顯示「想買了 N 天」→ 重整任一視窗，資料都還在。全部成立才算 done。

## 9. Context Pulled
- Scout `scout_cis.html`：Firebase Realtime Database 即時同步寫法、UI 慣例。
- 對話過程：affordability × accessibility 兩軸拆解；預算「判斷依據 vs 記帳系統」範疇決策；單人 → 兩人共用導致 localStorage 出局、回到 Firebase 的架構轉折。

## 10. Decisions（已拍板）
- **D1（框架）**：✅ Vue + Vite。
- **D2（預算範圍）**：✅ 兩人共用一個月預算（`budget/monthlyBudget` 單一節點）。
- **D3（Firebase project）**：✅ 新開 project `buylist-590d9`，與 Scout 隔離。
- **R1（即時同步衝突，已知風險）**：Firebase 預設 last-write-wins，個人規模通常夠用，不過度設計。

## 11. 給 Stanley 的交接註記（agentic-coding 對應）
- **§6 AC = `feature_list`**：交付時全標 failing，逐條自我驗證轉 passing 才算數。
- **§7 = one feature per loop**：照 build order 順序，**tracer bullet 先、做完就停等檢查**。禁止一口氣 one-shot 整個 app。
- **§8 = 用證據驗收**：實際開兩個瀏覽器視窗驗即時同步，show evidence（截圖 / 命令輸出），不接受口頭「完成了」。
- **§5 out of scope 釘死**：不加後端 / 登入 / 記帳。
- **Harness**：本專案有 build step（Vite），Firebase 設定走 `import.meta.env` 外部化、金鑰不進 git。deploy 方式（GitHub Pages 部署 Vite 產物 vs Firebase Hosting）未定，交接時一併決定。

---

# Part 2 — 交接資料（Firebase 後端已就緒）

Firebase 後端已由 CHIA 在 console 建好，狀態：

| 項目 | 內容 |
|---|---|
| 專案名稱 / ID | `buylist` / `buylist-590d9` |
| 方案 | Spark（免費） |
| Google Analytics | 已關閉 |
| Web app | `buylist-web` 已註冊 |
| Realtime Database | 已建立，位置 **asia-southeast1（新加坡）** |
| 安全規則 | 由 CHIA 於 console 選定（見下方 ⚠️ 提醒） |

### Firebase config → 放 `.env.local`（Vite 環境變數，勿進版控）
```
VITE_FIREBASE_API_KEY=AIzaSyBptTJEJu8VALTRGh1CTPlI9tHb8EJPmcA
VITE_FIREBASE_AUTH_DOMAIN=buylist-590d9.firebaseapp.com
VITE_FIREBASE_DATABASE_URL=https://buylist-590d9-default-rtdb.asia-southeast1.firebasedatabase.app
VITE_FIREBASE_PROJECT_ID=buylist-590d9
VITE_FIREBASE_STORAGE_BUCKET=buylist-590d9.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=825660362419
VITE_FIREBASE_APP_ID=1:825660362419:web:2fddd7b870e84c34816ac6
```
> 程式裡用 `import.meta.env.VITE_FIREBASE_DATABASE_URL` 等取用。確認 `.gitignore` 已排除 `.env.local`。

### ⚠️ 安全規則待 CHIA 後續拍板（不可由 Stanley 默默決定）
- 此 app **無登入機制**（§4 Won't），規則無法靠使用者身分鎖。
- 若目前是**測試模式**：**30 天後到期，app 會無預警停止讀寫**。
- **正式日常使用前**，CHIA 須有意識地把規則改成長期版本——無登入的個人規模，現實選擇是「開放讀寫並接受『網址即存取』」或「加一道輕量共用密鑰」。
- **Stanley：不要自行更動安全規則。** 若開發中遇到規則到期 / 權限被拒，回報 CHIA，由 CHIA 在 console 處理。

---

# Part 3 — 開場 Prompt（貼給 Stanley）

```
你是這個專案的執行端。先完整讀過本檔（buylist-handoff.md）的 Part 1 Spec 與 Part 2 交接資料，再開始。

工作契約：
1. 技術棧：Vue + Vite + Firebase Realtime Database。Firebase config 在 .env.local（Part 2），用 import.meta.env 取用；確認 .gitignore 排除 .env.local。
2. 把 §6 的所有 Acceptance Criteria 當成 feature_list，初始全部標 failing，逐條自我驗證通過才標 passing。
3. 一次只做一個 feature（one feature per loop），嚴格照 §7 Build Order 的順序。
4. **這一輪只做 §7 第 1 步：tracer bullet**——Vue+Vite 骨架、連上 Firebase、能新增一個「只有名字」的物品寫進 Realtime Database，開兩個瀏覽器視窗驗證即時同步（AC-1）。做完就停，不要往下做其他 feature，等我檢查。
5. 驗收用證據：實際開兩個瀏覽器視窗操作，附上截圖或命令輸出證明即時同步成立，不要只說「完成了」。
6. 範疇紀律（§5 out of scope）：不要加後端 server、登入/註冊、或任何記帳功能。有想加的東西先問我。
7. 安全規則：不要自行更動 Firebase 安全規則。若遇到權限被拒或規則到期，回報我，由我在 console 處理。

開始前，先用一兩句話複述你對「這一輪要交付什麼、做完在哪裡停」的理解，我確認後你再動手。
```
