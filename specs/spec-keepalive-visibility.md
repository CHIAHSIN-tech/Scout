# Spec — 讓「資料庫被暫停」這件事有人會知道

> **用途**：交給 Claude Code 執行的 SSOT。
> **需求來源**：Stanley，2026-09-11。起因是 2026-09-05 發現購物資料庫被 Supabase 自動暫停，
> 而**沒有任何人知道它是什麼時候壞的、也不知道為什麼**。
> **背景**：`web/netlify/functions/keepalive.js` 已經在跑，但它的能力被高估了。

---

## 0. Meta
- **Appetite（時間預算）**：小。Must 的部分是前端錯誤訊息分流，不碰資料層、不碰排程。
- **Status**：draft
- **Date**：2026-09-11

## 1. Problem Statement

Supabase 免費方案閒置 7 天會自動暫停。現況有三個疊在一起的洞：

1. **keepalive 只能「防止」暫停，不能「喚醒」已暫停的專案。**
   專案一旦停了，keepalive 打過去就是失敗，它救不回來——它只在還活著的時候有用。
2. **keepalive 失敗只寫進 Netlify function log。** 沒有人會主動去看 function log。
   而且 log 只有 Chia 進得去（Netlify 免費方案不能加成員，見 `for-chia-access.md`）。
3. **前端壞掉時的訊息幫不上忙。** 使用者看到的是通用連線錯誤，不知道
   「這是資料庫被暫停」，更不知道「按一個 Resume 就好，資料不會掉」。

2026-09-05 那次的實際經過就是三個洞的合成：專案不知何時被停 → 沒人收到通知 →
購物 Tab 壞掉但沒人把它跟 Supabase 聯想在一起 → 拖到有人為了別的事去查才發現。

**這個 spec 不是要讓暫停不發生**（那要付費，見 §10 R3），
**是要讓它發生時 10 秒內就有人知道發生什麼事、以及怎麼修。**

## 2. Primary User + JTBD
- **User**：Stanley / Chia，手機與桌面瀏覽器。
- **JTBD**：當 app 突然打不開資料時，我想要它直接告訴我原因和下一步，
  這樣我不用先懷疑自己網路壞了、再去翻 log、最後才猜到是資料庫被暫停。

## 3. Success Criteria
- 資料庫被暫停時，打開 app 的人**當場**看得懂發生什麼事、以及要做什麼。
- 不需要任何人去看 Netlify function log 才能發現問題。
- 不新增外部相依、不需要付費方案、不引入 build step。

## 4. MoSCoW

- **Must**
  1. **前端錯誤分流**：`sb()`（行程）與購物端的 fetch 失敗時，區分兩種情況——
     **連不上**（DNS 解析失敗 / network error，`TypeError: Failed to fetch`）
     vs **連得到但被拒**（4xx/5xx）。前者顯示「資料庫可能被暫停」的專屬訊息。
  2. **專屬訊息要可執行**：訊息裡直接給該專案的 Supabase 後台網址與一句話操作
     （「按 Resume，資料不會遺失」），不是只說「連線失敗」。
  3. **兩個 Tab 都要做**：行程接 Chia 的專案、購物接 Stanley 的專案，
     兩邊各自指向**自己**那個專案的後台網址（給錯網址比不給更糟）。

- **Should**
  4. **keepalive 失敗時回傳非 200 且訊息更明確**（目前已回 500，但訊息可以更好），
     讓 Netlify 內建的「function 失敗通知」有東西可以通知。
  5. **在 `for-chia-access.md` 加一項**：請 Chia 到 Netlify 開啟 function 失敗的 email 通知。
     這是一次性設定，且只有她能做。

- **Could**
  6. **心跳可見化**：keepalive 成功時寫一筆時間戳，app 顯示「上次保活：N 天前」，
     N 過大就變黃字。**優點**是把「沒有訊號」變成看得見的訊號。
     **為什麼列 Could**：要新增一張表或一個欄位（碰 schema），
     而且暫停時連寫入都會失敗，價值不如 Must 的錯誤分流直接。

- **Won't（本 spec 不做）**
  - 不做自動 resume（Supabase 沒有這種 API，帳號層級的動作本來就該人來按）。
  - 不改 keepalive 的排程頻率（現行週一、四已有餘裕，理由見 `netlify.toml`）。
  - 不引入任何外部監控服務（UptimeRobot 之類）——多一個要維護的帳號。
  - 不做付費升級的決定，那是 §10 R3 的獨立議題。

## 5. Scope & Interfaces

- **涉及檔案**：`web/checklist.js`（`sb()` 的錯誤路徑、`showError`）、
  `web/buylist.js`（連線錯誤路徑、`setStatus`）、
  `web/netlify/functions/keepalive.js`（Should 4）、
  `for-chia-access.md`（Should 5）。
- **無 schema 變動、無 DDL、無新相依。**

### 5.1 現成可重用的東西（先讀這段）

