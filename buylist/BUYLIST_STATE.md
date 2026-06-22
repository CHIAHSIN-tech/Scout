# BuyList — 專案現狀（給 Chat 接手用）

> **用途**：新開一個 chat 時，把這份 `.md`（＋ Chia 的 spec）貼進去，就能完整理解專案、接著做。
> **維護原則**：每完成一步，就更新 §5 現狀 與 §6 下一步。只記架構/決策/進度，不記瑣碎過程。
> **最後更新**：2026-06-22

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
| **執行/分享** | **桌面本機跑**：雙擊 `run.bat`（Win）/ `run.command`（Mac）→ 起本機伺服器 → 瀏覽器開 `localhost`。**兩人各自在自己電腦跑，靠 Supabase 同步**。 | 暫**不做手機**（Stanley 決定）。手機要用再改成公開網址（Cloudflare 從 private 出，程式碼仍 private）。不用 `file://` 雙擊（連雲端不可靠）。 |
| **後端** | **Supabase**，用 **Stanley 自己的專案** `kdmmjlaajqxjmiahfvos`（URL `https://kdmmjlaajqxjmiahfvos.supabase.co`），新表 `buylist_items`。 | spec 原寫 **Firebase**。改 Supabase：統一一個後端技術、SQL 查詢力、權限可預期、不鎖定。**注意：Scout 的 Supabase（`uarkccyqcqvgxukjcrey`）是 Chia 的、Stanley 沒後台權限**；所以 BuyList 改用 Stanley 自己的專案，他能自管（建表/改欄位都自己來）。BuyList 資料本來就跟 Scout 分開，無妨。anon key 寫在 `buylist/index.html`。 |
| **前端** | **單檔 vanilla HTML/JS**（無 build），UI 風格輕參考 dfg | spec 原寫 **Vue + Vite**。改 vanilla：最薄、好分享、tracer bullet 不需框架。`decision-focus-graph` 只是介面範例，**不改、不照抄**。 |
| **身分** | 無登入；anon key + 權限全開 | 同 spec（網址即存取）。實驗、兩人用，已接受風險。 |
| **同步** | Supabase Realtime（`postgres_changes`） | 達成 spec 的第一 Must：兩人即時同步。同步靠 Supabase，與「放哪/怎麼開」無關。 |

## 5. 現狀（current state）
- ✅ 落點/執行已定：private `Scout/buylist/`，雙擊啟動檔本機跑，桌面、不公開。
- ✅ 已退役公開的 `scout-checklist` repo（改 private）；Scout 內重複的 `checklist/` 已刪。
- ✅ `decision-focus-graph`：只當 UI 參考，未改動。
- ✅ **Build Order step 1（tracer bullet）完成並驗收通過**：表 `buylist_items` 已建在 Stanley 的專案；
  **AC-1 即時同步實測 OK**（從 API 端插入一筆 → 開著的 app 不重整、數秒內即顯示；app UI 端新增中文也正確存入並同步）。
- 後端：Supabase 專案 `kdmmjlaajqxjmiahfvos`（Stanley 的）；表 `buylist_items`（schema 見 `buylist/buylist-schema.sql`，已執行）。
- **下一步等 Chia 檢查後再做 step 2**（照 spec「一次一步、做完停」）。

## 6. 下一步（Build Order，from spec §7）
> 紀律：**一次只做一步、做完就停、附證據、等 Chia 檢查**。不要一口氣做完整個 app。

1. ✅ **tracer bullet**：即時同步（AC-1）—— 已驗收通過
2. ⬜ 新增表單（價格 / 迫切度 / 取得難易 / 本月想買）＋ 清單顯示 ＋ 刪除（AC-2、AC-5）
3. ⬜ 月預算 ＋「本月未購總價」加總 ＋ 爆預算提示（AC-3）
4. ⬜「已買」打勾 → 移出本月未購總價（AC-4）
5. ⬜ 冷卻期「想買 N 天」（AC-6）
6. ⬜（Should）2×2 視覺、誰加的、連結/備註（AC-7）

## 7. 怎麼跑 / 怎麼繼續
- **跑**：進 `Scout/buylist/`，雙擊 `run.bat`（Win）或 `run.command`（Mac）→ 瀏覽器會開買物清單。
- **接手**：新 chat → 貼「這份 `BUYLIST_STATE.md` ＋ `specs/buylist-handoff.md`」→ 說「做下一步」。
