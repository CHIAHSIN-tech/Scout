# ACCEPTANCE — 旅程頁模組 ＋ Cloudflare 遷移

規格：[`specs/spec-scout-trip-page.md`](specs/spec-scout-trip-page.md)
分支：`feat/trip-page-and-cloudflare`

> **狀態：尚未開工。** 本檔目前只記錄「執行前」的基線與勘查結果，
> 供正式執行的 session 接手。A1–A25 一項都還沒跑。
>
> **檔名為什麼不叫 `ACCEPTANCE.md`**：那個檔裝的是上一個 TASK（雙 Tab 視覺統一）的驗收，
> 直接覆寫會弄丟前一份成果。repo 既有慣例就是分檔——`ACCEPTANCE-mcp-server.md`、
> `ACCEPTANCE-ai-suggest.md`。`DECISIONS` 與 `KNOWN_ISSUES` 比照辦理。

## 基線（2026-09-12 取得，規格 A1 要求）

規格原文說「既有腳本目前的 exit code 未逐一驗證過」。已逐一驗過：

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

**所以 A1 的「不低於基線」＝五支腳本必須維持 exit 0、pytest 必須維持 79 passed、0 failed。**
（`uv run pytest` 這次沒撞到憑證問題，可照規格原文使用；若日後出現
`invalid peer certificate`，見 `mcp-server/README.md` 的疑難排解。）

## 執行前勘查（規格前置事實逐項對照）

| 查核項 | 結果 |
|---|---|
| `trips/_reference/` 七份參考檔 | ✅ 全在：`README.md`、`head3.part`、`body2.part`、`build2.py`、`days.py`、`rest.json`、`seoul-chuseok.html`、`legacy/`、全紀錄 |
| `rest.json` 筆數 | **39**（符合 A17 的斷言）。欄位：`seed_no, id, name, name_ko, chef_name, chef_nickname, chef_season, chef_result, chef_bio, chef_sources, cuisine, address, district, area, price_band, hours, reservation, alert, catchtable_url, gmaps_url, sources, notes` |
| Phase A 既有檔 | ✅ `netlify.toml`、`web/ai-suggest-core.js`、四支 function（`ai-parse` / `ai-suggest` / `share` / `keepalive`）都在 |
| 待建立 | `wrangler.toml`、`worker/`、`web/_redirects`、`state/graph-state.json` 皆不存在（符合預期） |
| `wrangler` | ✅ 全域已安裝 **4.110.0**，A21／A22 不需要 npx 下載 |

**規格的前置事實與現況相符，沒有需要先回報的落差。**

## 執行前就發現、需要處理的四件事

1. **🔴 規格 Q2 的前提是錯的：repo 是公開的。**
   Q2 寫「repo 僅 Stanley 與 Chia 使用、不公開，`trip.json` 可安全進版控」。
   2026-09-11 與 09-12 兩次以未登入的 GitHub API 查證：`private=false`，**公開**。
   而 `trip.json` 的 schema 含 `booking_ref`、旅館 `address`、班機時刻——規格自己在
   CHECKLIST 第 6 題也寫「旅程頁的內容更敏感」。
   參考檔本身經掃描**沒有**訂位編號或卡號（`rest.json` 是公開的餐廳研究資料），
   風險在未來真實的 `trip.json`。
   **採用的預設（2026-09-12，Stanley 當下未回應語音提問，依規格「沉默即採預設」）：
   `trips/` 暫時加進 `.gitignore`，不進版控。**
   理由是風險不對稱——把敏感資料推上公開 repo 不可逆（git 歷史留存；2026-09-11 已有
   個人 email 誤入公開 repo 的前例），而「先不推、之後補推」隨時可做。
   參考檔因此也一併留在本機（它們本身無機密，但與真實旅程檔同一個資料夾）。
   **執行 session 請先向 Stanley 確認**：若決定把 repo 轉回私有，刪掉 `.gitignore` 裡
   `trips/` 那段即可恢復規格 Q2 的原始設計；若維持公開，則 A4／A6／A15 牽涉的留檔策略
   需要在 `DECISIONS-trip-page.md` 重新論述。

2. **ADR-014 的衝突比規格描述的更即時。**
   Chia 在 **2026-09-11**（前一天）才剛把 Netlify 接上 GitHub 自動部署——那是她待辦清單上
   最重要的一件。本規格要把託管搬走。本次只寫設定不部署，沒有立即破壞，
   但 `for-chia-cloudflare.md` 必須誠實寫明這件事。

3. **N5（對抗性驗證節點）與全域規則衝突。**
   `~/dev-habits/rules/model-routing.md` 明寫「驗證不要派 subagent——Opus 5 本來就會自我驗證」。
   採用方式：驗證不外派，但**嚴格照 A-item 的命令跑並貼原始輸出**，不用印象判斷。
   此偏離寫進 `DECISIONS-trip-page.md`。

4. **產出物改為分檔命名**（見本檔開頭），不覆蓋既有三個檔。

## A1–A25 驗收表

尚未執行。正式跑完後在此填入 PASS/FAIL 與原始命令輸出。
