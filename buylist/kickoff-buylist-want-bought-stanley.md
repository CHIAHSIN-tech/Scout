# Kickoff Prompt — BuyList 想買/已買整合功能

**給 Stanley 的開發指令**

---

## Context（背景）

BuyList 要新增「已買」分頁，讓已購買項目可標星號收藏、記錄購買日期與商品連結。這不是新專案，是在**既有 BuyList 專案**上擴充功能。

**完整規格**：見 `spec-buylist-want-bought.md`
**設計參考**：Claude Design 高保真原型（`BuyList.dc.html` + `README.md`），視覺已定案，直接依規格內 Design Tokens 實作，不需再討論視覺細節

**技術棧**（沿用既有 BuyList）
- 前端：Vue 3 + Vite
- 後端：Firebase Realtime Database（`buylist-590d9`, asia-southeast1）
- 圖示：Icon 庫（例如 Tabler），**不手刻 inline SVG**
- Schema 遷移：**不寫 migration script**，改在讀取資料處做預設值防呆（例如 `item.status ?? 'want'`）

---

## 這一 Loop 的目標：Tracer Bullet（第 1 個可動的端點）

**目的**：證明「想買清單新增 → Firebase 儲存 → 畫面顯示」的核心流程在既有專案架構下成立。這一 loop **不包含**標記已買、星號、URL、多人同步視覺 QA——這些留給後續 loop。

**交付物**
- 擴充既有 Firebase items schema：加入 `status`、`starred`、`date`、`url` 欄位（新項目才會有這些欄位，既有項目靠讀取時防呆補齊，不做 migration）
- `src/services/itemService.js` — 新增 `addItem`、讀取邏輯（含預設值防呆）
- 想買清單畫面：新增表單（文字輸入 + 「+ 加入想買清單」按鈕）+ 卡片列表
- 新增功能完整連接：表單 submit → Firebase push → 清單即時顯示（新項目在最上方）

**停止點**：完成後停止，等待 CHIA 審核。不要進入第 2 loop（標記已買 / 已買清單）。

---

## 驗收標準（對應規格 AC-3 ~ AC-6, AC-9, AC-20 部分）

### AC-1: 專案擴充確認
- [ ] 在既有 BuyList 專案上開發，不是新建專案
- [ ] Firebase 連線正常，既有想買清單資料不受影響（若有既有測試資料）

### AC-2: 新增表單
- [ ] 想買分頁有輸入框，placeholder 文字：「想買什麼？例如：辣豆瓣醬」
- [ ] 輸入框樣式：高度 44px、圓角 100px（pill）、邊框 `1.5px solid #8AB8A0`
- [ ] Focus 狀態：邊框變 `#3D6B54`，加上 `box-shadow: 0 0 0 2px rgba(61,107,84,0.12)`

### AC-3: 提交邏輯
- [ ] 輸入文字 + 點「+ 加入想買清單」按鈕 → 新項目寫入 Firebase，`status: 'want'`, `starred: false`, `date: null`, `url: ''`
- [ ] 按 Enter 鍵效果同點擊按鈕
- [ ] 輸入為空或全空白 → 不提交（no-op）
- [ ] 提交後輸入框清空

### AC-4: 按鈕樣式
- [ ] 全寬、高度 46px、圓角 100px、背景 `#3D6B54`、文字色 `#EAF2ED`、字重 500
- [ ] Hover 背景變 `#2A4D3A`；按下時 `transform: scale(0.98)`

### AC-5: 清單顯示
- [ ] 新項目出現在清單最上方（新項目在前）
- [ ] 卡片樣式：白底、`0.5px solid #DCD8D0` 邊框、圓角 16px、內距 `14px 16px`、卡片間距 10px
- [ ] 項目名稱：15px、字重 500、顏色 `#3C3830`

### AC-6: 空狀態
- [ ] 清單為空 → 顯示置中斜體文字「想買清單是空的」，字體 Georgia/Noto Serif TC，顏色 `#A8A298`

### AC-7: 完整 End-to-End
```
1. 開啟 BuyList → 看到想買分頁（若尚未做分頁切換，先確保目前唯一畫面就是想買清單）
2. 輸入「手沖濾杯」
3. 點「+ 加入想買清單」
4. 驗證：清單最上方出現「手沖濾杯」卡片，樣式符合設計稿
5. 重新整理頁面
6. 驗證：「手沖濾杯」仍在清單中（確認 Firebase 有寫入成功）
```

---

## 實作指南

### 第 1 步：確認既有專案結構
先閱讀既有 BuyList 專案的檔案結構與現有 `itemService`（如果已存在），確認新欄位怎麼加進既有 schema，不要重建整個服務層。

### 第 2 步：擴充 Firebase 資料結構
```javascript
// 新項目寫入格式
{
  id: string,           // Firebase push key
  name: string,
  status: 'want',        // 新欄位
  starred: false,        // 新欄位
  date: null,             // 新欄位
  url: '',                // 新欄位
  createdAt: timestamp
}
```

**讀取既有資料時的防呆**（不寫 migration script）：
```javascript
function normalizeItem(raw) {
  return {
    ...raw,
    status: raw.status ?? 'want',
    starred: raw.starred ?? false,
    date: raw.date ?? null,
    url: raw.url ?? ''
  };
}
```

