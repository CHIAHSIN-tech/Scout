# Spec — 待買清單：實付金額 ＋ 當下估價 vs 實付差額

> **用途**：交給 Stanley（Claude Code）執行的 SSOT。單一小功能。
> **需求來源**：Chia 的購物模組 backlog——「待買→已買＋實付金額」「估價 vs 實付差額」。
> **shaping 定案（Path A）**：只在打勾當下讓你看一眼省/超多少；**不留帳、不做跨月統計、月初照清**——維持 app「幫你決定買不買、不做記帳帳本」的 DNA。
> **維護**：完工後更新 `buylist/BUYLIST_STATE.md`。

---

## 0. Meta
- **Appetite（時間預算）**：小。加一欄 `actual_price` ＋ 已買項目上一個 inline 輸入 ＋ 一行差額顯示。
- **Status**：done（落地 commit `91f323f`）
- **Date**：2026-07-25

## 1. Problem Statement
標記已買的當下，我想知道「這次比原本估的省了還是超了」，但現在只有估價、沒有實付，買完就沒對照。

## 2. Primary User + JTBD
- **User**：Chia / Stanley，桌面瀏覽器跑 `buylist/index.html`。
- **JTBD**：當我把一項標為已買、輸入實際花的錢時，我想要**當下**看到跟估價的差額，這樣我對自己買貴買便宜有即時感覺。

## 3. Success Criteria
- 打勾已買後，能在該項填「實付」。
- 填完立刻顯示「省 X / 超 X」（省=綠、超=紅）。
- 頂部月預算/未購總價**不受影響**（實付不進加總）。
- 不改「月初自動清上月已買」的行為——不做留帳。

## 4. MoSCoW
- **Must**
  - `buylist_items` 新增 `actual_price numeric`（可為 null，代表「已買但還沒填實付」）。
  - 已買項目（`.item.bought`）顯示一個 inline「實付」數字輸入，預設值＝該項估價 `price`。
  - 使用者改實付並失焦/送出 → 寫回 Supabase，並在該項顯示差額：`實付 < 估價` → 「省 NT$X」綠字；`>` → 「超 NT$X」紅字；`=` → 「持平」或不顯示。
  - 未購項目**不**顯示實付 UI（比照星號：只在已買時出現）。
- **Should**
  - 取消已買（unbought）時，保留已填的 `actual_price`（之後重新打勾還在），但差額顯示隨「非已買」一起隱藏。
- **Could**
  - （無）
- **Won't（這版明確不做，守住 DNA）**
  - 保留已買紀錄做**跨月/分類花費統計**——維持「月初自動清已買、不留帳」。
  - 把實付累加成「本月實際花費」帳本——不做記帳帳本（既有 Won't）。
  - 用實付回頭改月預算加總邏輯。

## 5. Scope & Interfaces
- **涉及檔案**：
  - `buylist/buylist-schema.sql`：加 `actual_price numeric`（`add column if not exists`）＋ Supabase `kdmmjlaajqxjmiahfvos` 執行 DDL。
  - `buylist/index.html`：`renderList()` 在已買項目加實付 input＋差額顯示；加一個 `updateActualPrice(id,val)` 寫回；`money()` 重用。
- **既有 pattern 對照**：
  - 「只在已買顯示」的元件：比照星號（第 285 行 `i.bought?'<button class="star"...':''`）。
  - 寫回單欄：比照 `toggleBought` / `toggleStarred`（第 324 行附近）——`sb.from('buylist_items').update({actual_price:val}).eq('id',id)`，錯誤走既有 `setStatus(...,'err')`。
  - 缺欄位容錯：比照 `starred`——`actual_price` 缺值/`null` 視為「尚未填」，`select *` 不炸。
- **明確 out of scope**：不改月預算/未購總價加總、不改月初自動清邏輯、不改未購項目 UI、不碰排序/篩選/AI。

## 6. Acceptance Criteria（初始全 failing）
- [ ] **AC-1**：把一個估價 100 的項目打勾已買 → 該項出現「實付」輸入，預設帶入 100。
- [ ] **AC-2**：把實付改成 90 → 顯示「省 NT$10」綠字。
- [ ] **AC-3**：把實付改成 120 → 顯示「超 NT$20」紅字。
- [ ] **AC-4**：實付＝估價（100）→ 顯示「持平」或不顯示差額（不誤報省/超）。
- [ ] **AC-5**：填了實付後，頂部「本月未購總價」數字不變（實付不進加總）。
- [ ] **AC-6**：未購項目上沒有實付輸入與差額。
- [ ] **AC-7**：重整頁面後，已買項目的實付值仍在（已存 Supabase）；另一台裝置也看得到。
- [ ] **AC-8**：把已買取消回未購 → 實付 UI 與差額消失；再打勾回已買 → 先前填的實付還在。

## 7. Build Order（一次一件事）
1. **schema**：加 `actual_price`，Supabase 執行 DDL。
2. **顯示 + 寫回**：`renderList` 在已買項目加實付 input（預設帶 `price`）＋差額計算顯示；`updateActualPrice` 寫回 → 驗 AC-1~AC-8。

## 8. End-to-End Verification
瀏覽器開 `buylist/index.html`：新增一項估價 100 → 打勾已買 → 實付填 90，看到「省 NT$10」綠字，且頂部總價不變 → 重整後實付還在 → 取消已買，差額消失、再打勾還在。

## 10. Open Questions / Risks
- **R1（DDL blocker）**：上線前先在 Supabase 跑 `actual_price` DDL，否則寫入實付會噴錯（同 `starred`/`quantity`/`tag`）。
- **R2（月初清掉＝差額也沒了）**：因為維持「月初自動清已買」，上個月的省/超差額不會留存——這是 Path A 的**刻意取捨**（不留帳）。若哪天想留，屬「輕帳本」方向的另一個大決策。
- **R3（實付為 0）**：實付真的 0（例如免費得到）與「還沒填」要分得開——所以用 `null`＝未填、`0`＝真的沒花錢；預設帶入估價可降低誤填 0。
