# Scout 確認清單（網頁版）

出發前的「必須確認 / 可以彈性 × 已確認 / 未確認」儀表板。與 Scout 的 Streamlit
後端共用**同一個 Supabase 資料庫**，因此在這裡標記「已確認」，Streamlit 端重新整理
也會看到；反之亦然。

> 這個資料夾是「獨立網頁版」的雛形，未來會搬到自己的 repo
> （原本是 Firebase，現改寫成 Supabase）。目前先放在主 repo 內方便一起開發。

---

## 它怎麼運作

- 純靜態網頁（HTML + CSS + 原生 JS），沒有後端、沒有打包步驟。
- 直接打 Supabase 的 REST API（PostgREST）讀寫 `itinerary_items`。
- 兩個頂層視圖，用上方「✅ 確認清單 / 🗓️ 行程表」切換：
  - **✅ 確認清單**（兩軸儀表板）：必須確認 / 可以彈性 × 已確認 / 未確認；
    「必須確認且未確認」置頂最顯眼，「已確認 / 可以彈性」預設收合（手機少捲動）。
  - **🗓️ 行程表**：
    - **清單**：依 Day 分組顯示已排入項目（時間 / 地點 / 類別 icon），最上方提醒「還有 N 項未排定」。
    - **時間軸**：當天項目依時間排在垂直時間軸，重疊項目並排顯示不互蓋；
      **按住卡片上下拖曳即可改時間**（放開自動寫回後端），重疊時顯示警告但不阻擋。
    - 旅行中自動聚焦並高亮「今天」。
    - **🤖 AI 匯入行程**：貼一段文字行程 → Gemini 解析成項目（含天 / 時間 / 地點 / 類別）→
      直接以「已排入行程」狀態加入；無法判斷天數的項目會退回候選。
- **排程**：候選卡片可「📅 排入行程」（選天 + 時間），已排定的可「↩ 退回候選」，
  與 Streamlit 端共用同一份資料。
- **身分機制**：網址帶 `?trip=<trip_id>`，`trip_id` 就是存取憑證，不做帳號系統。
  - ⚠️ 已知並刻意接受的取捨：分享連結外流 = 任何人可讀寫該趟旅程資料。
- **同步機制**：手動「↻ 重新整理」按鈕（不訂閱 Realtime，省成本）。

## 正式 vs 範例

- **正式（預設）**：`index.html?trip=<trip_id>`，無任何旗標即為對外正式版，按鈕會實際讀寫 Supabase。
- **範例（開發預覽）**：`index.html?demo=1` → 假資料、按鈕只在本機作用、不連網。
  適合先確認 UI 與互動，或在沒有 Supabase 連線時 demo。AI 匯入在範例模式用本地解析。

> 關於 spec 的「移除 demo 旗標」：正式體驗本來就不依賴旗標（預設即正式），demo 是「選用」的
> 離線預覽，保留它對正式版零影響、卻是無 Supabase 環境下唯一的預覽 / 測試途徑，故予以保留。

---

## 設定（第一次）

1. 在 Supabase SQL Editor 跑專案根目錄的 [`../supabase_schema.sql`](../supabase_schema.sql)
   （建表 + 確認狀態欄位 + 對 anon 開放存取）。
2. 填入連線資訊：`config.js` 已經建好（被 `.gitignore` 擋住），直接編輯它、替換兩個值即可
   （若不存在，`cp config.example.js config.js`）。
   到 Supabase 後台 **Project Settings → API** 拿：
   - `SUPABASE_URL` = Project URL
   - `SUPABASE_ANON_KEY` = anon / public key（可公開，不要用 service_role）
   - （選填）`GEMINI_API_KEY` = Google AI Studio 的 API key，只有「AI 匯入行程」會用到；
     不填則 AI 匯入會顯示提示，其餘功能照常。⚠️ 前端金鑰外露取捨見 `config.example.js` 註解。
3. 本機預覽（任一即可）：
   ```bash
   python -m http.server 8000
   # 開 http://localhost:8000/scout-checklist/?trip=1
   ```

沒設定好 `config.js` 時，頁面會顯示提示而不是壞掉。

---

## 分享連結格式

```
https://<你的 GitHub Pages 網域>/?trip=<trip_id>
```

`trip_id` 可在 Streamlit 端建立旅程後，從 Supabase 的 `trips` 表查到。

---

## 部署到 GitHub Pages

1. 把本資料夾內容放到 GitHub Pages repo（例如 `chiahsin-tech.github.io/scout-checklist/`）。
2. **`config.js` 必須一起部署**才能連到 Supabase。
   - 本地 `.gitignore` 預設擋掉 `config.js`（避免誤把設定混進主 repo）。
   - 要部署時，於 Pages repo 移除該行、或用 CI 注入 `config.js`。
   - anon key 屬可公開金鑰，commit 它是 Supabase 靜態網站的常見做法；
     真正的存取邊界是 `trip_id` 連結。

---

## 檔案

| 檔案 | 作用 |
|------|------|
| `index.html` | 進入點，載入 config / app |
| `app.js` | 抓資料、渲染兩軸儀表板、切換已確認 |
| `styles.css` | Scout 米色 + 森林綠配色，手機優先 |
| `config.example.js` | 設定檔範本（複製成 `config.js`） |
