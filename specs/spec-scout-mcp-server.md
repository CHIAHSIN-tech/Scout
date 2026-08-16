# Spec — Scout MCP Server

> 本 spec 為 self-contained：執行它不需要讀任何其他方法論文件。
> Written under GRAPH_PROTOCOL v2.2 路由（結果：單 agent 同步監督 → spec-skeleton 路徑）。

---

## 0. Meta
- **Appetite（投入上限，非估算）**：一個下午（afternoon）的 review／返工時間。超時警示：同一問題重 prompt 兩三回未果、或 context 被失敗嘗試塞爆 → 啟動砍範疇（順序見 §4，Could 先砍、Should 次之、Must 不砍）。
- **Status**：done（2026-08-16 落地。AC-5／AC-6／AC-7 已由命令驗證通過；
  AC-1～AC-4 需在真實 Claude Code ＋ 真實 Supabase 環境跑過才算數，見
  [`../ACCEPTANCE-mcp-server.md`](../ACCEPTANCE-mcp-server.md)）
- **Date**：2026-08-16

### 執行時的一項規格修正（已由 Stanley 拍板）

§5 假設「與網頁前端讀寫同一個 Supabase」，但偵察後發現**行程與購物分屬兩個 Supabase 專案**
（ADR-012 明確不合併），且 `supabase_schema.sql` 的 `wishlist` 表是 Streamlit 時代的遺留，
**現行購物 Tab 讀的是另一個專案的 `buylist_items`**。

照字面實作 `wishlist` 會讓 AC-4 的「網頁購物 Tab 可見」永遠不成立。
2026-08-16 拍板：**購物三工具改接 `buylist_items`**，工具名稱沿用規格的 wishlist 用語，
並新增 `SCOUT_BUYLIST_URL` / `SCOUT_BUYLIST_KEY` 兩個環境變數（Must 的「兩個環境變數」因此變成四個）。

### Triad（執行前閘門）
- **Objective**：Scout 的行程與購物資料可以從 Claude Code / Claude Desktop 透過 MCP 工具直接查詢與寫入（不含刪除），與網頁前端讀寫同一批資料。
- **Why it matters**：Stanley 與 Chia 用 Claude 規劃旅程時，資料只能透過網頁介面操作，AI 對話與資料之間靠人手搬運；做錯的代價是 agent 誤寫共用資料庫（兩人的真實旅程資料），所以寫入面必須窄（無刪除）且防呆寫進協定層。
- **Success measured by**：§6 的 AC-1 ~ AC-7，每條皆可獨立判定 pass/fail。

## 1. Problem Statement
Stanley 和 Chia 在 Claude 裡討論旅程規劃時，Scout 的資料（行程、候選、購物清單）只存在網頁介面裡，Claude 看不到也改不了——每次都要人工在對話與網頁之間來回抄寫，規劃的產出無法直接落地成資料。

## 2. Primary User + JTBD
- **User**：Stanley（開發者，本機 Claude Code）與 Chia（非技術使用者，未來透過 Claude Desktop；本版只需在文件附上她的設定步驟，不為她做額外功能）。兩人各自在自己的電腦跑 MCP server，連同一批雲端 Supabase 資料。
- **JTBD**：當我在 Claude 裡規劃旅程或整理購物清單時，我想要 Claude 直接讀寫 Scout 的資料，這樣規劃結果立刻出現在 Scout 網頁上，不用手動搬運。

## 3. Success Criteria
在 Claude Code 連上 MCP 後，一句自然語言能完成「查旅程」「加候選」「排日期並確認」「標記已購」，且結果在網頁前端重新整理後可見；工具出錯時 agent 得到的是「說明重試有沒有用、該改做什麼」的散文，不是裸狀態碼。

## 4. MoSCoW
- **Must（沒有就失敗）**：
  - stdio transport 的 MCP server，可被 Claude Code 以 `.mcp.json` / `claude mcp add` 啟動
  - 設定走環境變數；缺任一 → 非零 exit code ＋ stderr 人話錯誤（指名變數、說明該填什麼、給範例）
  - 七個工具：`list_trips`、`list_itinerary_items`（可篩 day_number／只看候選／只看未確認）、`add_itinerary_item`（不給 day_number ＝ 候選）、`update_itinerary_item`（含排入某天、改時間、確認）、`list_wishlist`（可篩 status）、`add_wishlist_item`、`update_wishlist_item`（含標記 purchased）
  - Server instructions（連線時給 agent 的規則，見 §5）
  - 錯誤散文政策：每個失敗訊息說明 (a) 重試原樣參數有沒有用 (b) 建議的下一步
  - 每個工具回傳「一句人話摘要 ＋ 完整 structured payload」
