# TASK: Scout 旅程頁模組（trip-page）＋ 託管遷移至 Cloudflare Workers

> Status: `draft` · v2（2026-09-12）
> 範圍：(A) 託管從 Netlify 遷移至 Cloudflare Workers；(B) 新增旅程頁模組（MCP 工具 + 單檔離線行程表 + web 列表）
> 參考產品：2026/9「首爾中秋五日」HTML artifact（45 版）。**原始檔已取得**，放在 `trips/_reference/`。

---

## OBJECTIVE

每趟出國前，Stanley 把機票／旅館／餐廳／想去的地方貼進 Claude 對話，Claude 用 Scout 的 MCP 工具把
查證過的事實與行程安排寫進一份 `trip.json`，跑排程衝突檢查、把取捨丟回給人選，最後產出**一個自含、
可離線開、手機可讀的單檔 HTML 行程表**，依「年月－國家－城市」留檔，並經由 Scout 網站可瀏覽；
同時整站託管從 Netlify 遷至 Cloudflare Workers，四支既有 Function 與保活排程功能等價、可回退。

---

## WHY IT MATTERS

**(B) 旅程頁**——參考產品證明價值不在「產生漂亮頁面」，而在**約束求解、事實查證、每次改動都重算連鎖
影響**。那次 session 最大的成本是第三件：同一筆資訊在頁面上出現於 13 個地方（時間軸、日標題、頁首摘要、
快捷 nav、地圖路線點序、地圖每段標籤、地圖文字轉乘表、地圖地點集合、車站三語對照表、訂位狀態表、
正餐一覽表、出發前待確認清單、頁尾來源），改一個行程漏改其中一處頁面就自相矛盾——而且**是使用者發現的**。
把 `trip.json` 做成單一資料來源，13 個地方全由它算出來，「漏改」在結構上不可能發生。
附帶解掉留檔：那次的成果只活在一個 artifact 網址裡，下一趟要重來；做進 Scout 之後每趟一份、格式一致、可比對。

**(A) 遷移**——Stanley 決定託管收斂到既有的 Cloudflare 帳號。**這與 ADR-011（部署採 Netlify）直接衝突，
並影響 ADR-014（repo 轉移給 Chia 的理由正是她的 Netlify 接著她的 GitHub）**，所以它不是設定調整，
是要寫 superseding ADR 的架構決策。做錯的代價很具體：Scout 是兩人每天在用的正式系統，
`share` 是家人在看的唯讀連結，`keepalive` 是唯一擋住 Supabase 閒置暫停的東西（2026-07、2026-08 已被暫停兩次）。
**遷移失敗的定義不是「Cloudflare 沒起來」，是「Netlify 已經拆掉而 Cloudflare 沒起來」**——所以本規格
要求可回退，拆除是獨立的最後一個 commit。

---

## 前置事實（已查證，執行時如與現況不符請先回報再動工）

| 事實 | 來源 | 查證日 |
|---|---|---|
| Cloudflare **Pages 不支援 Cron Trigger**；Workers 支援 | Cloudflare 社群官方回覆；官方遷移文件的相容性對照表 Pages ❌ / Workers ✅ | 2026-09-12 |
| Cloudflare 官方把 **Workers with Static Assets 定位為 Pages 的後繼**，可同時託管靜態資產與後端 API | `developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/` | 2026-09-12 |
| `_headers` / `_redirects` 在 Workers static assets **原生支援**，放在資產目錄即可 | 同上 | 2026-09-12 |
| Pages Functions 的 `functions/` 目錄要用 `wrangler pages functions build` 編成單一 Worker；直接改寫成一支 Worker 更單純 | 同上 | 2026-09-12 |

**因此目標是 Cloudflare Workers（Static Assets），不是 Pages。** 選 Pages 會為了一支保活排程被迫開
第二個 Cloudflare 專案，那比現狀更糟。

> 執行時必須用 `npx wrangler dev` 實測「靜態資產優先、`/api/*` 落到 Worker」的優先順序，
> **不得只依賴本表的文件摘要**（A-item A21 就是在釘這件事）。

---

## SUCCESS MEASURED BY

> 基線（baseline）在執行開始時先跑一次並記入 `ACCEPTANCE.md`：既有腳本目前的 exit code 未逐一驗證過，
> 「與改動前相同」比「exit 0」誠實。

### 共同：不回歸

**A1.** 既有測試與檢查腳本結果不低於基線 —
check: `cd mcp-server && uv run pytest`（通過數 ≥ 基線、失敗數 = 基線）；
`for s in check-style check-exports check-pwa check-share check-ai-suggest; do node scripts/$s.mjs; echo "$s=$?"; done`
每行 exit code 與基線相同。

**A2.** 既有 8 個 MCP 工具的名稱與參數簽章一字未改 —
check: `cd mcp-server && uv run pytest tests/test_tool_surface_frozen.py` exit 0。
比對凍結快照 `tests/fixtures/tool-surface-v1.json`（`list_trips / create_trip / list_itinerary_items /
add_itinerary_item / update_itinerary_item / list_wishlist / add_wishlist_item / update_wishlist_item`
的完整參數名與型別）。新工具只允許**增加**條目。

**A3.** HTTP 動詞允許清單仍只有 GET / POST / PATCH —
check: `grep -cE '"(DELETE|PUT)"' mcp-server/src/scout_mcp/rest.py` 回 0；
`cd mcp-server && uv run pytest tests/test_rest_verbs.py` exit 0。

---

### Phase A：Cloudflare 遷移

**A20.** 四支 Function 全數等價移植，且沒有殘留的 Netlify 路徑 —
check: `node scripts/check-cf-migration.mjs` exit 0。斷言：
(a) `worker/index.js` 路由涵蓋 `/api/ai-parse`、`/api/ai-suggest`、`/api/share`；
(b) `grep -rn "\.netlify/functions" web/ --include=*.js --include=*.html` 回空
（`web/_redirects` 的相容轉址除外，該檔允許且需存在）；
(c) `wrangler.toml` 含 `[assets]` 與 `[triggers] crons`；
(d) `worker/index.js` 匯出 `fetch` 與 `scheduled` 兩個 handler。

