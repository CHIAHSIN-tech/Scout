# 辣醬儀表板：參數與熱度訊號的功課

> 2026-09-19 · 給 `us-hot-sauce-corpus` 的下游儀表板用
> 這份是研究筆記，不是 spec。品牌名與產品名保留原文。

---

## 0. 一句話結論

**辣度不是品質軸，是篩選軸。** 兩個獨立權威講同一件事：

- PepperScale 的評分法把辣度當**分類標籤**（Mild / Medium / Extra-Hot / Super-Hot），
  不進分數：「A hotter sauce isn't a better one, so heat alone doesn't move the rating.
  Heat balance does.」他們真正打分的是 Overall Flavor、**Heat Balance**、Usability（各 1–5）。
- Scovie Awards 盲測評分項是 Appearance、Aroma、Spice Blend、Originality、
  **Flavor（權重最高）**、Overall Impression——**辣度完全不是評分項**，
  它只決定你在哪個組別比賽。

所以儀表板預設排序絕對不要用 SHU。SHU 放左邊的篩選欄。
多數辣醬網站都做錯這件事，這是你可以做對的第一件事。

第二個可借的結構：PepperScale 把分數拆成 **Eating Score**（好不好吃、好不好用）
與 **Collectibility Score**（瓶身、標籤、故事、產量、地域稀有度）兩個**互不換算**的軸。
這剛好對應你和 Chia 的兩種需求——「回購」與「嚐鮮」。別合成一個總分。

---

## 1. 參數五族（按資料從哪來分，因為那決定做不做得到）

### A. 身分與面向 — 來自目錄來源，覆蓋率高

| 參數 | 值域 | 備註 |
|---|---|---|
| `style` | Louisiana / Mexican-taqueria / sriracha / chili crisp / chili oil / sambal / harissa / peri-peri / hot honey / fermented mash / salsa macha / umami-XO | **最重要的一個分面**。不同 style 之間比黏稠度沒有意義 |
| `primary_peppers[]` | jalapeño, serrano, habanero, scotch bonnet, ghost, scorpion, reaper, chipotle, aji, calabrian, aleppo, guajillo, chiltepin… | 2026 趨勢報導點名 Calabrian 與 Aleppo 是「future-forward」 |
| `fermented` | bool | 分野很大，值得獨立欄位 |
| `base` | vinegar / oil / fruit purée / water / honey | |
| `vinegar_type` | distilled / cider / none | 老派 Louisiana 的爭論點 |
| `heat_claim_shu` + `heat_band` | 數字 + 五級 | **只做篩選，不做排序** |
| `origin_state` / `origin_country` | | 地域是 collectibility 的一部分 |
| `format` | bottle / jar+spoon / squeeze | chili crisp 要用湯匙，這影響「怎麼用」 |

### B. 成分與營養 — 來自 FDC / Open Food Facts，**這族被嚴重低估**

FDC Branded Foods 帶 GTIN，附成分表與營養標示。這是**唯一一族接近全覆蓋、
而且完全客觀**的參數——評論只蓋得到一兩成，成分表蓋得到大部分。

| 參數 | 為什麼值得放 |
|---|---|
| `first_ingredient` | 第一順位是辣椒、醋、水還是糖——最便宜的品質代理指標 |
| `ingredient_count` | 三種 vs 十七種，兩種做法 |
| `sodium_mg_per_100g` | 同類產品之間差好幾倍，沒人比較過 |
| `sugar_g_per_100g` | 把 swicy／hot honey 跟傳統派自動分開 |
| `has_xanthan` / `has_artificial_color` / `has_preservative` / `has_msg` | 各自一個 bool，不要合成「純不純」分數 |
| `allergens[]` | |

⚠️ **坑：serving size 被業界玩弄**（1 tsp vs 1 tbsp）。一律換算 per 100 g 再比。

### C. 判斷 — 來自評論庫，覆蓋率一到兩成

