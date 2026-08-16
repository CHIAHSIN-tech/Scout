# TASK: 雙 Tab 視覺統一 ＋ 行程可匯入 Google 日曆／Google Maps

> **Status**：done（2026-08-16 落地）。A1–A10 全部 PASS、無項目被砍。
> 驗收表與原始命令輸出見 [`ACCEPTANCE.md`](../ACCEPTANCE.md)；
> 取捨見 [`DECISIONS.md`](../DECISIONS.md)；建議事項見 [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md)。

## OBJECTIVE

合併版 web app 的兩個 Tab 共用同一套字體與顏色權杖（token），且任一趟行程能匯出成 Google 日曆與 Google Maps 讀得進去的檔案與連結。

## WHY IT MATTERS

兩個 Tab 是同一個網址下的同一個產品，但目前行程端用襯線體標題、購物端用無襯線，且兩邊各自定義了**同名不同值**的 CSS 變數（`--muted` 一邊是 #6B6558、一邊是 #A8A298；`--green` 一邊 #5C8C72、一邊 #3D6B54）。後果不只是「看起來不像同一個 app」——真正的成本是往後任何一次改色，改的人會以為改到兩邊，實際只改到一邊，而且不會有任何錯誤訊息告訴他。這個缺陷會隨每次改動放大。

匯出的價值在於行程資料目前是**孤島**：規劃好的行程無法進到出發當天真正會用的兩個工具（手機日曆提醒、地圖導航），等於每趟出發前都要手動再抄一次。抄錯的成本是現場走錯地方或錯過訂位時間。

## SUCCESS MEASURED BY

> 全部從 repo 根目錄執行。驗證腳本只准使用 Node 內建模組（見 BOUNDS 的無 build step 限制）。

**視覺統一**

- **A1.** 全站不再載入或引用襯線體。
  check：`! git grep -q "Noto Serif" -- web/`（exit 0 即通過）
- **A2.** `web/checklist.css` 的 token 定義區塊之外，不存在任何裸露的 hex 色碼（所有顏色都走變數）。
  check：`node scripts/check-style.mjs --no-raw-hex` exits 0
- **A3.** `#panel-shop` 與 `#panel-trip` 兩個區塊中，**同名的 token 一律同值**（消滅同名不同值）。
  check：`node scripts/check-style.mjs --token-parity` exits 0
- **A4.** 兩份 CSS 與所有 JS 通過語法檢查（改動未破壞檔案）。
  check：`node --check web/checklist.js && node --check web/buylist.js && node --check web/export-formats.js` exits 0

**匯出**

- **A5.** 給定測試資料，產出的 `.ics` 內容含 `BEGIN:VCALENDAR`、`VERSION:2.0`，且 `BEGIN:VEVENT` 出現次數**等於已排入行程（`day_number` 非 null）的項目數**——候選項目不得成為事件。
  check：`node scripts/check-exports.mjs --ics` exits 0
- **A6.** `.ics` 中每個 VEVENT 都有 `DTSTART` 與 `DTEND`，且 `DTEND` 由 `duration_minutes` 推出；`duration_minutes` 缺值時預設 60 分鐘。
  check：`node scripts/check-exports.mjs --ics-times` exits 0
- **A7.** 每個已排入的項目都能產生一個「加到 Google 日曆」連結，格式為 `https://calendar.google.com/calendar/render?action=TEMPLATE`，且帶有 `text` 與 `dates` 參數，`dates` 形如 `YYYYMMDDTHHMMSS/YYYYMMDDTHHMMSS`。
  check：`node scripts/check-exports.mjs --gcal-link` exits 0
- **A8.** My Maps CSV 第一列表頭恰為 `name,location,day,time,notes`，且**只輸出 `location` 非空的項目**，逗號與引號依 RFC4180 跳脫。
  check：`node scripts/check-exports.mjs --csv` exits 0
- **A9.** 每個有 `location` 的項目都能產生一個地圖連結，格式為 `https://www.google.com/maps/search/?api=1&query=<URL-encoded location>`。
  check：`node scripts/check-exports.mjs --maps-link` exits 0

**未引入建置相依**

- **A10.** repo 根目錄仍無 `package.json`，`netlify.toml` 未被修改，且 `web/` 底下未新增任何 `node_modules`。
  check：`test ! -f package.json && git diff --quiet -- netlify.toml && test ! -d web/node_modules` exits 0

## GRAPH

**Routing gate：無觸發 → 單節點（single node, single verifier）。**

逐項對照觸發條件：專業分工上兩塊工作都是前端 CSS/JS，無需不同工具或模型；平行工作流的寫入路徑**並非互斥**（匯出功能要在行程卡片加按鈕，會動到 `checklist.css`，與樣式統一同檔），因此本來就該循序；驗證全部是命令式檢查（grep 與 Node 腳本），不是產出者自評印象，因此不需要對抗式審查節點；無階段失敗會污染其他階段；路由無需稽核。

依 §2「a node that could be inlined is not a node」，本任務為單一 agent 迴圈（discover → plan → execute → verify），不畫多節點圖，不建 `state/graph-state.json` 以外的協調機制。

