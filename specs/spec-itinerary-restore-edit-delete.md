# Spec — 行程 Tab：補回 Streamlit 退役後遺失的編輯與刪除能力

> **用途**：交給 Claude Code 執行的 SSOT。
> **需求來源**：Chia，2026-08-08——「針對行程 tab 補上原本 Streamlit 版已有的功能」。
> **背景**：Streamlit 版（`page_itinerary.py`）已退役，但部分功能沒搬進 web 版（`web/checklist.js`），
> 造成**功能倒退**——以前做得到、現在做不到。本 spec 只補回既有能力，不加新功能。

---

## 0. Meta
- **Appetite（時間預算）**：中偏小。資料層大部分現成（見 §5.1），主要是補 UI 與 DELETE。
- **Status**：done（2026-08-16 落地，commit `e2ba895`；驗收見 `for-chia-itinerary-edit-delete.md`）
- **Date**：2026-08-08

## 1. Problem Statement
Streamlit 版退役後，行程項目**無法編輯任何欄位、無法刪除項目、也無法刪除旅程**。目前 web 版只能新增、排入行程、退回候選、標記確認、拖曳改時間。打錯字或加錯項目時，只能留著，沒有任何補救方式。

## 2. Primary User + JTBD
- **User**：Chia / Stanley，手機與桌面瀏覽器。
- **JTBD**：當我發現某個行程項目資訊有誤、排錯天、或根本不該存在時，我想要能改它或刪掉它，這樣清單才會是可信的。

## 3. Success Criteria
- 每個行程項目都能改內容、能換到別天、能刪掉。
- 不再需要的旅程能整個刪掉。
- 補回的行為與 Streamlit 版一致，不引入新的資料模型。

## 4. MoSCoW
- **Must**（沒有就是持續倒退）
  1. **編輯項目欄位**：名稱、分類、開始時間、停留分鐘、地點、地址、預約編號、備註。
  2. **跨天移動**：在編輯介面把項目改到第 N 天（Streamlit 是編輯表單裡的「第幾天」下拉）。
  3. **刪除單一行程項目**（需二次確認，避免手機誤觸）。
  4. **刪除旅程**（需二次確認，且需明示會連同其行程項目一併刪除）。
- **Should**
  - 編輯／刪除後畫面即時反映，不需手動重整；失敗顯示紅字錯誤（沿用既有 `showError` / `miniMsg` 模式，不靜默失敗）。
- **Could**
  - **上移↑／下移↓ 排序 ＋ 自動重算時間**（Streamlit `_tab_timeline` 的 ↑↓）。
    ⚠️ **刻意降級的理由**：web 版時間軸**已有拖曳改時間**（`tlAttachDrag`），Streamlit 當年做 ↑↓ 正是因為沒有拖曳。兩者目的重疊，先不做；等實際用起來覺得拖曳不夠精準再補。**不要為了「Streamlit 有」就照搬。**
- **Won't（本 spec 不做，另開）**
  - **AI 生成行程**（Streamlit `page_ai_suggest.py` 的多輪問答生成完整行程）——範疇大、屬 AI 範疇，另開 spec。
  - 新增任何 Streamlit 沒有的功能。
  - 改動資料表結構（本 spec 全部用既有欄位）。

## 5. Scope & Interfaces
- **涉及檔案**：`web/checklist.js`（主要）、`web/checklist.css`（編輯表單與刪除鈕樣式）。**無 schema 變動、無 DDL。**
- **後端**：珈欣的 Supabase（`uarkccyqcqvgxukjcrey`），表 `itinerary_items` / `trips`，走既有 REST 封裝 `sb(path, opts)`。

### 5.1 現成可重用的東西（**先讀這段，能省掉大半工作**）
`web/checklist.js` 既有的資料層已涵蓋大部分需求，**不要重寫**：

| 已存在 | 用途 | 本 spec 怎麼用 |
|---|---|---|
| `sb(path, opts)` | Supabase REST 封裝（自動帶 apikey/Authorization、非 2xx 丟錯） | 所有新請求都走它 |
| `patchItem(itemId, fields)` | PATCH 任意欄位到 `itinerary_items` | **編輯功能的資料層已完成**，只缺 UI |
| `scheduleItem(id, day, time)` | 改 `day_number` + `start_time` | 跨天移動可直接用 |
| `loadItems(tripId)` / `renderCurrentView()` | 重讀與重繪 | 編輯/刪除成功後呼叫以刷新 |
| `showError` / `miniMsg` | 錯誤顯示 | 失敗路徑沿用，不要自己發明提示方式 |

**缺口只有兩塊**：(a) 編輯用的 UI；(b) **DELETE 請求——整份 `checklist.js` 目前沒有任何 DELETE**，需新增：
```js
async function deleteItem(itemId) {
  await sb(`itinerary_items?id=eq.${encodeURIComponent(itemId)}`, { method: "DELETE" });
}
async function deleteTrip(tripId) {
  await sb(`trips?id=eq.${encodeURIComponent(tripId)}`, { method: "DELETE" });
}
```

