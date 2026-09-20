# 決策紀錄 — us-hot-sauce-corpus

> 每一條都是「卡在什麼、假設了什麼、之後要怎麼回頭改」。
> 與 spec 字面不同的地方一律記在這裡，不默默改。

---

## D1 — 連結事件叫 `entity.linked`，不是 `sauce.entity.linked`

**卡點**：spec 的 event_type 清單寫 `sauce.entity.linked`，並註明「實際字串在 N1 對照
`domains/ma/match.py` 的慣例後定案，不一致就記一筆並**以本 spec 為準**」。

**實際**：evdb 核心的 `evdb/query.py:orphans()` 是**硬寫** `event_type = 'entity.linked'`
去找連結的。用 `sauce.entity.linked` 的話，每一筆觀察都會被算成孤兒，**A27 直接破功**——
而 A27 在 spec 的 Never-cut 清單上。

**決定**：跟核心慣例，用 `entity.linked`（與 `domains/ma` 一致）。領域前綴留在被連結的
觀察事件上（`sauce.*`）。這是兩條 spec 條文互相衝突時選了「不可砍的那一條」。

**回頭改**：哪天 evdb 讓 `orphans` 接受自訂連結事件名，這裡可以改回去；
改的方式是再寫一批連結事件，不是改舊的。

---

## D2 — 觀察與評論走 `src:` 命名空間，verdict 走 `review:`

**卡點**：A27 要求「`evdb orphans --domain sauce` 的孤兒數**等於**沒有任何 verdict
連到產品的 `sauce.review.published` 筆數」。核心的 orphans 是數**事件**，不是數實體。

**決定**：
- 產品／提及／評論的觀察事件 → `src:<source>:<key>`（核心看得到）。
- verdict 事件 → `review:<outlet_key>:<sha12>`（核心的 orphans 只看 `src:%`，所以 verdict
  不會被算成孤兒）。
- 產品與提及的觀察**一定連得上**（實體身分就是從名字折出來的），所以剩下唯一可能的孤兒
  就是連不上產品的評論——A27 的等式因此成立，而不是靠調整檢查器去湊。

---

## D3 — 圖狀態檔叫 `state/graph-state-sauce.json`

`state/graph-state.json` 已經被 `spec-scout-trip-page` 佔用而且是完成的紀錄。
覆寫它會毀掉別人的工作紀錄。spec 沒有預期這個檔名已經有人用。

---

## D4 — Python 用 3.14，不是 3.12

**卡點**：interview Q13 的預設是 3.12（與 evdb 一致）。

**實際**：這台機器上 uv 裝的 CPython 3.12 走 HTTPS 一律當掉
（`OPENSSL_Uplink(...) no OPENSSL_Applink`），系統 Python 3.14.3 正常。
這是一個**網路密集**的任務，沒有 HTTPS 就沒有這個專案。

**決定**：`.venv` 建在系統 Python 3.14.3 上。evdb 的下限是 `>=3.12`，3.14 滿足契約；
duckdb 1.5.5 / pyarrow 25 都有 3.14 的輪子，實測可用。

---

## D5 — 砍掉 wikidata 這個來源（robots 禁止）

`query.wikidata.org/robots.txt` 明文 `Disallow: /sparql`；`www.wikidata.org` 的 robots
擋掉 `/w/`（Action API）。NON_GOALS 寫死「不繞過 robots.txt」，所以這個來源**沒有合法路徑**。

程式留著（`sauce/sources/wikidata.py`），它會照實回報 `robots_denied`——
把「我們不能抓」與「那裡沒有資料」分開，比刪掉檔案更誠實。
名單層的缺口由 `wikipedia` 與 `awards` 補。

---

## D6 — OFF 改走官方全量匯出，不走 search API

`world.openfoodfacts.org/robots.txt` 明文 `Disallow: /api`。OFF 自己公開一份
`static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz`（1.3 GB，不在禁止清單上，
而且本來就是給人下載的）。代價是要下載並串流過濾整份檔案；好處是不必對同一個站發幾百次請求。

---

## D7 — 召回率清單的來源與 spec 不同，而且這件事會壓低它的證據力

**卡點**：A18 要求清單每列的 `origin` ∈ `{supabase_sauces, shelf_photo, reddit_walk}`，
而且「人工建立於 harvest 設定定稿之前」。