## INTERVIEW（一批問完，每題帶預設；沉默即採預設）

- **Q1.** `.ics` 的時間要用哪種時區表示？ — **預設：floating local time**（`DTSTART:20260815T090000`，不帶 `Z`、不帶 `TZID`）。
  理由與風險：行程的 `start_time` 是**目的地當地時間**，但 `trips` 表沒有時區欄位。floating 讓「9:00」在使用者日曆裡就顯示 9:00；代價是若使用者日曆時區為台北而行程在日本，提醒會早響一小時。改用 `TZID` 需要先在資料表補時區欄位，超出本任務範圍。此取捨須寫入 `DECISIONS.md`。
- **Q2.** 匯出範圍是「當前選定的旅程」還是全部旅程？ — **預設：只匯出當前選定的旅程**。
- **Q3.** 匯出入口放哪？ — **預設：行程 Tab 的工具列**（與現有檢視切換同一列），三個入口：「⬇ 匯出 .ics」「⬇ 匯出地圖 CSV」，以及每張行程卡片上的兩個小連結（加到日曆／開地圖）。
- **Q4.** 候選項目（未排入行程、`day_number` 為 null）要不要進匯出？ — **預設：不進 `.ics`**（沒有日期無法成為事件）；**進地圖 CSV**（只要有 `location` 就輸出，`day` 與 `time` 欄留空），因為「還沒排時間但想去的地方」在地圖上仍有意義。
- **Q5.** 統一樣式時，行程端既有的綠色系語意標籤（已確認／需確認）要保留嗎？ — **預設：保留語意，但改用購物端的色票值**，不新增顏色。

## BOUNDS

- **Loop-back cap：** 每個階段最多 2 次退回；用盡後繼續前進，將該項記入 `KNOWN_ISSUES.md`，並把對應的 A-item 標為 **FAIL**。
- **Scope-cut order（先砍前面）：** My Maps CSV 匯出（A8） → `.ics` 檔下載（A5、A6） → 其餘不砍。
  理由：手機上真正會用的是「每張卡片的加到日曆／開地圖連結」，整包匯出是桌面規劃用途，價值較低。
- **Never cut：** 字體與 token 統一（A1–A4）、每張卡片的 Google 日曆連結（A7）、每張卡片的地圖連結（A9）、不引入 build step（A10）。
- **砍任何 A-item 等同修改規格**，必須寫入 `DECISIONS.md`，不得靜默移除。
- **External dependencies stubbed：** 無。本任務**不需要**任何 Google API 金鑰、OAuth 或帳號授權——`.ics` 與 CSV 是本地產檔，兩種連結是純 URL 組裝。唯一的人為步驟是使用者自己把檔案匯入 Google（且 `.ics` 匯入 Google 日曆**只能在電腦版瀏覽器操作，手機無法匯入**，此限制須在 UI 上以一行提示告知，不得假裝手機可用）。

## EXECUTION RULES

1. **一次訪談。** 問題只在開始時問，一批問完，每題帶預設；沉默即採預設。之後遇到阻礙不再回頭問，改為寫入 `DECISIONS.md`（什麼卡住、假設了什麼、如何回復），然後繼續。
2. **驗證器優先於印象。** 一個階段完成的定義是它的驗證命令 exit 0。主觀疑慮（例如「這個間距看起來怪」）寫進 `KNOWN_ISSUES.md` 當建議，**只有命令可檢測的失敗才退回重做**。
3. **審查只讀且抱持懷疑。** 判定只有 PASS/FAIL 並附 `檔案:行號` 證據。修正由產出方進行，複查只重驗失敗的部分。
4. **失敗隔離。** 重試在該階段內部完成；後續階段以前一階段 `status: done` 為前提才開始。
5. **先偵察後施工。** 動手前先讀 `web/shell.css`、`web/buylist.css`、`web/checklist.css`、`web/index.html` 的既有結構與命名。**共用型別／工具只能有一份**：純函式（`.ics`、CSV、兩種 URL 的組裝）必須集中在新檔 `web/export-formats.js`，由 `checklist.js` 與驗證腳本共用，同一個格式邏輯不得存在第二份實作。
6. **必要產出物：** `ACCEPTANCE.md`、`DECISIONS.md`、`KNOWN_ISSUES.md`，以及最終報告——報告的**第一節必須是 A1–A10 的 PASS/FAIL 表格與原始命令輸出**。只要有任一項 FAIL，整趟執行即報告為失敗，不論完成了多少其他工作。
7. **不得偽造通過。** 驗證腳本不得為了通過而放寬條件；若某項確實做不到，標 FAIL 並說明。

**技術限制（違反即等於任務失敗）：**

