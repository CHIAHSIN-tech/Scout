# Kickoff Prompt — Hot Sauce Library（辣醬庫）

**給 Stanley 的開發指令**

---

## Context（背景）

你正在開發 **Hot Sauce Library（辣醬庫）**——一個個人收藏管理 + 多人協作的辣醬資料庫應用。

**完整規格**：見 `/mnt/project/spec-hot-sauce-library.md`

**技術棧**
- 前端：Vue 3 + Vite
- 後端：Supabase Realtime DB
- 部署：GitHub Pages + Supabase
- 身份驗證：無帳號分享連結模式

---

## 這一 Loop 的目標：Tracer Bullet（第 1 個可動的端點）

**目的**：證明「從 Supabase 新增 → 列表顯示」的核心流程成立。還沒有編輯、刪除、圖片、多人同步，但這是基礎。

**交付物**
- Vue 3 + Vite 專案初始化
- Supabase 連接（環境變數配置）
- `sauces` table 建立（含 schema）
- `SauceList.vue` — 列表頁面（從 Supabase 讀取 & 按回購度排序）
- `SauceForm.vue` — 新增表單（驗證 4 個評分都必填）
- 「新增」功能完整連接（submit 後 insert 到 Supabase，列表自動重整）

**停止點**：完成後停止，等待 CHIA 審核。不要進入第 2 loop（編輯 / 刪除）。

---

## 驗收標準（Acceptance Criteria）

完成時，應該能執行以下流程：

### AC-1: 初始化與連接
- [ ] Vue 3 + Vite 專案成功建立
- [ ] Supabase CLI 初始化完成
- [ ] 環境變數 `.env.local` 配置（含 Supabase URL + API Key）
- [ ] 應用啟動後，console 無錯誤（可檢查 dev tools）

### AC-2: 列表頁面顯示
- [ ] 打開應用 → 看到「辣醬庫」標題 + 空列表或既有辣醬列表
- [ ] 所有辣醬按「回購度」降序排列（5 星在上）
- [ ] 每個辣醬卡片顯示：名稱、主評分（辣度 X 星）、商品連結（可點擊）
- [ ] 列表佈局在手機 (390px 寬) 上無橫向捲動

### AC-3: 新增表單顯示
- [ ] 列表頁有「+新增辣醬」按鈕
- [ ] 點擊後彈出或導到表單頁面
- [ ] 表單欄位完整：名稱、URL、辣度、香氣、CP值、回購度（各 1-5 星）

### AC-4: 表單驗證
- [ ] 名稱為空 → 無法提交（提示：「名稱必填」）
- [ ] URL 為空 → 無法提交（提示：「URL 必填」）
- [ ] 任何評分維度為空 → 無法提交（提示：「所有維度必填」）
- [ ] 所有欄位填完 → 「提交」按鈕啟用

### AC-5: 新增到 Supabase
- [ ] 填完表單 & 點「提交」→ 資料插入 Supabase `sauces` table
- [ ] Supabase Console 中能看到新記錄
- [ ] 新記錄含正確的欄位值（name, url, ratings 物件）

### AC-6: 列表自動重整
- [ ] 新增後自動回到列表頁
- [ ] 新辣醬立刻在列表上出現
- [ ] 列表重新按回購度排序（如新辣醬回購度 5，它應該在最上方）

### AC-7: 完整 End-to-End
```
1. 開啟應用 → 看到空列表
2. 點「+新增」
3. 輸入：
   - 名稱：「Frank's RedHot Original」
   - URL：「https://www.franksredhot.com/products/original-cayenne-pepper-sauce」
   - 辣度：4, 香氣：4, CP值：5, 回購度：5
4. 點「提交」
5. 列表自動重整，新辣醬出現在最上方
6. 卡片顯示：「Frank's RedHot Original」+ 「辣度 4★」+ 可點擊的 URL
```

---

## 實作指南

### 第 1 步：初始化專案
```bash
npm create vite@latest hot-sauce-library -- --template vue
cd hot-sauce-library
npm install
npm install @supabase/supabase-js
```

### 第 2 步：Supabase 設定
1. 登入 Supabase 控制台
2. 建立新專案（或用既有的 Scout 專案）
3. 在 SQL Editor 執行：
```sql
CREATE TABLE sauces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  ratings JSONB NOT NULL, -- {"spiciness": 1-5, "aroma": 1-5, "cpValue": 1-5, "repurchase": 1-5}
  image_url TEXT,
  price DECIMAL,
  purchase_date DATE,
  tags TEXT[],
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  created_by TEXT,
  last_edited_by TEXT
);
```

4. 設定環境變數 `.env.local`：
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### 第 3 步：組件架構
```
src/
  ├── services/
  │   └── sauceService.js        // Supabase CRUD 邏輯
  ├── pages/
  │   ├── SauceList.vue           // 列表頁面
  │   └── SauceForm.vue           // 新增 / 編輯表單
  ├── components/
  │   └── SauceCard.vue           // 列表項目卡片
  ├── App.vue
  └── main.js
```

