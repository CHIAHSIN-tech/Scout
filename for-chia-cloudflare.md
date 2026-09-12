# 給 Chia：Scout 要從 Netlify 搬到 Cloudflare

> 寫於 2026-09-12。這份是**要你做的事**，不是要你讀的技術文件。
> 每一步都寫了「做什麼」和「怎麼知道成功了」。卡住就停下來問 Stanley，不要硬猜。

---

## 先講三件你會在意的事

**1. 這件事會推翻你前一天才剛做好的設定。**

你在 **2026-09-11** 把 Netlify 接上 GitHub 自動部署——那是你待辦清單上最重要的一件，
而且它解掉了「公開站版本落後」那個老問題。現在 Stanley 決定把託管收斂到 Cloudflare，
等於那條線要重接一次。

這不是說你做錯了。當初 repo 轉給你（ADR-014）的理由就是「你的 Netlify 接著你的 GitHub」，
換平台就等於部分推翻那個理由。**所以要嘛你自己申請一個 Cloudflare 帳號、由你接 GitHub，
要嘛部署權就回到 Stanley 身上。** 這件事請你和他講清楚再動手，不要默默選一個。

**2. 網址會變，已經發給家人的分享連結會失效。**

現在的網址是 `shoppingtool.netlify.app`。搬到 Cloudflare Workers 之後預設會變成
`scout.<你的帳號>.workers.dev` 之類的東西。

- 你和 Stanley 自己用的：把手機主畫面上的捷徑重新加一次就好。
- **家人在看的購物分享連結（`/share.html?list=<情境標籤>`）會死。** 切換之後要重發一次。
  這次**不處理自訂網域**，所以沒有「網址不變」這個選項。

**3. 現在還沒有搬。** 這個 commit 只把設定檔寫好，**沒有建任何 Cloudflare 專案、
沒有部署、沒有動 DNS**。Netlify 站台照常運作。你按照下面做完，兩邊才會並存；
確認 Cloudflare 那邊真的好了，才輪到關掉 Netlify。

**4. 行程表要登入才看得到，購物分享連結不用。** 見步驟 4.5。
而且**行程表不會出現在 GitHub 上、也不會走你的自動部署**——它含訂位編號和旅館地址，
而 repo 是公開的。那些檔案由 Stanley 從自己電腦 `npx wrangler deploy` 上去。
你負責的靜態網站與 API 一切照常。

---

## 為什麼是 Workers 不是 Pages

你如果去 Cloudflare 後台看，會先看到 **Pages**，它看起來比較像 Netlify。**不要用 Pages。**

原因只有一個，但很致命：**Pages 不支援排程（Cron Trigger）**，Workers 支援。

Scout 有一支叫 `keepalive` 的排程，每週一、四各跑一次，去戳兩個 Supabase 專案，
不讓它們因為「閒置 7 天」被自動暫停。2026-07 和 2026-08 各被暫停過一次，
每次都要有人手動到後台按 Resume。這支排程是唯一擋著這件事的東西。

用 Pages 的話，就得為了這一支排程另外開第二個 Cloudflare 專案——那比現在更麻煩。

---

## 你要做的事

### 步驟 0：確認前提

- [ ] 你有一個 **Cloudflare 帳號**（免費方案就夠）。用**個人帳號，不要用公司帳號**
      （這是 Scout 一直以來的紀律，Netlify 和 Supabase 也是）。
- [ ] 你電腦上的 Scout repo 已經 `git pull` 到最新，根目錄看得到 `wrangler.toml` 和 `worker/` 資料夾。

### 步驟 1：在 Cloudflare 建一個 Worker，接上 GitHub

1. 登入 Cloudflare → 左邊選 **Compute (Workers)** → **Create** → 選 **Import a repository**
   （不是 "Start with Hello World"，也不是 Pages）。
2. 授權 GitHub，選 `CHIAHSIN-tech/Scout`。
3. 設定畫面：
   - **Project name**：`scout`
   - **Build command**：**留空**（Scout 沒有 build step，這是刻意的）
   - **Deploy command**：`npx wrangler deploy`
   - 其他保持預設
4. 按下去，等它跑完。

**怎麼知道成功了：** 部署紀錄最後一行是綠色的成功訊息，並且給你一個
`https://scout.<你的帳號>.workers.dev` 的網址。

**如果失敗：** 把整段錯誤訊息複製給 Stanley，不要自己改 `wrangler.toml`。

### 步驟 2：打開那個網址，確認是**新版**

這一步不能跳。**這個專案有「手動部署造成線上跑舊版」的前科**（2026 上半年踩過，
花了很久才發現）。所以切過去的第一件事永遠是確認版本，不是慶祝。

- [ ] 打開 `https://scout.<你的帳號>.workers.dev`，看得到「🛒 購物 / 🗺️ 行程」兩個 Tab。
- [ ] 兩個 Tab 都點一次，購物清單和行程都讀得到資料。
- [ ] 打開 `https://scout.<你的帳號>.workers.dev/share.html?list=送禮-媽媽`
      （`list=` 後面換成你們實際在用的情境標籤），確認清單顯示得出來——
      **這條就是家人會看到的頁面**。

三條都過了，才算「Cloudflare 上真的是新版」。

### 步驟 3：確認排程有掛上去

- [ ] Worker 頁面 → **Settings** → **Trigger Events**，應該看得到一條
      **Cron Trigger：`17 3 * * 1,4`**（台灣時間每週一、四上午 11:17）。

如果沒有，代表 `wrangler.toml` 的 `[triggers]` 沒被吃到，回報給 Stanley。

> 排程失敗不會有人通知你——它只寫進 Worker 的 log。這是既有的已知問題
> （`specs/spec-keepalive-visibility.md`），這次遷移沒有一起解決。

