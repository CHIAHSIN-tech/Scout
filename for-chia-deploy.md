# 給珈欣 — 把合併版 app 部署上線

> **背景**：購物清單（buylist）和行程確認清單（scout-checklist）已經合併成**一個網頁、頂部兩個 Tab**。
> 程式碼寫好也測過了，就差「接上 Netlify 讓它自動部署」這一步。
>
> **為什麼是你做**：未來後台主要是你在操作，所以 repo 的所有權轉到你名下，這樣你之後要改部署設定、
> 加服務、換平台都不用再找 Stanley。這是一次性的設定，做完就順了。

---

## 第 0 步：✅ 已完成 — repo 轉移

你已經接受了，repo 現在是 `github.com/CHIAHSIN-tech/Scout`，PR #4 也跟著搬過來了。

**只剩一個小調整（麻煩順手做）**：**Settings → Collaborators** → 把 **witsper-stanley** 從 **Write** 改成 **Admin**。

現在他是 Write，推程式、合併 PR 都沒問題（已實測），但改不了 repo 設定——例如之後要調整 webhook、
改公開/私有、或接別的服務時就會卡住又要來找你。給 Admin 可以省掉這類來回。
你自己仍然是擁有者，這不會影響你的任何權限。

---

## 第 1 步：Netlify 接上 repo

你的 Netlify 已經連著 CHIAHSIN-tech 這個 GitHub 帳號，所以轉移完 `Scout` 會**直接出現在清單裡，不用另外安裝任何東西**。

1. 開 Netlify → 進 **shoppingtool** 這個站
   > ⚠️ 是進**既有的站**，不是建新站。建新站會拿到一個新網址，`shoppingtool.netlify.app` 就不能用了。
2. 左側 **Site configuration** → **Build & deploy**
3. 找到 **Continuous deployment** 區塊 → 按 **Link repository**
4. 選 **GitHub** → 找 **Scout**
5. 設定：
   - **Branch to deploy**：`main`
   - **Build command**：**留空**
   - **Publish directory**：**留空**
   > 專案根目錄有 `netlify.toml`，發佈目錄（`web`）和 functions 位置都寫在裡面，
   > Netlify 會自己讀。手動填反而會蓋掉它、然後部署出錯。
6. 存檔

## 第 2 步：加環境變數

同樣在 **Site configuration** → **Environment variables** → **Add a variable**

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | 你的 Gemini 金鑰 |

> 這把金鑰是給「✨ AI 匯入行程」和「🔗 貼連結帶入」用的。
> 舊的 checklist 站上已經有一把，可以直接複製過來。
> **金鑰只放在這裡**，不會進程式碼、也不會外洩到前端（前端只呼叫 `/.netlify/functions/...`）。

## 第 3 步：合併 PR

回 GitHub → 開 **PR #4**（標題是「feat(web): 合併版雙 Tab app ＋ Netlify 部署設定」）→ **Merge**。

合併後 Netlify 會自動開始部署，大概一兩分鐘。

---

## 部署完請確認這幾件事

1. 開 `https://shoppingtool.netlify.app/`
   - 頂部有 **🛒 購物 / 🗺️ 行程** 兩個 Tab，可以切換
   - 重新整理後會停在你上次看的那個 Tab
2. **購物 Tab**：清單有資料、可以新增一筆
3. **行程 Tab**：
   - 有一個旅程下拉選單，選得到「沖繩 5 天（示範）」
   - 按 **＋ 新旅程** 可以建立新旅程（**這是新功能**，以前只能從 Stanley 的 Streamlit 建）
   - 按 **＋ 新增項目** 可以手動加一筆行程（以前只有 AI 匯入能加）
   - 確認清單 / 行程表 / 時間軸 三個檢視都正常
4. Netlify 的 **Functions** 分頁應該看到兩支：
   - `ai-parse`（AI 匯入行程）
   - `keepalive`（標示 **Scheduled**）

### keepalive 是什麼

Supabase 免費方案**閒置 7 天會自動暫停**，暫停後 app 就連不上資料庫（這個月已經發生過一次）。
這支排程每週一、四各跑一次，打一下兩個資料庫讓它們保持清醒。

**要驗證它有沒有用**：十天後打開行程 Tab，如果不用手動 un-pause 就是成功了。
在確認之前，萬一哪天真的連不上，還是去 Supabase 後台按 un-pause。

---

## 有問題的話

- **Netlify 部署失敗** → 進該次 deploy 的 **Deploy log**，把錯誤訊息貼給 Stanley
- **網頁打得開但沒資料** → 多半是 Supabase 被暫停了，去後台看專案狀態
- **行程 Tab 顯示「操作失敗」紅字** → 同上，那是連不到資料庫的訊號（它不會靜默失敗，一定會顯示紅字）

---

## 這次還有哪些變動（給你知道就好，不用做什麼）

- **Streamlit 版的 Scout 退役了**。行程規劃、購物清單的功能都已經在網頁版上，而且更完整。
  唯一沒搬過來的是「AI 生成行程」（多輪問答讓 AI 生一份完整行程）——那個功能暫時沒有替代品，
  真的需要再說。
- 行程項目的**欄位編輯、上下移排序、跨天移動、刪除旅程**也還沒搬過來，目前網頁版只能建立、
  新增、排入行程、退回候選、改時間（時間軸上拖曳）。要補再開 spec。
- 完整的技術脈絡在 `context.md`，這次合併的規格在 `specs/spec-scout-app-merge.md`。