| 參數 | 備註 |
|---|---|
| `stance_mix` | positive / mixed / negative / descriptive 的分佈 |
| `score_raw` + `outlet` | **不要跨 outlet 加總分數** |
| `rank_in_article` / `of_total` | **這個才是跨 outlet 可比的東西**——見下 |
| `descriptors[]` 詞頻 | 逐字不正規化，讓詞頻自己說話 |
| `best_of_designation` | 「Best Overall」「Best Value」這類標籤 |
| `outlet_tier` / `outlet_conflict` / `disclosure` | 信任權重，不是品質 |

**跨 outlet 比較只有一個東西真的成立：盲測排名。**
Delish 的 4/5 跟 Serious Eats 的 8.5/10 不在同一個尺度上，硬換算是假精確。
但「在 12 款盲測裡拿第 1」在哪家都是同一件事。所以儀表板的評論欄位
主打 `rank_in_article / of_total`，`score_norm` 只做同一 outlet 內的排序。

### D. 認可 — 獎項與名單

| 參數 | 備註 |
|---|---|
| `scovie_wins[]`（年份＋組別） | 盲測、評審是業界專業人士 |
| `hotones_season` + **`hotones_slot`（1–10）** | 見下，這個欄位有隱藏價值 |
| `expo_debut_year` | |

**`hotones_slot` 是免費的第三方辣度排序。** 每季 10 款由專家依辣度排序，
與廠商自己標的 SHU 互相獨立。所以它可以當**標榜 SHU 的交叉檢查**：
某款坐在第 3 棒卻宣稱 500,000 SHU，這兩件事必有一件是假的。
這種矛盾值得在儀表板上標出來，而不是二選一。

### E. 流通與價格 — 來自 storefront 抓取

| 參數 | 備註 |
|---|---|
| `price_per_fl_oz` | **真正的 value 指標**，不是瓶價 |
| `retailer_count` | 有幾家在賣——見下，這是我最推薦的熱度訊號 |
| `in_stock_ratio` | 缺貨也是訊號 |
| `first_seen_at` / `brand_published_at` | 見下 |

---

## 2. 「最新」怎麼知道——這題比想像中簡單

**答案已經在管線裡了，不必另外找資料源。**

1. **Shopify `/products.json` 每一筆帶 `created_at` 與 `published_at`。**
   品牌自己官網上架的時間，就是這款醬問世的時間，精度到天。
2. **evdb 的 `first_observed_at`** 本來就在每個事件上。
3. **半年跑一次 × append-only ＝ 第二次執行自動產生「這半年新增了什麼」**，
   只要把兩次的 entity 集合相減。精確、免費、不需要任何外部趨勢服務。
4. Heatonist 的 new arrivals collection、Hot Ones 新一季（目前是 **Season 30**，
   `heatonist.com/collections/hot-ones-hot-sauces-season-30` 這種 URL 形式）就是最新的 10 款。

⚠️ **但這件事有個前提，現在的 spec 不滿足**——見第 4 節。

---

## 3. 「最流行」怎麼知道——沒有單一數字，我會並列不合成

每個訊號都有自己的偏差。**合成一個總分會把「哪個訊號動了」藏起來**，
而那通常才是你想知道的事。以下按「值不值得做」排序：

| # | 訊號 | 取得成本 | 偏差 | 判斷 |
|---|---|---|---|---|
| 1 | **鋪貨廣度**（150 個 storefront 裡有幾家在賣） | **零，已經抓了** | 偏向有通路能力的品牌 | **最推薦。**零售商只囤賣得動的東西 |
| 2 | **各零售站自己的暢銷排序** | 低 | 每站客群不同 | Shopify 的 collection 端點會回傳該店排序；`sort_by=best-selling` 是標準排序。**各店 handle 不一，要逐站驗**。多站排名做 Borda count |
| 3 | **專業評論則數＋近期性** | **零，已經在語料庫裡** | 編輯注意力≠銷量，但通常領先 | 近 12／24 個月的評論數 |
| 4 | **Hot Ones 出現** | 零 | 一次性尖峰 | 這個品類最大的單一需求驅動力 |
| 5 | **獎項年份** | 零 | 落後指標 | 比較像「地位」不是「流行」 |
| 6 | **Wikipedia pageviews**（Wikimedia REST API，免金鑰） | 低 | **只有有條目的品牌有**——Tabasco／Cholula 那一層 | 前 50 名好用，長尾完全沒有 |
| 7 | **Google Trends** | **不確定** | 最理想的訊號 | 官方 API 到現在仍是 **v1alpha、需申請**，而且社群回報有人申請後**沒有下文**。→ **當成 stub，不要當依賴** |