**A21.** 本機實跑，靜態與 API 都通 —
check: 起 `npx wrangler dev --port 8788`，然後
`curl -sf http://localhost:8788/index.html | grep -q '<title>Scout</title>'`、
`curl -sf "http://localhost:8788/api/share?tag=__nonexistent__" | grep -q '"items"'`、
`curl -s -o /dev/null -w '%{http_code}' -X GET http://localhost:8788/api/ai-parse` 回 `405`。
三者全成立才算過。**這條同時是「靜態資產優先於 Worker」的實測**。

**A22.** 保活排程等價 —
check: `grep -q 'crons = \["17 3 \* \* 1,4"\]' wrangler.toml`；
`npx wrangler dev --test-scheduled` 起來後 `curl -sf "http://localhost:8788/__scheduled?cron=17+3+*+*+1,4"` 回 2xx，
且 Worker 的 `scheduled()` 對兩個 Supabase 專案各打一次最輕量查詢（測試以假 fetch 斷言呼叫了兩個 URL）。

**A23.** `ai-suggest-core.js` 仍然只有一份實作 —
check: `node scripts/check-ai-suggest.mjs` exit code 與基線相同，且
`grep -c "ScoutAiSuggest" web/ai-suggest-core.js` ≥ 1、
`grep -q 'import "\.\./web/ai-suggest-core.js"' worker/index.js`。
**理由**：現行 `ai-suggest.js` 用 `node:fs` + `node:vm` 讀共用核心，**Workers 沒有 fs 也沒有 vm**。
移植方式：該檔維持「傳統 script、把物件掛上 `globalThis`、不含 import/export 語法」，
Worker 端用 `import` 產生副作用後取 `globalThis.ScoutAiSuggest`——瀏覽器 `<script>` 與 Worker 共用同一個檔案。

**A24.** 可回退：Cloudflare 驗證通過前，Netlify 設定不得刪除 —
check: `git log --oneline -- netlify.toml web/netlify/` 顯示刪除發生在**最後一個 commit**，
且該 commit 的訊息含 `chore: 移除 Netlify 設定`；在此之前的每個 commit，`test -f netlify.toml` 都為真。
以 `scripts/check-cf-migration.mjs --history` 驗。

**A25.** 金鑰沒有進版控 —
check: `git grep -nE "GEMINI_API_KEY\s*[:=]\s*['\"][A-Za-z0-9_-]{10,}" -- . ':!*.example'` 回空；
`wrangler.toml` 中不含任何金鑰值（只允許 `[vars]` 的非敏感值與 secret 的名稱）。

---

### Phase B：旅程頁模組

#### 建檔與留檔

**A4.** 依日期與國家留檔 —
check: 呼叫 `create_trip_file(country="KR", city="Seoul", start_date="2026-09-21",
end_date="2026-09-25", party_size=2)` 後 `test -f trips/2026-09-kr-seoul/trip.json` 為真，且
`cd mcp-server && uv run python -m scout_mcp.travel.validate ../trips/2026-09-kr-seoul/trip.json` exit 0。
目錄名規則 `<YYYY>-<MM>-<ISO3166-1 alpha-2 小寫>-<城市 slug>`；重複建立回傳既有路徑，不覆寫。

**A5.** 寫入路徑無法逃出 `trips/` —
check: `cd mcp-server && uv run pytest tests/test_travel_paths.py` exit 0。
必含四個被拒案例：`../`、絕對路徑（`/etc/passwd` 與 `C:\Windows\...`）、symlink 指向外部、
slug 內含路徑分隔字元。所有寫入一律經過單一 `resolve_trip_path()`。

**A6.** 列表可用且與磁碟一致 —
check: `node scripts/check-trip-index.mjs` exit 0。斷言 `web/trips/index.json` 的條目集合
等於 `trips/*/` 中已建置過的旅程集合，每筆含 `country / city / start_date / end_date / title / page_path`，
依 `start_date` 新到舊排序。

**A15.** 部署路徑不可猜 —
check: `node scripts/check-trip-index.mjs --unguessable` exit 0。斷言 `web/trips/` 下每個目錄名
都以 `-[0-9a-f]{6,}` 結尾，產生來源為 `secrets.token_hex()`
（`grep -rq 'secrets.token_hex' mcp-server/src/scout_mcp/travel/`）。

#### 單一資料來源（本模組的核心）

**A7.** 改一處，多處一起改 —
check: `node scripts/check-trip-page.mjs --consistency` exit 0。
做法：對 fixture 建置得 `before.html`；把 `trip.json` 某一 event 的 `time` 由 `15:30` 改 `16:30` 並改其 `day`；
重建得 `after.html`。斷言下列**五個區塊文字全部改變**——當日時間軸、當日標題摘要、快捷 nav 日期標籤、
地圖 `DAYS[dN].legs` 文字轉乘表、正餐一覽表；
且**同樣輸入重建兩次必須位元相同**（build 為決定性，不含時間戳或亂數）。

**A8.** 頁面不含 `trip.json` 以外的店家 —
check: `cd mcp-server && uv run pytest tests/test_no_invented_content.py` exit 0。
斷言產出頁中出現的 place 名稱集合 ⊆ `trip.json` 的 `places[].name` 集合。
這是把參考產品的「沒有明確同意不要加內容」變成結構保證：renderer 只渲染資料，不生成內容。

**A17.** schema 扛得住真實資料 —
check: `cd mcp-server && uv run python -m scout_mcp.travel.import_reference ../trips/_reference/rest.json
--out /tmp/places.json && uv run python -m scout_mcp.travel.validate --places /tmp/places.json` exit 0，
且 `python3 -c "import json;assert len(json.load(open('/tmp/places.json')))==39"`。
**39 家真實餐廳全部無損轉入 `places[]`**——這是本 schema 最便宜也最真的測試。
無法對應的欄位一律進 `extra{}`，不得靜默丟棄（測試需斷言 `chef_bio`、`chef_sources`、`alert`、`area` 都還在）。