**實際**：
- `supabase_sauces`：buylist 的 `sauces` 表**目前是空的**（PostgREST 回 `[]`，唯讀確認）。
- `shelf_photo`：沒有照片可用。
- `reddit_walk`：Reddit Data API 需要憑證，本機沒有。

**決定**：清單改用第四種來源 `analyst_recall`——憑對美國市場的既有認知手寫 74 筆，
**在看任何一列抓取結果之前寫完**。抓取設定（來源、過濾規則）是在它之前寫的，
而且清單不是從抓取產出推導的，所以「規則沒有抄清單」這個性質仍然成立。

**但它比 spec 想要的弱，而且弱在可以講清楚的地方**：手寫的名單偏向有名的產品，
而有名的產品本來就最可能出現在 FDC 與 OFF 裡。**所以它量到的召回率會比真實的高。**
這件事必須寫進最終報告，不可以只報一個數字。

**回頭改**：`sauce/probe/export_from_buylist.py` 已經寫好而且驗過連得上（只是表是空的）。
buylist 的辣醬庫一有資料，或拿得到一張貨架照片，就換掉這份清單並重新量一次。

---

## D8 — 補一條 superseding ADR，不默默推翻既有的 Won't

`CLAUDE.md` 與 `context.md` §2.2 都寫著「**不做自動爬蟲**（由使用者主動貼連結）」。
這份任務整個就是自動爬蟲。已於 2026-09-19 向 Stanley 提出牴觸，取得授權：
補一條 superseding ADR，說明語料庫是**獨立資料層、不是 app 功能**，然後繼續。

---

## D9 — 產物檔名加 `-sauce-corpus` 後綴

spec 要 `ACCEPTANCE.md` / `DECISIONS.md` / `KNOWN_ISSUES.md`，但 Scout 根目錄已經有這三個檔
（屬於別的任務），而且既有慣例就是加後綴（`ACCEPTANCE-trip-page.md`、`DECISIONS-trip-page.md`）。
照既有慣例走，不覆寫別人的檔。

---

## D10 — 結構化來源走規則抽取，不燒模型

**卡點**：Q9 的預設是「產品標題解析走 llm-bridge 的便宜層」。

**實際**：FDC／OFF／Shopify 每一筆都**已經**帶著結構化的品牌欄位，品名就是標題扣掉品牌。
這是純規則、可機械驗證的工作。走模型的代價是幾千筆 × 20 RPM ≈ 數小時，外加一次
llm-bridge 的冷啟動人工審查；走規則是兩秒。Stanley 自己的分流標準第 5 節寫得很明白：
不需要模型判斷的事不要燒模型。

**決定**：
- 結構化來源 → `sauce/extract_rules.py`（版本 `rule:sauce-structured-1`）；
- 只有名字、沒有品牌欄位的提及，以及**評論正文 → 評語**，才走 llm-bridge。
- 兩種抽取器產生同一種事件（`sauce.extraction.parsed`），`extractor` 欄位寫清楚是誰抽的，
  `model_id` 記的是「這一筆是哪個版本產生的」——模型抽的是模型 id，規則抽的是規則版本。
  A10 第一層要的可追溯性兩邊都做得到；**把規則寫成假的模型 id 才是真的失去可追溯性。**

**代價**：規則抽出來的品名可讀性比模型差（FDC 的全大寫逗號分段）。所以 A11 的試樣
一定要人看，而且 N7 要附 20 筆隨機抽樣的原樣。

---

## D11 — 重建 `.evdb` 一次（規則版本改了，而且還沒有基準）

規則抽取器改版之後，舊的 `sauce.extraction.parsed` 事件是舊規則的產物；
append-only 不能刪，留著會雙重計數。此時**還沒有任何 A7 基準檔**，
所以砍掉 `.evdb` 從快照重放是乾淨的——快照與 MANIFEST 都在，重放得到同一份輸入。

**這件事只能在基準存在之前做一次。** 之後規則要改版，就是改 `names_version` /
`extractor` 版本、寫新的一批事件、產生新的視圖目錄，舊的不覆寫。

---

## D12 — 隨機抽樣抓到假陽性，所以把過濾規則升到 `sauce-filter-3` 並重建產品層

