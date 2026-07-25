# BuyList — 專案現狀（給 Chat 接手用）

> **用途**：新開一個 chat 時，把這份 `.md`（＋ Chia 的 spec）貼進去，就能完整理解專案、接著做。
> **維護原則**：每完成一步，就更新 §5 現狀 與 §6 下一步。只記架構/決策/進度，不記瑣碎過程。
> **最後更新**：2026-07-25

---

## 1. 一句話
兩人即時共用的「想買清單 ＋ 買不買決策」app：月預算爆預算提示、迫切度（需要/想要/再看看）、
取得難易（台灣易/需國外/稀有）、冷卻期「想買 N 天」。

## 2. 分工
- **Chia**：思考 / 出 spec（決定「做什麼」）。
- **Stanley**：在 Claude Code 執行（決定「怎麼做」）。

## 3. 需求來源（SSOT）
Chia 的 spec：Scout repo 的 `specs/buylist-handoff.md`（status: approved）。
**spec 是需求真相**；下面 §4 的技術決策是執行端對 spec 的調整，已標明出入與理由。

## 4. 技術決策（已拍板；與 spec 原文有出入處標明理由）

| 項目 | 決定 | 與 spec 差異 / 理由 |
|---|---|---|
| **落點** | **private 的 `Scout` repo**，放在 `buylist/` 資料夾。**不開自己的 repo、也不放公開 repo。** | spec 原寫「全新獨立專案」。改放既有 private repo：全程 private、不增 repo、Chia 是 Scout 協作者也拿得到。 |
| **執行/分享** | **桌面本機跑**：雙擊 `run.bat`（Win）/ `run.command`（Mac）→ 起本機伺服器 → 瀏覽器開 `localhost`。**兩人各自在自己電腦跑，靠 Supabase 同步**。 | 暫**不做手機**（Stanley 決定）。手機要用再改成公開網址（Cloudflare 從 private 出，程式碼仍 private）。不用 `file://` 雙擊（連雲端不可靠）。　⚠️ **2026-07-25 已部分 supersede，見 §4.1（改為要上手機）** |
| **後端** | **Supabase**，用 **Stanley 自己的專案** `kdmmjlaajqxjmiahfvos`（URL `https://kdmmjlaajqxjmiahfvos.supabase.co`），新表 `buylist_items`。 | spec 原寫 **Firebase**。改 Supabase：統一一個後端技術、SQL 查詢力、權限可預期、不鎖定。**注意：Scout 的 Supabase（`uarkccyqcqvgxukjcrey`）是 Chia 的、Stanley 沒後台權限**；所以 BuyList 改用 Stanley 自己的專案，他能自管（建表/改欄位都自己來）。BuyList 資料本來就跟 Scout 分開，無妨。anon key 寫在 `buylist/index.html`。 |
| **前端** | **單檔 vanilla HTML/JS**（無 build），UI 風格輕參考 dfg | spec 原寫 **Vue + Vite**。改 vanilla：最薄、好分享、tracer bullet 不需框架。`decision-focus-graph` 只是介面範例，**不改、不照抄**。 |
| **身分** | 無登入；anon key + 權限全開 | 同 spec（網址即存取）。實驗、兩人用，已接受風險。 |
| **同步** | Supabase Realtime（`postgres_changes`） | 達成 spec 的第一 Must：兩人即時同步。同步靠 Supabase，與「放哪/怎麼開」無關。 |

### 4.1 Superseding 決策（2026-07-25，Chia 拍板）
覆寫 §4「執行/分享」中「暫不做手機」那條：

- **決定：buylist 要上手機**，範圍限「**能在手機瀏覽器開來用**」——**不做** PWA/安裝、**不做**離線。
- **拆解與分工**：
  1. **部署/可達性（Stanley，部署範疇）**：把單檔靜態 app 放到手機連得到的網址（Cloudflare Tunnel 或靜態託管）。⚠️ **安全**：從「只在 localhost」變公開網址＝Supabase anon key ＋ 全開 RLS 攤在網址上，誰有網址誰能讀寫；§4「網址即存取」的風險在公開後放大，需確認接受。
  2. **手機介面優化（Chia，UI 範疇）**：現行偏桌面的 UI 改 responsive／手機優先（呼應 Scout 主 app 的手機優先原則）。
- **仍不做（留待「能線上手機用」之後再議）**：PWA 離線、離線編輯的兩人合併。
- **狀態**：方向已定，HOW（部署方式）待 Stanley 決定；手機 UI 優化待 Chia 出 spec。

