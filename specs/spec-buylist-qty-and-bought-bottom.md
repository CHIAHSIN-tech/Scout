# Spec — 待買清單顯示層小改：已買永遠沉底 ＋ 數量欄位

> **用途**：交給 Stanley（Claude Code）執行的 SSOT。兩個獨立小功能，合成一份，可一起做也可分開做。
> **需求來源**：Chia 的購物模組 backlog（2026-07 筆記）。此份為其中最先落地的兩項。
> **維護**：完工後更新 `buylist/BUYLIST_STATE.md` 的現狀與下一步。

---

## 0. Meta
- **Appetite（時間預算）**：小。兩項都該在一個工作段落內做完；若超時，先交「Feature A（已買沉底）」——它零 schema、零風險。
- **Status**：done（落地 commit `41ccb7e`）
- **Date**：2026-07-25

## 1. Problem Statement
清單一長，已買的項目仍夾在中間干擾視線；而且切到「價格 / 想最久」排序時，已買項目又會照價格散回清單裡。另外，同一項有時要買不只一個（幾個、幾包），現在只能記名稱和價格，記不了數量。

## 2. Primary User + JTBD
- **User**：Chia / Stanley，兩人共用，桌面瀏覽器跑本機 `buylist/index.html`，Supabase 同步。
- **JTBD A**：當我在滑清單找「還沒買的」時，我想要已買的一律沉到最底、且不管我怎麼排都一樣，這樣我的視線只需停在上半部。
- **JTBD B**：當我把一項加進清單、而它要買不只一個時，我想要記下數量，這樣採買當下不會漏買或買錯量。

## 3. Success Criteria
- 三種排序（預設 / 價格高→低 / 想最久）下，已買項目**全部**都在未購項目之下。
- 新增項目時可填數量，清單上看得到數量；不填時預設為 1、顯示維持現況（不因此多出雜訊）。
- 月預算「本月未購總價」加總**維持不變**（不乘數量）。

## 4. MoSCoW
- **Must**
  - A：已買項目在**全部**排序模式下都沉到清單最底。
  - B：新增表單可輸入數量（整數，預設 1）；清單項目顯示數量（>1 時才顯示，避免 ×1 到處出現）。
- **Should**
  - （無）
- **Could**
  - （無）
- **Won't（這版明確不做）**
  - 「單位」欄位（個/包/瓶）——Chia 已定案不做，只留純數字數量。
  - 總價/月預算乘上數量（Chia 已定案：數量只作記錄，不動加總邏輯）。
  - 數量的加減 stepper、批次改量、庫存概念。
  - 2×2 矩陣顯示數量（矩陣只看迫切度×價格，不塞數量）。

## 5. Scope & Interfaces
- **涉及檔案**：
  - Feature A：只動 `buylist/index.html`——`visibleItems()` 的排序區塊（現行第 262–269 行）。
  - Feature B：`buylist/index.html`（新增表單、`addItem`、`renderList` 顯示）＋ `buylist/buylist-schema.sql`（新增一欄）＋ Supabase 執行該欄 DDL。
- **既有 pattern 對照**：
  - 排序：現行 `default` 分支（第 264–266 行）已用「群組優先鍵 + 群內排序」的寫法，A 只是把「已買沉底」這條鍵**抽出來套用到三種排序之上**，照抄同一風格即可。
  - 加欄位流程：完全比照上一輪 `starred` 欄位的做法——schema 用 `add column if not exists`（冪等），程式對缺欄位容錯（`select *` 不炸）。
- **明確 out of scope**：不改月預算加總（`thisMonthUnbought()` / 頂部總價）、不改 2×2 矩陣、不改 AI 貼連結帶入、不動篩選邏輯。

## 6. Acceptance Criteria（初始全 failing，逐條驗證）
- [ ] **AC-1**：清單有未購與已買混合項目，選「預設排序」→ 所有已買項目都在所有未購項目之下。
- [ ] **AC-2**：同上資料，切到「價格高→低」→ 未購項目照價格由高到低排在上半；已買項目**全部**在未購之下（已買群內照價格排即可）。
- [ ] **AC-3**：切到「想最久」→ 行為同 AC-2：未購在上、已買全部在下。
- [ ] **AC-4**：把一個上半的未購項目打勾為已買 → 該項**立即掉到已買群**（清單重排），並維持既有的劃線＋變灰樣式。
- [ ] **AC-5**：新增一項時把數量填 3 → 清單該項顯示數量 3（例如名稱旁 `×3`）。
- [ ] **AC-6**：新增一項時數量留空或填 1 → 正常加入，清單**不**顯示 `×1`（維持現況乾淨）。
- [ ] **AC-7**：加入數量為 3、單價 100 的項目後，頂部「本月未購總價」增加的金額是 100（**不是** 300）——確認加總未受數量影響。
- [ ] **AC-8**：重整頁面後，數量仍在（已存進 Supabase）。

## 7. Build Order（一次一件事）
1. **Feature A（先做，零風險）**：改 `visibleItems()`，讓「已買沉底」成為套在三種排序之上的主鍵。瀏覽器切三種排序各看一遍 → 過 AC-1～AC-4。
2. **Feature B step 1**：`buylist-schema.sql` 加 `quantity int default 1`（`add column if not exists`），在 Supabase `kdmmjlaajqxjmiahfvos` SQL Editor 執行。
3. **Feature B step 2**：新增表單加數量 input（`bl-qty`，放價格旁）、`addItem` 帶入 `quantity`、`renderList` 在 `>1` 時顯示 → 過 AC-5～AC-8。

## 8. End-to-End Verification
在瀏覽器開 `buylist/index.html`：加三筆（一筆未購高價、一筆未購低價、一筆已買），依序切「預設 / 價格 / 想最久」三種排序，確認已買永遠在最底（AC-1~3）；再加一筆數量 3、單價 100，確認清單顯示 `×3` 且頂部總價只加 100（AC-5、AC-7）；重整頁面數量還在（AC-8）。

## 10. Open Questions / Risks
- ~~**Q1（單位欄位）**~~：已定案**不做**，只留純數字數量（見 §4 Won't）。
- **Q2（DDL blocker）**：Feature B 上線前**必須**先在 Supabase 執行 `quantity` 欄位的 DDL，否則寫入數量會噴錯（同上一輪 `starred` 的坑）。程式對缺欄位需容錯：沒有該欄時 `quantity` 視為 1，不可炸。
- **Q3（歷史資料）**：既有項目沒有 `quantity`，`default 1` 會補上；顯示端也要把 `null/undefined` 當 1 處理。