**怎麼發現的**：N7 要求附 20 筆隨機抽樣的原樣。抽出來之後看到
`Wawa Cranberry Sauce, For Junior Hot Hoagies`、`Pumpkin Noodles with Spicy Curry sauce`、
`Kandoo Spicy Marinade`——全部通過了所有結構檢查，**也全部不是辣醬**。

**原因**：第二版把 `hot`、`spicy`、`pepper` 當成辣度詞。`hot` ＋ `sauce` 這個組合
會命中任何名字裡同時有這兩個字的東西，而蔓越莓醬的標題剛好兩個都有。

**改法**（`sauce-filter-3`）：
- 辣度詞拿掉 `hot`／`spicy`／`pepper`——`hot sauce` 這個組合本來就在明講型清單裡；
- 醬體詞拿掉 `marinade`／`vinegar`／`juice`；
- 排除清單補上抽樣抓到的那幾類（蔓越莓、咖哩醬、三明治、飲料…）與 `black pepper`。

**代價**：產品層要重建。這是 D11 之後的第二次重建，而且這一次**只砍產品那一半**——
評論的 spool 與 `raw/` 的 1,827 篇正文留著（那是五十分鐘的抓取，而且過濾規則跟它們無關）。
A7 的基準檔跟著重寫，因為它記的是重建前那一批事件。

**這一條同時是 A11 存在的理由的實例**：機器驗不到「這一列是不是辣醬」，
是人看了 20 筆隨機抽樣才看出來的。

---

## D13 — 本機 commit，不 push（問了沒回應時的預設）

2026-09-19 收工前問過「先看 diff 還是直接 commit、要不要推上去」，120 秒內沒有回應，
工具要求以合理預設繼續。

**假設**：
- **commit 是安全的**——本機的 commit 可以改、可以丟，而且 dev-habits 寫著
  「session 結束不留未 commit 的東西」；
- **push 不是**——`origin` 是 `CHIAHSIN-tech/Scout`，一個**公開**而且不屬於 Stanley 的 repo。
  推上去就進 git 歷史，拿不回來。dev-habits 也寫著「要曝光給外界的動作先問我」。

**所以**：在 `feat/sauce-corpus`（從最新 `main` 切出來）本機 commit 一筆，**不 push**。
推不推、以及要不要開 PR，留給 Stanley 決定。

順帶做的一件防呆：本分支的 `.gitignore` 補上 `trips/` 與 `web/trips/`。
那兩個資料夾在工作樹裡是未追蹤狀態（從另一個分支留下來的），裡面有 booking_ref、
旅館地址與班機時刻，而這個 repo 是公開的。本次 commit 沒有包含它們，補規則是為了下一次。

---

## D14 — 加上「必須有地方在賣、有價錢」，與 spec 的 NON_GOALS 直接衝突

**Stanley 2026-09-19 的原話**：「必須要是有地方在賣，有價錢的 Hot Sauce」。

**衝突**：spec 的 NON_GOALS 寫著「**不追價格**、不追庫存、不追運費。可購性只到
『有沒有在美國賣』這個粒度」。這是使用者本人推翻自己寫的約束，照辦。

**做法——兩張表，不是砍掉一張**：
- `sauce_catalog`（`views:build`）＝**母體**：這個世界上有哪些辣醬。FDC 與 OFF 只有條碼、
  沒有貨架，但「這款存在過」對語料庫仍然有意義。
- `sauce_buyable`（`views:buyable`）＝**貨架**：現在去哪裡買、多少錢。
  沒有價格、沒有購買連結、幣別不是 USD、或價格是 0 的列一律不在這裡。

砍掉母體會讓「這款存不存在」這個問題**再也回答不了**，而那正是漏收最難察覺的那一面。

**兩個實作陷阱（兩個都會讓價格欄位安靜地錯）**：
1. **Shopify 會依請求來源的國家在地化價格。** 從台灣打過去，Heatonist 的 JANG 回
   `452.00`（TWD）；帶 `?currency=USD` 才是 `14.00`。兩個都「像價格」。
2. **WooCommerce 的價格是最小單位的整數字串**：`"3799"` 是 $37.99。
   直接當金額用會整整差一百倍。小數位數在同一個物件的 `currency_minor_unit` 裡。

**這一輪的數字**：母體 7,037 款，其中**真的買得到且有價錢的 1,763 款**（205 個品牌、
73 間店、中位數 $11.95、USD 100%）。A8 的 4,000 門檻是對母體量的；
對 `buyable` 這張表來說，1,763 距離 4,000 還很遠——要靠更多聚合站補。

