# 最終報告 — us-hot-sauce-corpus（v3）

> 驗收表逐條 PASS/FAIL 與**原始輸出**在 [`ACCEPTANCE-sauce-corpus.md`](ACCEPTANCE-sauce-corpus.md)。
> 對照 Stanley 原話的三份清單在 [`REQUEST_CHECK-sauce-corpus.md`](REQUEST_CHECK-sauce-corpus.md)。

## 0. 這一輪是失敗的，而且卡在同一個地方

**41 PASS / 7 FAIL / 1 BLOCKED。** 依 spec 的規則，任何一項 FAIL 或 BLOCKED，
整個 run 就是失敗，不論產出多少列。

七條 FAIL 裡有**五條是同一個原因**：兩個冷啟動閘都還沒有人審。

| 項目 | 判定 | 為什麼 | 誰能解 |
|---|---|---|---|
| A11 | FAIL | 試樣要 ≥15 筆 verdict，目前 0 筆 | 審 `sauce-review-verdict` 的待審檔 |
| A27 | FAIL | 孤兒 2,232 筆——沒有 verdict 的評論全部算孤兒 | 同上 |
| A30 | FAIL | verdict 0 筆（門檻 3,000）；評論篇數 1,827 篇（門檻 1,200，這一項達標） | 同上 |
| A38 | FAIL | 庫裡 0 筆 `sauce.label.read` | 審 `sauce-label-read` 的待審檔 |
| A39 | FAIL | 沒有成分面板判讀可以驗詞庫覆蓋率 | 同上 |
| A41 | FAIL | 試樣要 ≥20 筆標籤判讀 ＋ ≥15 筆 verdict，兩邊都是 0 | 兩份都要審 |
| A17 | FAIL | 召回率 0.743，門檻 0.90 | 需要一份更硬的召回率清單（D7） |
| A32 | BLOCKED | 從空的 `.evdb` 照作業書跑到底這一輪沒有做（一次三小時以上的重跑） | 下一輪自然會驗到 |

**A38/A39 這一輪是新加的守門員，而且它們原本會「通過」。** 庫裡 0 筆判讀時，
這兩條檢查什麼都沒驗到，卻會印出跟真的驗過 300 筆一模一樣的輸出。
已經改成「0 筆直接判不過」（D26）——冷啟動閘保證了每一輪的第一次執行都會踩到那一格。

## 1. 卡在你身上的那兩件事

兩份待審檔，格式一樣：每一列把 `reviewed` 改成 `true`、必要時修 `expected`。

```
sauce/prompts/sauce-review-verdict/golden.pending.jsonl     ← 20 筆（評論 → 評語）
sauce/prompts/sauce-label-read/golden.pending.jsonl         ← 20 筆（標籤照片 → 逐字）
```

審完各自 promote 再重跑：

```powershell
.venv\Scripts\python -m llm_bridge.prompts promote sauce\prompts sauce-review-verdict
.venv\Scripts\python -m llm_bridge.prompts promote sauce\prompts sauce-label-read
.venv\Scripts\python -m sauce.extract   --home .evdb --what reviews
.venv\Scripts\python -m sauce.labelread --home .evdb --panel ingredients
.venv\Scripts\python -m sauce.load --home .evdb --stage ingest
.venv\Scripts\python -m sauce.composition --home .evdb
.venv\Scripts\python -m sauce.load --home .evdb --stage ingest,match,views --rules v1
```

**標籤那 20 筆比評語那 20 筆更需要你看。** 評語至少還有一條機器檢查在擋
（引文必須是正文的逐字子字串，A25）。標籤判讀的「原文」是一張圖，
**連子字串都沒得比**：詞庫覆蓋率（A39）只擋得住模型整批造字，
擋不住順序錯、數字錯、漏掉一行。那三種錯誤用的都是詞庫裡的詞，覆蓋率完全正常。