#### 離線與手機

**A9.** 自含單檔，斷網可開 —
check: `node scripts/check-trip-page.mjs --offline` exit 0。斷言產出的 `index.html`：
無 `<script src=`、無 `<link rel="stylesheet"`、無 `@import`、CSS 無 `url(http`、無 `<img src="http`、
無 `fetch(` 與 `XMLHttpRequest`。**唯一允許外部 http(s) 出現的位置是 `<a href>`**
（Google Maps 導航、來源連結），腳本需逐一確認每個外部 URL 都落在 `<a>` 的 `href` 內。

**A10.** 375px 寬不橫向溢位 —
check: `node scripts/check-trip-page.mjs --mobile` exit 0。靜態規則斷言：
(a) 每個 `<table>` 都在 `overflow-x:auto` 容器內，或有 `@media (max-width:560px)` 的卡片化規則
（`thead{display:none}` + `tr{display:grid}`）；(b) 地圖 `<svg>` 在 `overflow-x:auto` 容器內；
(c) 樣式表中沒有作用在非容器元素、且 `min-width` 大於 `360px` 的規則；
(d) 不得靠 `body{overflow-x:hidden}` 蒙混（該宣告存在時仍須滿足 a–c）。

#### 排程與查證（參考產品的決策規則）

**A11.** 排程檢查器只報不改 —
check: `cd mcp-server && uv run pytest tests/test_schedule_check.py` exit 0。五類衝突各至少一案例：
(1) 鎖定項目被要求移動；(2) 候選點營業時間不覆蓋該時段；(3) 交通時間吃掉指定停留時長（可用時間 < `min_dur_min`）；
(4) 21:00 後安排跨區移動且最後一站不在旅館步行範圍；(5) `sunset_locked` 項目抵達晚於日落前 60 分。
且斷言呼叫前後 `trip.json` 的 sha256 完全相同——**它回報「要犧牲什麼」，永遠不自己刪、不自己搬。**

**A12.** 未查證的事實不會變成頁面上的數字 —
check: `cd mcp-server && uv run pytest tests/test_unverified.py` exit 0。斷言：
`place.hours.sources` 為空陣列時，(a) 頁面不輸出該店營業時間，
(b) 建置時自動在 `open_questions[]` 產生一筆，含 `what / why / check_by / source_hint`。

**A13.** 來源衝突不被消滅，往下游傳成待確認 —
check: 同上測試檔。`place.hours.sources` 有兩筆 `value` 不同時，(a) 頁面同時顯示兩個值並標註衝突，
(b) 自動產生一筆 `open_questions`，(c) 程式不得挑一個當「正確答案」。

#### Web 檢視

**A14.** 行程 Tab 能列出並開啟歷次行程表 —
check: `node scripts/check-trip-index-ui.mjs` exit 0。斷言 `web/index.html` 的 `#panel-trip` 內存在
`id="trip-pages"` 區塊、載入 `web/trip-pages.js`；該區塊不依賴 `config.js`
（無 config.js 時仍能顯示列表，因為它讀的是靜態 `trips/index.json`）。

#### 首跑交付物（不是 gate）

**A16.** 第一趟真實資料由人逐條看過一次 —
check: `test -f trips/2026-09-kr-seoul/REVIEW.md`，該檔含 **n ≥ 20 條**逐項核對
（至少涵蓋：每一餐的店名與訂位狀態、每天時間軸首末項、地圖每日路線起訖點、每一筆 open_question），
每條標 `OK` 或 `WRONG: <說明>`，並記下建置時的 `trip.json` sha256。

> **這是第一次跑這個任務類別**，沒有可比對的標註集，A12/A13 的驗證器目前只有 schema 與不變式兩層。
> A16 產出的 `REVIEW.md` 就是下一趟的標註基準——從第二趟起它是前置條件而非交付物，
> 驗證器才補得上第三層。**第一趟的價值是產生標註集，不是通過檢查。**

---

## GRAPH

Routing gate — 觸發三項：執行層邊界（遷移／服務層／渲染器彼此換手）、可平行且寫入路徑互斥、
驗證必須對抗性（渲染器不得替自己的頁面打分）。

```
┌──────────────────────────────┐        ┌───────────────────────────────┐
│ N1  contract                 │        │ N4  migrate  (Cloudflare)     │
│ trip.json schema             │        │ wrangler.toml + worker/       │
│ 目錄命名規則                 │        │ 四支 Function → 一支 Worker   │
│ render(trip)->str 簽章凍結   │        │ 前端 /.netlify/* → /api/*     │
│ tool-surface-v1.json 快照    │        │ scheduled() 保活              │
│ rest.json → places 對應表    │        │ 最後一個 commit 才拆 Netlify  │
│ layer: claude                │        │ layer: claude                 │
└──────────┬───────────────────┘        └───────────────┬───────────────┘
           │ gate: schema 與 render 簽章寫定            │ 與左側無相依
   ┌───────┴────────┐                                   │
   ▼                ▼                                   │
┌────────────┐  ┌──────────────────┐                    │
│ N2 mcp     │  │ N3 renderer      │                    │
│ travel/ 服 │  │ travel/page/     │                    │
│ 務層       │  │ 移植 head3.part  │                    │
│ check_     │  │ 移植地圖 IIFE    │                    │
│ schedule   │  │ 移植 days.py     │                    │
│ tools.py   │  │ scripts/check-*  │                    │
│ instructions│ │ web/trip-pages.js│                    │
│ layer:claude│ │ layer: claude    │                    │
└──────┬─────┘  └────────┬─────────┘                    │
       └────────┬────────┘                              │
                │ join: N2 / N3 / N4 皆 status: done     │
                └───────────────┬───────────────────────┘
                                ▼
                  ┌──────────────────────────────┐
                  │ N5  verify                   │
                  │ 唯讀、對抗性                 │
                  │ 跑 A1–A25，PASS/FAIL + 證據  │
                  │ layer: script                │
                  └──────────────────────────────┘
                     │ FAIL → 回退造成該項的節點（cap 2）
```