---

## D15 — 改用「聚合站優先」找貨源，不再猜網域

**Stanley 2026-09-19 的原話**：「不需要排山倒海的搜，我覺得只要找到有限的 aggregator
就可以完整的找到來源……因為產品一定要推廣，總會在某些地方一起出現的」。

**實測證明這是對的**：用品牌名折網域去猜，命中率大約一成；而 `heathotsauce.com`
（55 個品牌／頁）與 `crafthotsauce.com`（42 個品牌／頁）這兩個聚合站，
**猜是猜不到的**——它們是搜出來的，一搜就有。

**做法**：`SEED_RETAILERS` 改成五個驗過的聚合站（每一個都確認 `/meta.json` 回
country=US、而且第一頁就有 ≥15 款辣醬），品牌直營店則由得獎名錄的公司網址推導。
名單刻意短。

---

## D16 — 評論抽取的三個修正（人審那 20 筆之前先修）

拿第一批待審檔給人看之前先自己看了一遍，發現那 20 筆不能拿來當 golden：

1. **20 筆全部來自同一家（ATK），而且 12 筆是食譜不是評測。**
   取樣是「前 20 筆」，而事件排序讓 ATK 全排在最前面。
   → `sauce/extract.py` 加 `_stratify()` 跨 outlet 輪流取。
2. **食譜頁上的 4.5 顆星是讀者評分**，那是 user rating，照規格根本不該進庫。
   → 加 `looks_like_review()`：`/recipes/`、`for Two`、`Slow-Cooker`、`Grilled` 這類排除；
     但「The Best Hot Sauce for Wings」這種評測型標題優先通過。
   → prompt 升到 v2，明寫「忽略讀者星等」。
3. **模型抽到 `pesto`、`chimichurri`、以及通用詞 `Hot Sauce`。**
   → prompt v2 明寫「只收辣椒類」「通用品類名不是產品」。

**沒有重抓那 1,827 篇**：過濾是在抽取端做的，原始正文留著不動——
語料庫的原始層本來就不該因為下游規則改了而被修剪。

---

## D17 — 我上一則的「FDC／OFF 不值得抓」是錯的，推翻自己的 D14 推論

**怎麼發現的**：Stanley 2026-09-19 要求 double check——挑一批「存在但標記買不到」的，
逐一去搜怎麼買。抽 14 筆，其中 6 筆根本不是辣醬（過濾器漏的），剩下 7 筆真辣醬裡
**6 筆現在就買得到**（Hot Jawn $12、Iguana En Fuego $5.99、Spontaneous Combustion $7.99、
Madame Gougousse、Crippling Limping、Texas Pete），只有 White's Valley 是澳洲品牌、
美國通路買不到——那一筆我標對了。

**錯在哪**：我量到的「只貢獻 19 列」不是「那些產品沒人賣」，是**我的抓取器只會講兩種 API**
（Shopify `/products.json`、Woo Store API）。實測搜尋結果裡的 13 家店：

- 抓得到的 4 家：chillychiles.com（124 款）、garlicshoppe.com（188 款）、
  halfmoonbaytrading.com（34 款）、allthejawns.com
- **抓不到的 9 家**：hotsauce.com、peppers.com、hotsauceworld.com、hotsaucemall.com、
  hotsauceplanet.com、mohotta.com、scorchedlizardsauces.com…——Magento／BigCommerce／自建車，
  而且**連 schema.org 的 Product JSON-LD 都沒有**（逐站驗過）

**所以**：FDC／OFF 的列不是死列，它們是**「有這個產品、但我的爬蟲沒去對的店」的線索**。
兩個缺口要分開處理：
1. **發現缺口**（店在、API 也通，只是沒找到網域）——多搜幾輪就好，成本低；
2. **平台缺口**（店不講我會的兩種語言）——要寫第三條路徑，而且沒有 JSON-LD 可以靠。

**教訓**：拿自己的覆蓋率去證明「那邊沒東西」是循環論證。要否證「買不到」，
只能一筆一筆去外面找，不能在自己的庫裡查。

---

## D18 — 「必須有價錢」放寬成「有貨架」

