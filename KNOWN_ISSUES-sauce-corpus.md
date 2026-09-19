# 已知限制 — us-hot-sauce-corpus

> 這裡記「知道它在、而且知道它會怎麼害人」的東西。
> 每一條都寫清楚**從哪裡看得出來**——看不出來的限制才是真正危險的那種。

---

## K1 — 主流食媒對誠實的 user-agent 回 403，所以它們進不了白名單

Dotdash Meredith 整個網路（Serious Eats、Food & Wine、Simply Recipes、Allrecipes、
Southern Living）、NYT、Washington Post、Chili Pepper Madness 等，對
`us-hot-sauce-corpus/1.0` 這個 UA 回 403 或直接斷線。

**不偽裝 UA、不繞過**是 NON_GOALS 寫死的，所以這些站沒有合法路徑。
後果是白名單偏向**專門站與地方媒體**，`1_methodology` 這一層特別薄。
分析時如果只看 tier 1，樣本會很小——這一點在 `reports/sauce-reviews.md` 的 outlet 表上看得到。

## K2 — Wikidata 整個來源不可用（robots）

`query.wikidata.org/robots.txt` 擋 `/sparql`，`www.wikidata.org` 擋 `/w/`。
程式留著並照實回報 `robots_denied`。名單層只剩 `wikipedia` 與 `awards`。
**缺口**：跨語言別名（Wikidata 的強項）這次完全沒有收到，
所以非英文名稱的同一款醬比對不起來。

## K3 — Scovie 得獎名錄的 PDF 有連字遺失，名字會缺字

那份 PDF 的字型把 `tt`／`ti` 之類的連字對應成 `[`：`GW Wa[s Sauce`（應為 Watts）、
`h[ps://`（應為 `https://`）。pypdf 與 pymupdf 兩個抽取器結果相同，**是文件本身的問題**。

不自動修——修錯了事後看不出來。受影響的列照收，payload 標 `text_fidelity=ligature_loss`。
**後果**：這些名字折出來的鍵跟其他來源對不起來，所以它們多半會是單一來源的列。
看得到的地方：`sauce_catalog` 的 `corroboration` 欄位。

## K4 — 召回率清單是手寫的，量到的數字會偏高

見 `DECISIONS-sauce-corpus.md` D7。`supabase_sauces` 那張表是空的、沒有貨架照片、
Reddit 沒憑證，所以清單改用 `analyst_recall`。手寫名單偏向有名的產品，
而有名的產品本來就最可能在 FDC／OFF 裡。**recall 這個數字要配著這句話讀。**

## K5 — FDC 的同一個 GTIN 有多筆歷史版本

4,871 筆 FDC 候選列只對應 1,349 個 GTIN——FDC 會替同一個商品的每次更新開一筆新的 fdc_id。
GTIN 合併把它們收成一款（這是對的），但也代表 **FDC 只提供約 1,349 款母體**，
規模要靠 OFF 與長尾店面撐。看得到的地方：`sauce_catalog` 的 `sources` 欄位分佈。

## K6 — 規則抽取的品名可讀性比模型差

FDC 的 `description` 是全大寫、逗號分段、而且常常重複
（`HOT & SPICY MADRAS CURRY SAUCE, HOT & SPICY, MADRAS CURRY`）。
規則抽取只**丟掉**重複的段，不改寫任何字，所以留下來的仍然是全大寫。

**沒有任何自動檢查蓋得到「這個名字唸不唸得出來」**——這正是 A11 的試樣要人看的理由，
也是 N7 要附 20 筆隨機抽樣原樣的理由。

## K7 — 代表句選得好不好沒有自動化的守門員

A25 只能證明 `quote` 出自原文，不能證明它是那篇評論的**重點**。
一篇說「it's fine but the vinegar dominates」的評論，抽到 `"it's fine"` 一樣會通過。
A11 要求試樣裡至少 15 筆是 verdict，就是為了讓人自己判斷抽句品質。
**這一項目前沒有自動化的守門員**，最終報告必須明說。

## K8 — 給 evdb 的提案：streaming derive

`evdb/derive.py` 會把全部事件 `all_events()` 讀進記憶體再交給視圖函式。
事件量往上長時這是第一個會爆的地方，所以本任務加了 A9 的天花板（80 萬）當保險絲。

**提案**（交給 evdb 自己的 spec，本任務不實作、不繞過、也不在 Scout 這邊複製一份 derive）：
`Store.rows(sql)` 已經是現成的 SQL 入口，缺的是 `derive` 那一層的串流版本
與同樣的 manifest 契約（`rows_sha256` 必須仍然可重現，所以串流版要保證輸出順序穩定）。

## K9 — Reddit 與 podcast 逐字稿這次是空的

- `reddit`：沒有 `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`，節點標 `degraded`，
  **不得改用網頁抓取**（BOUNDS）。缺口：只有討論區講過的新品收不到。
- `podcast_transcript`：只收發布者自己公開的逐字稿，本輪沒有找到可用的來源設定。
  它在 scope-cut 順序的第二位，本來就是最先被放掉的那幾個之一。