### 寫入路徑（互斥，這是可平行的唯一理由）

| 節點 | 可寫 |
|---|---|
| N1 | `mcp-server/src/scout_mcp/travel/schema.py`、`mcp-server/tests/fixtures/`、`trips/_reference/`（唯讀參考，不改） |
| N2 | `mcp-server/src/scout_mcp/travel/{service,paths,schedule,validate,import_reference}.py`、`instructions.py`、`tools.py`、`mcp-server/tests/test_*.py` |
| N3 | `mcp-server/src/scout_mcp/travel/page/**`、`scripts/check-trip-*.mjs`、`web/index.html`、`web/trip-pages.js`、`web/checklist.css` |
| N4 | `wrangler.toml`、`worker/**`、`web/_redirects`、`web/checklist.js`、`web/buylist.js`、`web/share.html`、`web/ai-suggest-core.js`、`netlify.toml`、`web/netlify/**`、`scripts/check-cf-migration.mjs`、`for-chia-cloudflare.md` |
| N5 | `ACCEPTANCE.md`、`KNOWN_ISSUES.md`、`REQUEST_CHECK.md`（唯讀其餘一切） |

**`web/index.html` 只有 N3 能寫，`web/checklist.js` 只有 N4 能寫。** N3 的行程表列表 UI 因此放在新檔
`web/trip-pages.js`，不改 `checklist.js`——這是為了讓 N3 與 N4 真的互斥，不是風格偏好。
N3 對外只暴露純函式 `scout_mcp.travel.page.render(trip: dict) -> str`，簽章由 N1 凍結，N2 呼叫它。

### state — `state/graph-state.json`

| key | 類型 | 寫入者 |
|---|---|---|
| `nodes.<name>.status` | exclusive | 該節點自己 |
| `contract.render_signature` / `contract.schema_path` | exclusive | N1 |
| `baseline.commands` | exclusive | N5（執行開始時） |
| `decisions[]` / `known_issues[]` / `handoffs[]` / `verdicts[]` | append-only | 各節點（handoff 為 `{from,to,task,inputs,acceptance_items_covered,status}`，status ∈ sent/accepted/bounced） |

state 只放路由需要的旗標與檔案路徑，**不放頁面內容、不放 `trip.json` 內容**。

---

## 資料模型（N1 凍結，其餘節點不得各自擴充）

`trips/<YYYY>-<MM>-<cc>-<city>/trip.json`：

```jsonc
{
  "schema_version": 1,
  "trip": {
    "title": "首爾中秋五日",
    "country": "KR", "country_name": "韓國",
    "city": "Seoul", "city_name": "首爾",
    "start_date": "2026-09-21", "end_date": "2026-09-25",
    "party_size": 2, "currency": "KRW",
    "budget": { "per_person_per_meal": { "value": 2000, "currency": "TWD" } },
    "notes": "中秋連假，店休風險高",
    "supabase_trip_id": null,                 // 選填；只用於把既有候選撈進來當素材，不做雙向同步
    "page_slug": "2026-09-kr-seoul-a7f3c2"    // 部署路徑；建立時產生一次就固定
  },

  "flights": [
    { "dir": "out", "date": "2026-09-21", "from": "TPE", "to": "ICN",
      "dep": "10:30", "arr": "14:40", "no": null, "terminal": null, "locked": true }
  ],

  "lodging": [
    { "name": "Oriens Hotel & Residences", "station": "Chungmuro",
      "check_in": "2026-09-21", "check_out": "2026-09-25",
      "address": "…", "lat": 37.5615, "lon": 126.9945, "booking_ref": null, "locked": true }
  ],

  "places": [
    {
      "id": "central-reducer",
      "name": "Central Reducer", "name_local": "중앙감속기", "name_zh": "中央減速機",
      "kind": "meal|shopping|sight|service|cafe|queue",
      "cuisine": ["中式義式融合"],
      "area": "城東區・聖水", "district": "성동구",
      "price_band": { "band": "₩₩", "note": "每人 ₩10,000–40,000", "source": "https://…" },
      "hours": {
        "sources": [                          // 空陣列 = 未查證（A12）；兩筆 value 不同 = 衝突（A13）
          { "value": "12:00–15:00 / 17:30–21:00", "closed_days": [],
            "url": "https://…", "fetched_at": "2026-09-11" }
        ]
      },
      "reservation": { "required": true, "done": false, "difficulty": "advance",
                       "rule": "訂金每人 ₩30,000…", "url": "https://…" },
      "location": { "address": "…", "station": "Seongsu", "exit": "3", "walk_min": 5,
                    "lat": 37.5447, "lon": 127.0557, "map_url": "https://…" },
      "queue_only": false,                    // true = 只進候補清單，不排進時間軸
      "alert": null,
      "sources": ["https://…"],
      "notes": "…",
      "extra": { "chef_name": "崔鉉碩", "chef_bio": "…", "chef_sources": ["…"],
                 "chef_season": "S1 (2024)", "seed_no": 1 }   // rest.json 無法對應的欄位一律進這裡
    }
  ],

  "events": [
    { "id": "e12", "day": 3, "time": "15:30", "dur_min": 210, "min_dur_min": 210,
      "type": "shopping|meal|move|sight|service",
      "title": "聖水洞：延武場街、快閃店", "place_id": "seongsu",
      "locked": false,                        // true = 已訂位／已預約，求解器不得移動
      "sunset_locked": false,                 // true = 鎖在日落前 60 分抵達
      "links": [{ "label": "地圖", "url": "…" }], "note": "…" }
  ],

  "legs": [
    { "from": "yeo", "to": "seong", "mode": "subway", "lines": ["5", "2"],
      "transfer_at": ["Wangsimni"], "min": 40,
      "label_t": 0.5, "label_dx": -58, "label_dy": 0 }   // 地圖標籤微調，可省略
  ],

  "open_questions": [
    { "id": "h7", "date": "2026-09-24", "what": "沙龍國定假日有沒有營業",
      "why": "行程 14:00 開始", "check_by": "2026-09-20",
      "source_hint": "Naver Map", "auto": true }         // auto=true 由 A12/A13 自動產生
  ],

  "stations": [ { "en": "Chungmuro", "zh": "忠武路", "local": "충무로", "days": [1,3,5] } ],

  "sections": {                                          // 選填；有資料才渲染該子分頁
    "pharmacy": { "title": "藥局", "blocks": [ … ] },
    "weather":  { "title": "天氣", "blocks": [ … ] },
    "predeparture": { "todos": [ … ], "packing": [ … ] }
  },

  "map": { "lon0": 126.87, "lon1": 127.13, "lat0": 37.498, "lat1": 37.628,
           "river": [ [lat,lon], … ] }                   // river 可省略
}
```

