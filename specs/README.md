# specs/ — 需求文件

Chia 出的每一份 spec 都是一份 **`.md`**，放在這個資料夾。這是**唯一**的出題方式。

## 流程

> **Chia 思考/出題（寫 spec `.md`）→ Stanley 用 Claude Code 執行。**

1. **Chia** 把寫好的 spec `.md` 放進這個 `specs/` 資料夾，二選一（結果一樣）：
   - **本機 git**：`.md` 放進 `specs/` → `git add` → `git commit` → `git push`。
   - **GitHub 網頁**（免本機 git）：repo 頁 → 進 `specs/` → 「Add file → Upload files / Create new file」→ Commit。
2. **Stanley** 用 Claude Code 讀該檔 → 執行落地（小步 commit、先看 diff 再進）。
3. 完成後產一份**給 Chia 看的回報**（範例：repo 根 `for-chia.md`），說明實際做了什麼、與 spec 有無出入。

## 命名與狀態

- 檔名：`NNN-簡稱.md`，三位數編號遞增（例：`001-confirm-integration.md`）。
- 每份檔頭標 **Status**：`draft`（草稿）/ `approved`（可開工）/ `in-progress`（執行中）/ `done`（完成）。

## 索引

> 早期幾份沒照 `NNN-` 編號、直接用 `spec-<主題>.md`，維持原檔名不動（改名會斷掉既有連結）。
> **狀態以每份檔頭的 Status 為準，這張表是導覽用。**

| 標題 | 範圍 | 狀態 |
|------|------|------|
| [001 候選＋確認狀態整合](001-confirm-integration.md) | 行程/待辦/餐廳 | ✅ done |
| [scout-checklist 行程表＋AI 匯入＋UI 翻新](spec-scout-checklist-itinerary-view.md) | 行程 | ✅ done（併入合併版） |
| [buylist 交接包](buylist-handoff.md) | 購物（本體） | ✅ done |
| [數量欄位＋已買沉底](spec-buylist-qty-and-bought-bottom.md) | 購物 | ✅ done |
| [一次貼多行批次新增](spec-buylist-bulk-add.md) | 購物 | ✅ done |
| [情境標籤＋依標籤篩選](spec-buylist-context-tag.md) | 購物 | ✅ done |
| [Markdown 匯出](spec-buylist-md-export.md) | 購物 | ✅ done |
| [實付金額＋估價差額](spec-buylist-actual-price.md) | 購物 | ✅ done |
| [辣醬庫作為 buylist 的一個 tab](../buylist/spec-buylist-sauce-tab.md) | 購物 | ✅ done |
| [合併為單一雙 Tab App](spec-scout-app-merge.md) | 全站 | ✅ done |
| [行程 Tab 補回編輯與刪除](spec-itinerary-restore-edit-delete.md) | 行程 | ✅ done |
| [雙 Tab 視覺統一＋日曆／地圖匯出](TASK-ui-unify-and-calendar-maps-export.md) | 全站 | ✅ done |

**目前沒有待執行的 spec。** 下一批候選見 [`buylist/BACKLOG.md`](../buylist/BACKLOG.md)
（最大的缺口是 Streamlit 退役後沒有替代品的「AI 生成行程」，需先決定做不做）。

### 已作廢
- `spec-hot-sauce-library.md` 與 `kickoff-hot-sauce-library-stanley.md`（Vue 3 + Vite 獨立 app）
  已於 2026-08-16 刪除。2026-07-26 拍板改成「buylist 的一個 tab、不開新 app、不用 Vue」，
  現行 SSOT 是 [`buylist/spec-buylist-sauce-tab.md`](../buylist/spec-buylist-sauce-tab.md)。
