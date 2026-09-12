# DECISIONS — 旅程頁模組 ＋ Cloudflare 遷移

規格：[`specs/spec-scout-trip-page.md`](specs/spec-scout-trip-page.md)
分支：`feat/trip-page-and-cloudflare`
日期：2026-09-12

> 架構層級的決策在 `context.md` §4（ADR-018、ADR-019、ADR-010 補註）。
> **這份記的是執行過程中卡住、規格沒寫、或與規格不符而自己拍板的事**——
> 每一筆都寫「卡在什麼、假設了什麼、怎麼回頭改」。
>
> 檔名為什麼不叫 `DECISIONS.md`：那個檔裝的是上一個 TASK 的決策，
> 直接覆寫會弄丟前一份。repo 既有慣例就是分檔。

---

## D1. 一次訪談，沉默即預設

規格 EXECUTION RULES 第 1 條要求「問題只在開始問、一批問完、每題帶預設、沉默即預設」。

開工前用語音問了三題，**120 秒無回應**，依規格採預設值繼續：

| 問題 | 採用的預設 |
|---|---|
| repo 是公開的，旅程資料要不要進版控？ | 不進（見 D2） |
| Cloudflare 這次只寫設定檔、不進後台、不部署？ | 是 |
| 首爾那趟用參考檔重建，產一份核對清單？ | 是 |

之後執行過程中不再問，卡關一律寫進這份檔案。

---

## D2. 🔴 `trips/` 與 `web/trips/` 都不進版控（與規格 Q2／Q3 不符）

**卡在什麼：** 規格 INTERVIEW 的 Q2 寫「repo 僅 Stanley 與 Chia 使用、不公開，
`trip.json` 可安全進版控」，Q3 因此讓建置產物跟著網站一起部署。
**這個前提是錯的**——2026-09-11 與 09-12 兩次以未登入的 GitHub API 查證，`private=false`，
repo 是公開的。而 `trip.json` 的 schema 含 `booking_ref`、旅館地址、班機時刻，
規格自己在 CHECKLIST 第 6 題也寫「旅程頁的內容更敏感」。

**假設了什麼：** 風險不對稱。把敏感資料推上公開 repo **不可逆**（git 歷史留存；
2026-09-11 已有個人 email 誤入公開 repo 的前例），而「先不推、之後補推」隨時可做。
所以 `.gitignore` 擋住 `trips/`。

**為什麼 `web/trips/` 也要擋：** 那是同一份資料變成 HTML。只擋 `trips/` 而不擋產出，
等於從後門把它推上公開 repo。

**代價（誠實寫出來）：** **行程表目前不會跟著網站部署。**
規格 A15「部署路徑不可猜」的機制已經做好（6 碼亂碼、`secrets.token_hex`），
但沒有東西可部署。行程 Tab 的「歷次行程表」列表在線上會顯示空狀態。

**怎麼回頭改：**
- repo 轉私有 → 刪掉 `.gitignore` 裡那兩段，`git add trips/ web/trips/`，恢復規格原設計。
- 維持公開 → 另找部署位置（例如 Cloudflare 的私有 R2 bucket ＋ Access），
  那是新的一件事，不在本次範圍。

---

## D3. `web/_redirects` 用 308，不是規格寫的 200

**卡在什麼：** 規格 Phase A 實作要點明寫轉址規則是
`/.netlify/functions/*  /api/:splat  200`。本機 `wrangler dev` 實測**不成立**：
打 `/.netlify/functions/share?tag=x` 回 **404 空 body**。

**原因：** Workers static assets 的 `200` 是「代理」，而代理目標**必須是靜態資產**。
`/api/*` 是 Worker 程式碼，不是資產，代理不過去。
Cloudflare 官方文件也明說「`_redirects` 的規則不會套用在由 Worker 程式碼處理的請求上」。

**改成什麼：** `308`。實測通過（`308 → /api/share?tag=...`，跟隨後拿到 `{"items":[]}`）。
**為什麼是 308 不是 301/302：** 308 保留 HTTP 方法與 body。
`ai-parse` 與 `ai-suggest` 是 POST，用 301/302 會被瀏覽器降級成 GET，那兩支就壞了。

**怎麼回頭改：** 如果哪天 Cloudflare 讓 200 代理打得到 Worker，改回去即可，
`scripts/check-cf-migration.mjs` 的斷言同時接受 301 與 308（`30[18]`）。

---

## D4. `compatibility_date` 用 2026-07-15，不是今天

**卡在什麼：** 規格草案寫 `compatibility_date = "2026-09-12"`。本機 wrangler 4.110.0 拒絕啟動：
`This Worker requires compatibility date "2026-09-12", but the newest date supported by this
server binary is "2026-07-15"`。

**採用：** `2026-07-15`（本機 wrangler 支援的最新日期）。升 wrangler 之後可以往後推。

