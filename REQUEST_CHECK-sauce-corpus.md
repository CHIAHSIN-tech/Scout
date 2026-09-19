# 對照原始請求 — us-hot-sauce-corpus

> 基準是 **Stanley 寫的原話**，不是 A 表。A 表全過也不代表請求被滿足；
> 請求裡有、而 A 表沒有任何一條對應的約束，即使 A 表全過也要進第二份清單。
> 只寫分歧；一致的地方一行帶過。

原話（spec 執行規則第 7 條列出的那幾句，加上這次執行中補的兩句）：

1. 「comprehensive… from all sources」
2. 「manually, maybe once every half a year」
3. 「build it into scout」
4. 「use the database logic of madb (keenodb)」
5. 「all the reviews every written/spoken regarding each product」
6. 「comprehensive enough for future ai analysis」
7. 「我不要抓任何 youtube 評論，zero」
8. 「只用現成字幕，不花錢」
9. 「只收就是專業評論，不是 user review」
10. （2026-09-19 本次）「他可以看到這些資料沒問題的，但我這個資料庫的檢索有可能是單獨工具」

---

## 一、有要求且已交付

| 原話 | 交付什麼 | 在哪裡驗 |
|---|---|---|
| 2「半年一次、手動」 | 沒有排程、沒有背景服務、沒有 CDC；一份逐步可複製貼上的作業書 | [`RUNBOOK-sauce-refresh.md`](RUNBOOK-sauce-refresh.md)；`sauce/load.py:--refresh` 只在人執行時跑 |
| 3「build it into scout」 | `sauce/` 在 Scout repo 裡，但**不 import Scout 的應用程式碼、也不被它 import** | `sauce/__init__.py` 的模組說明；`grep -rn "buylist\|app\.py\|page_" sauce/` 無輸出 |
| 4「用 madb（KeewanoDB）的資料庫邏輯」 | 整份建立在 evdb 上：append-only 事件、event_id＝內容雜湊、版本化衍生視圖、rejects 不丟列、raw store 放原文 | `sauce/contract.py`、`sauce/views.py`；A2／A5／A24／A31 |
| 7「zero YouTube」 | 一行都沒有。Hot Ones 的名單改從 Heatonist 的 season pack 商品頁取得 | A19 的 git grep；`sauce/sources/hotones.py` |
| 8「只用現成字幕，不花錢」 | 沒有任何 ASR、沒有付費轉錄；口說來源只收發布者自己公開的逐字稿 | A23 的 git grep；`requirements-sauce.txt` |
| 9「只收專業評論，不收 user review」 | UGC 來源只能產生 `sauce.observation.mention`（只有名字）；`sauce.review.*` 落在 UGC 來源就 exit 1 | A20；`sauce/contract.py:UGC_SOURCES`；`tests/sauce/test_contract.py` |
| 10「檢索可能變成獨立工具」 | `sauce/` 只依賴 evdb 與標準函式庫，整包搬走不會壞；`sauce/out/*.csv` 是可攜的產物 | `ADR-018`；`requirements-sauce.txt` |

## 二、有要求但缺席

| 原話 | 缺什麼 | 為什麼 |
|---|---|---|
| 1「from all sources」 | **Wikidata 整個來源沒有收到** | `query.wikidata.org/robots.txt` 明文 `Disallow: /sparql`，`www.wikidata.org` 擋 `/w/`。不繞過 robots 是硬規則。缺口：跨語言別名這次完全沒有。見 D5／K2。 |
| 1「from all sources」 | **Reddit 沒有收到任何名字** | 沒有 `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`；BOUNDS 寫死「不得改用網頁抓取」。節點標 degraded。見 K9。 |
| 1「from all sources」 | **主流食媒（Serious Eats、NYT、Food & Wine、Allrecipes…）沒有進白名單** | 它們對誠實的 user-agent 回 403。不偽裝 UA 是 NON_GOALS。後果：`1_methodology` 這一層很薄。見 K1。 |
| 5「all the reviews ever written/spoken」 | **「ever written」做不到，而且差得很遠** | 白名單是 opt-in 的：只抓准入的 outlet、只抓它們 sitemap 上找得到的文章。沒有 sitemap、被 403、或不在名單上的，一篇都沒有。這不是可以靠再跑一次補起來的缺口——**它是這個設計的形狀**。 |
| 5「spoken」 | **口說評論這一輪是 0** | 只收發布者自己公開的逐字稿，本輪沒有找到可用的 RSS 來源設定。它在 scope-cut 順序的第二位。見 K9。 |
| 6「comprehensive enough for future ai analysis」 | **評語（verdict）這一輪停在冷啟動** | llm-bridge 對沒有 golden 樣本的任務只跑前 20 筆就停（exit 3），要人逐列審過才會跑全量。**這是刻意的關卡，不是故障**，但它代表這一輪的評論層沒有跑完。 |

