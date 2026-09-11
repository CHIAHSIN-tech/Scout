# 給珈欣 — 權限對等：讓我們兩個都不會卡住對方

> **建立於 2026-09-06。**
> **背景**：Stanley 反映「這個協作很卡，一下需要她一下需要我」。查下來發現這不是誰的操作問題，
> 是**四個系統各自只有一個擁有者**，任何一件事都會落在其中一個人身上，另一個人只能等。
>
> 這份的目的是把能對等的都對等掉。**下面這幾件都只有珈欣能做**，Stanley 這邊做不到。
> （2026-09-11 更新：③ 自動部署已完成、④ 依 ADR-017 已不需要）

---

## 為什麼會卡 — 現況盤點

| 系統 | 擁有者 | 對方能不能做事 | 能不能兩人同權 |
|---|---|---|---|
| Supabase・購物資料庫 | Stanley | ❌ 珈欣進不去 | ✅ 可以（**已邀請，待接受**） |
| Supabase・行程資料庫 | 珈欣 | ❌ Stanley 進不去 | ✅ 可以 |
| GitHub `Scout` repo | 珈欣（ADR-014 轉移） | ⚠️ Stanley 是協作者，權限待確認 | ✅ 可以 |
| Netlify（正式站） | 珈欣 | ❌ Stanley 完全進不去 | ❌ **不行**，見下方說明 |

**Netlify 是唯一做不到的**：免費方案不允許加團隊成員，後台畫面直接寫
「**Upgrade to add members**」。這是方案限制，不是設定沒調對。

但這個限制可以繞過，方法就是下面的第 ③ 件事 —— **接上自動部署之後，日常根本不需要進 Netlify 後台**。

---

## ① 接受 Supabase 的 Owner 邀請（30 秒）

邀請信已經寄到你的 Gmail（Stanley 邀請你時用的那個信箱），角色是 **Owner**，跟 Stanley 完全同權。收信點接受即可。

**為什麼**：購物清單的資料庫在 Stanley 帳號底下。它前陣子因為閒置**被 Supabase 自動暫停**，
購物 Tab 就整個壞掉，而當時只有 Stanley 能重新啟動。你接受之後這種事你也能自己救。

> 補充：那次暫停已經在 2026-09-05 手動 resume 好了，資料完好，購物功能已恢復。

## ② 反過來，把 Stanley 加進你的 Supabase（1 分鐘）

**為什麼**：行程資料庫在你帳號底下，同樣的事會反過來發生一次 —— 哪天它被暫停，就只有你能救。
現在對等掉，以後誰在線誰處理。

做法：
1. Supabase 後台 → 左側 **Team**
2. **Invite members**
3. 角色選 **Owner**（不要選 Developer，那個不能改專案設定，也就不能 resume）
4. 填 `stanley.luke.de@gmail.com`

## ③ ~~把 Netlify 站接上 GitHub 自動部署~~ —— ✅ 已完成（2026-09-11 確認線上已是新版）

**現在的狀況**：`shoppingtool.netlify.app` 上跑的版本，比 GitHub 上的**舊很多**。
以下功能全部寫好、測過、已經在 `main` 上，但線上都沒有：

- 行程項目的編輯／刪除／跨天移動、刪除旅程
- 匯出到 Google 日曆（`.ics`）與 Google Maps（每張卡片也有「加到日曆／開地圖」連結）
- AI 生成行程（六題問答生成整份行程）
- 購物清單的唯讀分享連結
- 兩個 Tab 的字體與配色統一
- 可以加到手機主畫面（PWA）
- 購物清單的關鍵字搜尋、分類折疊、從星號收藏一鍵再買

**原因**：這個站是用**拖拉檔案**的方式部署的，跟 GitHub 沒有連動。
所以我們把程式推上去，網站不會自己更新 —— 要有人手動再拖一次。

做法：Netlify 後台 → 這個站 → **Site configuration** → **Build & deploy** →
連到 GitHub 的 `Scout` repo，分支選 **`main`**。

**接好之後**：我們任何一個人推程式上去，網站自己更新。這一步解決的不只是「現在版本太舊」，
而是「以後每次發布都要找你」這件事本身。