## 5. 現狀（current state）
- ✅ 落點/執行已定：private `Scout/buylist/`，雙擊啟動檔本機跑，桌面、不公開。
- ✅ 已退役公開的 `scout-checklist` repo（改 private）；Scout 內重複的 `checklist/` 已刪。
- ✅ `decision-focus-graph`：只當 UI 參考，未改動。
- ✅ **整個 app 完成、AC-1～AC-7 全綠（實測通過）**。
  - **Stanley 決定 one-shot 全做**，有意識覆寫 Chia spec「一次一步、做完停、等 Chia 檢查」的流程。
  - 實測：即時同步、新增(價格/迫切度/取得難易/本月)+標籤、月預算「本月未購總價」+爆預算紅字、標已買移出總價(不留帳)、想買N天、2×2 分群、誰加的——全部正確；中文新增/顯示正常。
- 後端：Supabase 專案 `kdmmjlaajqxjmiahfvos`（Stanley 的）；表 `buylist_items`(11 欄) + `buylist_budget`，schema 見 `buylist/buylist-schema.sql`（已執行）。DDL 由 Claude 用 DB 連線直接套用（密碼已重設可用）。
- ✅ **spec Could 也全做完**：分類、篩選(狀態/分類)、排序(價格/想最久)、月初自動清上月已買(用 `buylist_budget.last_cleared` 月份標記)、後續成本(訂閱/耗材)欄位、連結欄位。`buylist_items` 已擴到 13 欄。
- 測試資料已清空，兩人可從零開始用。
- ✅（2026-07-12）已買星號收藏 ＋ 全站 CIS 換色 完成（詳見 §6.1）；`starred` 欄位 DDL 待在 Supabase 執行。

## 6. Build Order（from spec §7）— 全部完成
> spec 原要求「一次一步、做完停、等 Chia 檢查」；**Stanley 選擇 one-shot 全做**（有意識覆寫）。

1. ✅ tracer bullet：即時同步（AC-1）
2. ✅ 新增表單（價格 / 迫切度 / 取得難易 / 本月想買）＋ 清單 ＋ 刪除（AC-2、AC-5）
3. ✅ 月預算 ＋「本月未購總價」加總 ＋ 爆預算提示（AC-3）
4. ✅「已買」打勾 → 移出本月未購總價（AC-4）
5. ✅ 冷卻期「想買 N 天」（AC-6）
6. ✅（Should）2×2 視覺、誰加的、備註（AC-7）
7. ✅（Could，本輪一併做）物品**分類**、狀態/分類**篩選**、價格/想最久**排序**、**月初自動清**上月已買、**後續成本**(訂閱/耗材)欄位、**連結**欄位 UI。

> Must / Should / Could **全部完成**。spec §4 **Won't 維持不做**（不做記帳帳本、登入、自動抓價、降價追蹤）。

## 6.1 下一步（新任務，2026-07-12 起）

**已買星號收藏（可再買）＋ 全站改用 Scout CIS 配色** — 完整規格見 `specs/buylist-starred.md`（由 Chia 撰寫，狀態 **approved**）。

- **Part A（星號功能）**：已買項目可加星號，代表「值得回購」；星號只有打勾（已買）後才能標記，並新增「已買・星號」篩選選項
  - Schema 增量：`buylist_items` 新增 `starred boolean default false`（見 `buylist-schema-add-starred.sql`）
  - 改動範圍：僅 `index.html`（CSS + JS + HTML，共 6 處小改動）+ schema 一行
- **Part B（全站換色，範圍較大）**：`index.html` 現行的 blue/green/amber 配色改為 Scout 品牌 CIS 的 sage/linen/wheat 配色（對照 `scout_cis.html`）
  - 改動範圍：`:root` 變數區塊、focus 光暈 rgba 值、6 種標籤的寫死 hex 色碼、2×2 矩陣格底色——完整對照表與逐行改法見 spec 的 Part B
  - 語意取捨：CIS 只有 3 色系，裝不下原本 6 種語意分類，已與 Chia 討論定案「迫切度」與「取得難易度」各自成深淺階梯，唯獨保留「需要」與「稀有難找」同色系（語意相近，文字標籤已可區分）
- 顏色：星號沿用既有 `--amber` 討論後改為 CIS 的 `wheat-400`（已確認），全站換色詳見 Part B 對照表
- Stanley 可直接照 spec 第 7 節（Part A）與 B.3 節（Part B）的逐行改動指引動手，不需另外的 Kickoff 文件；兩部分可一併做或分開做