### 第 4 步：關鍵檔案框架

**`src/services/sauceService.js`**
```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY
const supabase = createClient(supabaseUrl, supabaseKey)

export async function getAllSauces() {
  // 從 Supabase 取得所有辣醬，按 ratings.repurchase 降序
}

export async function addSauce(sauceData) {
  // 新增辣醬到 sauces table
  // sauceData: { name, url, ratings: { spiciness, aroma, cpValue, repurchase } }
}
```

**`src/pages/SauceList.vue`**
- 掛載時呼叫 `getAllSauces()`
- 顯示辣醬卡片列表
- 卡片點擊導入詳細頁（第 2 loop 才實作）
- 「+新增」按鈕導到 SauceForm

**`src/pages/SauceForm.vue`**
- 表單欄位：name, url, 4 個評分星級選擇器
- 驗證邏輯（所有欄位必填）
- 提交時呼叫 `addSauce()`
- 提交後導回列表

---

## 檢查清單

完成前，確認：

- [ ] 專案結構清晰，檔案分層符合上述架構
- [ ] 環境變數正確配置，應用啟動無錯誤
- [ ] `sauces` table 在 Supabase 建立完成
- [ ] 「新增」流程完整：表單 → 驗證 → 插入 DB → 列表重整
- [ ] 列表按回購度正確排序
- [ ] 卡片 UI 在手機寬度 (390px) 下正常顯示，無橫向捲動
- [ ] 所有 AC (AC-1 ~ AC-7) 都能通過

---

## 停止點與審核

**這裡停下來。** 完成上述內容後，不要進入第 2 loop。

準備審核時：
1. 推送到 GitHub（新建 `hot-sauce-library` repo）
2. 貼上 repo 連結
3. 貼上已部署到 GitHub Pages / Vercel 的 live demo URL（如果有部署的話）
4. 附上一份簡短的「做了什麼 & 碰到什麼困難」報告

**CHIA 會審核：**
- 代碼品質 & 架構是否清晰
- 是否所有 AC 都通過
- 是否還有改進空間

審核後，會給出下一 loop 的指令（編輯 / 刪除）。

---

## CLAUDE.md（給 Claude Code 的環境指標）

```markdown
# Hot Sauce Library — Claude Code 運作指南

## 結構
- `/src` — Vue 3 組件 + 服務層
- `/src/services/sauceService.js` — Supabase 邏輯（SSOT）
- Supabase table: `sauces`（schema 見下）

## 禁止項
1. ❌ 不要一次實作超過一個 feature（一個 loop = 一個 feature）
   → 若感覺還能多做，停止、等人審核
2. ❌ 不要加 Should / Could 功能（圖片、價格、購買日期）到這 loop
   → 只做 Must：新增 + 列表 + 驗證
3. ❌ 不要實作編輯 / 刪除 / 多人同步
   → 第 2, 3 loop 才做
4. ❌ 不要自動導入假資料（seed data）
   → 除非 CHIA 明確要求

## 檔案不動作品
- `spec-hot-sauce-library.md` — 規格 SSOT，勿修改
- `.env.local` — 人工填 Supabase 金鑰，勿 commit

## 部署
- 開發：`npm run dev`（localhost:5173）
- 預發佈：`npm run build && npm run preview`
- 驗收命令：`npm test`（若有測試的話）

## 認知債清單
- 第 2 loop：新增編輯 / 刪除功能
- 第 3 loop：Realtime sync（多人協作）
- 第 4+ loop：圖片、價格、購買日期、搜尋、分類
```

---

## 常見問題

**Q: 要建立帳號系統嗎？**  
A: 不。這 loop 沒有帳號。分享連結模式是第 6 loop 才實作（暫時先假設所有用戶都能編輯同一個庫）。

**Q: 要連接 Realtime 嗎？**  
A: 不。這 loop 只做「新增」，多人同步是第 3 loop。

**Q: 圖片怎麼做？**  
A: 第 4 loop。現在只做 `image_url` 欄位備好，暫不上傳邏輯。

**Q: 要寫測試嗎？**  
A: 如果有時間，加基本的 unit test（例如表單驗證）。但不是必須，done > perfect。

---

## 成功的樣子

當你完成這個 loop 時，應該能做到：

```
👤 使用者打開應用
  ↓
📋 看到空列表（或既有辣醬）
  ↓
➕ 點「+新增」
  ↓
📝 填入「Frank's RedHot」+ URL + 評分（辣度 4, 香氣 4, CP值 5, 回購度 5）
  ↓
✅ 點「提交」
  ↓
🎉 列表自動重整，新辣醬出現在最上方，卡片顯示「辣度 4★」
```

這樣就 tracer bullet 成功了。

---

**祝你編碼愉快！如有問題，就在對話裡提。**

—— CHIA

