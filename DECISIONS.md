# DECISIONS — 雙 Tab 視覺統一 ＋ 行程匯出

規格：[`specs/TASK-ui-unify-and-calendar-maps-export.md`](specs/TASK-ui-unify-and-calendar-maps-export.md)
本檔記錄執行過程中「規格沒有明講、由執行端決定」的取捨。**沒有任何 A-item 被砍。**

---

## D1 — `.ics` 採 floating local time（規格 INTERVIEW Q1 的預設，沉默即採用）

`DTSTART:20260901T100000`，不帶 `Z`、不帶 `TZID`。

**取捨**：`trips` 表沒有時區欄位，`start_time` 是**目的地當地時間**。floating 讓「9:00」在使用者日曆裡就顯示 9:00。
**代價**：若使用者的日曆時區是台北、行程在日本，提醒會早響一小時。
**為什麼不修**：改用 `TZID` 需要先在資料表補時區欄位，屬規格 NON-GOALS（不改資料表結構）。

## D2 — 已排入某天但沒填時間的項目，`.ics` 用 09:00 起算

規格 A5 要求「VEVENT 數 == `day_number` 非 null 的項目數」，A6 要求每個 VEVENT 都有 DTSTART/DTEND。
兩者相加，代表「排了天但沒填時間」的項目**必須**成為事件，卻沒有時間可用。

**決定**：預設 `09:00`（常數 `DEFAULT_TIME`，與 AI 匯入既有的預設值一致）。
**沒有選的作法**：做成全日事件（`DTSTART;VALUE=DATE`）——那樣就沒有能由 `duration_minutes` 推出的 DTEND，會直接違反 A6。

## D3 — 行程端主色改名為 `--brand`，而不是改值

`--green` 在兩邊同名不同值（行程 `#3D6B54` / 購物 `#5C8C72`），是 A3 要消滅的缺陷。
規格限制「以購物端為準、不得反向修改購物端」。

**決定**：
- 行程端原本的 `--green`（`#3D6B54`，主色）改名為 **`--brand`**——購物端沒有這個名字，不構成同名衝突。
  這個值在購物端叫 `--blue`，但把行程端的森林綠叫成 `--blue` 只會更難讀。
- 行程端原本的 `--green-line`（`#5C8C72`）改名為 **`--green`**，與購物端同名同值。
- 同理 `--sub`→`--muted`（`#6B6558`）、原 `--muted`→`--faint`（`#A8A298`），兩個新名字都與購物端同名同值。

**沒有選的作法**：把 token 抽到 `shell.css` 成為單一來源——規格 NON-GOALS 明確排除。

## D4 — 新增 `--warn-ink`，因為 `--amber` 當文字色對比不足

`--amber` 依規則對齊購物端的 `#C4915A`。但行程端有多處把 amber 當**文字色**用
（`.banner.warn`、`.tl-item-warn`、衝突時間、必須確認的數量徽章）。
`#C4915A` 對米色底約 2.3:1、白字對 `#C4915A` 約 2.5:1，都低到看不清楚。

**決定**：`--amber` 保留給邊框與底色；文字改用新 token `--warn-ink: #7A5230`。
**這不算「新增顏色」**（規格 Q5 要求不新增）：`#7A5230` 就是購物端 `--red` / `--need` 的既有值，只是在行程端換個語意名字。對比拉到約 6.5:1。

## D5 — 匯出入口放在工具列**下方獨立一列**，不塞進既有 toolbar

規格 Q3 預設是「行程 Tab 的工具列」。既有 `.toolbar` 是 `space-between` 的三格（重新整理／AI 匯入／更新時間），再塞兩個按鈕加一行說明，在 375px 寬會擠成不可讀。

**決定**：緊接在 toolbar 下方新增 `.exportbar`，含兩個匯出按鈕、手機限制說明、訊息列。位置與意圖一致（仍在頁面頂部的工具區），只是不共用同一個 flex 容器。

## D6 — `.ics` 手機限制寫在畫面上，不只寫在文件裡

規格 BOUNDS 要求「此限制須在 UI 上以一行提示告知，不得假裝手機可用」。
畫面上的原文：

> `.ics` 只能用**電腦版瀏覽器**匯入 Google 日曆，手機匯不進去；手機請用每個項目的「📅 加到日曆」。CSV 是給 Google My Maps 手動上傳用的。

## D7 — 地圖匯出一律用 `location`，`address` 欄位維持沒人用

規格 NON-GOALS 明列。但同一天完成的另一份規格
（`spec-itinerary-restore-edit-delete.md`）把 `location` 與 `address` **都**加進了編輯表單，
所以 `location` 從此有正常的填寫路徑——地圖匯出因此真的有資料可用，不是空殼。

## D8 — 驗證腳本用 `node:vm` 讀 `web/export-formats.js`，不複製一份實作

規格 EXECUTION RULES 第 5 條要求「同一個格式邏輯不得存在第二份實作」。
`export-formats.js` 掛在全域物件上，瀏覽器用傳統 `<script>` 載入，Node 端用內建
`node:vm` 餵一個假的 `window` 求值後取出純函式。零相依、零 build step。