**怎麼確認成功**：接好後看到一次 build 跑完，用無痕視窗開站，行程 Tab 上應該會出現
「⬇ 匯出 .ics」這顆按鈕 —— 那是舊版沒有的。

## ④ ~~設環境變數~~ —— 不用做了（2026-09-11 決定）

Stanley 決定：**需要 AI token 的功能一律走 MCP**（在 Claude 裡用 Scout MCP 工具操作），
網頁本身不再依賴 Gemini 金鑰。所以 `GEMINI_API_KEY` 不需要設。
另外兩個 `SCOUT_BUYLIST_URL` / `SCOUT_BUYLIST_KEY` 在程式裡本來就有內建預設值，分享連結不設也能用。

## ④-b ~~打開「function 失敗通知」~~ —— 做不到，已改用程式解決（2026-09-11）

原本以為 Netlify 能在排程程式失敗時寄信。珈欣的 Claude Code 實際進後台查過：
- **Netlify 沒有「function 錯誤」這種通知事件**，Notifications 頁只有部署相關的事件
- email 通知本身是 **Pro 付費方案**才有

所以這條路不存在（這段原本是 Stanley 那邊憑印象寫的，沒有查證）。
改用程式解決：**app 連不上資料庫時，畫面會直接說「可能被 Supabase 自動暫停」並附上後台連結**
（`specs/spec-keepalive-visibility.md`，2026-09-11 已上線）。不需要任何人去看 log，打開 app 的人當下就知道。

## ⑤ 確認 Stanley 在 GitHub repo 是 Admin

repo 現在在你名下（ADR-014）。

做法：GitHub → `Scout` repo → **Settings** → **Collaborators** →
看 `witsper-stanley` 的權限是不是 **Admin**，不是的話改成 Admin。

**為什麼**：不是 Admin 的話，改分支保護、加 webhook、調 repo 設定都要再找你一次。

---

## ⑥（選配）在 Claude Desktop 裝好 Scout MCP

**為什麼**：2026-09-11 起，網頁上需要 AI token 的功能（AI 匯入行程、AI 生成行程、貼連結帶入）
都已經藏起來，AI 改由 Claude ＋ Scout MCP 提供（`context.md` ADR-017）。
程式碼都還在，只是入口從網頁移到了 Claude。**想在 Claude 裡用 AI 排行程或加購物清單，就要裝這個**；
只用網頁的話不用做。

步驟見 `mcp-server/README.md` 的「非開發者設定步驟」，或直接用下面那段指令讓 Claude Code 帶你做。

## 做完之後長什麼樣

| 系統 | 做完後 |
|---|---|
| Supabase・購物 | 兩人都是 Owner ✅ |
| Supabase・行程 | 兩人都是 Owner ✅ |
| GitHub | 兩人都是 Admin ✅ |
| Netlify | 仍然只有珈欣進得去 ⚠️ 但日常不需要進了（有自動部署） |

剩下真正只有珈欣能做的事，會縮小到：改網域、改環境變數、看 build log。
那些是偶爾一次的事，不是每天都會卡的事。

---

## 之後還可以考慮（不急，不用現在決定）

- **開一個 GitHub Organization，兩人都當 Owner。** ADR-014 當時評估過但沒選，理由是要手動走網頁流程。
  現在感受到的卡點正好就是它要解的問題，值得重新拿出來討論。
- **Supabase 升 Pro**（$25/月）就不會再被自動暫停。注意是**每個 organization 各算一份**，
  兩個帳號各一個 org 就是兩份 —— 除非合併成同一個 org，但那會撞到 ADR-012「不合併兩個 Supabase 專案」，
  要動得先建 superseding ADR。
- **keepalive 失敗時沒有人會知道。** 現在有一支排程函式在保活兩個資料庫，
  但它只能「防止暫停」，**不能把已經暫停的專案叫醒**，而且失敗只寫進 log，沒有通知。
  這個洞會再發生一次，值得另開一份 spec 處理。

---

# 🤖 最省事的做法：把下面這段貼進 Claude Code

如果你手邊有 Claude Code，不用自己一步一步對照上面。**把下面整段複製貼進去**，
它會先幫你查哪些已經做好了、只帶你做還沒做的；能幫你點的它會先試著點，點不到再告訴你點哪裡。