**不變式**：`places[].id` 唯一；`events[].place_id` 與 `legs[].from/to` 必須存在於 `places`
（或是 `hotel` / `airport` 這類保留 id）；`day` 合法範圍 `1..(end_date−start_date+1)`；
`time` 是 `HH:MM` 純文字、目的地當地時間、**不做任何時區換算**（沿用既有 MCP server 的既定語意）。

### `rest.json` → `places` 對應（N1 產出，供 A17 驗）

| rest.json | places |
|---|---|
| `id` / `name` / `name_ko` | `id` / `name` / `name_local` |
| `cuisine`（字串） | `cuisine`（切成陣列，原字串留在 `extra.cuisine_raw`） |
| `price_band{source,value,band}` | `price_band{band,note:value,source}` |
| `hours{source,value,closed_days}` | `hours.sources[0]{value,closed_days,url:source,fetched_at}` |
| `reservation{source,rule,difficulty}` | `reservation{rule,difficulty,url:source,required:true,done:false}` |
| `address` / `district` / `area` / `gmaps_url` | `location.address` / `district` / `area` / `location.map_url` |
| `catchtable_url` | `reservation.url`（若與 `source` 不同則兩者都留，後者進 `sources[]`） |
| `alert` / `notes` / `sources` | 同名 |
| `seed_no` / `chef_*` | `extra{}` |

---

## 新增的 MCP 工具（既有 8 個一律不動）

| 工具 | 做什麼 |
|---|---|
| `list_trip_files` | 列出 `trips/` 下所有旅程，依出發日新到舊，含國家、城市、日期、頁面路徑 |
| `create_trip_file` | 建立 `trips/<YYYY>-<MM>-<cc>-<city>/trip.json` 骨架；已存在則回傳既有路徑 |
| `read_trip` | 讀回整份 `trip.json`（給 agent 排程與討論用） |
| `upsert_place` | 新增／更新地點；`hours.sources` 是陣列，**追加不覆蓋** |
| `upsert_event` | 新增／更新行程事件 |
| `upsert_leg` | 新增／更新交通段 |
| `upsert_open_question` | 新增／更新待確認 |
| `set_trip_section` | 寫入 `sections`（藥局／天氣／出發前）與 `stations` |
| `check_schedule` | **只回報不修改**：列出所有衝突與「要犧牲什麼」的選項 |
| `build_trip_page` | 產出 `trips/<slug>/index.html` 與 `web/trips/<page_slug>/index.html`，更新 `web/trips/index.json`，回傳兩個路徑 |

**沒有刪除工具。** 既有 server「不具備移除能力」延伸到檔案層：新工具不得刪除任何檔案，
也不得覆寫 `trips/<slug>/` 以外的路徑（A5）。要刪一趟旅程，到檔案總管刪那個資料夾。

---

## server instructions 擴充（`instructions.py`）

既有三條規則保留不動，追加旅程頁模組的規則。這些是**跨 session 都適用、從工具簽章看不出來**的規則，
來源是參考產品第 4 節「決策規則」：

1. **鎖定不可動。** `locked: true` 與 `sunset_locked: true` 的項目，求解器與你都不得移動。
2. **沒有明確同意就不新增內容。** 使用者沒說要的店不進 `places`，更不進 `events`。
3. **查不到就說查不到。** 不猜營業時間或價格；把它變成一筆 `open_questions`。
4. **來源衝突兩個都寫。** 不自己挑一個當正確答案。
5. **距離一律用站數／分鐘算**，不憑印象說遠近。
6. **衝突時列出「要犧牲什麼」讓使用者選**，不自己刪。
7. **站名以英文為主**（現場招牌與地圖 App 都是英文），另附三語對照表。
8. **價位用價位帶**，不寫精確金額當承諾。
9. **現場排隊的店標 `queue_only`**，進候補清單而不是時間軸。
10. **全程繁體中文**，先講結論，有取捨先列選項。
11. **每次回覆分三段：我改了什麼／犧牲了什麼／你要確認什麼。**

---

## Phase A 實作要點（遷移）

```toml
# wrangler.toml（草案；優先順序必須以 A21 的 wrangler dev 實測為準）
name = "scout"
main = "worker/index.js"
compatibility_date = "2026-09-12"

[assets]
directory = "./web"
binding = "ASSETS"

[triggers]
crons = ["17 3 * * 1,4"]   # 台灣時間週一、四 11:17，與 netlify.toml 同值
```

`worker/index.js` 匯出兩個 handler：

- `fetch(request, env, ctx)` — 只處理 `/api/ai-parse`、`/api/ai-suggest`、`/api/share`，
  其餘回 404（靜態資產由平台先行處理，不進 Worker；A21 實測這件事）。
- `scheduled(event, env, ctx)` — 原 `keepalive.js` 的內容。