## K10 — evdb 工作樹在本任務開始前就是髒的

`git -C ../1-github/evdb status --porcelain` 回報 `M domains/ma/views.py`，
**這是本任務開工前就存在的狀態**（開工當下已取雜湊存證：診斷用 diff 的 sha256
`43a32cc4f871f5fbcc5e690e3cb7e6c578e91ba49ae89e718a1b1ef4da41c30e`）。

本任務沒有動 evdb 任何一個檔。A4 照實報 FAIL，但原因不在這份工作；
要讓 A4 過，得由 evdb 那邊的人決定那份未提交的修改要 commit 還是丟掉——
**不是由這裡替他決定**。

## K11 — 這一輪的四條 FAIL 裡有三條是同一個關卡

`A11`（試樣要 ≥15 筆 verdict）、`A27`（孤兒等式）、`A30`（評論規模）三條全部卡在
**同一個地方**：llm-bridge 對沒有 golden 樣本的任務只跑前 20 筆就停（exit 3），
要人逐列審過並 promote 之後才會跑全量。

- 已經抓回來的評論：**1,827 篇**（≥1,200，A30 的第一個門檻其實達標了）
- 已經產生的 verdict：**0 筆**（全量沒跑）
- 待審檔：`sauce/prompts/sauce-review-verdict/golden.pending.jsonl`
  （20 筆樣本，其中 18 筆通過三層驗證、1 筆被「引文不是原句」擋下、1 筆 schema 不合）

**這不是故障，是設計。** 但它代表這一輪的評論層停在半路，而三條驗收會照實報 FAIL。
人審完之後重跑 `sauce.extract --what reviews`，這三條才有機會過。

順帶一提，那 20 筆樣本平均每篇只抽出 0.72 筆 verdict——如果全量維持這個比例，
最後大約是 1,300 筆，**仍然低於 A30 要求的 3,000**。原因是白名單上的文章有很大一部分
是食譜與導購清單，不是逐款評測。要補的話得往「每篇都在評單一產品」的專門站再擴白名單。

## K12 — outlet 白名單的證據網址是機器挑的，還沒有人逐列看過

`sauce/admit.py` 找到的是「站上第一個看起來像編輯團隊／評測方法的頁，而且真的回 200」。
有些挑得很準（`americastestkitchen.com/about-us/…`），有些只是勉強及格。
spec 要的是**人的判斷**，所以 `RUNBOOK` §2 寫的是「`--emit` 的輸出不會自己寫進白名單，
人看過再貼」。這一輪為了把管線跑通，是直接 emit 進去的。
下一輪要逐列打開那 44 個 `evidence_url` 確認。

## K13 — `A14` 這一輪只實際驗到 18 組裡的 5 組

`fixtures/sauce/confusables.csv` 有 18 組，但其中 13 組的兩邊至少有一邊還沒被收進總表
（多半是還沒抓到的小廠）。檢查器對「兩邊都不在」的組回報 skip 而不是 pass——
所以 A14 這一輪的實際保護力只有 5 組。母體長大之後這條會自動變強。

## K14 — `sauce-filter-3` 仍然會收到堅果類的假陽性（下一版要修的第一件事）

filter-3 之後重抽 20 筆，19 筆是真的辣醬，剩下那一筆是
`Rocky Mtn Provisions, Sriracha Honey Roasted Cashews`——`sriracha` 在明講型清單上，
而排除清單只有 `peanut`，沒有 `cashew`／`almond`／`nuts`。

**沒有跟著修進這一輪的資料**：規則版本與已經寫進庫的事件是一對一的
（每一筆 payload 都帶 `filter_version`），改了清單卻不重跑，會讓版本號說謊。
所以這一條留到 `sauce-filter-4`：加上堅果類的詞，下一輪重跑時 `filter_version`
會照實變成 4，差異也就看得出來是規則改了而不是市場變了。

**目前的假陽性率**：20 筆隨機抽樣中 1 筆（5%）。這是抽樣估計，不是全表統計。

## K15 — `sauce_buyable` 裡還有整箱與組合包的殘留

`1 CS`（一箱）、`Build Your Own`、`Mix, Match` 這類品項還在表上，因為：
- 排除規則是**這一輪才加的**，而先前那一批觀察事件已經寫進庫（append-only 不能刪）；
- `1 CS` 這種寫法沒有被 `NOT_A_SINGLE_BOTTLE` 的字面規則涵蓋。

**影響**：價格分佈的右尾會被拉高（$51 的「一箱」混在單瓶 $11.95 的中位數裡）。
下一輪重跑時舊事件仍在，但新的觀察會帶著新規則的版本號，視圖取的是最低報價，
所以整箱那一筆自然不會是被選中的價格——除非那款醬只有整箱在賣。

## K16 — WooCommerce 店的品牌欄多半是空的

Woo 的 Store API 有 `brands` 欄位，但多數店沒有填。所以 `sauce_buyable` 裡
woo 來源的列品牌是空字串，產品名要自己帶品牌才認得出來。
Shopify 的 `vendor` 欄則幾乎都有填。
