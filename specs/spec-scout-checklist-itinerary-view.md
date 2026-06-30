# Spec — Scout Checklist：完整行程表 + AI 匯入行程 + UI 整體翻新

## 0. Meta
- **Appetite（時間預算）**：不限定（此版本不以 appetite 做範疇削減依據）
- **Status**：✅ done（2026-06-30 落地於 `scout-checklist/`）
- **Date**：2026-06-27

---

## 1. Problem Statement
目前 Scout Checklist（`chiahsin-tech.github.io/scout-checklist`）只有「依確認狀態分組」的清單（必須確認／已確認／可以彈性），使用者看不到「整個行程實際排起來是什麼樣子」，無法一眼確認每天在幹嘛、時間會不會衝突或太趕。同時，行程項目目前只能手動一筆一筆輸入，沒有從既有資料（例如 Google Maps 已儲存清單）快速匯入的方式。介面本身也尚未翻新。

## 2. Primary User + JTBD
**User**：CHIA、Stanley，以及一起出遊的旅伴。出發前在手機或電腦上做最後確認；旅行中主要用手機查看。

**JTBD（行程表）**：當我在出發前做最後確認、或旅行中想知道接下來該去哪，我想要看到依日期排好的完整行程總覽，這樣我才能確認排程合理、快速找到現在／接下來該去哪。

**JTBD（AI 匯入）**：當我已經在別處（例如 Google Maps）整理好一份想去的地方清單，我想要直接貼上文字讓系統自動拆成行程項目並排入行程，這樣我就不用一筆一筆手動輸入。

**JTBD（UI 翻新）**：當我在手機上打開 Scout Checklist，我想要不用捲動很久就能看到最重要的資訊（必須確認的項目、今天的行程），這樣我才能快速掌握現在該做什麼，不用每次都從頭捲到尾找。
> 註：此項目聚焦在「手機資訊架構」（減少捲動才能看到重點），不是單純視覺翻新。視覺風格沿用 demo 現有設計即可，但分類區塊的呈現順序／收合邏輯需另外設計。

## 3. Success Criteria
- 使用者能在一個畫面看到所有已排入行程的項目，依 Day 分組
- 使用者能切換時間軸視圖，並用拖曳調整時間，調整後資料即時寫回 Firebase（或 Supabase，視 Stanley 確認結果）
- 使用者貼上一段文字行程，AI 能自動拆成項目並直接以「已排入行程」狀態加入
- 正式網址（移除 `?demo=1` 旗標後）即為唯一對外使用的版本

## 4. MoSCoW

- **Must**：
  1. Day-grouped 清單檢視（依 Day 1 / Day 2... 分組，顯示時間／地點／類別 icon）
  2. 未排定項目提醒（例如「還有 N 項未排定」）
  3. 時間軸／日曆型視圖（同時段重疊項目並排顯示，不互相蓋住）
  4. 拖曳調整時間（自由拖曳，不做格線吸附；放開後直接寫回後端 day/time 欄位）
  5. UI 整體翻新（手機資訊架構優化）：「必須確認」區塊預設展開並置頂顯示數量摘要；「已確認」「可以彈性」等非緊急區塊預設收合（Collapsible），視覺風格沿用 demo 現有設計
  6. AI 匯入行程（貼文字 → AI 解析拆成項目 → 自動以「已排入行程」狀態加入，含 day/time）
  7. 網址正式化（移除 demo 旗標，`witsper-stanley.github.io/scout-checklist` 作為正式對外網址）

- **Should**：
  - 今天（Today）自動定位、高亮顯示
  - AI 解析失敗或無法判斷 day/time 時的 fallback 處理（見 Open Questions）

- **Could**：
  - 同時段衝突的額外視覺警告樣式強化

- **Won't（這版不做）**：
  - 列印／匯出行程
  - 多人同時拖曳的即時同步動畫
  - AI 匯入支援截圖／PDF／網頁連結（這版只支援貼文字）
  - 正式版資料從 `chiahsin-tech` 舊版搬移的自動化工具（如需搬移，這版先用手動方式）

---

## 5. Scope & Interfaces

**涉及的檔案／模組**
- Repo：`witsper-stanley/scout-checklist`（直接作為正式版基礎，移除 `?demo=1` 判斷邏輯）
- 已知全域函式：`loadTrip()`、`loadItems()`、`patchItem()`、`buildTripCtx()`、`getTripId()`
  - `patchItem()` 需確認／擴充為可直接更新 day/time 欄位
- 資料模型：項目已有 day、time、category（餐廳／景點／交通／其他）、status（候選中／已確認）欄位

**明確 out of scope**
- Scout 本體（Streamlit）— 不同 app，不在此範疇
- 舊版 `chiahsin-tech` 正式資料的自動遷移工具

