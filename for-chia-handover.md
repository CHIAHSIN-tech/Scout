# 給 Chia：三件只有你做得到的事

> 寫於 2026-09-12。取代 `for-chia-cloudflare.md` 裡原本要你做的那六個步驟——
> **那些現在由 Stanley 自己做。** 這份只剩三件事，因為它們都需要你的帳號權限，
> 沒有別的辦法。

---

## 先講為什麼改

2026-08-01 我們把 Scout repo 轉到你名下（ADR-014），理由只有一個：
**你的 Netlify 接著你的 GitHub**，轉過去你就不用裝任何東西，部署全部自己來。

現在託管要搬到 Cloudflare（ADR-018），那個理由就沒了——Cloudflare 專案還沒建，
開在誰名下都行。

而實際的分工一直是另一個樣子：**你出 spec，Stanley 用 Claude Code 執行**
（`specs/README.md` 第一句就是這個）。權限散在你這邊的結果是，
每次要動基礎設施都得等你。光是 2026-09-12 這一天就卡了兩次。

所以 Stanley 決定**把基礎設施的擁有權收回去**（ADR-020）。
**這會讓你失去部署自主權**——那正是當初 ADR-014 想給你的東西。
我們不打算假裝這不是一件事，所以直接寫在這裡：
你之後不會再被基礎設施的事情卡住，但也不再需要（或能夠）自己部署。
**你保留 repo 的寫入權限**，spec 照樣直接推。

如果你對這個安排有意見，跟 Stanley 說，**不要默默照做**。

---

> **2026-09-13 更新：Cloudflare 那邊 Stanley 已經部署好了**，
> 網址是 **https://scout.nailbook.workers.dev**。下面三件事仍然只有你做得到。

## 三件事

### 1. 把 Scout repo 轉回 Stanley

GitHub 的轉移**只有擁有者能發起**，所以這件事只有你做得到。

1. GitHub → `CHIAHSIN-tech/Scout` → **Settings** → 最下面 **Danger Zone**
   → **Transfer ownership**。
2. 新擁有者填 **`witsper-stanley`**。
   （那是 Stanley 的**個人**帳號。名字和 email 看起來像公司，但不是。）
3. 照它的指示打 repo 名稱確認。

**怎麼知道成功了：** Stanley 那邊會收到一封接受轉移的信；他接受之後，
repo 網址變成 `github.com/witsper-stanley/Scout`。GitHub 會自動轉址，
你本機的 `git push` 不會壞。

> 轉移之後 Stanley 會把你加回**協作者**，你照樣 push spec。
> 如果隔天發現推不上去，跟他說一聲，那是他忘了加。

### 2. 停用 Netlify 站台（**要等，不是現在**）

**先不要做。** 要等 Cloudflare 那邊實際跑起來、而且跨過一次排程日
（週一或週四）之後再動手。Stanley 會跟你說什麼時候。

到時候：

1. Netlify 後台 → Scout 站台 → **Site settings → Danger zone** → **Stop builds**
   （先停建置，**不要直接刪站**）。
2. 再觀察幾天，確定沒有人在用舊網址，才 **Delete site**。

> repo 裡的 `netlify.toml` 和 `web/netlify/` 已經刪掉了，
> 但**後台的站台只有你能關**——程式碼刪掉不會讓它自己消失。

### 3. 把行程的 Supabase 專案轉給 Stanley

`uarkccyqcqvgxukjcrey`（行程資料：`trips` / `itinerary_items` / …）在你名下。
Stanley 一直沒有那個專案的後台權限，**連加一個欄位都做不到**——
2026-07 另外開購物專案就是為了繞過這件事（ADR-009）。

⚠️ **要用「轉移」，不要「開新專案再搬資料」。**
轉移之後 project ref 還是 `uarkccyqcqvgxukjcrey`，**程式一行都不用改**；
重建的話網址和 key 全變，前端、保活排程、本機設定都要跟著改，
而且搬資料期間你們兩個都不能用。

1. Supabase 後台 → 選 `uarkccyqcqvgxukjcrey` 專案 → **Settings** → **General**
   → **Transfer project**。
2. 目標選 Stanley 的 organization。

**如果按不下去，很可能是這兩件事之一，跟 Stanley 說就好：**
- 他的免費方案 organization 已經有一個購物專案，可能撞到「一個 org 幾個 active project」的上限。
- Transfer 通常要求發起的人在**來源和目標兩邊都有權限**，
  所以可能要先把你加進他的 org（或他加進你的），做完再移除。

**怎麼知道成功了：** 專案出現在他的 organization 底下，
而且 Scout 網頁的行程 Tab 照樣讀得到資料（ref 沒變，本來就該照常）。

---

## 做完之後你還有什麼

- **repo 的寫入權限**：spec 照樣直接 push 到 `specs/`，流程完全不變。
- **兩個 Supabase 專案的存取**：資料你照樣看得到、改得到，只是後台管理權在 Stanley。
- **出題權**：這本來就是重點。`specs/README.md` 的流程一個字都沒改。

## 你不用再管的

- Cloudflare 的建置、部署、Google 登入設定 —— Stanley 自己來
  （`runbook-cloudflare.md`）。
- GitHub 的可見性、分支保護、App 授權。
- 排程、金鑰、Worker。

---

## 附帶一提：repo 會變成私有

Stanley 會在接手之後把 repo 轉成私有——行程表的資料含訂位編號、旅館地址、班機時刻。
**你是協作者，私有之後照樣看得到、推得上去**，對你沒有影響。
（如果你希望在轉移之前就先私有，你現在就可以自己改，那樣更早安全，
但不是必要——Stanley 接手後第一件事就是這個。）
