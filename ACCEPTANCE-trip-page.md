# ACCEPTANCE — 旅程頁模組 ＋ Cloudflare 遷移

規格：[`specs/spec-scout-trip-page.md`](specs/spec-scout-trip-page.md)
分支：`feat/trip-page-and-cloudflare`
驗收日期：2026-09-12

---

## A1–A25 驗收表

**結果：25 項全部 PASS。**

| # | 項目 | 結果 | 在哪裡驗的 |
|---|---|---|---|
| A1 | 既有測試與檢查腳本不低於基線 | ✅ PASS | 五支腳本全 exit 0；pytest **139 passed**（基線 79，新增 60，失敗 0） |
| A2 | 既有 8 個 MCP 工具簽章一字未改 | ✅ PASS | `tests/test_tool_surface_frozen.py`（比對動工前產生的快照） |
| A3 | HTTP 動詞只有 GET / POST / PATCH | ✅ PASS | `grep -cE '"(DELETE\|PUT)"' rest.py` = **0**；`test_rest_verbs.py` 8 passed |
| A4 | 依日期與國家留檔 | ✅ PASS | `trips/2026-09-kr-seoul/trip.json` 存在，validate exit 0；重複建立回傳既有路徑不覆寫 |
| A5 | 寫入路徑無法逃出 `trips/` | ✅ PASS | `test_travel_paths.py` **23 passed**（四類逃逸全覆蓋） |
| A6 | 索引可用且與磁碟一致 | ✅ PASS | `check-trip-index.mjs` |
| A7 | 改一處，多處一起改 ＋ 建置決定性 | ✅ PASS | `check-trip-page.mjs --consistency`（五個區塊全變；建兩次位元相同） |
| A8 | 頁面不含 `trip.json` 以外的店家 | ✅ PASS | `test_no_invented_content.py` 5 passed |
| A9 | 自含單檔，斷網可開 | ✅ PASS | `check-trip-page.mjs --offline`（11 條禁則 ＋ 外部網址只在 `<a href>`） |
| A10 | 375px 寬不橫向溢位 | ✅ PASS | `check-trip-page.mjs --mobile`（a–d 四組靜態規則） |
| A11 | 排程檢查器只報不改 | ✅ PASS | `test_schedule_check.py` **18 passed**（五類各有案例 ＋ sha256 不變） |
| A12 | 未查證的事實不會變成頁面上的數字 | ✅ PASS | `test_unverified.py` |
| A13 | 來源衝突不被消滅 | ✅ PASS | `test_unverified.py`（含「對調順序兩個值都還在」） |
| A14 | 行程 Tab 能列出並開啟歷次行程表 | ✅ PASS | `check-trip-index-ui.mjs` 12 項 |
| A15 | 部署路徑不可猜 | ✅ PASS | `check-trip-index.mjs --unguessable` |
| A16 | 第一趟真實資料逐條看過（交付物，非 gate） | ✅ 交付 | `trips/2026-09-kr-seoul/REVIEW.md`，**30 條**，含 sha256 |
| A17 | schema 扛得住真實資料 | ✅ PASS | 39 家無損轉入；`chef_bio` / `chef_sources` / `alert` / `area` 都還在 |
| A20 | 四支 Function 等價移植、無 Netlify 殘留 | ✅ PASS | `check-cf-migration.mjs`（31 項）＋ `--worker`（14 項） |
| A21 | 本機實跑，靜態與 API 都通 | ✅ PASS | `--live`（wrangler dev 實跑，6 項）。命令有一處調整，見下方說明 |
| A22 | 保活排程等價 | ✅ PASS | cron 值逐字相同；`__scheduled` 回 200；假 fetch 斷言打了兩個 Supabase URL |
| A23 | `ai-suggest-core.js` 仍然只有一份實作 | ✅ PASS | `check-ai-suggest.mjs` 仍 exit 0；Worker 以 `import` 取 `globalThis.ScoutAiSuggest` |
| A24 | 可回退：驗證通過前不刪 Netlify 設定 | ✅ PASS | `--history`；拆除是**最後一個 commit**，訊息含 `chore: 移除 Netlify 設定` |
| A25 | 金鑰沒有進版控 | ✅ PASS | `git grep` 無命中；`wrangler.toml` 無金鑰值 |

### 與規格命令不同的三處（理由在 `DECISIONS-trip-page.md`）

1. **A21 的 `curl /index.html` 要跟隨轉址**（D5）。Workers static assets 預設會把
   `/index.html` 307 轉到 `/`，`curl -sf` 不跟隨所以會失敗。驗收改用會跟隨的 `fetch`，
   並**額外斷言 `GET /` 回 200**——這比原命令更強。
2. **A21／A22 實跑用 port 8790／8791，不是 8788**（D6）。第一次啟動失敗留下的 workerd
   行程佔著 8788 且不回應，本環境不允許結束行程。斷言內容一字不差。
3. **`web/_redirects` 用 308 不是 200**（D3）。實測 200（代理）打不到 Worker。

---

## 基線（2026-09-12 執行前取得）

```
$ for s in check-style check-exports check-pwa check-share check-ai-suggest; do node scripts/$s.mjs; echo "$s=$?"; done
check-style=0
check-exports=0
check-pwa=0
check-share=0
check-ai-suggest=0

$ cd mcp-server && uv run pytest
79 passed
```

**A1 的「不低於基線」＝ 五支腳本維持 exit 0、pytest 通過數 ≥ 79、失敗數 = 0。**

---

## 原始命令輸出

### A1–A3：不回歸