- **Should**：`create_trip`；本地預檢；pydantic 回應驗證；離線測試（fake 不得比真 API 寬鬆）
- **Could**：`list_adjustments`、`confirm_item` 專用工具
- **Won't**：任何 delete 工具（HTTP client 層不允許該動詞）；HTTP/SSE transport；認證體系、RLS 變更、schema 變更；改動 `web/`、Streamlit 舊世代、Netlify functions；寫入 `trip_adjustments`

## 5. Scope & Interfaces
- **新增（唯一的寫入範圍）**：repo 根目錄新資料夾 `mcp-server/`。技術棧：Python + 官方 MCP SDK。
- **資料路徑**：Supabase PostgREST 的純 HTTP client。不 import 任何資料庫 driver。
- **Schema SSOT**：`supabase_schema.sql` 與 `buylist/buylist-schema.sql`。
  關鍵語意：候選 ＝ `day_number IS NULL`；確認兩軸 ＝ `confirm_required` × `is_confirmed`；
  `start_time` 是 text `'HH:MM'`，無時區概念；`username` 從 `SCOUT_USERNAME` 讀（預設 `stanley`）。
- **要遵循的 pattern**（移植自 Unipost `packages/mcp-server`，以 Python 重現精神而非翻譯程式碼）：
  1. 純 HTTP client，永不碰資料庫連線
  2. 工具的輸入／輸出 schema 單點定義，註冊處不重複宣告
  3. Server instructions 交代三條跨 session 規則
  4. 錯誤是散文
  5. stdout 只屬於 JSON-RPC，診斷走 stderr
  6. 明顯錯誤在本地預檢
  7. 回傳 ＝ 一句摘要 ＋ structured content
- **明確 out of scope**：`mcp-server/` 以外的一切檔案（例外：`.gitignore` 加一行、`.mcp.json.example`、驗收文件）。
- **註解**：繁體中文。

## 6. Acceptance Criteria
- [ ] **AC-1**：clean clone、設好環境變數、在 Claude Code 完成 MCP 設定後，說「列出我的旅程」→ 回傳 `trips` 表中既有旅程的名稱與日期。（**待真實環境驗**）
- [ ] **AC-2**：說「把〈某店名〉加進〈某旅程〉當候選」→ `itinerary_items` 新增一列且 `day_number IS NULL`。（**待真實環境驗**）
- [ ] **AC-3**：說「把〈該項目〉排到第 2 天 14:00 並標記已確認」→ 該列 `day_number=2`、`start_time='14:00'`、`is_confirmed=true`。（**待真實環境驗**）
- [ ] **AC-4**：說「〈某商品〉買到了」→ 該列標記為已買，網頁購物 Tab 可見。（**待真實環境驗**）
- [x] **AC-5**：清空 `SCOUT_SUPABASE_URL` 後啟動 server → 非零 exit code，stderr 指名缺的變數並給範例值。
- [x] **AC-6**：`git grep -inE "\"DELETE\"|'DELETE'" -- mcp-server/src/` 回空；動詞允許清單只有 GET / POST / PATCH。
- [x] **AC-7**：在 `mcp-server/` 內、無網路環境下 `pytest` exit 0（79 項，全部走 fake Supabase）。

## 7. Build Order
1. `config` ＋ HTTP client（動詞允許清單）＋ `list_trips`
2. 行程讀：`list_itinerary_items` 與三種篩選
3. 行程寫：`add_itinerary_item`、`update_itinerary_item`
4. 購物三工具
5. Server instructions ＋ 錯誤散文打磨 ＋ AC-6 自查
6. Should 項：預檢、pydantic 回應驗證、fake ＋ pytest，行有餘力再 `create_trip`

## 8. End-to-End Verification
在 Claude Code 說「列旅程 → 把〈新店名〉加進〈旅程〉候選 → 排到第 2 天 14:00 並確認 → 把〈商品〉標已購」，每步之後用 REST GET 比對資料庫實際狀態，最後開網頁前端目視兩個 Tab 都反映變更。

## 9. Context Pulled
Unipost `packages/mcp-server`（2026-08-16 盤點）；Scout `supabase_schema.sql`、`buylist/buylist-schema.sql`、`web/checklist.js`、`web/buylist.js`、`web/config.js.example`、`netlify.toml`（同日讀取）。

## 10. Open Questions（皆附預設，未答視同採預設）
- **Q1 套件管理？** — 預設：`uv` ＋ `pyproject.toml`，鎖檔進 repo。**採預設。**
- **Q2 `SCOUT_USERNAME` 之外要不要區分 Chia 的寫入？** — 預設：不區分，`username` 只是紀錄欄位。**採預設。**
- **Q3 Chia 的安裝文件放哪？** — 預設：`mcp-server/README.md` 附「非開發者設定步驟」一節。**採預設。**
- **已知並刻意接受的風險**：publishable key ＋ RLS 停用 ＝ key 在手即可全讀寫；「無刪除」由工具面與動詞允許清單保證，不是資料庫層強制。此為 Scout 既有安全姿態（ADR-013），本版不改。