移植時逐支對照，**行為等價、錯誤訊息等價**：

| 原 | 新 | 移植注意 |
|---|---|---|
| `exports.handler = async (event) => {}` | `export default { async fetch(req, env) {} }` | `event.httpMethod` → `req.method`；`event.body` → `await req.text()`；`event.queryStringParameters` → `new URL(req.url).searchParams`；回傳 `{statusCode, body}` → `new Response(body, {status})` |
| `process.env.GEMINI_API_KEY` | `env.GEMINI_API_KEY` | 值用 `wrangler secret put`，**不進 `wrangler.toml`**（A25） |
| `ai-suggest.js` 的 `node:fs` + `node:vm` 載入共用核心 | `import "../web/ai-suggest-core.js"` 後取 `globalThis.ScoutAiSuggest` | **Workers 沒有 fs／vm**；該檔須維持不含 import/export 語法，才能同時被 `<script>` 與 Worker 用（A23） |
| `netlify.toml` 的 `[functions."keepalive"] schedule` | `[triggers] crons` | Pages 不支援 cron，這是選 Workers 不選 Pages 的原因 |
| 前端 `/.netlify/functions/x` | `/api/x` | 同時留 `web/_redirects` 一行相容轉址；A20 斷言 JS/HTML 內不得再有 `.netlify/functions` |

`web/_redirects`（Workers static assets 原生支援）：

```
/.netlify/functions/*  /api/:splat  200
```

---

## INTERVIEW（Stanley 已回答，記錄在此供執行端參照）

| # | 問題 | 答案 |
|---|---|---|
| Q1 | 有沒有參考產品的原始檔？ | **有，已提供**。放在 `trips/_reference/`（`head3.part`、`body2.part`、`build2.py`、`days.py`、`rest.json`、`seoul-chuseok.html`、`legacy/`）。**直接移植 CSS 與地圖 IIFE，不重寫。** |
| Q2 | `trips/` 要不要進版控？ | **要**。repo 僅 Stanley 與 Chia 使用、不公開，`trip.json` 可安全進版控。 |
| Q3 | 建置產物要不要放上網？ | **要**。寫進 `web/trips/`，跟著 Scout 一起部署，路徑含 6 碼隨機碼（A15）。風險比照 ADR-013「網址即憑證」，須寫進 `DECISIONS.md`。 |
| Q4 | 手機溢位要不要用 Playwright 實測？ | **不要**，用 A10 靜態規則。理由：ADR-010 零 build step；代價寫進 `KNOWN_ISSUES.md`。 |
| Q5 | 地圖用示意投影還是真地圖磚？ | **示意投影**，直接沿用 `body2.part` 的 IIFE（換城市只需換投影範圍、`P{}`、`DAYS{}`）。真地圖磚需要網路，與 A9 衝突。**畫布大小固定**，不隨日期縮放。 |
| Q6 | 要不要對應 Supabase 的 `trips` 列？ | **選填、單向**。`trip.json` 可存 `supabase_trip_id`，只用於撈素材，不做雙向同步。 |
| Q7 | 深淺色主題要不要做？ | **要**，`head3.part` 已有（CSS 變數 + `prefers-color-scheme`），照搬即可。 |
| Q8 | 託管平台 | **搬到 Cloudflare**。目標為 **Workers（Static Assets）**，不是 Pages——Pages 不支援 Cron Trigger，保活排程會死。 |

執行時若還有未決問題，**一批問完、每題帶預設、沉默即預設**；之後不再問，寫 `DECISIONS.md` 繼續。

---

## BOUNDS

- **Loop-back cap**：每節點 2 次。用盡後繼續前進，寫 `KNOWN_ISSUES.md`，對應 A-item 標 FAIL。
- **Scope-cut 順序**（不夠時依序砍）：
  `sections` 的藥局／天氣子分頁 → 排隊候補的地圖定位互動 → 深淺色主題 → 地圖每段「線號＋分鐘」標籤（退成純文字 legs 表）
- **絕不砍**：
  A24（可回退）、A21／A22（Cloudflare 實跑與保活）、A9（自含單檔離線）、A7（單一資料來源）、
  A11（檢查器只報不改）、A1／A2（不回歸）、A5（路徑逃逸防護）、A25（金鑰不進版控）
- **外部相依，以 stub＋lead time 處理，不得假裝已完成**：

| 項目 | 為什麼卡 | 本次怎麼做 | lead time |
|---|---|---|---|
| **Cloudflare 帳號連上 `CHIAHSIN-tech/Scout`** | ADR-014 把 repo 轉給 Chia，正是因為她的 **Netlify** 接著她的 GitHub。搬到 Cloudflare 等於**部分推翻 ADR-014 的理由**——Chia 需要自己的 Cloudflare 存取權，否則部署自主權會退回 Stanley 身上。 | 本次**只寫設定檔，不部署**。另產 `for-chia-cloudflare.md`，寫清楚她要做的每一步。 | 需 Chia 本人，未知 |
| **`GEMINI_API_KEY` 設為 Worker secret** | 金鑰不能進版控 | 寫進交接文件，程式讀 `env.GEMINI_API_KEY`，缺值時回與現行相同的 500 訊息 | 人工，分鐘級 |
| **網址變更 / 自訂網域** | `shoppingtool.netlify.app` 之類的既有網址會換 | 本次不處理；`share` 連結若已發給家人，切換後會失效——**這件事必須在 `for-chia-cloudflare.md` 明寫** | 未知 |
| **Netlify 站台停用** | 要等 Cloudflare 實際驗過 | 本次只刪 repo 內的 `netlify.toml` 與 `web/netlify/`（最後一個 commit，A24）；**Netlify 後台的站台由人自行停用** | 人工 |
| **首爾那趟的人工複核（A16）** | 需要 Stanley 本人看過 | 標為交付物非 gate | 人工 |

---

## EXECUTION RULES