```
### A1 既有腳本
check-style=0
check-exports=0
check-pwa=0
check-share=0
check-ai-suggest=0

### A1 pytest
139 passed in 1.68s

### A2 tool surface
3 passed in 0.79s

### A3 HTTP 動詞
grep -cE "(DELETE|PUT)" rest.py = 0
8 passed in 0.02s
```

> `check-share.mjs` 在拆除 Netlify 設定的那個 commit 一起改成呼叫 Worker 的 `/api/share`，
> **14 條斷言一條都沒改**，只換了被測的外殼（D10）。

### Phase B：旅程頁模組

```
### A4 建檔與驗證
{'slug': '2026-09-kr-seoul', ..., 'created': False, 'note': '這趟已經存在，沒有覆寫。要改內容請用 upsert_* 工具。'}
test -f trips/2026-09-kr-seoul/trip.json => 0
..\trips\2026-09-kr-seoul\trip.json 通過驗證
exit=0

### A5 路徑逃逸
23 passed in 0.13s

### A6 / A15 索引
  ok   A6  依 start_date 新到舊排序（實際 2026-09-21）
  ok   A15  web/trips/2026-09-kr-seoul-cf758e 以 6 碼以上的十六進位亂碼結尾
  ok   A15  亂碼來自 secrets.token_hex（不是可預測的雜湊或流水號）
全部通過（13 項斷言）

### A7 / A9 / A10 頁面
  ok   A7  同樣輸入建兩次位元相同（… bytes）
  ok   A7  時間軸 跟著變了
  ok   A7  當日標題摘要 跟著變了
  ok   A7  快捷nav 跟著變了
  ok   A7  地圖文字轉乘表 跟著變了
  ok   A7  正餐一覽表 跟著變了
  ok   A9  外部網址只出現在 <a href>（其餘殘留：無）
  ok   A10c  沒有 min-width > 360px 的非容器規則（違規：無）
  ok   A10d  沒有用 body{overflow-x:hidden} 把溢位藏起來
全部通過（29 項斷言）

### A8 不生成內容
5 passed in 0.02s

### A11 排程檢查器
18 passed in 0.02s

### A12 / A13 未查證與來源衝突
11 passed in 0.02s

### A14 行程 Tab 列表
全部通過（12 項斷言）

### A16 首跑複核
REVIEW.md 存在，核對條目數 = 30

### A17 rest.json 39 家無損轉入
轉出 39 筆 → /tmp/places.json
import exit=0
validate exit=0
len(places)==39 OK
chef_bio 全在 extra: True
chef_sources 全在 extra: True
area 全在: True
alert 保留（4 筆是物件）: 4
```

### Phase A：Cloudflare 遷移

```
### A20 / A22static / A23 / A25 靜態
全部通過（31 項斷言）

### A20 / A22 Worker 實跑（假 fetch）
  ok   A22  scheduled() 打了 2 次（實際 2）
  ok   A22  打到行程專案（Chia 的 Supabase）
  ok   A22  打到購物專案（Stanley 的 Supabase）
  ok   A22  兩次都是最輕量查詢 select=id&limit=1
  ok   A20  GET /api/ai-parse → 405「只接受 POST」
  ok   A20  tag 有跳脫，呼叫端插不進額外的 filter（唯讀出口的核心保證）
  ok   A23  import worker 之後 globalThis.ScoutAiSuggest.buildPrompt 可用
全部通過（14 項斷言）

### A21 / A22 wrangler dev 實跑
  ok   A21  GET /index.html 拿到 Scout 首頁（status=200）
  ok   A21  GET / → 200（實際 200）
  ok   A21  GET /api/share 回傳含 items（status=200）
  ok   A21  GET /api/ai-parse → 405（實際 405）
  ok   A20b  舊網址 /.netlify/functions/share 仍然通（status=200）
  ok   A22  __scheduled 觸發回 2xx（實際 200）
全部通過（6 項斷言）

### A24 可回退（拆除前）
  ok   A24  netlify.toml / web/netlify/ 在 git 歷史中存在過
  ok   A24  Netlify 設定仍在（還沒走到拆除那一步）——此時可回退的條件自動成立
全部通過（2 項斷言）
```

> **A24 拆除後的輸出**寫在拆除 commit 的訊息裡——那個 commit 必須是最後一個，
> 所以它的驗證結果沒辦法再放進本檔。要重驗直接跑
> `node scripts/check-cf-migration.mjs --history`。

---

## 排程檢查器在真實資料上的第一個發現

`check_schedule` 對重建後的首爾行程回報 **1 個衝突**：

> 「晚餐：Mamalee Dining」要留 90 分，但到下一站「汝矣島漢江公園夜景散步」只剩 80 分
> （間隔 90 分，扣掉交通 10 分）。

**這是真的，而且參考產品那次沒有察覺。** 它自己寫 Mamalee「最後點餐 20:30」，
下一站也排 20:30 出發——兩邊剛好卡死。

---

## 沒有被任何 A-item 驗到的事（誠實清單）

1. **線上是不是真的新版。** 所有 A-item 都在本機驗，`wrangler dev` 過不代表線上通。
   這正是把部署列為外部相依、並要求 A24 可回退的原因。
   `for-chia-cloudflare.md` 的步驟 2 就是「切換後第一件事是打開線上站台確認版本」。
2. **頁面在真手機上好不好讀。** A10 只驗溢位規則，不驗可讀性。
   `REVIEW.md` 第 26–30 條留白等 Stanley 填。
3. **`check_schedule` 報得準不準。** A11 只驗它抓得到我們寫進測試的五類衝突，
   不驗「真實行程裡的衝突都抓得到」。要靠 A16 的 `WRONG:` 累積成第二趟的測試案例。