第一次跑視覺模型時 20 筆裡有 6 筆回的是 markdown 散文而不是 JSON，
prompt 進版到 v2 之後是 20/20（D25）。**驗證器一個字都沒動**——
把通過率拉上去的辦法只有改 prompt，或放寬驗證器，後者是把沒讀對的改判成讀對了。

## 2. 這一輪實際收到什麼

| | 數量 |
|---|---|
| 事件總數 | 120,883 |
| 產品（`sauce_catalog` 的列） | **7,186** |
| 品牌 | **2,803** |
| 買得到的（`sauce_buyable`） | **1,861** |
| 專業評論文章（正文逐字落地） | **1,827** |
| 評語（verdict） | **0**（卡在冷啟動閘） |
| 標籤照片 | **145 張**（成分面板 121、營養 11、正面 13） |
| 標籤逐字判讀 | **0**（卡在冷啟動閘） |
| 結構化成分列 | **1,211**（FDC 1,200、店面文字 11、實物標籤 0） |
| 辣度上界算得出來的 | **777**（其中 43 筆是 `unbounded`：含辣椒萃取物） |
| 有排序 rank 的 | **15**（排序事實 < 2 筆的一律留空） |
| 代工聚類 | **50 組**，納入比對 3,633 款 |

來源分佈（`sauce_catalog` 的列）：`off` 4,635・`shopify` 1,781・`fdc` 1,250・
`woo` 180・**`webshop` 153**。

### 2.1 這一輪唯一一個「多出來」的來源

`webshop` 是第三條抓取路徑，補的是 D17 量到的平台缺口：
用搜尋找到的 13 間店裡 9 間既不是 Shopify 也不是 Woo，
於是它們在資料上**連「這間店存在」都沒有被記下來**。

四間店、161 筆商品觀察、**83 列進了 `sauce_buyable`**——
這 83 列在上一輪是零。做法是只讀站方自己宣告的結構化資料
（JSON-LD → microdata → OpenGraph），讀不到就記 `structured=none` 並留空價錢，
**不猜**（D24）。猜出來的 `$12.99` 在表上跟站方宣告的長得一模一樣。

## 3. 沒有任何自動檢查蓋得到的三件事

spec 點名要在報告裡誠實寫出來的。v3 多了第三件，而且它是三件裡最沒有防護的。

### 3.1 名字讀不讀得懂

`"Original Hot Sauce 5oz 2pk Value"` 通得過所有機器檢查——它確實是來源字串的
連續詞串——但它不是一個人會拿來稱呼那瓶醬的說法。試樣裡的 25 筆產品就是要看這個。

這一輪順手修了兩個看得見的例子：webshop 的標題會帶店名尾巴
（`Chipotle Hot Sauce - Hot Sauce World`），拿掉 variant 之後會留下 `, .` 這種殘渣。
兩個都改了，但**改的是明顯的那些**；剩下的只有人看得出來。

### 3.2 代表句選得好不好

一篇說「it's fine but the vinegar dominates」的評論，抽到 `"it's fine"`
一樣會通過 A25——引文的確出自原文，但它不是那篇的意思。

### 3.3 那張圖上到底印了什麼（v3 新增，也最危險）

標籤判讀**沒有原文可以比對**。A38 只驗「這筆判讀指得到一張真的存在的照片、
說得出模型與 prompt 版本」；A39 只驗「轉錄出的詞有沒有整批落在詞庫外」。

兩條都擋得住「憑空生出一整份成分表」，**兩條都擋不住「順序錯、數字錯、漏了一行」**。
而成分順序在美國標籤上是有意義的——它代表含量由多到少。
順序錯掉的那一列，在 `sauce_catalog` 上跟讀對的長得一模一樣。

## 4. 這一輪修掉的、原本看不見的三個錯

都不是測試抓到的，是檢查之間互相對不上才浮出來。

