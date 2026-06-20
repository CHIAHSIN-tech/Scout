# specs/ — 完整需求文件（design doc / RFC）

這個資料夾放「完整的 spec」。搭配 GitHub Issues 一起用：

## 分工與流程

> **Chia 思考/出題 → Stanley 用 Claude Code 執行。**

1. **Chia 開 issue**（GitHub 網頁/手機即可，不用碰 git）：用「**Spec / 需求**」範本寫她的構想。
   - 小改動：內容直接寫在 issue 裡就好。
   - 大型 spec：把完整內容放這個 `specs/` 資料夾的一個檔，issue 內文連過來。
2. **Stanley 執行**：用 Claude Code 讀 issue / spec → 落地 → commit 訊息寫 `closes #N` 自動關 issue。
3. **回報 Chia**：完成後產一份白話回報（範例：repo 根的 `for-chia.md`），說明實際做了什麼、與 spec 有無出入。

## 檔名與狀態

- 檔名：`NNN-簡稱.md`，三位數編號遞增（例：`001-confirm-integration.md`）。
- 每份 spec 檔頭標 **Status**：`draft`（草稿）/ `approved`（可開工）/ `in-progress`（執行中）/ `done`（完成）。

## 索引

| 編號 | 標題 | 狀態 | Issue |
|------|------|------|-------|
| 001 | 候選＋確認狀態整合（行程/待辦/餐廳） | ✅ done | #1 |
