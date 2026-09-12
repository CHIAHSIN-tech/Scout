# REQUEST_CHECK — 以原始請求為準的收尾對照

規格：`specs/spec-scout-trip-page.md` ｜ 日期：2026-09-12

> 規格 EXECUTION RULES 第 7 條：**收尾報告以原始請求為準，不以本規格為準。**
> 三張清單，每行標明在哪裡驗的。**只寫分歧**；一致的地方一句話帶過。
>
> 一致的部分：OBJECTIVE 的兩件事（旅程頁模組、Cloudflare 遷移）都做了，
> 25 個 A-item 全 PASS，明細在 `ACCEPTANCE-trip-page.md`。下面只列有出入的。

---

## 一、要求且已交付（只列與規格字面不同、或值得特別確認的）

| 原始要求 | 交付狀況 | 在哪裡驗的 |
|---|---|---|
| 「查證過的事實與行程安排寫進 `trip.json`」 | ✅ 十個新工具，既有 8 個一字未改 | `test_tool_surface_frozen.py`（快照比對） |
| 「跑排程衝突檢查、把取捨丟回給人選」 | ✅ 五類衝突、每類附選項；**在真實資料上抓到一個參考產品沒察覺的衝突** | `test_schedule_check.py` 18 passed；`REVIEW.md` §五 |
| 「產出一個自含、可離線開、手機可讀的單檔 HTML」 | ✅ 自含與離線有斷言；**「手機可讀」只驗了溢位規則，沒驗可讀性** | `check-trip-page.mjs --offline/--mobile`；缺口見 K2 |
| 「依年月－國家－城市留檔」 | ✅ `trips/2026-09-kr-seoul/` | `check-trip-index.mjs` |
| 「經由 Scout 網站可瀏覽」 | ⚠️ **UI 做好了，但目前沒有東西可瀏覽**——`web/trips/` 不進版控（見第二張表 B1） | `check-trip-index-ui.mjs` 12 項 ok |
| 「四支既有 Function 功能等價、可回退」 | ✅ 等價（含錯誤訊息逐字）；拆除是最後一個獨立 commit | `check-cf-migration.mjs --worker / --history` |
| 「保活排程功能等價」 | ✅ cron 值逐字相同；`scheduled()` 打兩個 Supabase | `--worker`、`--live` |
| 「一個 commit 只做一件事、小步、先看 diff」 | ✅ 九個 commit，每個一件事 | `git log --oneline` |

---

## 二、要求但缺席（附原因）

| 原始要求 | 為什麼沒有 | 影響 |
|---|---|---|
| **B1. 「建置產物要不要放上網？**要。寫進 `web/trips/`，跟著 Scout 一起部署」（INTERVIEW Q3） | repo 是**公開的**（規格 Q2 的前提「不公開」經查證為誤）。Stanley 已決定 **repo 轉私有**（D13 選項 B），但**他沒有 admin 權限，要 Chia 執行** | **目前**行程表不會跟著部署。Chia 轉私有之後刪掉 `.gitignore` 那段就恢復規格原設計 |
| **B2. 「`trips/` 要不要進版控？**要」（INTERVIEW Q2） | 同上——決定要進，卡在 repo 還沒轉私有。**順序不能反**：公開時進版控，推上去就進 git 歷史拿不回來 | 旅程資料暫時只在執行者的機器上 |
| **B3. Cloudflare 帳號連上 repo、設 secret、停用 Netlify 站台** | 規格 BOUNDS 明列為外部相依，本次「只寫設定檔，不進任何供應商後台」 | 線上仍然是 Netlify。步驟寫在 `for-chia-cloudflare.md` |
| **B4. A16 的人工複核** | 需要 Stanley 本人在真手機上看過 | `REVIEW.md` 前 25 條已完成（比對參考產品），第 26–30 條留白 |
| **B5. 規格 A21 的 `curl -sf .../index.html`** | Workers static assets 預設把 `/index.html` 307 轉到 `/`，`curl -sf` 不跟隨轉址 | 改用會跟隨的 `fetch` 並額外斷言 `GET /` 回 200（更強）。理由 `DECISIONS-trip-page.md` D5 |
| **B6. 規格寫 `_redirects` 用 `200`** | 實測不行：Workers 的 200 是代理，代理目標必須是靜態資產，`/api/*` 是 Worker 程式碼 | 改用 308（保留方法與 body）。D3 |
| **B7. 排隊候補在地圖上定位** | 規格「延後」清單第四項 | 候補清單本身有，只是點不到地圖 |

### 請求裡有、卻沒有任何 A-item 回答的限制

規格 CHECKLIST 第 6 題自己承認了兩處，本次沒有改善，也修不了：

- **(a) 建置產物部署後是公開網址，只靠 6 碼隨機路徑，沒有憑證檢查。**
  沒有任何 A-item 斷言「錯誤憑證會被拒」——因為根本沒有憑證這個概念（ADR-013）。
  旅程頁的內容比購物清單敏感（訂位編號、旅館地址、班機時刻），這個取捨寫進了
  `DECISIONS-trip-page.md` D2 與 ADR-019，**不是默默採用**。
  附帶效果：B1 讓它暫時不成為實際風險，因為根本沒部署。
- **(b) `/api/share` 沿用「匿名可讀、欄位白名單」模型。**
  本次只換平台不改模型；白名單的斷言（14 條）在 `check-share.mjs` 裡，一條未改。

---

## 三、交付但沒人要求

| 交付物 | 為什麼做了 |
|---|---|
| `mcp-server/tests/fixtures/tool-surface-v1.json` | A2 要求「比對凍結快照」，規格沒說快照怎麼來。**在動工前產生**，之後任何人可以用 git 看它沒被改過 |
| `scripts/check-cf-migration.mjs` 的 `--worker` 模式 | A22 只要求「測試以假 fetch 斷言呼叫了兩個 URL」。順手把 Worker 的**路由與錯誤行為**也一起斷言（405／400／注入防護），因為那是「等價移植」的實質內容 |
| `check-trip-page.mjs` 的 A10 額外兩條 | 規格 A10 列了 (a)–(d)。另加「固定 `width` > 360px」——只擋 `min-width` 擋不住寫死寬度的溢位 |
| 地圖標籤避讓 | 首爾那趟 27 個地點，不避讓的話蠶室／汝矣島／光化門三處整團糊住，頁面不可用。不是新功能，是讓既有功能能看 |
| `web/checklist.css` 的 `.tp-*` 樣式 | A14 只要求列表存在。沒有樣式的話它是一串裸連結，與兩個 Tab 的視覺完全不搭（ADR-015 的 token 紀律） |
| `check-share.mjs` 改指向 Worker | 不改的話拆除 Netlify 之後 A1 會 FAIL。斷言一條未改（D10） |
| `trips/_preview/` 曾短暫存在 | 純粹是開發時看畫面用的，已刪除 |

---

## 四、一句話結論

**兩件事都做完了，25 個 A-item 全 PASS。**

唯一與原始請求不同的地方已經有決議了：**repo 轉私有、旅程資料進版控、
網站照樣公開部署、行程表另外用 Google SSO 擋**（D13 選項 B）。
**但它卡在一個 Stanley 做不到的動作**——改 repo 可見性需要 admin，
他在 `CHIAHSIN-tech/Scout` 只有 push。**要 Chia 按一下**
（`for-chia-cloudflare.md` 步驟 0.5），之後刪掉 `.gitignore` 兩段就回到規格原設計。

其餘差異都是「規格與現實不符、以實測為準」的小修正，理由逐條寫在
`DECISIONS-trip-page.md`。
