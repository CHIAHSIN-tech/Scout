# KNOWN_ISSUES — 雙 Tab 視覺統一 ＋ 行程匯出

規格：[`specs/TASK-ui-unify-and-calendar-maps-export.md`](specs/TASK-ui-unify-and-calendar-maps-export.md)

以下都是**建議**，不是失敗。規格 EXECUTION RULES 第 2 條：只有命令可檢測的失敗才退回重做，
主觀疑慮寫在這裡。A1–A10 全部 PASS，沒有任何項目被砍。

---

## K1 — `.ics` 沒有做 RFC5545 的 75 位元組折行

長的 `SUMMARY` / `DESCRIPTION` 會超過 75 octets 仍寫成一行。規範要求折行（continuation line 開頭一個空白）。
**為什麼先不做**：Google 日曆、Apple 行事曆、Outlook 實測都吃未折行的檔案，且沒有任何 A-item 涵蓋此項。
**什麼時候要處理**：若真的遇到某個日曆軟體匯入失敗或字被截斷。

## K2 — `--text` 與購物端的 `--ink` 是同值不同名

兩邊都是 `#3C3830`。本次只要求「同名同值」（A3），同值不同名不構成缺陷，故未動。
真要收斂得把 token 抽成共用層，那是規格 NON-GOALS 明確排除的。

## K3 — 字級（font-size）仍未統一

行程端字級全部寫死、購物端也沒有字級 scale。規格 CHECKLIST 第 4 題已把此項標為**刻意延後**：
統一字級等於重排整個版面，遠超本次預算，且不影響「同名不同值」這個真正的缺陷。

## K4 — 兩個 panel 各自有一份 token 定義，仍可能各自漂移

A3 的 parity 檢查只在有人執行 `node scripts/check-style.mjs` 時才會抓到。
**建議**：若日後接上 CI 或 pre-commit，把
`node scripts/check-style.mjs && node scripts/check-exports.mjs` 掛進去，
這個缺陷就從「需要有人記得」變成「改壞會被擋下來」。

## K5 — 只有 `location` 有填的項目才進得了地圖

`location` 欄位以前在 web 版根本沒有寫入路徑（AI 匯入是把地點塞進 `notes` 的
「地點：⋯」字串裡）。現在編輯表單補上了 `location` 輸入，但**舊資料的地點仍留在 `notes` 裡**，
不會出現在地圖 CSV 或導航連結中。
**建議**：需要的人手動把舊項目的地點補進 `location` 欄；或另開一份 spec 做一次性搬移。
本次不做——規格 NON-GOALS 排除資料遷移。

## K6 — 沒有留下畫面截圖

本次執行環境的瀏覽器面板未顯示，截圖 API 會逾時。改以 DOM 與 computed style 的斷言留證
（字體家族、對比色值、375px 下的溢出檢查），證據記在 `ACCEPTANCE.md`。
視覺上的最終確認仍建議由人打開頁面看一眼。
