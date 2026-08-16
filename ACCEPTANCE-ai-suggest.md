# ACCEPTANCE — AI 生成行程（web 端）

規格：[`specs/spec-ai-suggest-web.md`](specs/spec-ai-suggest-web.md)
盤點：[`specs/inventory-ai-suggest.md`](specs/inventory-ai-suggest.md)
執行日期：2026-08-17

## A1–A8 驗收表

| A-item | 內容 | 結果 |
|---|---|---|
| A1 | 三支 JS 通過語法檢查 | ✅ PASS |
| A2 | 六題依序、第 4 題多選 10 選項、題目與參照系統一致 | ✅ PASS |
| A3 | prompt 帶入六答案、含五條規則與七欄位 | ✅ PASS |
| A4 | 正規化：category 白名單／day 夾範圍／時間預設／duration 預設／兩軸 false | ✅ PASS |
| A5 | 解析容錯：圍欄、非陣列、無法解析、空陣列各有不同散文訊息 | ✅ PASS |
| A6 | 前端無 Gemini 金鑰字面值 | ✅ PASS |
| A7 | 未引入建置相依 | ✅ PASS |
| A8 | 進入點與兩階段 DOM 齊備、生成路徑不走前端金鑰 | ✅ PASS |

**無 FAIL，無 A-item 被砍。** 三項 scope-cut 候選（全選鈕／已答回顧／重新開始）全部保留。

## 原始命令輸出

```
$ node --check web/checklist.js && node --check web/netlify/functions/ai-suggest.js && node --check web/ai-suggest-core.js
PASS

$ node scripts/check-ai-suggest.mjs
全部通過（68 項斷言）

$ git grep -nE "AIza[0-9A-Za-z_-]{10,}" -- web/ scripts/
（空 → PASS）

$ test ! -f package.json && test ! -d web/node_modules
PASS
```

既有驗收未被弄壞：`check-style` A2/A3 PASS、`check-exports` 44 項、`check-share` 14 項、mcp-server `pytest` 79 項。

## 瀏覽器實測（本地假後端，無網路）

六題問答 → 生成 → 勾選 → 寫入，一路走完：

| 觀察 | 結果 |
|---|---|
| 進度指示 | 「第 1 / 6 題」 |
| 空白擋下 | 「請選擇或輸入回答後再繼續。」 |
| 第 4 題 | 10 個選項，多選串成「🍜 在地美食、🌿 自然風景」 |
| 最後一題 | 有「跳過」，跳過後 `extra` 送出空字串 |
| 已答回顧 | 顯示 5 筆 |
| 送出的 answers | 六個 key 全對 |

**正規化在真實流程中逐項生效**（餵給假 AI 的是刻意做壞的資料）：

| 餵進去 | 出來 | 對應 |
|---|---|---|
| `category: "美食"` | `other`（顯示📌其他） | 參照系統缺陷 1，不移植 |
| `day: 9`（旅程只有 4 天） | `day_number: 4` | 參照系統缺陷 2，不移植 |
| `start_time: "25:99"` | `09:00` | 同參照系統 |
| `start_time: "9:30"` | `09:30`（補零） | 比參照系統嚴謹 |
| `duration_minutes: 0` | `60` | 同參照系統 |
| `name: ""` | **整筆丟掉**（5 筆進 → 4 筆出） | 不寫「未命名」進資料庫 |
| 全部四筆 | `confirm_required=false`、`is_confirmed=false` | 參照系統缺陷 3，不移植 |

未勾選就按「加入行程」→「請至少勾選一個項目。」；全選 → 「4 / 4 已勾選」；加入後 modal 關閉、清單從 4 張卡變 8 張。

## ⚠️ 沒有驗到的部分（不得宣稱可用）

規格 BOUNDS 已聲明的外部相依，兩項都仍未清除：

1. **Gemini 金鑰要由人在 Netlify 環境變數設 `GEMINI_API_KEY`。** 本 session 做不到。
   上面所有測試餵的是**假的 AI 回應**——驗到的是「prompt 組得對、回應處理得對」，
   **沒有驗到**「真的呼叫得到 Gemini、真的生得出合理行程」。
2. **Netlify 的 Git 自動部署目前是壞的**（2026-08-17 實測 deploy preview 失敗，
   見 PR #6 的討論）。就算金鑰設好，這個功能也要等部署修好才會上線。

換句話說：**程式完成、離線驗證通過；線上可用性未經證實。**
