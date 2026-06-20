# Spec 001 — Scout 候選＋確認狀態整合（行程/待辦/餐廳）

> **Status**: ✅ done（2026-06-20 落地）
> **Issue**: #1
> **實作 commits**: `55c429c` … `38522bd`（main）
> **回報**: 見 repo 根 [`for-chia.md`](../for-chia.md)、[`HANDOFF_itinerary_confirm.md`](../HANDOFF_itinerary_confirm.md)
> **這份是範例**：示範一份完整 spec 長怎樣（由 Chia 撰寫，Stanley 執行）。

---

## 0. Meta
- **Appetite（時間預算）**：幾週；超過就砍範疇或交付當下能用的，不無限延伸
- **Status**：approved
- **Date**：2026-06-20

## 1. Problem Statement
旅遊出發前容易遺漏重要事項（尤其是需要訂位/預約的項目），且行程排定與遺漏追蹤目前分屬兩個互不相通的系統（Streamlit/SQLite 的行程排程，Firebase 的確認清單），導致無法在排行程的同時看到「這個還沒確認」。

## 2. Primary User + JTBD
- **User**：CHIA + 旅伴（多人協作，技術程度不一，用網頁版與 Streamlit 後端）
- **JTBD**：當我旅遊時，我想要在出發前不遺漏任何東西，這樣我就能安心享受旅程

## 3. Success Criteria
- 一個項目（景點/住宿/餐廳）可以先以「候選中」狀態存在，不需要指定日期/時段
- 「必須確認」的候選項目，若長時間未排定或未確認，會在優先儀表板中被標示出來；「可以彈性」的候選項目即使永遠不排定也不算遺漏
- 行程排定（日期/時段）與確認狀態（必須確認/可以彈性 × 已確認/未確認）來自同一個 Supabase 資料來源，Streamlit 後端與網頁版皆讀寫此來源
- 多人編輯彼此的更動，靠手動重新整理即可看到（不要求即時推送）

## 4. MoSCoW
- **Must**：
  - 候選中狀態（無時段）支援所有項目類型（景點/住宿/餐廳，非餐廳專屬）
  - 確認狀態（必須確認/已確認）可隨時更動安排
  - 單一資料來源（Supabase），Streamlit 與網頁版共用
- **Should**：
  - 多人同步編輯（驗收標準：手動重新整理可接受，不要求即時推送）
- **Could**：
  - AI 自動推算安排在哪一天比較方便（距離、時間）
- **Won't**（這版明確不做）：
  - AI 餐廳推薦
  - Supabase Realtime 訂閱（成本與複雜度考量，以免費/輪詢為優先）
  - 既有 SQLite 試用資料的遷移保留

## 5. Scope & Interfaces
- **涉及的檔案／模組／介面**：
  - `db.py`（schema：`day_number` / `start_time` 改為可 NULL；新增確認狀態欄位）
  - `itinerary.py`（`reorder_and_recalculate`、`adjust_with_cascade` 需排除候選項目，避免 `min()` / 時間差計算因 NULL 出錯）
  - `page_itinerary.py`（候選區 UI、確認狀態切換）
  - Supabase 遷移腳本（新建表結構，含確認狀態欄位；不搬遷既有 SQLite 試用資料）
  - Scout Checklist 網頁版（獨立 repo：`chiahsin-tech.github.io/scout-checklist/`，改寫資料層 Firebase → Supabase API，UI 結構盡量沿用既有的必須確認/可以彈性 × 已確認/未確認儀表板）
- **明確 out of scope**：
  - AI 推算排哪天、餐廳推薦
  - 即時推送（WebSocket / Supabase Realtime 訂閱）
  - 行李／購物 tab（維持 localStorage，不搬遷）
  - 帳號驗證系統（不做，見下方身分機制）
- **身分機制**：以「共享連結」識別 trip（trip_id 即存取憑證），不做帳號系統。**已知風險**：連結外流＝任何人可編輯該趟旅程全部資料，此風險為刻意接受的取捨（換取簡單性），非疏漏
- **同步機制**：手動重新整理／輪詢（polling），不訂閱 Realtime
- **要遵循的既有 pattern**：沿用現有「必須確認/可以彈性 × 已確認/未確認」兩軸命名與優先儀表板邏輯，不重新發明命名

## 6. Acceptance Criteria
- [x] **AC-1**：使用者在 Streamlit 新增一個項目，不填日期/時段，項目以「候選中」狀態存在，不出現在 Day-based Kanban
- [x] **AC-2**：使用者把候選項目排入某天某時段，原有的串聯調整/重排邏輯正常運作，不因候選項目存在而出錯
- [x] **AC-3**：使用者將某候選或已排定項目標記為「必須確認」，若未確認，會出現在優先儀表板的未確認清單
- [x] **AC-4**：使用者在網頁版把某項目標記為「已確認」，Streamlit 後端讀到同一筆資料也顯示已確認（同一資料來源）
- [x] **AC-5**：兩位旅伴各自在網頁版編輯不同項目，雙方手動重新整理後都能看到對方的更動

## 7. Build Order
1. Supabase schema 設計＋遷移腳本（候選欄位可 NULL ＋確認狀態欄位）——最小可驗證的資料層切片，不搬既有 SQLite 試用資料
2. `itinerary.py` / `db.py` 邏輯更新：排除候選項目於時間計算之外；Streamlit 端可新增/排定候選項目（端到端可動，僅 Streamlit 範圍）
3. `page_itinerary.py` UI：候選區顯示 + 確認狀態切換按鈕
4. 網頁版資料層改寫：Firebase 呼叫換成 Supabase API（先求功能對等，UI 結構不變，沿用共享連結存取）
5. 網頁版優先儀表板驗證：確認狀態變更後，雙端（網頁/Streamlit）讀到一致結果

## 8. End-to-End Verification
在 Streamlit 新增一個「候選」餐廳項目並標記「必須確認」→ 切到網頁版重新整理，該項目出現在「未確認」清單 → 在網頁版標記為「已確認」並排入某天某時段 → 回到 Streamlit 重新整理，該項目出現在對應日期的 Kanban，且確認狀態顯示已確認。

## 9. Context Pulled
- 既有 Supabase 遷移工作（SQLite → Supabase）已在進行中，此 spec 的 schema 異動疊加於該遷移之上
- SQLite 既有資料（trips / itinerary_items）為試用性質，不需遷移保留，可直接重建 schema
- 沿用既有「PostgreSQL 保留字」教訓：`user` 為保留字，欄位命名避開

## 10. Open Questions / Risks
（已於對話中解決，列入第 5 格作為決策記錄；目前無未決項目）

---

## 落地註記（執行端補充）
- 網頁版改放公開 repo **witsper-stanley/scout-checklist** + GitHub Pages（非原 spec 設想的 chiahsin-tech 帳號）。
- 網頁版**也做了排程**（候選可在網頁直接排入某天某時段），超出 spec §5 對網頁版「只做儀表板」的界定，因 §8 劇本需要。
- 順手修掉 Supabase 遷移遺留的崩潰：`db.get_conn()` 已移除卻仍被呼叫、`requirements.txt` 漏 `supabase`、wishlist CRUD 被刪、anon 角色缺 GRANT。
