# ACCEPTANCE — 雙 Tab 視覺統一 ＋ 行程匯出 Google 日曆／Maps

規格：[`specs/TASK-ui-unify-and-calendar-maps-export.md`](specs/TASK-ui-unify-and-calendar-maps-export.md)
執行日期：2026-08-16　／　全部命令從 repo 根目錄執行

## A1–A10 驗收表

| A-item | 內容 | 結果 |
|---|---|---|
| A1 | 全站不再載入或引用襯線體 | ✅ PASS |
| A2 | `checklist.css` token 區塊外無裸露 hex | ✅ PASS |
| A3 | `#panel-shop` / `#panel-trip` 同名 token 同值 | ✅ PASS |
| A4 | 兩份 CSS 與三支 JS 通過語法檢查 | ✅ PASS |
| A5 | `.ics` 的 VEVENT 數 == 已排入項目數，候選不成為事件 | ✅ PASS |
| A6 | 每個 VEVENT 都有 DTSTART/DTEND，缺 duration 預設 60 分 | ✅ PASS |
| A7 | 每個已排入項目都能產生 Google 日曆 TEMPLATE 連結 | ✅ PASS |
| A8 | My Maps CSV 表頭正確、只輸出有 location 者、RFC4180 跳脫 | ✅ PASS |
| A9 | 每個有 location 的項目都能產生地圖連結 | ✅ PASS |
| A10 | 未引入建置相依（無 package.json / netlify.toml 未動 / 無 node_modules） | ✅ PASS |

**無任何 FAIL，無任何 A-item 被砍。**

## 原始命令輸出

```
$ ! git grep -q "Noto Serif" -- web/
exit=0 PASS

$ node scripts/check-style.mjs
A2 PASS：checklist.css 的 token 區塊外沒有裸露 hex 色碼
A3 PASS：6 個同名 token 兩邊同值（--amber, --bg, --card, --faint, --green, --muted）
exit=0

$ node --check web/checklist.js && node --check web/buylist.js && node --check web/export-formats.js
exit=0

$ node scripts/check-exports.mjs
  ok   A5  含 BEGIN:VCALENDAR
  ok   A5  含 VERSION:2.0
  ok   A5  VEVENT 數 4 == 已排入項目數 4
  ok   A5  候選項目沒有變成事件
  ok   A6  取到 4 個 VEVENT
  ok   A6  「美麗海水族館」同時有 DTSTART 與 DTEND
  ok   A6  「美麗海水族館」長度 120 分 == 預期 120 分
  ok   A6  「居酒屋\, 一番」同時有 DTSTART 與 DTEND
  ok   A6  「居酒屋\, 一番」長度 60 分 == 預期 60 分
  ok   A6  「殘波岬」同時有 DTSTART 與 DTEND
  ok   A6  「殘波岬」長度 45 分 == 預期 45 分
  ok   A6  「飯店休息」同時有 DTSTART 與 DTEND
  ok   A6  「飯店休息」長度 90 分 == 預期 90 分
  ok   A6  測試資料涵蓋 duration_minutes 缺值
  ok   A6  duration 缺值時的預設為 60 分（實作是 60）
  ok   A7  （4 個已排入項目 × 4 項斷言，全 ok）
  ok   A7  候選項目不產生日曆連結
  ok   A8  表頭為 "name,location,day,time,notes"
  ok   A8  資料列 4 == 有 location 的項目數 4
  ok   A8  沒有 location 的項目不輸出
  ok   A8  候選項目只要有 location 就輸出
  ok   A8  含逗號的欄位有加引號
  ok   A8  欄位內的引號有重複跳脫
  ok   A8  每列都是 5 個欄位
  ok   A9  （5 個項目逐一驗連結格式或不產生連結，全 ok）
全部通過（44 項斷言）
exit=0

$ test ! -f package.json && git diff --quiet -- netlify.toml && test ! -d web/node_modules
exit=0 PASS
```

## 驗證腳本本身有被反向測試過

規格 EXECUTION RULES 第 7 條要求「不得偽造通過」。兩支腳本都刻意注入過違規再確認會失敗：

| 注入的違規 | 腳本反應 |
|---|---|
| 在 token 區塊外加 `color: #ABCDEF` | `A2 FAIL … web/checklist.css:347  #ABCDEF` |
| 把 `--faint` 改成 `#A8A29F`（與購物端差一碼） | `A3 FAIL … --faint: #panel-trip=#a8a29f #panel-shop=#a8a298` |
| 把 CSV 表頭 `notes` 改成 `memo` | `A8 FAIL 表頭為 "name,location,day,time,memo"` |
| 把 `DEFAULT_DURATION` 從 60 改成 30 | `A6 FAIL`（2 項斷言） |

第 4 項第一次測時**沒有**失敗——因為 A6 原本拿實作自己的 `X.DEFAULT_DURATION` 當預期值，等於「實作寫幾分都算過」。已改成硬寫規格要求的 60。

## 瀏覽器實測（無法由命令涵蓋的部分）

Supabase 在本機瀏覽器沙箱連不到，且不應對珈欣的正式資料庫做刪除測試，
因此以本地假後端（in-memory PostgREST 替身）驅動真實的 `checklist.js` 驗證：

- 匯出按鈕實際產出的檔案：`沖繩四日.ics`（`text/calendar;charset=utf-8`）與
  `沖繩四日-地點.csv`（`text/csv;charset=utf-8`），內容逐字檢查正確。
- 卡片連結按項目狀態長出：已排入＋有地點 → 兩個連結；已排入無地點 → 只有日曆；
  候選無地點 → 都不出現。
- 行程標題的 computed `font-family` 為 `"Noto Sans TC", sans-serif`；
  已載入的樣式表中含 `Serif` 的規則數為 **0**。
- 375px 寬、所有 `<details>` 全部展開的情況下，`document.scrollWidth == clientWidth == 375`，
  無任何元素水平溢出。

## 兩個誠實標示的人為步驟（不計入自動驗收）

1. 把 `.ics` 匯入 Google 日曆需使用者手動操作，**且僅限電腦版瀏覽器**。此限制已寫在畫面上。
2. 把 CSV 匯入 Google My Maps 需使用者手動上傳。

A-item 只驗「產出的檔案格式正確」，**不驗**「已經進到某個 Google 帳號裡」——後者不在本次執行的能力範圍，不得宣稱通過。