## 三、沒要求但做了

| 做了什麼 | 為什麼還是做了 |
|---|---|
| `fixtures/sauce/outlets-candidates.csv` 與 `sauce/admit.py`（白名單的准入稽核工具） | spec 只要求白名單本身；但「當初憑什麼收它」如果不是資料，半年後就沒有人能檢討。 |
| 從得獎名錄的 PDF 撈**公司網址**去推導店面名單 | spec 的 Q8 說種子網域「人工補」。實測用品牌名猜網域的命中率大約一成；名錄裡直接有網址，一年一千筆。 |
| `sauce/extract_rules.py`（結構化來源走規則，不走模型） | Q9 的預設是全部走模型。FDC／OFF／Shopify 已經把品牌與品名分開了，那是純規則的工作。見 D10。 |
| `text_fidelity` 欄位（標記 PDF 連字遺失） | spec 沒有這一欄。但那些名字確實缺字，不標起來就會被當成正常資料。見 K3。 |
| 得獎名錄的個人資料過濾（承辦人姓名、email、電話、地址一律不取） | spec 沒提。名錄裡有自然人的聯絡方式，收進語料庫之後從任何一張表上都看不出來。 |
| `sauce/net.py` 的憑證信任鏈修正（truststore → certifi → 預設） | 不修的話 `query.wikidata.org` 這類站會回「憑證過期」，而那在事後跟「站掛了」長得一模一樣。 |
| `ADR-018` 寫進 `context.md` | `CLAUDE.md` 要求牴觸既有決策時先提出；Stanley 2026-09-19 授權補 superseding ADR。 |

---

## 四、請求裡有、而 A 表沒有任何一條對應的約束

這一節是這份對照表存在的理由。**下面兩條即使 A1–A35 全過也不會被驗到。**

### 4.1 「comprehensive」沒有上界，A 表只有下界

A8 要 ≥4,000 款、A30 要 ≥1,200 篇。**達標不等於 comprehensive。**
美國市場到底有幾款辣醬沒有人知道，所以「收齊了」這件事在這個專案裡**無法被證明**，
只能被反證（A17 的召回率清單抓得到漏收）。而這一輪的召回率清單本身是弱的（見 D7／K4）。

**要怎麼讓它變強**：換一份不是憑記憶寫的清單——buylist 的辣醬庫有資料之後、
或拍一張實體貨架的照片。那時候量到的數字才有辦法回答「comprehensive 了沒」。

### 4.2 「comprehensive enough for future ai analysis」沒有被任何一條 A 項定義

A 表驗的是**保真**（正文逐字、引文是原句、原生分數不被改寫）與**規模**，
這兩件事是「日後拿得出來分析」的必要條件，但不是充分條件。
沒有任何一條 A 項回答「這些資料足夠回答哪一類問題」——因為日後要問什麼現在不知道，
而那正是不在收錄階段做摘要的理由。

**目前最接近的保證**：`sauce_reviews` 的每一列都帶著 `outlet_tier`、`outlet_conflict`、
`disclosure`、`score_raw`、`quote`、`descriptors`（逐字、不正規化），
所以日後任何一種切法都還有原料可用。**這是設計上的賭注，不是驗過的事實。**