---

## D5. A21 的 `curl /index.html` 要跟隨轉址

**卡在什麼：** 規格 A21 寫 `curl -sf http://localhost:8788/index.html | grep -q '<title>Scout</title>'`。
實測 `/index.html` 回 **307**，轉到 `/`——那是 Workers static assets 的預設行為
（`html_handling = "auto-trailing-slash"`，會把 `index.html` 從網址上拿掉）。
`curl -sf` 不跟隨轉址，所以那條命令會失敗。

**沒有兩全的設定：** 改成 `html_handling = "none"` 可以讓 `/index.html` 直接回 200，
但 `/` 就會 404——那更糟，`/` 才是大家實際打的網址。

**採用：** 驗收改成跟隨轉址（`scripts/check-cf-migration.mjs --live` 用 `fetch`，預設就跟隨），
並且**額外斷言 `GET /` 回 200**。這比原本的命令更強：它證明了轉址鏈最後落在真的首頁上。
A21 的本意（「靜態資產優先於 Worker」）完全成立——兩個路徑都由資產層處理，
沒有進到 Worker（Worker 對未知路徑會回 JSON 404）。

---

## ~~D6. A21／A22 的實跑用 port 8790，不是 8788~~ ✅ 2026-09-13 已消失

**卡在什麼：** 第一次啟動 `wrangler dev` 因 D4 的 compatibility_date 失敗，
但 workerd 行程仍佔著 8788 並且不回應。本環境**不允許結束行程**（權限被擋），
所以 8788 在本次 session 內拿不回來。

**採用：** 改用 8790 跑同一組斷言。`check-cf-migration.mjs --live=<port>` 接受任何 port。
斷言內容與規格一字不差，只有 port 不同。

**怎麼回頭改：** 新開一個 shell（或重開機）之後 8788 就會釋放。

**2026-09-13：換 session 之後埠已釋放，複驗用的就是規格原本的 8788，六項全過。
這條偏離不再存在。**

---

## D7. N5 不外派 subagent

**卡在什麼：** 規格 GRAPH 把 N5（驗證）列為獨立節點並要求「對抗性」；
而 `~/dev-habits/rules/model-routing.md` 明寫「驗證不要派 subagent」。

**採用：** 驗證不外派，但**嚴格照 A-item 的命令跑並貼原始輸出**（見 `ACCEPTANCE-trip-page.md`），
不用印象判斷。對抗性的部分靠三件事補：
(a) 每個驗收腳本都是**獨立於實作的黑箱**——只看產出的 HTML／JSON／git 歷史，不 import 渲染器內部；
(b) 每條斷言都印出實際值，不是只印 ok；
(c) 失敗的項目照實記在 `KNOWN_ISSUES-trip-page.md`，不改斷言遷就實作。

---

## D8. 排隊候補的地圖定位互動不做

規格的「延後」清單第四項就是這個（「排隊候補『點卡片跳到地圖位置』——
scope-cut 順位第二，先確保候補清單本身存在」）。**候補清單本身做了**，
地圖上的編號標記與點選定位沒做。參考產品那段 JS 在 `trips/_reference/body2.part` 裡，
要補的時候直接移植。

---

## D9. 「在旅館步行範圍」的判準改用車站，不用 `location.walk_min`

**卡在什麼：** `check_schedule` 的第 4 類衝突要判斷「最後一站在不在旅館步行範圍」。
第一版拿 `place.location.walk_min` 當門檻，測試立刻打臉——那個欄位講的是
**「從車站走到店」**，跟**「從店走回旅館」**是兩回事。用它會把「離旅館很遠但出站就到」
的店判成「走得回去」。

**採用：** 判準是**最後一站與旅館同一個車站**（或那一站就是旅館）。
schema 沒有「到旅館的步行分鐘數」這個欄位，而**憑既有欄位猜一個距離比不判斷更危險**。

**怎麼回頭改：** 如果需要更細，就在 `places[].location` 加一個明確的
`hotel_walk_min`，由查證的人填——那是新增欄位，要改 `travel/schema.py`。

---

## D10. `check-share.mjs` 改指向 Worker

**卡在什麼：** 拆掉 `web/netlify/` 之後，`scripts/check-share.mjs` 會找不到
`share.js` 而失敗——那會違反 A1（既有腳本不得比基線差）。

**採用：** 把它改成呼叫 `worker/index.js` 的 `/api/share`，斷言內容一字未改
（欄位白名單、只回未購、tag 跳脫、405／400）。這動到了規格寫入邊界表裡沒列的檔案，
但 A1 是「絕不砍」的項目，優先於寫入邊界的整潔。

---

## D11. 首爾那趟的資料只重建到「參考產品明文寫出來的程度」

**卡在什麼：** 參考產品的 `days.py` 只寫了行程項目與交通段，沒有逐一查證
明洞商圈、石村湖、景福宮這類地點的營業時間。