| 已存在 | 在哪 | 本 spec 怎麼用 |
|---|---|---|
| `sb(path, opts)` | `checklist.js` | 錯誤分流加在它的 catch，一處改到全部呼叫端 |
| `showError(err)` | `checklist.js` | 已經會渲染 `.banner.error`，只要換訊息內容 |
| `setStatus` / `.status.err` | `buylist.js` | 購物端既有的錯誤顯示，沿用不要另發明 |
| `TARGETS` 陣列 | `keepalive.js` | 兩個專案的 URL 已經寫在這，後台網址可由 ref 推出 |

**專案後台網址的組法**：`https://supabase.com/dashboard/project/<ref>`，
`<ref>` 就是 Supabase URL 的子網域（`https://<ref>.supabase.co`）。
不要寫死兩串網址，從既有的 URL 推出來，這樣換專案時不會漏改。

### 5.2 怎麼分辨「被暫停」

專案暫停時 Supabase 會**移除 DNS 記錄**，所以瀏覽器端的表現是
`fetch` 直接 reject（`TypeError: Failed to fetch`），而不是回一個狀態碼。
2026-09-05 實測：`nslookup` 回 `Non-existent domain`，還原後才有 A 記錄。

⚠️ **但這個訊號不是唯一解釋**——使用者自己斷網、擋廣告的擴充套件、
公司防火牆擋掉 `*.supabase.co`，表現一模一樣。所以訊息措辭要用
**「可能」**，並同時給出「先確認你的網路」這個替代解釋，不要武斷。

## 6. Acceptance Criteria（初始全 failing）

- [ ] **AC-1**：把裝置切成飛航模式（或用 devtools 斷網）開行程 Tab →
      看到「資料庫可能被暫停」的專屬訊息，而不是通用錯誤。
- [ ] **AC-2**：同上，購物 Tab 也是，且訊息裡的後台網址指向**購物**那個專案（`kdmm...`），
      不是行程那個。
- [ ] **AC-3**：把 anon key 改成錯的（模擬 401）→ **不會**顯示「可能被暫停」，
      而是顯示原本的權限／設定錯誤訊息。（分流沒有把所有錯誤都吃掉）
- [ ] **AC-4**：訊息裡含可點擊的 Supabase 後台連結，且含「資料不會遺失」這個資訊。
- [ ] **AC-5**：訊息同時提到「也可能只是你的網路問題」，沒有武斷斷言。
- [ ] **AC-6**：手機寬度下訊息不溢出、連結點得到。
- [ ] **AC-7**：`node --check web/checklist.js && node --check web/buylist.js` exit 0。

## 7. Build Order（一次一件事）

1. **抽一個共用的錯誤判定**：判斷一個 fetch 失敗是不是「連不上」型。
   兩個檔案各自有自己的 IIFE，**不共用模組**——這裡刻意各寫一份小函式，
   不為了 DRY 硬抽第三個檔案（只有兩處、且是 5 行的判斷）。
2. **行程端**：接進 `sb()` 的 catch → `showError` → 驗 AC-1、AC-3、AC-7。
3. **購物端**：接進既有的連線錯誤路徑 → 驗 AC-2、AC-3。
4. **訊息措辭與樣式**：驗 AC-4、AC-5、AC-6。
5. **Should**：keepalive 訊息、`for-chia-access.md` 補一項。

## 8. End-to-End Verification

桌面 + 手機寬度各一次：devtools 切 offline → 兩個 Tab 分別開一次，
確認訊息正確、連結指向正確的專案、措辭沒有武斷。
再把 anon key 改錯一碼 → 確認顯示的是設定錯誤而不是「可能被暫停」。

## 9. Context Pulled
- `web/netlify/functions/keepalive.js`（現況與它自己承認的限制：「前端不會顯示任何東西」）
- `context.md` §6.3、§6.6（外部相依風險）
- `for-chia-access.md`（Netlify 只有 Chia 進得去，所以 log 這條路對 Stanley 是死路）
- 2026-09-05 的實測：暫停時 DNS 回 `Non-existent domain`，Resume 後恢復

## 10. Open Questions / Risks

- **R1（誤判）**：斷網、擴充套件、防火牆都會產生一樣的訊號。緩解方式是措辭用「可能」
  並列出替代解釋（AC-5）。**不要**為了訊息更斬釘截鐵而加偵測邏輯——
  那會變成猜測，而猜錯的成本是讓人跑去 Supabase 後台找一個不存在的問題。
- **R2（Netlify 通知只有 Chia 能設）**：Should 5 依賴她。Must 的部分刻意不依賴任何人，
  這樣即使她沒做，前端訊息仍然有效。
- **R3（要不要升 Pro）**：$25/月/organization，且兩人各一個 org = 兩份。
  真正的解法但屬獨立決策，撞到 ADR-012（不合併兩個 Supabase 專案），
  要動得先建 superseding ADR。本 spec 不處理。
- **R4（行程專案更容易中招）**：購物天天用不會閒置，行程是「規劃旅行才用」的季節性用途，
  2026-07、2026-08 已被暫停兩次。所以行程端的訊息比購物端更常被看到，優先做對。