**Stanley 2026-09-20**：「不需要『必須有價錢』，這只是買得到的驗證而已，
如果某種原因『買得到但是沒價錢』成立的話，也是可以」。

`sauce_buyable` 的條件改成：有購買連結（真的商品頁）。價格有就存、沒有就留空——
**留空跟填 0 是兩件事**。缺貨也照收（Hot Jawn 實測就是上架、標價 $12、當下缺貨），
缺貨是 `in_stock` 那一欄的事。

結果：1,778 列有貨架，其中 1,252 列當下有貨。

---

## D19 — Q8 驗證：llm-bridge 的視覺支援（v3 的第一個閘）

**結論：可行，但要改 llm-bridge 的批次層。**

- `client.call_provider()` 把 `messages` 原樣送出 → **transport 層本來就支援** OpenAI 格式的
  多模態 content blocks。
- `batch._render_messages()` 只會產生純字串的 user message → **批次層不支援**。
- 實測同一個 NVIDIA 端點、同一把金鑰：
  - `nvidia/nemotron-3-super-120b-a12b`（目前釘住的文字模型）→ HTTP 400，明說收到多模態資料但沒有處理器
  - `meta/llama-3.2-11b-vision-instruct` → **可用**（1×1 PNG 測試回 "Pink."）
  - `meta/llama-3.2-90b-vision-instruct` → 逾時（可能要更長 timeout）

**所以 N4c 不用標 degraded**，但要在 llm-bridge 加一種「item 可以帶圖」的建法。
那是 Stanley 自己的 repo（不像 evdb 是唯讀），屬於合理的擴充，不是繞過。

## D20 — OFF 影像授權已確認（v3 BOUNDS 唯一一個「沒確認就停」的依賴）

Open Food Facts 的**產品照片**是 **CC BY-SA 3.0**（與資料庫的 ODbL 不同）：
要署名、衍生作品同條款分享。站方另有提醒：照片本身的授權不涵蓋包裝上的商標與設計，
那些可能另有第三方權利。

**本專案的用法相容**：照片只落地在 `<HOME>/raw/`（不進版控、不進 view、不重新散布），
只拿來給模型判讀成分表。`sauce.label.image` 的 payload 要帶 `licence_note` 記下這件事。

---

## D21 — FDC 的 `data_source` 不只 {GDSN, LI}

v3 的 A10 斷言 `data_source ∈ {GDSN, LI}`。實測 2026-04-30 那份批次檔：
`LI` 4,942 筆、`GDSN` 89 筆、**`Euromonitor` 1 筆**（fdc_id=2757070）。

**資料是對的，spec 的 enum 不完整。** 照實放寬檢查器的允許值並記在這裡，
而不是把那一列丟掉——丟掉會讓「FDC 只有兩種來源」這個錯誤的認知繼續留著，
而且母體會少一筆，事後從任何一張表上都看不出來。

## D22 — 標籤照片抓取要能中途斷、續得回來，其餘 harvester 不改

**問題**：`off_image` 跟別的 harvester 有一個量級上的差別——一張圖一次請求，
守禮讓速之下大約 6–20 秒一張。300 款 ×2.3 張就是幾小時。
而原本的 `harvest_all` 跟其他來源一樣，**事件全部累積在記憶體，最後一次交出去**。

第一次跑就踩到了：900 秒的上限砍下來時，硬碟上有 147 張圖，
**庫裡一筆事件都沒有**。圖存在，但沒有任何東西指得到它們——等於白抓。

**決定**：只給 `off_image` 加兩個參數，其他 harvester 一律不動。

- `sink`：每 25 筆就落盤一次。
- `skip_codes`：已經有事件的 GTIN 不重抓，所以斷在半路可以直接重跑。

**為什麼不套用到全部**：其他來源一次請求拿回幾百款（Shopify 的 `/products.json`、
FDC 的 zip、OFF 的全量 CSV），跑完只要幾分鐘，加了分批落盤只是多一層可能出錯的東西。
**這不是最佳化，是失敗路徑**——只有那個真的會斷在半路的步驟需要它。

## D23 — v3 的驗收項接在 A35 後面編號（A36–A49）

v3 的規格全文只存在於對話裡，壓縮之後救不回來（本機所有 transcript 都搜過）。
可選的做法有兩個：

1. 憑印象把 A1–A49 整套重編——**會動到 35 條已經對得上規格原文的編號**；
2. A1–A35 原封不動，v3 追加的十四條接在後面。

