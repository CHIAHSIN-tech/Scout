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