**明確不建議：**
- Amazon BSR——沒有正當取得管道。
- 社群平台計數——ToS 加機器人雜訊。
- Reddit 提及量——你已經排除使用者意見；而且提及量受洗版與季節影響大，
  當熱度指標不可靠。留著發現名字就好。

### 關於你說的 celebrity thread

誠實講：追名人社群平台這條路 ToS 有問題、雜訊又高，投入產出比很差。
**但這個品類的「名人機制」本來就集中在一個地方——Hot Ones。**
所以：

- **Hot Ones lineup ＝ 名人訊號本身**，而且是乾淨的結構化資料（季、棒次）。
- **名人創立／投資的品牌** ＝ 一個 bool ＋ 證據 URL，來源是白名單媒體的報導——
  **評論庫免費附送**，不必另外做。
- **主廚背書** 同理，從白名單 outlet 的文章裡自然掉出來。

也就是說，名人這一軸你已經在收了，一行新的抓取程式都不用寫。

---

## 4. 現行 spec 的一個缺口（要改）

**趨勢需要兩個快照，而現在的 spec 會把前一份蓋掉。**

`sauce/out/sauce_catalog-v1.csv` 是單一檔案，半年後重跑就覆蓋。
上面第 2、3 節所有「新增了什麼」「哪些爬升了」全部要拿上一次的 view 來 diff——
沒有舊檔就算不出來。事件庫本身是 append-only 所以原始資料不會丟，
但 view 層會丟，而且丟得無聲無息。

**建議改動（一行）：**
```
sauce/out/<run_date>/sauce_catalog-v1.csv
sauce/out/<run_date>/sauce_reviews-v1.csv
```
外加一條 A 項：第二次執行後 `sauce/out/` 至少有兩個 run 目錄，
且 `python -m sauce.trend --from <run1> --to <run2>` exit 0 並列出新增／消失／
rank 變動的產品。

這種東西不先講，半年後才發現，就真的要再等半年。

---

## 5. 儀表板版面的三個建議

1. **左邊篩選、右邊排序，SHU 只在左邊。** 篩選：style、pepper、heat_band、
   fermented、價格帶、有沒有專業評論。排序：鋪貨廣度、price_per_fl_oz、
   評論則數、最近上架。
2. **兩個分數不要合成。** Eating（好不好吃好不好用）與 Collectibility（值不值得收）
   分開顯示，沿用 PepperScale 的拆法。
3. **每個熱度訊號各自一條 sparkline，不要一個總分。**
   使用者要看的是「它為什麼上升」——是多了三家店在賣，還是上了 Hot Ones。

---

## 6. 沒查證的東西（別當事實用）

- Shopify 各店的 best-selling collection handle 不統一，第 3 節第 2 項要逐站實測。
- Google Trends alpha 的實際配額與條款沒讀到原文，只看到社群回報；要用先自己申請。
- Scovie 的完整組別清單在報名表裡，官網規則頁沒有；要拿組別當 style 分類法得去抓報名表。
- 2026 風味趨勢（swicy、yuzu／tamarind、miso／black garlic、Calabrian／Aleppo）
  出自 IFT 的專家預測，**是觀點不是銷售數據**，該文沒有任何百分比。

---

Sources:
- [How We Review Hot Sauces — PepperScale](https://pepperscale.com/how-we-review-hot-sauces/)
- [2027 Scovie Awards Rules — Scovie Awards](https://www.scovieawards.com/2027-scovie-awards-rules)
- [Outlook 2026: Flavor Trends — IFT](https://www.ift.org/food-technology-magazine/outlook-2026-flavor-trends)
- [Hot Ones Hot Sauce Lineup Season 30 — HEATONIST](https://heatonist.com/collections/hot-ones-hot-sauces-season-30)
- [Introducing the Google Trends API (alpha) — Google](https://developers.google.com/search/blog/2025/07/trends-api)
- [Get early access to the Google Trends API alpha — Google](https://developers.google.com/search/apis/trends)