### 5.2 對照來源（要補的行為以此為準）
Streamlit `page_itinerary.py` 對應段落：`_render_items()` 的 ✏️ 展開編輯表單（含「第幾天」`new_day_label`、分類 `new_category`、地點 `new_location`、地址 `new_address`、預約編號 `new_booking`、備註 `new_notes`）、項目刪除鈕（`del_item_{id}`）、旅程刪除鈕（`del_{trip_id}`）。

- **明確 out of scope**：不改確認清單／行程表／時間軸三個檢視的既有邏輯（只在項目卡片上加入口）；不動 AI 匯入；不碰購物 Tab；不改排序規則（`loadItems` 的 order 維持）。

## 6. Acceptance Criteria（初始全 failing）
- [x] **AC-1**：任一行程項目上有「編輯」入口；點開後看到現值已帶入的表單（名稱／分類／開始時間／停留分鐘／地點／地址／預約編號／備註）。
- [x] **AC-2**：改名稱後儲存 → 畫面立即顯示新名稱；重整後仍是新名稱（確認已寫入 Supabase）。
- [x] **AC-3**：在編輯介面把項目從第 1 天改到第 3 天 → 該項目從第 1 天消失、出現在第 3 天（三個檢視都正確）。
- [x] **AC-4**：編輯開始時間與停留分鐘 → 時間軸上該項目的位置／長度隨之改變。
- [x] **AC-5**：點項目的刪除 → 出現二次確認；確認後該項目從清單消失，重整後不再出現。
- [x] **AC-6**：取消二次確認 → 項目仍在，什麼都沒改變。
- [x] **AC-7**：刪除旅程 → 出現二次確認且提示會一併刪除其行程項目；確認後該旅程從下拉選單消失，畫面回到「未選旅程」狀態。
- [x] **AC-8**：斷網或後端錯誤時，編輯/刪除失敗會顯示紅字錯誤訊息，不靜默失敗、不假裝成功。
- [x] **AC-9**：手機寬度下編輯表單可用（欄位不溢出、按鈕點得到）。

## 7. Build Order（一次一件事）
1. **刪除單一項目**：加 `deleteItem` ＋ 卡片上的刪除鈕 ＋ 二次確認 → 驗 AC-5、AC-6、AC-8。（最小、獨立、立刻有用）
2. **編輯項目欄位**：編輯 UI（展開式表單或 modal，沿用既有樣式語彙）＋ 接 `patchItem` → 驗 AC-1、AC-2、AC-4、AC-9。
3. **跨天移動**：編輯表單加「第幾天」選擇，接 `scheduleItem` → 驗 AC-3。
4. **刪除旅程**：加 `deleteTrip` ＋ 旅程列的刪除入口 ＋ 二次確認（含連帶刪除提示）→ 驗 AC-7。

## 8. End-to-End Verification
瀏覽器（桌面 + 手機寬度各一次）開合併版 → 行程 Tab：
建一筆測試項目 → 編輯它的名稱、時間、停留分鐘、備註，確認三個檢視都同步 → 把它從第 1 天移到第 3 天，確認位置正確 → 刪除它，確認二次確認有出現、刪除後重整不再出現 → 最後建一個測試旅程再刪掉，確認連帶提示與下拉選單更新。

## 9. Context Pulled
- `page_itinerary.py`（Streamlit 版行為對照來源）
- `web/checklist.js`（現行 web 版能力盤點：`patchItem` 已有、無任何 DELETE）
- `for-chia-deploy.md`（「欄位編輯、上下移排序、跨天移動、刪除旅程還沒搬過來」）

## 10. Open Questions / Risks
- **R1（旅程刪除的連帶行為）**：`trips` 與 `itinerary_items` 若已設 CASCADE（CLAUDE.md 的 schema 註記為 CASCADE 刪除），刪旅程會自動清掉其項目；執行前**先確認珈欣 Supabase 上的實際外鍵設定**。若沒有 CASCADE，需先刪項目再刪旅程，否則會出現孤兒資料或外鍵錯誤。
- **R2（無登入、兩人共用）**：刪除是破壞性且不可復原，另一人可能同時在看同一份資料。本版採「二次確認」為唯一保護，不做軟刪除／垃圾桶（維持既有 app 的輕量精神）；若日後誤刪頻繁再議。
- **R3（編輯 UI 形式未定）**：展開式（Streamlit 的 ✏️ 展開）或 modal 皆可，執行者依 `checklist.css` 既有樣式語彙選一致的做法即可，不需回頭問。
- **R4（AI 生成行程仍缺）**：本 spec 明確不含。Streamlit 退役後這個功能**目前沒有任何替代品**，是唯一尚未補回的重大缺口，需另開 spec 決定要不要做、怎麼做。