> 貼之前先確認：Claude Code 開在 Scout 這個專案的資料夾底下（這樣它讀得到 repo）。
> 沒有也沒關係，它會問你。

```text
我是 Chia，Scout 這個專案的共同開發者。Stanley 那邊列了幾件只有我能做的事，
請你先幫我確認哪些已經做完了，再一件一件帶我做還沒做的。全程用繁體中文。

重要前提：
- 這些事大多要在網頁後台點（Supabase、Netlify、GitHub）。
  如果你有辦法操作瀏覽器（例如 Claude in Chrome），就先試著幫我點；
  遇到要登入、點不到、或不確定的地方，停下來告訴我點哪裡，我自己點。
- 會寄信給別人或改權限的動作（邀請成員、改角色），按下送出前先跟我確認一次。
- 每次只帶我做一件，做完驗證過再進下一件。不要一次把四件全倒給我。
- 如果某一件你查得出來已經做好了，直接說「這件已完成」並跳過，不要叫我重做。

請按這個順序：

【第 0 步：先查現況】
用命令列查這兩件，不要用猜的，把結果告訴我：
1. 正式站是不是已經是最新版：
   curl -s https://shoppingtool.netlify.app/ | grep -c "export-formats.js"
   （回 1 = 自動部署已接好；回 0 = 還沒）
2. repo 根目錄有沒有 for-chia-access.md，有的話讀它，那是這件事的完整說明。

【第 1 件：把 Stanley 加進我的 Supabase】
行程資料庫在我的帳號底下。如果它被自動暫停，現在只有我能救；
把他加成 Owner 之後誰在線誰救。
帶我到：Supabase → 左側 Team → Invite members → 角色選 Owner
→ 填 stanley.luke.de@gmail.com。
注意：角色一定要 Owner 或 Administrator，選 Developer 沒有用（不能改專案設定）。

【第 2 件：接受 Stanley 寄來的 Supabase 邀請】
他已經把我加進他的 Supabase 帳號，權限跟他一樣。
信寄到我的 Gmail（寄件者是 Supabase），找一下有沒有這封信，點接受就好。
如果找不到，請他重寄。

【第 3 件：確認 Stanley 在 GitHub 是 Admin】
帶我到：GitHub → Scout repo → Settings → Collaborators，
看 witsper-stanley 的權限是不是 Admin，不是的話改成 Admin。

【第 4 件（選配）：在 Claude Desktop 裝好 Scout MCP】
網頁上的 AI 功能已經關掉了（Stanley 決定：要用 AI 一律走 MCP）。
想在 Claude 裡用 AI 排行程、加購物清單，就要做這件；不需要的話可以跳過。
1. 先把我本機的 Scout 專案更新到最新（git pull）——mcp-server/ 這個資料夾
   是 2026-08-16 才加的，舊的副本裡沒有。
2. 確認有 uv，沒有就裝：curl -LsSf https://astral.sh/uv/install.sh | sh
3. 在 mcp-server/ 裡跑 uv sync。如果出現 invalid peer certificate: UnknownIssuer，
   改跑 uv sync --system-certs，而且下面設定檔的 args 最前面也要加 "--system-certs"。
4. 幫我編輯 Claude Desktop 的設定檔
   （Mac：~/Library/Application Support/Claude/claude_desktop_config.json）。
   先備份原檔；如果裡面已經有 mcpServers，只把 "scout" 這一塊加進去，不要覆蓋其他的。
   格式照 mcp-server/README.md 的「非開發者設定步驟」。四個連線值直接從 repo 讀，
   不用跟 Stanley 要（它們是公開的 publishable key，不是密碼）：
   - 行程：web/checklist.js 裡 SCOUT_CONFIG 的 SUPABASE_URL 與 SUPABASE_ANON_KEY
   - 購物：web/buylist.js 開頭的 SUPABASE_URL 與 SUPABASE_KEY
   SCOUT_USERNAME 填 "Chia"（大寫開頭，跟網頁上「我是」的名字一致）。
5. 把 Claude Desktop 完全關掉再重開（你能做就直接做，不行就叫我）。
6. 驗證：請我在 Claude Desktop 說「列出我的旅程」，應該要看到「沖繩 5 天（示範）」。

全部做完之後，幫我用一段話總結哪些完成了、哪些還卡著，
我要把那段話傳給 Stanley。
```