**採用：** 那些地點的 `hours.sources` 一律**留空陣列**，不是去網路上補查。
理由是 server instructions 第 3 條「查不到就說查不到」——
那次 session 的確沒查，寫成「查過」會是假的。
建置時它們自動變成 17 筆待確認，其中 4 筆（開放街區與公園）是噪音，
已記在 `REVIEW.md` 第 25 條當作下一趟的改進項目。


---

## D12. A24 的「拆除必須是最後一個 commit」改成驗本意

**卡在什麼：** A24 的原文檢查是「`git log` 顯示刪除發生在最後一個 commit」。
照字面實作之後發現：**遷移之後只要再 commit 任何東西，這條就永遠是紅的**——
包括「看畫面之後修 UI」這種正常到不行的後續工作。那不是驗收條件，那是地雷。

**採用：** 改驗三件真正代表本意（「Cloudflare 驗證通過前不得刪除」）的事：
1. **拆除的那個 commit 裡，`ACCEPTANCE-trip-page.md` 已經存在** → 驗證先於拆除。
   這條比原文更直接：它證明的是「驗完才拆」，而不是「拆完沒再做事」。
2. 拆除之後沒有任何 commit 再動過 `netlify.toml` / `web/netlify/`。
3. 現在的工作區裡確實沒有 Netlify 設定。
加上原本就有的「從加入到拆除之間每個 commit 它都還在」。

**怎麼回頭改：** 想要原本的字面語意，把 `head === sha` 那行加回去即可。

---

## D13. 🔵 行程表走 Google SSO ＋ **repo 轉私有**（選項 B）——卡在 Chia

**變更來源（兩次，同一天）：**
1. 2026-09-12 Stanley 在 review 介面時先說「那我們公開，但是藏在 Google 登入後面好了，做 SSO」。
2. 我指出 SSO 保護不到公開的 GitHub repo，給了 A／B 兩條路。Stanley 回：
   **「那就部署公開，repo 不要公開，這樣 OK 的，做 B」。**

所以最終決定是 **B**：**網站公開部署、行程表以 SSO 擋、repo 轉私有、`trips/` 進版控。**
這**取代** D2 的暫定狀態，也取代本條稍早採用的 A。

**查證過的前提（2026-09-12，Cloudflare 官方文件）：**
Access 可以掛在 **`workers.dev` 的主機名 ＋ 單一路徑**（`/trips/*`）上，
**不需要自訂網域**，所以 NON-GOALS 的「不改網域、不動 DNS」仍然成立。

### 🚧 為什麼還沒做：Stanley 沒有權限

```
$ gh api repos/CHIAHSIN-tech/Scout --jq '{private, permissions}'
{"private": false,
 "permissions": {"admin": false, "maintain": false, "pull": true, "push": true, "triage": true}}
```

repo 在 **Chia 名下**（ADR-014 把所有權轉給她）。改可見性需要 **admin**，
Stanley 只有 push。**只有 Chia 能把它轉成私有。**

**因此本次執行到此為止，`trips/` 與 `web/trips/` 仍然擋在版控外。**
這不是選了 A，是 B 的前置還沒完成——**順序不能反**：
repo 還公開的時候把 `trip.json` 進版控，一旦被推上去就進了 git 歷史，拿不回來
（2026-09-11 已有個人 email 誤入公開 repo 的前例）。

### Chia 做完之後，翻過去只有兩步

```bash
# 1. 確認真的私有了（回 true 才能往下）
gh api repos/CHIAHSIN-tech/Scout --jq .private

# 2. 刪掉 .gitignore 最後那兩段（trips/ 與 web/trips/），然後
git add .gitignore trips/ web/trips/
git commit -m "feat(travel): repo 轉私有後，旅程資料與行程表進版控（ADR-019 / D13 選項 B）"
```

翻過去之後：
- 行程表**可以走 Chia 的 GitHub 自動部署**，不必有人手動 `wrangler deploy`。
- 多機同步正常（換電腦 `git pull` 就有旅程資料）。
- `KNOWN_ISSUES-trip-page.md` 的 K1 就解掉了。

### 轉私有的連帶影響（要先讓 Chia 知道）

- **她的 Netlify 與之後的 Cloudflare Workers Builds 都要能存取私有 repo。**
  GitHub App 通常已經有權限，但若部署開始出現 "repository not found"，
  就是要回 GitHub 的 Applications 設定把該 repo 重新授權。
- repo 一私有，**沒有被加為協作者的人就完全看不到**——目前只有她和 Stanley，不受影響。

**怎麼回頭改：** 要退回 A（repo 維持公開、行程表手動 deploy），
就是不要動 `.gitignore`，並在 `for-chia-cloudflare.md` 拿掉步驟 0.5。
Access 的設定兩種都要，不用改。