1. **一次訪談。** 問題只在開始問、一批問完、每題帶預設、沉默即預設。之後卡關不再問——
   寫 `DECISIONS.md` 一筆（卡在什麼、假設了什麼、怎麼回頭改）後繼續。
2. **驗證器優於印象。** 節點完成 = 它的驗證命令 exit 0。主觀疑慮寫 `KNOWN_ISSUES.md`，
   只有命令可檢測的問題才退回重做。
3. **N5 唯讀且對抗性。** 判決 PASS/FAIL 附 `file:line` 證據並寫進 state。生產節點修，
   N5 只重驗失敗那一項。渲染器不得驗自己的頁面，遷移節點不得驗自己的遷移。
4. **失敗隔離。** 重試在節點內部。下游以上游的 `status: done` 為閘門。
5. **先勘查再動工。** 動手前讀 `context.md`（特別是第 4 章 ADR 與第 6 章已知限制）、`CLAUDE.md`、
   `mcp-server/README.md`、`specs/spec-scout-mcp-server.md`、`trips/_reference/README.md`。
   共用型別只有一份——`trip.json` 的 schema 定義在 `travel/schema.py`，任何地方要驗結構都 import 它，
   **不得出現第二份欄位清單**；`ai-suggest-core.js` 同理，永遠只有一份實作。
6. **必要產出物**：`ACCEPTANCE.md`（第一節就是 A1–A25 的 PASS/FAIL 表與原始命令輸出）、
   `state/graph-state.json`、`DECISIONS.md`、`KNOWN_ISSUES.md`、`REQUEST_CHECK.md`、
   `for-chia-cloudflare.md`。**任一 A-item FAIL，整個 run 報告為失敗**，不論產出多少。
7. **收尾報告以原始請求為準，不以本規格為準。** `REQUEST_CHECK.md` 三張清單，每行標明在哪裡驗的：
   **要求且已交付**／**要求但缺席**（附原因）／**交付但沒人要求**。請求裡有、卻沒有任何 A-item 回答的限制，
   即使 A-item 全過也要列進第二張清單。只寫分歧；一致處一句話帶過。
8. **本專案既有紀律**（`CLAUDE.md`）：註解與回覆用繁體中文、範疇最小、小步 commit、
   重構與功能變更分開提交、絕不 commit 機密；commit 格式 `feat: / fix: / refactor: / docs: / chore:`；
   用 branch 開發不直推 main。
9. **必須新增的 ADR**（`context.md` 第 4 章），完成前不算 done：
   - **ADR-018：託管由 Netlify 遷移至 Cloudflare Workers（Static Assets）** — supersedes ADR-011；
     須明寫「選 Workers 不選 Pages 是因為 Pages 不支援 Cron Trigger」，以及對 ADR-014 部署自主權的影響。
   - **ADR-019：旅程頁模組以本機 `trip.json` 為 SSOT** — 與 ADR-012（不合併兩個 Supabase 專案）、
     ADR-016（MCP server）並存，不取代；須說明為何不進 Supabase。
   - **ADR-010 補註**：引入 `wrangler` 作為**部署工具**。前端仍無 build step、無打包器；
     這是對「零 build step」的一次界線澄清，不是推翻。
   完成後更新 `CHANGELOG.md`，並在 `specs/README.md` 索引補一列。

---

## NON-GOALS

明確不做，且**不得因為「順手」而做**：

- 不改 Supabase schema，不動 `trips` / `itinerary_items` / `buylist_items` 的任何既有欄位
- 不新增任何刪除工具（延續既有決策），也不用「清空欄位」變相刪除
- 不動 `sw.js`、不做 service worker 離線快取（2026-08-17 決策：會快取的 SW 只會讓「線上跑舊版」的坑更深）。
  **離線 = 單檔自含、使用者自己存到手機**，不是 PWA 快取
- 不引入前端 build step、不引入打包器、不把既有靜態檔改成模組化（ADR-010 仍然有效）
- 不接 Google Places / Naver / ODsay / KMA 任何外部 API；事實查證維持 WebSearch／WebFetch
- 不做拖拉式行程編輯 UI，也不做「拖一個行程即時看見連鎖影響」的互動版
- 不做自動取捨：塞不下時一律回報選項給人選，程式永遠不自己刪行程
- 不做帳號系統、不做權限控制、不改 ADR-013 的「網址即憑證」模型
- 不把 `trip.json` 遷進 Supabase，也不做雙向同步
- 不改既有 8 個 MCP 工具的名稱或簽章
- 不做資料遷移（既有 `itinerary_items` 的舊資料不搬進 `trip.json`）
- 不做 `.ics` / Google My Maps 匯出（`export-formats.js` 已有，不重做第二份）
- **不改網域、不設自訂網域、不動 DNS**
- **不在 Cloudflare 後台操作**（不建專案、不設 secret、不接 GitHub）——那些是人的步驟，寫進交接文件
- 不把 buylist 或 checklist 的功能一起重構（遷移只改 API 路徑，不改功能）

**延後，附理由**（參考產品有、本次不做）：

| 項目 | 為什麼延後 |
|---|---|
| Playwright 截圖與溢位實測 | 需要 node_modules 與新的 CI 前提（INTERVIEW Q4） |
| 公休風險分數（依節日／週幾／來源新舊給風險值） | 需累積多趟資料才知道權重怎麼給 |
| 出發前時間軸（D-7 查預報、D-3 查公休、D-1 打包） | 該用排程任務做，不是這個模組的責任 |
| 排隊候補「點卡片跳到地圖位置」 | scope-cut 順位第二，先確保候補清單本身存在 |
| 多趟旅程共用地點庫（去過的店累積成 seed） | 需 ≥2 趟真實資料才知道欄位夠不夠；`rest.json` 已可當首批種子 |
| Cloudflare 的 D1／KV／R2 等服務 | 本次只做等價遷移，資料層維持 Supabase（ADR-007／012） |

---

## CHECKLIST ANSWERED

