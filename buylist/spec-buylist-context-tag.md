# Spec — 待買清單：情境標籤（tag）＋ 依標籤篩選

> **用途**：交給 Stanley（Claude Code）執行的 SSOT。單一小功能。
> **需求來源**：Chia 的購物模組 backlog——「多清單／情境清單」。經 shaping 後定為**輕量標籤版（Path A）**，不做多清單資料架構、不做每清單獨立預算。
> **維護**：完工後更新 `buylist/BUYLIST_STATE.md`。

---

## 0. Meta
- **Appetite（時間預算）**：小。一張表加一欄 ＋ `index.html` 加一個輸入、一個篩選、一個顯示標籤。**刻意不含**標籤的批次改名/刪除管理（見 §4 Won't）。
- **Status**：draft
- **Date**：2026-07-25

## 1. Problem Statement
待買的東西其實分屬不同**購物情境**（「日本要買」「Costco」「藥妝」），現在全部混在一張清單，想「只看某個情境」時只能靠眼睛撈。現有的「分類」是講物品**種類**（3C/美妝…），跟情境是兩回事，塞不進去。

## 2. Primary User + JTBD
- **User**：Chia / Stanley，桌面瀏覽器跑 `buylist/index.html`，Supabase 同步。
- **JTBD**：當我在規劃某個場合要買的東西時，我想要幫項目標上情境（如「日本」）並只看該情境，這樣我不會被其他情境的項目干擾。

## 3. Success Criteria
- 新增/編輯項目時可指定一個情境標籤，可**打字建立新的**或**選既有的**。
- 篩選列多一個「情境」下拉，選某標籤 → 只顯示該標籤的項目。
- 標籤與現有「分類」並存、互不取代；月預算加總維持現況（全清單共用一個預算，不因標籤改變）。

## 4. MoSCoW
- **Must**
  - `buylist_items` 新增一個 `tag`（單一自由文字，預設空字串）。
  - 新增表單有「情境」輸入框：自由打字即建立新標籤；同時提供既有標籤的 autocomplete（用 `<datalist>` 帶出目前已用過的標籤）。
  - 篩選列新增「情境」下拉 `f-tag`，選項＝目前資料裡出現過的 distinct 標籤（＋「全部情境」）；選某標籤只顯示該項目。
  - 清單項目顯示其情境標籤（有 tag 才顯示，樣式與現有分類 chip 區分得出來）。
- **Should**
  - 既有的單項編輯能改這個標籤（若現行有編輯項目的路徑；沒有就沿用「刪掉重加」不勉強）。
- **Could**
  - （無）
- **Won't（這版明確不做）**
  - 多清單資料架構（獨立 lists 表、切換工作區）——已於 shaping 定案走輕量標籤。
  - 每情境獨立預算 / 每情境加總——維持單一共用預算。
  - 一個項目掛**多個**標籤（v1 只單一 tag）。
  - 標籤的批次**改名/整個刪除**管理 UI——v1 靠打字建立、靠編輯單項改標籤；整體標籤管理留 v2。
  - 2×2 矩陣依標籤切換（矩陣維持現況）。

## 5. Scope & Interfaces
- **涉及檔案**：
  - `buylist/buylist-schema.sql`：加 `tag text default ''`（`add column if not exists`，冪等）＋ 在 Supabase `kdmmjlaajqxjmiahfvos` 執行該 DDL。
  - `buylist/index.html`：新增表單一個輸入（`bl-tag` ＋ `<datalist>`）、篩選一個下拉（`f-tag`）、`visibleItems()` 加一條 tag 篩選、`renderList()` 顯示 tag chip、`addItem` 帶入 `tag`。
- **既有 pattern 對照**：
  - 加欄位＋容錯：完全比照 `starred` / `quantity`——`select *` 對缺欄位不炸，`tag` 缺值視為空字串。
  - 篩選下拉：比照現有 `f-cat`（第 168、215、255–257 行）的建法，差別是 `f-tag` 的選項要**從 `items` 動態算 distinct**（分類是寫死的 `CATS`，標籤是使用者自訂的，所以動態產生）。
  - autocomplete：用原生 `<datalist>`，選項同樣由 `items` 的 distinct tag 動態填。
- **明確 out of scope**：不改月預算/加總、不改分類、不改排序、不改 2×2、不碰 AI 帶入、不做多標籤。

## 6. Acceptance Criteria（初始全 failing）
- [ ] **AC-1**：新增項目時在「情境」框打「日本」（清單裡還沒有這個標籤）→ 成功新增，該項顯示標籤「日本」。
- [ ] **AC-2**：再新增一項時，「情境」框的 autocomplete 會出現既有的「日本」可直接選。
- [ ] **AC-3**：篩選列「情境」下拉出現目前所有 distinct 標籤（含剛建立的「日本」）＋「全部情境」。
- [ ] **AC-4**：情境選「日本」→ 清單只剩標籤為「日本」的項目；切回「全部情境」→ 全部回來。
- [ ] **AC-5**：不填情境的項目正常新增，清單不顯示情境 chip，且不會出現在任一具體標籤的篩選結果裡（只在「全部情境」看得到）。
- [ ] **AC-6**：加了標籤的項目不影響頂部「本月未購總價」的算法（總價與未加標籤時相同）。
- [ ] **AC-7**：情境與分類可並存——一個項目同時有分類「食品」和情境「日本」，兩個 chip 都顯示，兩種篩選各自有效。
- [ ] **AC-8**：重整頁面後標籤仍在（已存 Supabase）；另一台裝置（Realtime）也看得到。

## 7. Build Order（一次一件事）
1. **schema**：`buylist-schema.sql` 加 `tag`，Supabase 執行 DDL。
2. **寫入 + 顯示**：新增表單加 `bl-tag` 輸入、`addItem` 帶 `tag`、`renderList` 顯示 chip → 驗 AC-1、AC-5~AC-7。
3. **既有標籤重用 + 篩選**：`<datalist>` 與 `f-tag` 都用 `items` 的 distinct tag 動態填；`visibleItems()` 加 tag 篩選條件 → 驗 AC-2~AC-4、AC-8。

## 8. End-to-End Verification
瀏覽器開 `buylist/index.html`：新增「藥妝棉（分類=美妝，情境=日本）」「醬油（分類=食品，情境=空）」「衛生紙（情境=Costco）」。確認：清單三筆各自的 chip 正確；「情境」下拉有「日本 / Costco / 全部情境」；選「日本」只剩藥妝棉；切回全部三筆都在；頂部總價不因標籤而變；重整後標籤還在。

## 10. Open Questions / Risks
- **R1（DDL blocker）**：上線前必須先在 Supabase 執行 `tag` 欄位 DDL，否則寫入標籤會噴錯（同 `starred`/`quantity` 的坑）。程式對缺欄位需容錯（缺 `tag` 視為空字串）。
- **R2（標籤管理 v2）**：v1 無「改名/刪除整個標籤」；使用者改名要逐項編輯。若之後常改，再開 v2 做批次管理。此為 Appetite 取捨、Chia 已知悉。
- **R3（空/髒標籤）**：`tag` 存前先 `trim`；空字串一律當「未分情境」，不進 distinct 下拉。
- **R4（多標籤需求）**：若日後某項想同時屬於多情境，單一 `tag` 欄位不夠，需改設計；v1 先接受單一。
