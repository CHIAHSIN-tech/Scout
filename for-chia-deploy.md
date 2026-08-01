# 給珈欣 — 把合併版 app 部署上線

> **背景**：購物清單（buylist）和行程確認清單（scout-checklist）已經合併成**一個網頁、頂部兩個 Tab**。
> 程式碼寫好、測過、也已經合併進 `main` 了。就差「接上 Netlify」這一步。
>
> **你要做的是下面第 1～4 步。** Stanley 只有最後第 5 步（刪掉舊站），而且要等你確認新站正常之後才做。

---

## 為什麼要在你的帳號建新站

現在的狀況是這樣：

| 東西 | 在誰那裡 |
|---|---|
| `CHIAHSIN-tech/Scout` repo | **你**（已轉移完成） |
| `shoppingtool.netlify.app` 這個 Netlify 站 | **Stanley 的個人 Netlify 帳號**（2026-07-26 他架 buylist 時建的） |

你登入自己的 Netlify（團隊「Scout」）看不到任何專案，就是因為那個站不在你的帳號底下。

未來後台主要是你在操作，所以決定**把部署也搬到你這邊** —— repo 和 Netlify 都在你手上，之後改設定、
加服務都不用再找 Stanley。

**好消息：網址可以保留。** Stanley 已經把他那個舊站改名成 `shoppingtool-old`，
所以 `shoppingtool` 這個名字現在是空的，你建好站之後改成這個名字就接手了（第 4 步）。

> ⚠️ 在你完成第 4 步之前，`shoppingtool.netlify.app` 是 404。
> 這段期間要用舊版的話，網址是 **`shoppingtool-old.netlify.app`**（資料相通，連的是同一個 Supabase）。

---

## 第 1 步：建立新站

1. 登入你自己的 Netlify → 進團隊 **Scout**
2. **Add new site** → **Import an existing project**
3. 選 **GitHub** → 第一次會跳授權畫面：
   - 選 **CHIAHSIN-tech**（你自己的帳號）
   - **Only select repositories** → 勾 **Scout** → **Install**
   > repo 現在在你名下，所以這個授權你自己就能完成，不需要 Stanley。
4. 回到 Netlify，選 **Scout** 這個 repo

## 第 2 步：部署設定（重點：三個都留空）

| 欄位 | 填什麼 |
|---|---|
| **Branch to deploy** | `main` |
| **Build command** | **留空** |
| **Publish directory** | **留空** |
| **Functions directory** | **留空** |

> ⚠️ 專案根目錄有 `netlify.toml`，發佈目錄（`web`）和 functions 位置都寫在裡面，Netlify 會自己讀。
> **手動填反而會蓋掉它、然後部署出錯。**

按 **Deploy**。第一次部署大概一兩分鐘。

## 第 3 步：加環境變數

**Site configuration** → **Environment variables** → **Add a variable**

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | Gemini 金鑰（跟 Stanley 拿，或從舊的 checklist 站的環境變數複製） |

加完到 **Deploys** 分頁按 **Trigger deploy** → **Deploy site** 重跑一次，環境變數才會生效。

> 這把金鑰是給「✨ AI 匯入行程」和「🔗 貼連結帶入」用的。
> **金鑰只放在這裡**，不進程式碼、也不會外洩到前端（前端只呼叫 `/.netlify/functions/...`）。

## 第 4 步：確認正常後，把站名改成 shoppingtool

先用 Netlify 給的臨時網址（像 `xxx-yyy-123.netlify.app`）確認下面這些都對：

1. 頂部有 **🛒 購物 / 🗺️ 行程** 兩個 Tab，可以切換；重新整理後停在上次看的那個
2. **購物 Tab**：清單有資料、可以新增一筆、辣醬庫那個 tab 也在
3. **行程 Tab**：
   - 有旅程下拉選單，選得到「沖繩 5 天（示範）」
   - 按 **＋ 新旅程** 可以建立新旅程 ← **這是新功能**（以前只能從 Stanley 的 Streamlit 建）
   - 按 **＋ 新增項目** 可以手動加一筆 ← **也是新功能**（以前只有 AI 匯入能加）
   - 確認清單 / 行程表 / 時間軸 三個檢視都正常
4. **Functions** 分頁有兩支：`ai-parse`、`keepalive`（後者標示 **Scheduled**）
5. 手機打開不破版

都對了之後 → **Site configuration → General → Site details → Change site name** → 改成 **`shoppingtool`**

（這個名字是空的，Stanley 已經把他的舊站改名讓出來了。改完網址就變回 `https://shoppingtool.netlify.app/`。）

然後跟 Stanley 說一聲。

## 第 5 步（Stanley 做）：刪掉舊站

你確認新站正常、名字也接手之後，Stanley 到他自己的 Netlify 把 `shoppingtool-old` 這個站刪掉。
**在那之前舊站留著當退路**，反正兩個站連的是同一個 Supabase，資料一致。

---

## 順手一提：把 Stanley 升成 Admin

**Settings → Collaborators** → **witsper-stanley** → 從 **Write** 改成 **Admin**。

他現在是 Write，推程式、合併 PR 都沒問題（已實測），但改不了 repo 設定，之後接服務會卡住又要找你。
你自己仍然是擁有者，這不影響你的任何權限。

---

## 出問題的話

- **部署失敗** → 進那次 deploy 的 **Deploy log**，把錯誤訊息貼給 Stanley
- **網頁打得開但沒資料** → 多半是 Supabase 被暫停了，去 Supabase 後台看專案狀態
- **行程 Tab 顯示「操作失敗」紅字** → 同上，那是連不到資料庫的訊號（它不會靜默失敗，一定顯示紅字）

### keepalive 是什麼

Supabase 免費方案**閒置 7 天會自動暫停**，暫停後 app 就連不上資料庫（這個月已經發生過一次，
Stanley 手動 un-pause 才恢復）。這支排程每週一、四各跑一次，打一下兩個資料庫讓它們保持清醒。

**驗證方式**：十天後打開行程 Tab，不用手動 un-pause 就是成功了。
在確認之前，萬一哪天連不上，還是去 Supabase 後台按 un-pause。

---

## 這次還有哪些變動（知道就好，不用做什麼）

- **Streamlit 版的 Scout 退役了**。行程規劃、購物清單的功能都已經在網頁版上，而且更完整。
- **沒搬過來的功能**：AI 生成行程（多輪問答讓 AI 生一份完整行程）、行程項目的欄位編輯、
  上下移排序、跨天移動、刪除旅程。目前網頁版能做的是：建立旅程、新增項目、排入行程、
  退回候選、時間軸上拖曳改時間。要補再開 spec。
- 完整技術脈絡在 `context.md`，這次合併的規格在 `specs/spec-scout-app-merge.md`。