### 第 3 步：Icon 庫安裝
安裝專案適用的 icon 套件（例如 Tabler Icons 的 Vue 版本，或既有專案已經在用的圖示庫——**先確認 BuyList 現有專案有沒有已安裝的圖示庫，優先沿用**，避免重複安裝）。

這個 loop 只需要用到「新增」相關的圖示，如果表單本身不需要圖示可以先跳過安裝，等第 2 loop（需要打勾、星星、垃圾桶等圖示時）再處理。

### 第 4 步：套用 Design Tokens
規格文件第 5 節已列出完整的色彩、字體、間距 token 表，直接對照使用，不要自己猜配色。

---

## 檢查清單

完成前，確認：

- [ ] 是在既有 BuyList 專案上擴充，檔案結構跟原本一致
- [ ] Firebase schema 新增四個欄位，讀取邏輯有防呆（新舊資料都能正常顯示）
- [ ] 新增流程：表單 → 驗證 → 寫入 Firebase → 清單即時更新
- [ ] 視覺樣式（顏色/字體/圓角/間距）對照規格 Design Tokens 表
- [ ] 手機寬度（375-420px）下無橫向捲動
- [ ] 所有 AC（AC-1 ~ AC-7）皆通過

---

## 停止點與審核

**這裡停下來。** 完成上述內容後，不要進入第 2 loop（標記已買 / 已買清單 / 星號 / URL）。

準備審核時：
1. Commit & push 到既有 BuyList repo
2. 貼上變更的檔案清單（diff 摘要）
3. 附上簡短「做了什麼 & 碰到什麼困難」報告，特別是：既有專案結構跟這次擴充有沒有衝突的地方

**CHIA 會審核：**
- 是否正確擴充既有專案，而非另起爐灶
- Firebase 防呆邏輯是否確實運作（用舊資料測試過嗎）
- 視覺是否對齊 Design Tokens

審核後，會給出第 2 loop 指令（標記已買 + 已買清單 + 移回想買）。

---

## CLAUDE.md（給 Claude Code 的環境指標）

```markdown
# BuyList 想買/已買整合 — Claude Code 運作指南

## 結構
- 這是既有 BuyList 專案的功能擴充，不是新專案
- 開工前先讀懂既有 `src/services/` 和元件結構，沿用既有慣例（命名風格、資料夾組織）
- Firebase project: buylist-590d9（既有，不建新專案）

## 禁止項
1. ❌ 不要一次做超過這個 loop 範圍的功能
   → 只做：新增想買項目 + 清單顯示 + Firebase 寫入/讀取
   → 不做：標記已買、已買清單、星號、URL、分頁切換、篩選
2. ❌ 不要寫 migration script 處理既有資料
   → 用讀取時的預設值防呆取代（見規格 Open Questions 決策）
3. ❌ 不要手刻 inline SVG 圖示
   → 這個 loop 若不需要圖示可以先跳過；真的需要時用既有專案已安裝的圖示庫，或新裝 Tabler 等套件
4. ❌ 不要自創視覺樣式
   → 一切顏色/字體/間距，查規格文件第 5 節 Design Tokens 表，不要自己配色

## 檔案不動作品
- `spec-buylist-want-bought.md` — 規格 SSOT，勿修改
- 既有 BuyList 專案的其他既有功能（不在這次範圍內的東西）不要動

## 部署
- 開發：`npm run dev`
- 驗收前：手動測試 AC-1 ~ AC-7 全部通過

## 認知債清單（後續 loop）
- 第 2 loop：標記已買 + 已買清單畫面 + 移回想買
- 第 3 loop：星號收藏 + 篩選（全部/只看星號）
- 第 4 loop：URL 欄位（想買 + 已買卡片皆需要）+「開啟」連結
- 第 5 loop：視覺 QA + 多人同步驗證
```

---

## 常見問題

**Q: 要先做分頁切換（想買/已買 pill）嗎？**  
A: 不用。這個 loop 只有想買清單，分頁切換等第 2 loop 已買畫面做出來後一起做。

**Q: 圖示庫要在這個 loop 就裝好嗎？**  
A: 看情況。如果這個 loop 完全不需要圖示（例如新增表單本身沒有圖示），可以留到第 2 loop 再裝。不要為了「以後會用到」提前做額外工作。

**Q: 既有 BuyList 資料要特別處理嗎？**  
A: 不用寫遷移腳本。只要讀取資料的地方有做預設值防呆（見上面 `normalizeItem` 範例），舊資料自然會補上新欄位的預設值。

---

## 成功的樣子

```
👤 使用者打開 BuyList
  ↓
📋 看到想買清單（空的或既有項目）
  ↓
📝 輸入「手沖濾杯」+ 點「+ 加入想買清單」
  ↓
✅ 清單最上方出現「手沖濾杯」卡片，樣式對齊設計稿
  ↓
🔄 重新整理頁面，項目仍在（確認 Firebase 寫入成功）
```

這樣就 tracer bullet 成功了。

---

**祝你編碼愉快！如有問題，就在對話裡提。**

—— CHIA