**要遵循的既有 pattern**
- 沿用 manual refresh/polling 同步策略，不導入 Realtime 訂閱
- 沿用 shared trip_id 存取模式

---

## 6. Acceptance Criteria

- [x] **AC-1**：開啟「行程表」畫面，已排入行程的項目依 Day 分組顯示，含時間／地點／類別 icon
- [x] **AC-2**：有未排定項目時，畫面上方顯示「還有 N 項未排定」提醒
- [x] **AC-3**：時間軸視圖中，當天項目依時間排列，同時段重疊項目並排顯示
- [x] **AC-4**：時間軸視圖中拖曳項目可改變時間，放開後寫回後端，重新整理後新時間保留
- [x] **AC-5**：拖曳到與其他項目時段重疊時顯示警告提示（不阻擋操作）
- [x] **AC-6**：旅行中開啟行程表，自動高亮顯示「今天」
- [x] **AC-7**：手機畫面下開啟頁面，不需捲動即可看到「必須確認」項目數量摘要；「已確認」「可以彈性」區塊預設收合，點擊才展開
- [x] **AC-8**：貼上一段文字行程並送出後，AI 自動拆成多個項目，每項帶 day/time／地點／類別，直接以「已排入行程」狀態顯示在行程表
- [~] **AC-9**：預設網址（無 `?demo=1`）即為正式版、按鈕實際寫入 Supabase ✅；但**刻意保留** `?demo=1` 作為離線預覽（理由見 `for-chia.md`：對正式版零影響、是無 Supabase 時唯一可預覽途徑）。如需完全移除 demo 再議。

> **落地註記（2026-06-30）**：Open Question 1（後端）確認為 **Supabase**；Open Question 2
> （`patchItem` 改 day/time）確認**原本就支援**，無前置工作。Open Question 3（AI fallback）採
> 「判斷不出天數 → 退回候選」。Open Question 4（前端金鑰外露）沿用既有 trip_id / anon key
> 信任模型，於 `config.example.js` 寫明風險與替代方案。驗證：Playwright 手機尺寸端到端 24 項全綠。

---

## 7. Build Order

1. Day-grouped 清單視圖（含未排定提醒）—— AC-1、AC-2
2. 時間軸視圖 —— AC-3、AC-6
3. 拖曳調整時間（含寫回後端、衝突警告）—— AC-4、AC-5
4. 網址正式化（移除 demo 旗標）—— AC-9（與 1–3 平行進行，邊做邊用）
5. AI 匯入行程 —— AC-8
6. UI 手機資訊架構優化（收合邏輯、必須確認摘要置頂）—— AC-7

---

## 8. End-to-End Verification

開瀏覽器進入正式網址（無 `?demo=1`）→ 貼一段文字行程測試 AI 匯入 → 確認項目自動出現在行程表並有正確 day/time → 切到時間軸視圖 → 拖曳一項到新時間 → 重新整理頁面確認新時間保留、衝突有警告 → 確認未排定提醒數字正確。

---

## 9. Context Pulled
- 過去對話：Scout Checklist 現有架構（Firebase Realtime Database、shared trip_id）
- demo 頁面 inspect 結果：`loadTrip`、`loadItems`、`patchItem`、`buildTripCtx`、`getTripId` 等全域函式

---

## 10. Open Questions / Risks

1. **後端確認（阻斷項目，需在網址正式化前解決）**：demo 頁面提示文字寫的是「不會連到 Supabase」，但現有正式版用 Firebase。需要 Stanley 確認這個 fork 實際／預計接的後端是 Firebase 還是 Supabase，這會決定「正式化」時資料怎麼接。
2. **`patchItem()` 現況**：目前是否已支援直接更新 day/time，還是只能改 status？需要 Stanley 看程式碼確認，若不支援則是前置工作。
3. **AI 解析失敗的 fallback**：如果 AI 無法從貼上的文字判斷某個項目的 day/time，這個項目該怎麼處理？（例如：退回候選區、標記為「待補時間」、還是要求使用者重新輸入文字）目前未決定，先列為 Should，不阻擋 Must 項目開發。
4. **API 金鑰外露風險**：Scout Checklist 是純前端靜態網站，若直接在前端呼叫 Gemini API，金鑰會暴露在瀏覽器可見的程式碼中。需要決定：接受這個風險（與現有 trip_id 存取模式相同的安全假設），或另外架設 proxy/serverless function 保護金鑰。
5. **舊資料搬移**：若正式網址切換後，`chiahsin-tech` 舊版裡已有的真實旅程資料需要搬到新版，這次不做自動化工具（見 Won't），搬移方式待你和 Stanley 決定。