1. **辣度上界從一份視圖上看不到的舊成分算出來**。`heat.py` 收所有版本的成分事件，
   視圖只收當前版本，於是出現 `peppers` 是空的、`heat_ceiling_shu` 卻有數字的列——
   那個數字沒有任何一欄解釋得了它從哪來。A45 紅了才發現。
2. **Hot Ones 的「棒次」根本不是棒次**（K19）。抓到的是禮盒商品頁的規格條列，
   於是排序表上出現 `entity_id = "Custom gift box ready to share"`，有 rank 有信賴區間。
   是 evdb 的命名空間體檢先紅的，不是辣度那幾條檢查。
   修法是要求棒次每一行先對得回一個真的實體，對不上整對丟掉——
   目前 11 行全部對不上，所以 **`heat_rank` 完全來自品牌線內的順序，不是跨品牌的辣度**。
3. **三條靜態檢查抓到自己**。禁用字的清單就寫在 `sauce/acceptance.py` 裡，
   所以 `git grep` 每次都會命中那個檔。A19 另外還抓到白名單媒體自己的文章網址
   （`...-live-on-youtube/`）——那是一篇文章的標題，不是我們去抓了影音平台。
   pattern 收窄成「真的去抓 YouTube」（`youtube.com/watch`、字幕端點、下載器）。
   **一條長期紅著的檢查等於沒有檢查**，因為久了就沒有人看它。

## 5. 產物

| 檔 | 是什麼 |
|---|---|
| `sauce/out/2026-09-20/sauce_catalog-v1.csv` | 產品總表（7,186 列），**每次執行一個目錄，不覆蓋上一次** |
| `sauce/out/2026-09-20/sauce_buyable-v1.csv` | 買得到的（1,861 列） |
| `sauce/out/2026-09-20/sauce_reviews-v1.csv` | 評語表（目前 0 列） |
| `reports/sauce-copackers.md` | 代工聚類 50 組，每個成員都附證據 |
| `reports/sauce-label-oov.md` | 標籤判讀的詞庫外詞彙（目前空的，因為判讀是 0 筆） |
| `reports/sauce-coverage.md` | 召回率逐筆命中／未命中 |
| `reports/sauce-reviews.md` | 評論覆蓋率四張表（**沒有門檻**，用途是把「多數產品沒有評論」變成數字） |
| `ACCEPTANCE-sauce-corpus.md` | 驗收表 ＋ 每一條的原始輸出 |
| `DECISIONS-sauce-corpus.md` | 26 條決策（與 spec 字面不同的地方都在這裡） |
| `KNOWN_ISSUES-sauce-corpus.md` | 20 條限制，每條都寫「從哪裡看得出來」 |
| `RUNBOOK-sauce-refresh.md` | 半年重跑的逐步作業書（含 v3 的標籤與成分那一段） |

**標籤照片一張都不進版控**：它們留在 `.evdb/raw/`，是 CC BY-SA 3.0，
而且授權不涵蓋包裝上的商標與設計（D20）。

## 6. 下一輪最值得做的四件事

1. **把兩份待審檔審掉**——一次解開五條 FAIL 的唯一路徑。
2. **重跑時用「重放既有 snapshot」而不是重抓**（K20）。`event_id` 是內容的雜湊、
   `observed_at` 算在內容裡，所以重抓會換掉每一筆的 id，
   於是「舊事件不見了」與「這是同一件事的新版本」在 A7 眼裡長得一模一樣。
3. **標籤照片的覆蓋率上限不在我們手上**（K18）。OFF 上多數美國辣醬有正面照與營養照，
   成分照很少。要提高只有兩條路：補其他有背標照片的來源，
   或接受「多數列的成分來自 FDC 文字而不是實物標籤」——
   後者已經照實標成 `fdc`，不會冒充成 `label_photo`。
4. **v3 的規格全文沒有進版控**（K17）。A36–A49 的編號是照實作順序重建的，
   對規格時**動編號、不要動檢查**。
