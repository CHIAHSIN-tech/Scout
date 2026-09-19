# 最終報告 — us-hot-sauce-corpus

> 驗收表逐條 PASS/FAIL 與**原始輸出**在 [`ACCEPTANCE-sauce-corpus.md`](ACCEPTANCE-sauce-corpus.md)。
> 對照 Stanley 原話的三份清單在 [`REQUEST_CHECK-sauce-corpus.md`](REQUEST_CHECK-sauce-corpus.md)。

## 0. 這一輪是失敗的

**29 PASS / 5 FAIL / 1 BLOCKED。** 依 spec 的規則，任何一項 FAIL 或 BLOCKED，
整個 run 就是失敗，不論產出多少列。

| 項目 | 判定 | 為什麼 | 誰能解 |
|---|---|---|---|
| A4 | FAIL | evdb 工作樹在**本任務開工前**就有一份未提交的修改（`domains/ma/views.py`）。本任務沒有動 evdb 任何一個檔。 | evdb 那邊的人決定那份修改要 commit 還是丟掉 |
| A11 | FAIL | 試樣要 ≥15 筆 verdict，目前 0 筆 | 見下面「卡在你身上的那一件事」 |
| A17 | FAIL | 召回率 0.743，門檻 0.90 | 需要更多長尾店面，或一份更硬的召回率清單 |
| A27 | FAIL | 孤兒 2,232 筆，但「沒有 verdict 的評論」只有 1,827 筆；差額 405 筆是**還沒被抽取的名單型提及** | 同 A11 |
| A30 | FAIL | verdict 0 筆（門檻 3,000）；評論篇數 1,827 篇（門檻 1,200，這一項達標） | 同 A11 |
| A32 | BLOCKED | 從空的 `.evdb` 照作業書跑到底這一輪沒有做（那是一次三小時以上的重跑） | 下一輪自然會驗到 |

## 1. 卡在你身上的那一件事

llm-bridge 對沒有 golden 樣本的任務只跑前 20 筆就停（exit 3），要人逐列審過才會跑全量。
**這是刻意的關卡，不是故障**，而且它一次擋住了 A11、A27、A30 三條。

```
sauce/prompts/sauce-review-verdict/golden.pending.jsonl     ← 20 筆待審
```

審的方式：每一列把 `reviewed` 改成 `true`、必要時修 `expected`，然後

```
python -m llm_bridge.prompts promote sauce/prompts sauce-review-verdict
python -m sauce.extract --home .evdb --what reviews
python -m sauce.load --home .evdb --stage extract_rules,match,views
```

那 20 筆裡 18 筆通過三層驗證、1 筆被「引文不是原句」擋下、1 筆 schema 不合。

**先講清楚**：那 20 筆平均每篇只抽出 0.72 筆 verdict。全量 1,827 篇照這個比例大約是
1,300 筆，**仍然低於 A30 要的 3,000**。原因是白名單上的文章有很大一部分是食譜與導購清單，
不是逐款評測。

## 2. 這一輪實際收到什麼

| | 數量 |
|---|---|
| 事件總數 | 38,804 |
| 產品（`sauce_catalog` 的列） | **6,675** |
| 品牌 | **2,286** |
| 專業評論文章（正文逐字落地） | **1,827** |
| 評論來源 outlet | **44 家**（白名單），實際抓到 40 家 |
| 長尾店面 | 83 間（74 Shopify、9 WooCommerce） |
| 評語（verdict） | **0**（卡在上面那一關） |

來源分佈：`off` 16,623・`fdc` 14,996・`shopify` 4,637・`outlet_web` 1,827・
`woo` 445・`wikipedia` 161・`awards` 102・`hotones` 13。

## 3. 沒有任何自動檢查蓋得到的兩件事

spec 點名要在報告裡誠實寫出來的就是這兩項。

### 3.1 名字讀不讀得懂

沒有任何 A 項能保證 `product` 欄位讀起來像人話。下面是**隨機抽的 20 筆原樣**
（seed 20260919），請自己看：

| # | brand | product | 來源 |
|---|---|---|---|
| 1 | Rocky Mountain Foods Inc. | Rocky Mtn Provisions, Sriracha Honey Roasted Cashews | off |
| 2 | — | Veronica’s Salsa Picante | off |
| 3 | Zia Cantina | Zia Chile Traders Red Chile Hot Sauce | shopify |
| 4 | Grace | caribbean style hot pepper sauce | off |
| 5 | — | Pokón Lava Hot Sauce | woo |
| 6 | Wicked Provisions | Magic Mushroom Stout Hot Sauce | shopify |
| 7 | Salsa Culichi Llc | Seafood hot sauce | off |
| 8 | Torchbearer Sauces | Mushroom Mayhem – Mushroom Hot Sauce | shopify |
| 9 | Val Vita | Habanero Tomato Sauce | off |
| 10 | GUNTHER'S GOURMET | SPICY CHIPOTLE PEPPER & SMOKED CORN SALSA | fdc|off |
| 11 | High Mesa Chile Co. | Roasted Serrano Hot Sauce | shopify |
| 12 | Taco Terco | Monterrey Pepper Sauce | off |
| 13 | OLD PUEBLO | POBLANO SALSA RANCHERA | fdc |
| 14 | Down to Ferment | That’s What Shishito Said | shopify |
| 15 | — | Lucky's hot sauce | off |
| 16 | — | Organic jalapeño peppers stir in puree | off |
| 17 | I Love Chamoy | Spicy Watermelon Chamoy | off |
| 18 | — | Taco Bell Hot Sauce | off |
| 19 | Mitchell's | Chili Garlic sauce | off |
| 20 | — | Datil apeppers Sauce | off |

