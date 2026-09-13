# Runbook：Stanley 自己把 Scout 搬上 Cloudflare

> 寫於 2026-09-12（ADR-018 遷移 ＋ ADR-020 權限收回）。
> 這份取代 `for-chia-cloudflare.md` 裡原本要 Chia 做的六個步驟——**現在你自己做。**
> Chia 那邊只剩三件事，在 `for-chia-handover.md`。
>
> **每一步都寫了「怎麼知道成功了」。** 這個專案有「手動部署造成線上跑舊版」的前科，
> 所以每一步都要驗，不要憑感覺往下走。

---

## 進度（2026-09-13 更新）

| 步驟 | 狀態 |
|---|---|
| 1. 本機驗證 | ✅ 六項全過（port 8788） |
| 2. 部署 | ✅ **https://scout.nailbook.workers.dev** |
| 3. 確認線上是新版 | ✅ 兩個 Tab 都讀得到資料、舊網址轉址通、`/api/*` 正常 |
| 4. 排程 | ✅ deploy 輸出含 `schedule: 17 3 * * 1,4` |
| **5. Google 登入（Access）** | ⬜ **只剩這個要你做**，見下面 |
| 6. AI 金鑰 | ⬜ 可跳過 |
| 7. 重發分享連結 | ⬜ 等你決定什麼時候切 |
| 8. 叫 Chia 關 Netlify | ⬜ 要先跨過一次排程日 |

> **⚠️ 第一次部署刻意排除了行程表。** `web/.assetsignore` 裡有一行 `trips/`。
> 理由：deploy 會上傳整個 `web/`，而 Access 必須綁主機名、**要先有網站才設得起來**。
> 不排除的話，行程表會在登入保護生效前先公開一段時間。
> **你設完步驟 5 之後**：刪掉 `web/.assetsignore` 的 `trips/` 那一行，再 `npx wrangler deploy` 一次。

---

## 開始前

- [ ] 用**個人** Cloudflare 帳號登入。不要用公司帳號（`context.md` §6.6 的紀律）。
- [ ] 本機 `wrangler --version` 有東西（目前 4.110.0）。
- [ ] `git pull` 到最新，根目錄看得到 `wrangler.toml` 與 `worker/`。

**不需要先等 Chia。** 下面每一步你現在就能做——repo 轉移與 Supabase 轉移是平行的另一條線。

---

## 1. 先在本機驗一次（2 分鐘，別跳）

```bash
npx wrangler dev --port 8788 --test-scheduled
```

另開一個終端機：

```bash
node scripts/check-cf-migration.mjs --live
```

**成功長這樣**：6 項全 ok（首頁、`/`、`/api/share`、`/api/ai-parse` 回 405、
舊網址轉址、排程觸發）。

> 8788 被佔住的話用 `--port 8790` 起，驗收跟著用 `--live=8790`。

## 2. 部署

```bash
npx wrangler deploy
```

第一次會叫你在瀏覽器授權，跟著走就好。

**怎麼知道成功了：** 最後印出網址。實際是 **https://scout.nailbook.workers.dev**。

## 3. 確認線上是新版 ⚠️ 這步不能跳

```bash
curl -s https://scout.nailbook.workers.dev/ | grep -c 'panel-trip'
curl -s 'https://scout.nailbook.workers.dev/api/share?tag=__nonexistent__'
```

- 第一條要回 `1`。
- 第二條要回 `{"tag":"__nonexistent__","count":0,"items":[]}`。

然後用瀏覽器打開，**兩個 Tab 都點一次**，購物清單與行程都讀得到資料。

## 4. 確認排程掛上去了

Cloudflare 後台 → 你的 Worker → **Settings** → **Trigger Events**，
要看得到 **Cron Trigger `17 3 * * 1,4`**（台灣時間週一、四 11:17）。

沒有的話是 `wrangler.toml` 的 `[triggers]` 沒被吃到。

> 排程失敗不會通知任何人，它只寫進 Worker log。既有問題
> （`specs/spec-keepalive-visibility.md`），這次沒解。

## 5. Google 登入擋住行程表（Cloudflare Access）

**只擋 `/trips/*`。** 整個網域都擋的話，家人的購物分享連結會一起死。

1. **Zero Trust** → **Access** → **Applications** → **Add an application** → **Self-hosted**
2. Application domain：`scout.nailbook.workers.dev`，Path：`trips/*`
3. **Add a policy** → Allow → Include **Emails** → 你和 Chia 的 Google 帳號
4. Login methods 留 Google（One-time PIN 可以一起留當備援）

**怎麼知道成功了**（開無痕視窗）：

- 打 `.../trips/` → 被導到 Google 登入 ✅
- 打 `.../share.html?list=<某個情境標籤>` → **不用登入就看得到** ✅

兩條都成立才算對。免費方案含 50 人，不需要自訂網域。

## 6. AI 金鑰（**可以跳過**）

網頁上的兩個 AI 按鈕依 ADR-017 預設隱藏，AI 走 Claude ＋ MCP。
**不設這個金鑰，日常功能完全不受影響。**

之後要開網頁 AI 再做：

```bash
npx wrangler secret put GEMINI_API_KEY
```

**金鑰絕對不要寫進 `wrangler.toml`。**

## 7. 重發家人的分享連結

網址從 `shoppingtool.netlify.app` 變成 `scout.nailbook.workers.dev`，舊連結會死。

產生方式：購物 Tab 選一個「情境」→ 按分享，連結自動複製
（格式是 `/share.html?list=<情境標籤>`）。

## 8. 跨過一次排程日之後，才叫 Chia 關 Netlify

**至少並存幾天**，跨過一個週一或週四，確認保活排程真的有跑。
然後跟 Chia 說可以執行 `for-chia-handover.md` 的第 2 件事。

---

## repo 轉移完成之後（另一條線）

Chia 發起轉移、你接受之後：

```bash
# 1. 更新 remote（GitHub 會自動轉址，但寫明確比較好）
git remote set-url origin https://github.com/witsper-stanley/Scout.git

# 2. 轉成私有（現在你有 admin 了）
gh repo edit witsper-stanley/Scout --visibility private

# 3. 確認
gh api repos/witsper-stanley/Scout --jq '{private, permissions}'
```

`private: true` 且 `admin: true` 之後，**旅程資料才能進版控**：

```bash
# 刪掉 .gitignore 最後那一段（trips/ 與 web/trips/），然後
git add .gitignore trips/ web/trips/
git commit -m "feat(travel): repo 轉私有後，旅程資料與行程表進版控（ADR-019 / D13 選項 B）"
```

- [ ] 把 Chia 加回**協作者**（她要繼續推 spec）
- [ ] 重跑一次 `node scripts/check-trip-index.mjs --all` 確認索引與磁碟一致

## Supabase 轉移完成之後

project ref 不變（`uarkccyqcqvgxukjcrey`），**程式一行都不用改**。但還是驗一次：

```bash
node scripts/check-cf-migration.mjs --worker   # keepalive 仍打得到兩個專案
```

然後開一次 Scout 網頁的行程 Tab，確認讀得到資料。

---

## 出事了怎麼退回去

在 Chia 執行第 2 件事（停用 Netlify）之前，**Netlify 站台一直都還在跑**：

1. 停用 Cloudflare 的 Worker。
2. 繼續用 `shoppingtool.netlify.app`。

repo 裡的 `netlify.toml` 與 `web/netlify/` 已經刪了，但那只是設定檔——
`git revert` 掉「chore: 移除 Netlify 設定」那個 commit 就回來了。