**1. 沒寫這段程式的人能不能逐條驗每個 A-item？**
能。A1–A15、A17、A20–A25 全部是可貼的命令，fixture、凍結快照與參考資料（`trips/_reference/rest.json`
的 39 家真實餐廳）都在 repo 裡。A16 是人的目視核對，但它產出一個可檢查存在與行數的檔案，不是「感覺對了」。

**2. 有沒有哪一項宣稱可用、其實卡在外部核准？**
有五項，全部列在 BOUNDS 的外部相依表並加了 lead time：Cloudflare 帳號與 GitHub 連接、
`GEMINI_API_KEY` secret、網址變更、Netlify 站台停用、A16 人工複核。
**本次一律只寫設定檔與交接文件，不進任何供應商後台、不執行部署**，所有 A-item 都在本機可驗
（A21／A22 用 `wrangler dev`，不需要帳號）。外部 API（Places／Naver／KMA）不在範圍，
schema 已預留 `url` 與 `fetched_at`，換來源不需改結構。

**3. Scope-cut 順序有沒有保護住驗收表？**
有。可砍的四項全不對應任何 A-item（藥局／天氣子分頁、候補地圖定位、深淺色主題、地圖標籤），
`sections` 本來就是「有資料才渲染」。絕不砍清單直接對應 A24／A21／A22／A9／A7／A11／A1／A2／A5／A25。
若真要砍一個 A-item，那是規格修訂，寫 `DECISIONS.md`，不是默默丟掉。

**4. 參考產品與被取代系統的每一項，有沒有都落進「做／不做／延後」三桶之一？**
有，逐節對照過。
**參考產品**：第 2.2 節三個主分頁與子分頁——行程／地圖／車站／出發前**做**，藥局／天氣**做但 scope-cut 第一**；
第 2.3 節互動——三層 tab **做**、localStorage 勾選**做**、深淺色主題**做（cut 第三）**、候補點選定位**延後**；
第 3.1 節排程演算法——步驟 1–4 **做**（`check_schedule`）、步驟 5「不自動決定」**做（A11）**；
第 4 節決策規則——**全部做**，寫進 `instructions.py`；第 5 節資料模型——**做**（本規格的 `trip.json`）；
第 6 節實作技巧——CSS／地圖 IIFE／`days.py`／`build2.py` 的 `assert '{{' not in t` **全部移植**，
Playwright **延後**；第 7 節查證——WebSearch/WebFetch **做**、抓不到變待確認**做（A12）**、
衝突往下游傳**做（A13）**；第 8 節八個坑——全部轉成規則或 A-item（自己加內容→A8、連鎖更新→A7、
地圖縮放→Q5 固定畫布、往返合併→`legs` 分向、CSS 跑到 `</style>` 外→模板組裝不 append）；
第 9.2 節差異化——鎖定機制**做**、取捨對話**做**、拖拉看連鎖影響**不做**、公休風險分數**延後**、
夜間動線檢查**做（A11 第 4 類）**、出發前時間軸**延後**；第 9.3 節外部 API——**全部不做**；
第 9.4 節 LLM 架構——查證與排程分離**做**、硬規則進系統提示**做**、輸出固定 JSON 由程式 render **做**、
三段式回覆**做**。
**被取代的 Netlify 設定**：`ai-parse`／`ai-suggest`／`share`／`keepalive` 四支**全做**（A20–A22）；
`netlify.toml` 的 `node_bundler = "esbuild"` **不做**（Workers 自帶；`ai-suggest.js` 的 fs/vm 相依改成 import）；
`publish = "web"` → `[assets] directory`**做**；Netlify 的 deploy preview／表單／Identity 等功能
**專案本來就沒用，不做**。

**5. 沒讀過 Graph Protocol 的人能不能執行這份規格？**
能。loop-back cap、驗證器判定權、各節點寫入邊界、必要產出物清單、必須新增的三筆 ADR，
全部寫在本檔內，不靠引用。本檔可單獨貼給任何 agent。

**6. 讀寫個人資料的表面，有沒有 A-item 斷言錯誤憑證會被拒？**
分兩塊，誠實回答：
**旅程頁模組不新增任何網路端點、不新增權限面**——它寫本機檔案，路徑由 A5 的 `resolve_trip_path()`
鎖死（四個逃逸案例）。
**真正的存取風險有兩處，都沒有被任何 A-item 修好，也修不了**：
(a) 建置產物部署後是公開網址、只靠 6 碼隨機路徑（A15），沒有憑證檢查；
(b) `/api/share` 沿用既有的「匿名可讀、欄位白名單」模型。
兩者都是 ADR-013 既有且已接受的風險模型的延伸，但**旅程頁的內容更敏感（訂位編號、旅館地址、班機時刻）**，
所以必須在 `DECISIONS.md` 明寫這個取捨，不可默默採用。
本規格對 A25（金鑰不進版控）與 `web/_redirects` 不得開放任意轉址則有明確斷言。

**7. 全部 A-item 都過了，系統有沒有可能還是不好用？**
有三個缺口，都已納入：
(a) **頁面在真手機上好不好讀**——A10 只驗溢位規則、不驗可讀性，這是 A16 存在的理由，
Stanley 必須在真手機上開過一次那 20 條核對。
(b) **`check_schedule` 報得準不準**——A11 只驗它抓得到我們寫進測試的五類衝突，不驗「真實行程裡的衝突都抓得到」。
靠 A16 首跑把漏掉的衝突記成 `WRONG:`，成為第二趟的測試案例。
(c) **遷移後「線上是不是真的新版」**——本次所有 A-item 都在本機驗，`wrangler dev` 過不代表線上通。
這正是 BOUNDS 把部署列為外部相依、並要求 A24 可回退的原因；`for-chia-cloudflare.md` 必須寫明
「切換後第一件事是打開線上站台確認版本」，這個專案有手動部署造成線上跑舊版的前科。

---

Written under GRAPH_PROTOCOL v2.7.