**選 2。** 理由是錯的代價不對稱：選 1 錯了，35 條驗過的事情門牌全錯，
而且錯得很像對的；選 2 錯了，只有新的十四條要改號，而且一眼看得出是哪十四條。

對規格時**動編號、不要動檢查**。詳見 `KNOWN_ISSUES-sauce-corpus.md` K17。

## D24 — 第三條抓取路徑只讀站方自己宣告的東西，讀不到就把「讀不到」記下來

D17 量到的平台缺口：用搜尋找到的 13 間店裡 9 間既不是 Shopify 也不是 Woo，
而且逐站驗過**連 schema.org 的 Product JSON-LD 都沒有**。

三個可選做法：

1. 寫解析器猜 HTML 裡哪一段是價錢；
2. 只讀站方自己宣告的結構化資料（JSON-LD → microdata → OpenGraph），讀不到就留空；
3. 不做。

**選 2。** 1 的問題不是準確率不夠，是**猜錯的那筆在表上跟查證過的長得一模一樣**——
一個猜出來的 `$12.99` 沒有任何下游檢查擋得住它。3 的問題是那 9 間店繼續等於不存在。

實測（`hotsauce.com` / `peppers.com` / `mohotta.com`，各看 12 頁）：

| 站 | sitemap 找到的商品頁 | 讀得懂 | 留下 |
|---|---|---|---|
| hotsauce.com | 0 | — | 0 |
| peppers.com | 6 | 0 | 0 |
| mohotta.com | 23 | 0 | 6 |

三個結果都不一樣，而且**三個都被記下來了**——這才是這條路徑真正的產出。
以前這三站的結果都是同一個：什麼都沒有。

**兩個設計上的後果**：

- `storefronts.csv` 多一欄 `product_urls`，平台認不出來但有商品頁的記成 `webshop`。
  「我們沒去過」與「那裡沒有辣醬」從此在資料上分得開。
- 商品頁本身就算 `retail_listing`（見 D18：有貨架就算數）。站方明講缺貨才降回 `unknown`。
  那一頁是從店自己的 sitemap 走進來的，它列在架上這件事不需要再被誰確認一次。

**沒有做的**：不猜價錢、不爬全站（只走 sitemap）、不碰要登入的頁。

## D25 — 視覺 prompt 進版到 v2：把「只准回 JSON」放在最前面，並在 user 那一輪再講一次

第一次冷啟動 20 筆裡 **6 筆解析失敗**（70% 通過）。失敗的樣子全都一樣：
模型回的是 markdown 散文——`**Transcription of Ingredients Label**`、
`The image shows a close-up of...`，內容其實讀對了，但不是 JSON。

這跟 nemotron 那次不是同一個病（那次是 thinking 吃掉 token 額度，回空字串）。
`meta/llama-3.2-11b-vision-instruct` 是 11B，指令遵從比 120B 弱很多，
而原本的 prompt 把 JSON 的要求寫在第三段、`user_template` 只有 `{input}`——
到了真正下筆的那一輪，模型手上沒有任何「要回 JSON」的提示。

**v2 改了三件事**：把「Output a single JSON object and nothing else」移到第一行、
加一句「Never describe the photograph」並附上一個完整的正確回覆範例、
`user_template` 在圖片之後再講一次「Reply with the JSON object only」。

**結果：20/20 解析成功，19 個相異轉錄**（兩筆同款不同 GTIN 本來就該一樣）。

**沒有改的**：驗證器一個字都沒動。**把通過率從 70% 拉到 100% 的辦法只有兩種——
改 prompt，或放寬驗證器。後者是把沒讀對的東西改判成讀對了。**

## D26 — 「0 筆判讀」不准印成 PASS

A38 與 A39 原本在庫裡一筆 `sauce.label.read` 都沒有時會**通過**：
沒有東西可以驗，所以沒有問題可以報。那份輸出跟真的驗過 300 筆長得一模一樣。

冷啟動閘的存在保證了這個狀態一定會發生（待審檔沒有人審之前，事件數就是 0），
所以這不是理論上的漏洞，是**每一輪的第一次執行都會踩到的那一格**。

兩條檢查都加上「0 筆直接判不過」，訊息寫明白：
「0 筆不是『全部合格』，是什麼都沒驗到」。