第 1 筆（`Sriracha Honey Roasted Cashews`）是假陽性——那是腰果，不是醬。
規則版本與資料是一對一的，所以沒有偷偷改清單；修法記在 `KNOWN_ISSUES` K14，
下一輪會以 `sauce-filter-4` 的身分出現。

**這一節本身就是它存在的理由的實例**：第一次抽樣抽到蔓越莓醬與咖哩麵，
那是機器完全驗不出來的，改法記在 `DECISIONS` D12。

### 3.2 代表句選得好不好

A25 只能證明 `quote` 出自原文，**不能證明它是那篇評論的重點**。
一篇說 "it's fine but the vinegar dominates" 的評論，抽到 "it's fine" 一樣會通過。

**這一項目前沒有自動化的守門員。** 下面是 10 筆抽出來的句子（來自待審的 20 筆樣本，
因為全量還沒跑），請自己判斷抽句品質：

| # | 抽到的醬 | stance | 引文（原句） |
|---|---|---|---|
| 1 | Fragrant Fresno Chile Sauce | positive | This sauce is great on grilled chicken and fish , tacos , roasted or grilled vegetables , and salads . |
| 2 | Trappey’s Louisiana Hot Sauce | positive | This “tart, brightly tangy” sauce has “a lemony overtone.” It’s also “fruity” and has a “hint of sweetness to counterbalance the tang.” Tasters liked  |
| 3 | Panola Cajun Hot Sauce | positive | This sauce was a bright, summery reddish orange. Tasters described it as “sparky” and “citrusy” and compared it to the bite of an “unripe tomato.” Ove |
| 4 | Barberton Hot Sauce | positive | This delicious, mild, and tangy condiment is a sauce and a side dish in one. |
| 5 | Comeback Sauce | positive | This tangy, creamy sauce takes only minutes to make and will enhance pretty much anything you put it on. |
| 6 | Sriracha | positive | our favorite was definitely Sriracha. (More specifically, we love the kind made by Huy Fung Foods in California. Buy a bottle . Like, right now.) |
| 7 | Hot Sauce | descriptive | 4. Hot Sauce - No Most hot sauce is highly acidic, which prevents a bottle from spoiling at room temperature. Its flavor may change over time, and ref |
| 8 | pesto | positive | As the eggs cooked, the pesto became a delicious crust of basil and garlic that was mind-blowingly good. I could taste the pesto in every bite. |
| 9 | chili crisp | positive | The eggs became encrusted in it and were spicy, rich, and crunchy. This may be my new favorite way to eat my eggs, and it’s even better than the pesto |
| 10 | chimichurri | positive | The brightness of the chimichurri came through, and infused itself into the egg just like the pesto. You could taste the freshness of the cilantro and |


## 4. 產物

| 檔 | 是什麼 |
|---|---|
| `sauce/out/sauce_catalog-v1.csv` | 產品總表（6,675 列），進版控 |
| `sauce/out/sauce_reviews-v1.csv` | 評語表（目前 0 列） |
| `reports/sauce-coverage.md` | 召回率逐筆命中／未命中 |
| `reports/sauce-reviews.md` | 評論覆蓋率四張表（**沒有門檻**，用途是把「多數產品沒有評論」變成數字） |
| `ACCEPTANCE-sauce-corpus.md` | 驗收表 ＋ 每一條的原始輸出 |
| `REQUEST_CHECK-sauce-corpus.md` | 對照 Stanley 原話的三份清單 |
| `DECISIONS-sauce-corpus.md` | 12 條決策（與 spec 字面不同的地方都在這裡） |
| `KNOWN_ISSUES-sauce-corpus.md` | 14 條限制，每條都寫「從哪裡看得出來」 |
| `RUNBOOK-sauce-refresh.md` | 半年重跑的逐步作業書 |
| `docs/sauce-recon.md` | 動工前的偵察（evdb 表面歸位、實測到的環境事實） |
| `state/graph-state-sauce.json` | 圖狀態（只放指標，不放產物） |

## 5. 下一輪最值得做的三件事

1. **把待審的 20 筆審掉**——一次解開三條 FAIL 的唯一路徑。
2. **換一份更硬的召回率清單**：現在這份是憑記憶手寫的，偏向有名的產品，
   所以量到的 0.743 已經是**高估**。buylist 的辣醬庫有資料、或拍一張貨架照片，
   那時候的數字才有意義（`DECISIONS` D7）。
3. **白名單往「逐款評測」的專門站擴**：現在 44 家裡有很多是食譜站，
   文章多但 verdict 少。要撐起 A30 的 3,000 筆，需要的是評測密度高的站，不是文章多的站。