- 本 repo **刻意不使用 build step**（見 `netlify.toml` 註解與 ADR-010）。驗證腳本一律放 `scripts/`（不在 `web/` 底下，不會被發佈），且**只准使用 Node 內建模組**，不得新增 `package.json`、不得 `npm install`。
- `web/export-formats.js` 必須能同時被瀏覽器的傳統 `<script>`（現行 `index.html` 用傳統標籤載入，非 module）與 Node 驗證腳本讀取。做法：檔案掛載到全域物件（例如 `window.ScoutExport`），Node 端用內建 `node:vm` 以假的 `window` 求值後取出純函式。此路徑不得引入任何相依套件。
- 統一樣式**以購物 Tab（`#panel-shop`）為準**：字體全站統一 `Noto Sans TC`，行程端標題的 `Noto Serif TC` 一併從 `index.html` 的 Google Fonts 連結移除（少載一套字重）。行程端 token 改名／改值向購物端對齊，**不得反向修改購物端色票**。

## NON-GOALS

以下明確不做。這些項目在本次執行中出現，一律視為越界：

- **不做與 Google 的雙向同步**：不從 Google 日曆或 Maps 讀回資料，不做 OAuth 登入，不呼叫任何 Google API。
- **不把 token 抽成共用樣式層**（不把 `#panel-shop` / `#panel-trip` 的變數上移到 `shell.css` 成為單一來源）。此選項已被明確評估後不採用，理由是改動範圍過大；本次只要求「同名同值」。
- **不改任何資料表結構**，不新增欄位、不跑 DDL。
- **不補 `address` 欄位的使用**：資料表雖有 `address`，現行 web 版完全未使用，地圖匯出一律以 `location` 為準。補 `address` 是另一件事。
- **不做 `.ics` 的進階功能**：不產生 `RRULE` 重複規則、不加提醒（`VALARM`）、不加與會者、不做行事曆訂閱網址（webcal feed）。
- **不動購物 Tab 的任何功能邏輯**（只允許因 token 對齊而必要的樣式調整）。
- **不做行程 Tab 的編輯／刪除補功能**——那屬於 `specs/spec-itinerary-restore-edit-delete.md`，不得順手一起做。
- **不做手機版 `.ics` 匯入的替代方案**（例如自架訂閱網址）；手機限制以 UI 提示告知即可。
- **不做匯出歷史紀錄、不存檔到後端**：匯出是當下產檔即走。

## CHECKLIST ANSWERED

> §6 五問，逐項書面作答。

**1. 沒寫這段程式的人能否逐項檢查每個 A-item？**
能。A1 是一行 `git grep`；A2–A3 是 `scripts/check-style.mjs` 的兩個旗標；A4 是 `node --check`；A5–A9 是 `scripts/check-exports.mjs` 的五個旗標，全部以固定測試資料執行、與畫面無關；A10 是三個檔案系統斷言。所有命令都寫在 A-item 旁，複製即可執行，不需要理解實作。

**2. 是否有任何宣稱可用、實則依賴外部核准的東西？**
沒有。本任務不需要 Google API 金鑰、OAuth 或任何帳號授權。有兩個**人為步驟**必須誠實標示、不得計入自動驗收：(a) 把 `.ics` 匯入 Google 日曆需使用者手動操作，且**僅限電腦版瀏覽器**；(b) 把 CSV 匯入 Google My Maps 需使用者手動上傳。A-item 只驗「產出的檔案格式正確」，不驗「已經進到 Google 帳號裡」——後者不在本 session 能力範圍，不得偽稱通過。

**3. Scope-cut order 是否保護驗收表？**
是。砍除順序（My Maps CSV → `.ics` 下載）明確對應到會失效的 A-item（A8 → A5、A6），且已聲明**砍任一 A-item 即為規格修改，必須寫入 `DECISIONS.md`**，不得靜默移除。Never-cut 清單保住了核心價值（樣式統一與兩種手機可用的連結）。

**4. 參照系統的表面是否每一項都落進「做／不做／延後」三個桶之一？**
參照系統有二。其一是**現行 app 自身的樣式表面**：字體家族、顏色 token、圓角 token、字級——前三者在 scope 內（A1–A3）；**字級（font-size）刻意延後**，理由是行程端字級全部寫死、購物端也未建立字級 scale，統一字級等於重排整個版面，遠超本任務預算，且不影響「同名不同值」這個真正的缺陷。其二是 **Google 的匯入表面**：`.ics` 檔匯入、Google 日曆 TEMPLATE 連結、My Maps CSV/KML 匯入、Maps 搜尋連結——前述四項中 KML **明確不做**（CSV 已足夠且更易產生），其餘三項在 scope 內；`.ics` 的 `RRULE`／`VALARM`／訂閱 feed 已列入 NON-GOALS。My Maps 的 2,000 筆／每圖 10 圖層上限經查證遠高於本專案規模，不需處理。

**5. 沒讀過 Graph Protocol 的人能否執行這份規格？**
能。執行規則（訪談一次、驗證器 exit 0 才算完成、只有命令可檢測的失敗才退回、退回上限 2 次、必要產出物清單、報告首節為 PASS/FAIL 表）已**完整重述於 EXECUTION RULES 與 BOUNDS**，不是引用。無 build step、驗證腳本只用 Node 內建模組、共用純函式只能有一份等技術限制亦寫在規格內。本規格可獨立貼出執行，不需附上 protocol。

---

Written under GRAPH_PROTOCOL v2.2.