### 步驟 4：AI 金鑰（**可以先跳過**）

網頁上的兩個 AI 按鈕（匯入行程／生成行程）依 ADR-017 **預設是隱藏的**，
AI 現在走 Claude ＋ MCP，不走網頁。所以**不設這個金鑰，Scout 的日常功能完全不受影響**。

之後真的要把網頁 AI 打開時，才需要做這件事：

```bash
npx wrangler secret put GEMINI_API_KEY
```

然後把金鑰貼進去。**金鑰絕對不要寫進 `wrangler.toml` 或任何檔案**——那個檔案在 GitHub 上是公開的。

沒設的話，那兩個功能會回一則明確的 500 錯誤訊息（「伺服器未設定 GEMINI_API_KEY」），
不會靜默壞掉。

### 步驟 4.5：把行程表擋在 Google 登入後面（Cloudflare Access）

2026-09-12 Stanley 決定：**行程表要登入才看得到，購物的分享連結維持公開。**

行程表的內容比購物清單敏感得多——訂位編號、旅館地址、班機時刻。
購物分享連結是刻意要給家人隨手打開的，加登入等於把它廢掉。所以只擋一個路徑。

1. Cloudflare 後台 → **Zero Trust** → **Access** → **Applications** → **Add an application**
   → 選 **Self-hosted**。
2. **Application domain** 填：`scout.<你的帳號>.workers.dev`，**Path** 填 `trips/*`。
   ⚠️ 只填這個路徑。整個網域都擋的話，家人的購物分享連結會一起被擋住。
3. **Add a policy** → Action 選 **Allow** → Include 選 **Emails**，
   把你和 Stanley 的 Google 帳號加進去。
4. **Login methods** 至少留 Google（Zero Trust 預設就有 One-time PIN，可以一起留當備援）。

**怎麼知道成功了：**
- 開無痕視窗打 `https://scout.<帳號>.workers.dev/trips/`，會被導到 Google 登入。
- 同一個無痕視窗打 `https://scout.<帳號>.workers.dev/share.html?list=<某個標籤>`，
  **不需要登入就看得到**。兩個都成立才算對。

> 免費方案含 50 個使用者，兩個人綽綽有餘。**不需要自訂網域**——
> Access 可以直接掛在 `workers.dev` 的主機名加路徑上。

### 步驟 5：重發分享連結

- [ ] 把新的 `/share.html?list=...` 連結重新發給在看清單的家人。
      產生方式：購物 Tab 選一個「情境」→ 按分享，連結會自動複製。
- [ ] 舊的 Netlify 連結先**不要**急著讓它死（見下一步）。

### 步驟 6：確認一切正常「之後」，才關掉 Netlify

**至少讓兩邊並存幾天**，跨過一次排程日（週一或週四）再動手。

- [ ] Netlify 後台 → Scout 站台 → **Site settings → Danger zone**，
      選 **Stop builds**（先停建置，不要直接刪站）。
- [ ] 再觀察幾天，確定沒有人在用舊網址，才 **Delete site**。

repo 裡的 `netlify.toml` 和 `web/netlify/` 由 Stanley 在最後一個 commit 刪掉；
**Netlify 後台的站台只有你能關**，程式碼刪掉不會讓它自己消失。

---

## 出事了怎麼退回去

在你做完步驟 6 之前，**Netlify 站台一直都還在跑**。所以退路很簡單：

1. 停用 Cloudflare 的 Worker（Worker 頁面 → Settings → 刪掉，或把 GitHub 連接斷開）。
2. 繼續用 `shoppingtool.netlify.app`。

repo 裡的 `netlify.toml` 與 `web/netlify/` 只要還在版本控制裡，Netlify 就照常運作——
這是刻意的：**遷移失敗的定義不是「Cloudflare 沒起來」，是「Netlify 已經拆掉而 Cloudflare 沒起來」。**

如果 Stanley 已經 commit 了拆除，也還可以 `git revert` 那一個 commit 把它救回來。

---

## 這次改了什麼（給你參考，不用動手）

| 原本（Netlify） | 現在（Cloudflare Workers） |
|---|---|
| `netlify.toml` 的 `publish = "web"` | `wrangler.toml` 的 `[assets] directory = "./web"` |
| 四支檔案 `web/netlify/functions/*.js` | 一支 `worker/index.js`，裡面四段分開 |
| `/.netlify/functions/ai-parse` | `/api/ai-parse` |
| `/.netlify/functions/ai-suggest` | `/api/ai-suggest` |
| `/.netlify/functions/share` | `/api/share` |
| `netlify.toml` 的 `[functions."keepalive"] schedule` | `wrangler.toml` 的 `[triggers] crons`（同一個值） |
| — | `web/_redirects`：舊網址 308 轉到新網址，換過去的當下不會有人看到 404 |

功能完全沒改，只換了路徑和平台。購物和行程的資料都還在原本的兩個 Supabase 專案，**沒有動過**。

---

## 還沒解決、你應該知道的

1. **自訂網域沒做。** 這次不碰 DNS。要一個穩定的網址（例如 `scout.你的網域`），
   是另一件事，要另外決定。
2. **Netlify 那邊的環境變數不會自動搬過來。** 如果你在 Netlify 上設過 `GEMINI_API_KEY`，
   Cloudflare 這邊要重設一次（步驟 4）。
3. **排程失敗仍然沒有通知。** 換平台沒有改善這件事。
4. **這份文件寫的每一步，Stanley 都沒有實際在 Cloudflare 後台跑過**——
   他只在自己電腦上用 `wrangler dev` 驗過程式碼會動（靜態頁、三個 API、排程觸發都通）。
   後台的畫面和選單名稱可能和上面寫的有出入，以你看到的為準。