### ✅ 完工（2026-07-12）
- **Part A（星號）＋ Part B（全站 CIS 換色）皆已實作**，改動全在 `buylist/index.html`；schema 增量已寫進 `buylist-schema.sql`（新增 `starred` 那行）。
- 廢棄的 `spec-buylist-want-bought.md` 與其 kickoff 已刪除（那份假設 Vue+Firebase，與真實 app 不符）。
- 過了一輪 3-persona 對抗式審查（部署現實／視覺對比／JS 邏輯）：JS 邏輯與視覺皆 PASS（視覺留幾個低對比 NOTE，見下）；唯一 BLOCKER 是部署順序。
- 🔴 **上線前必做（BLOCKER）**：到 Supabase 專案 `kdmmjlaajqxjmiahfvos` 的 SQL Editor 執行 `buylist-schema-add-starred.sql`（就一行 `alter table … add column if not exists starred …`，冪等）。**沒跑這行，星號一點就噴「更新失敗」紅字、「已買・星號」篩選永遠空白。** 程式碼本身對缺欄位容錯（`select *` 不會炸、既有功能不受影響），只有寫入星號會失敗。
- 🟡 視覺 NOTE（spec 已定案的色值，留給 Chia 決定要不要微調）：`cat` 分類標籤文字 linen-400 on linen-50 對比僅 2.24:1（可辨但吃力，建議改用 `--muted` 可拉到 5.11:1）；`u-maybe`／`later`／`cat` 三種標籤換色後底色相近、只能靠文字區分。

### ✅ 追加：貼連結自動帶入（2026-07-12，Stanley 直接指示，非 Chia spec）
- 「＋加入」右邊新增「🔗 貼連結帶入」按鈕：把商品連結貼到「連結」欄 → 按按鈕 → 呼叫 Gemini（`url_context` 工具實際讀網頁）抽出名稱+價格填進表單，**不自動送出**，使用者確認後自己按加入（防 AI 抓錯灌垃圾）。
- Gemini 金鑰放 **gitignored 的 `buylist/config.js`**（`window.BUYLIST_CONFIG`），**不進版控**；`.gitignore` 已加 `buylist/config.js`。換機器：把 committed 的 `buylist/config.js.example` 複製成 `config.js` 再填金鑰（同一把金鑰，或去 `scout-checklist/config.js` 拿）。
- 模型 `gemini-2.5-flash` + `url_context` tool，可在 config.js 換模型。
- 已實測 iHerb 連結：正確抽出「Mike's Hot Honey 含辣椒」+ 換算台幣 454，未自動送出。
- 失敗路徑：連結欄空 / 無金鑰 / API 錯 / 解析失敗 都會在狀態列顯示對應紅字，不靜默失敗。


## 6.2 下一步（新一批 backlog，2026-07-25，Chia 整理＋出 spec）

Chia 從購物模組 backlog 整理出下面這批，已寫成 spec（都在 `buylist/`），交給 Stanley 執行。

**進度（5 份 spec — 全部完成 ✅，2026-07-26 一輪做完，branch `feat/buylist-qty-bought-bottom`）**

1. ✅ `spec-buylist-qty-and-bought-bottom.md` — 已買沉底（套在三種排序之上的主鍵）＋ 數量欄位（`quantity`，純記錄不動加總）。commit `41ccb7e`。
2. ✅ `spec-buylist-bulk-add.md` — 一次貼多行批次新增（換行/頓號/逗號拆分、本次去重）。純前端。commit `750fda6`。實測 AC-1~8。
3. ✅ `spec-buylist-context-tag.md` — 情境標籤（`tag`）＋依標籤篩選（datalist autocomplete、動態 distinct 下拉、📍chip）。commit `23e4229`。實測 AC-1~8。
4. ✅ `spec-buylist-md-export.md` — 一鍵匯出 `.md`（依情境分段、已買劃線、匯出全部不受篩選）。純前端。commit `ff808e7`。實測 AC-1~8。
5. ✅ `spec-buylist-actual-price.md` — 已買填實付＋當下省/超差額（`actual_price`，不進總價、不留帳）。commit `91f323f`。實測 AC-1~8。

**DDL 全部已執行 ✅**（Supabase `kdmmjlaajqxjmiahfvos`）：`quantity int default 1`、`tag text default ''`、`actual_price numeric`。⚠️ 該專案免費方案會自動暫停，DDL/使用前先確認沒被 pause（見 memory `buylist-supabase-pause`）。

**尚未 merge**：branch `feat/buylist-qty-bought-bottom` 有 6 個 commit（含這份 state），待 merge 回 `main`。

**擱置（有意識地不做）**

- **結構化輸出（Gemini JSON schema 強制）**：把現有 AI 貼連結帶入的自寫 parse 換成強制 schema。歸 Stanley（AI 範疇）；現況 parse 實測可用，等真的抓錯再做，暫列 backlog。
- **PWA / 離線可用**：與既有決策衝突（桌面本機跑、靠 Supabase Realtime 同步、暫不做手機）。要先決定「buylist 是否上手機」才談，屬 superseding 級別的大方向，先擱置。

## 7. 怎麼跑 / 怎麼繼續
- **跑**：進 `Scout/buylist/`，雙擊 `run.bat`（Win）或 `run.command`（Mac）→ 瀏覽器會開買物清單。
- **接手**：新 chat → 貼「這份 `BUYLIST_STATE.md` ＋ `specs/buylist-handoff.md`」→ 說「做下一步」。
