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

| 編號 | 標題 | 狀態 |
|------|------|------|
| 001 | 候選＋確認狀態整合（行程/待辦/餐廳） | ✅ done |
