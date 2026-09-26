# TASK: us-hot-sauce-corpus — 全美辣醬語料庫＋專業評論庫（Scout × evdb）

> Status: approved
> Repo: `C:\Users\luke_\Desktop\AI\Scout`
> 依賴 repo（唯讀）: `C:\Users\luke_\Desktop\AI\1-github\evdb`
> Date: 2026-09-19 · spec v2（v1 只有產品目錄；v2 加入專業評論庫）
> 語言規範：本文與程式註解用繁體中文；識別碼、欄位名、event_type、指令一律英文；
> **辣醬品牌名與產品名一律保留原文，任何情況都不翻譯、不加註中文**。

---

## OBJECTIVE

Scout 裡有一個可離線重跑的 evdb domain（`sauce`），一次執行就產出兩份互相連結的東西——
一份「在美國買得到的辣醬」產品總表，以及一份掛在這些產品上的**專業評論語料庫**（正文逐字保存、
評語可追溯到原句）——每一列都帶著出處與證據，半年手動重跑一次只會新增事件、不會改寫舊事件。

---

## WHY IT MATTERS

Scout 現在的辣醬庫（buylist 的 `sauces` 表）是兩個人手打的幾十筆評分，它回答「我吃過的這瓶好不好」，
但回答不了「我還沒吃過的有哪些」、更回答不了「懂的人怎麼評價它」。這份語料庫要同時補上這兩層：
**母體**（有哪些）與**判斷**（別人怎麼說，原句在哪）。

判斷對錯的成本是不對稱的，三個方向都要講明白：

- **漏收一款辣醬，事後完全看不出來。** 總表少了 Secret Aardvark，查詢端只會得到「查無此醬」，
  跟「這款不存在」長得一模一樣。所以 recall 優先——沿用 madb 的原則：**寧可多收一筆證據薄的，
  也不要漏掉一筆。** 缺 SHU、缺連結、缺分類都可以接受，缺整筆不行。
- **過度合併，事後同樣看不出來，而且無法還原。** 把兩個不同品牌的同名產品併成一列之後，
  總表會顯示「一列、兩個來源」，看起來比實際更有佐證。所以比對規則保守：**只在 GTIN 相同、
  或 (brand_key, product_key) 折疊後完全相同時才合併**，其餘一律各自成列並標 `duplicate_candidate`。
- **在收錄階段做摘要，等於把語料庫燒掉。** 評論庫的用途是「日後拿給 AI 分析」，而日後要問什麼現在不知道。
  一旦入庫時只存摘要或情緒分數，所有沒被那次摘要保留的訊號就永久消失，而且無從察覺。
  所以**正文逐字保存、原生分數逐字保存、評語必須是正文的子字串**——抽取層可以重跑、可以換模型、
  可以改規則版本，原始那層不動。這是 KeewanoDB 的核心紀律，不是可選項。

**為什麼只收專業評論。** 使用者評論（Reddit、零售站星等、marketplace）數量是專業評論的上百倍，
但三件事讓它們不適合作為這個語料庫的評論層：訊號密度低（多數只有一句話）、
來源正當性不一致（多半要繞過 ToS 才拿得到）、且清洗成本會吃掉整個專案。
專業評論——有掛名作者、有編輯流程、有方法論的那種——每一篇都帶著可比較的判準與可引用的原句，
這才是 AI 分析吃得下的東西。使用者內容在本專案只用來**發現名字**，永遠不會變成評論事件。

**結果是評論覆蓋率會很低，這是預期內的。** 目錄會有四千款以上，有專業評論的大概只有一到兩成。
這件事必須被量出來寫進報告，而不是讓人查了三次都查不到評語才自己發現。

半年一次的節奏決定了架構：這不是一條長期跑的 pipeline，而是**一份可以隔半年在乾淨環境重放的作業**。
所有來源快照要落地、所有規則要有版本、view 要能重算出同樣的雜湊。做不到這點，
半年後第二次執行會分不出「這筆是新出的辣醬」還是「我們這次抓法不一樣」。

---

## SUCCESS MEASURED BY

以下每一條都在 Scout repo 根目錄、`.venv` 啟用的狀態下執行。`<HOME>` 預設 `.evdb`。

### 基礎設施與契約

- **A1.** 乾淨 clone ＋ `pip install -r requirements-sauce.txt` 之後，`python -m pytest tests/sauce -q` exit 0。
- **A2.** `python -m sauce.load --home .evdb --register-only` 之後 `evdb --home .evdb validate --json` exit 0，
  且 `rules_violated` 為空陣列（命名空間與來源都登記過）。
- **A3.** evdb 核心沒有被汙染：
  `git -C ..\1-github\evdb grep -niE "sauce|scoville|capsaicin|pepper" -- evdb/` 回傳空。
- **A4.** evdb repo 的工作樹沒有被這份任務改動：`git -C ..\1-github\evdb status --porcelain` 回傳空。

### 收錄與不丟資料

- **A5.** 批次匯入不丟列：`python -m sauce.checks.conservation --home .evdb` exit 0——
  對每一份匯入檔驗證 `rows_in == events_written + rejects`，任何一份不相等即 exit 1 並印出檔名。
- **A6.** 冪等：同一份 snapshot 連跑兩次
  （`python -m sauce.load --home .evdb --snapshot state/snapshot-<id>` ×2），
  第二次的 `evdb --home .evdb stats --json` 事件總數與第一次完全相同。
- **A7.** 只追加：用第二份（較晚的）snapshot 重跑之後，
  `python -m sauce.checks.append_only --home .evdb --baseline state/events-<id>.txt` exit 0——
  第一份 snapshot 產生的每一個 `event_id` 仍在庫裡且內容未變，事件總數只增不減。
- **A8.** 產品規模：`python -m sauce.checks.scale --home .evdb --rules v1` exit 0——
  view 的 distinct product 列數 ≥ **4,000**、distinct `brand_key` ≥ **800**，任一未達即 exit 1。
- **A9.** **記憶體天花板**：`python -m sauce.checks.ceiling --home .evdb` exit 0——
  事件總數 ≤ **800,000**。超過即 exit 1 並印出各 source 的事件數，要求收緊該 source 的候選過濾規則。
  （`evdb derive` 會把全部事件讀進記憶體；這條是擋在它前面的保險絲，
  不是放寬 derive 的理由。見 KNOWN_ISSUES 裡給 evdb 的 streaming derive 提案。）

### 抽取品質（bulk output → 驗證器，不是描述）

- **A10.** 抽取不變式：`python -m sauce.validate --home .evdb` exit 0。三層依序檢查，任一層失敗即 exit 1 並印出規則名稱：
  1. schema：每個 `sauce.extraction.parsed` 事件的 payload 具備 `brand`、`product`、`model_id`、`prompt_version`；
     每個 `sauce.review.verdict` 具備 `review_id`、`sauce_entity_id`、`stance`、`quote`、`model_id`、`prompt_version`；
     **必須 100% 通過**。
  2. 任務不變式（機械可判）：折疊後的 `brand_key` 與 `product_key` 都是來源字串折疊後的子字串（模型不得憑空造字）；
     `heat_shu` 為空或正整數；`us_availability` ∈ `{retail_listing, brand_us_site, mention_only, discontinued, unknown}`；
     `stance` ∈ `{positive, mixed, negative, descriptive}`；`variant` 不得等於 `product`。
  3. 與人工標註集一致（**第二次執行起才啟用**，見 A11）：抽樣 ≥ 40 筆與 `sauce/pilot/sample-v1.jsonl` 的裁決比對，
     不一致率 > 10% 即 exit 1。
- **A11.** **第一次執行的交付物（不是關卡）**：`sauce/pilot/sample-v1.jsonl` 進版控，n ≥ 40
  （其中 ≥ 15 筆是 `sauce.review.verdict`），每筆帶 `model_id`、`prompt_version`、來源 `event_id`
  與人工裁決欄位（預設空白）。`python -m sauce.pilot check` exit 0 表示檔案存在、筆數足夠、欄位齊全。
  人看過並填入裁決之後，這個檔案就是 A10 第三層的標註集，第二次執行起 A10 三層全開。
- **A12.** bridge 節點不吃降級輸出：把 pinned model id 改成不存在的字串再跑
  `python -m sauce.extract --home .evdb --limit 5`，程序 exit 1 且 `evdb --home .evdb stats --json` 事件數不變（一筆都沒寫）。

### 身分與去重

- **A13.** 同一個 GTIN 不得出現在兩列：`python -m sauce.checks.dupes --home .evdb --rules v1` exit 0。
- **A14.** 不過度合併：`python -m sauce.checks.confusables --home .evdb --rules v1` exit 0——
  `fixtures/sauce/confusables.csv`（人工維護，≥ 15 組已知易混品項）的每一組在 view 中仍為各自獨立的列。
- **A15.** 每一列可追溯：`python -m sauce.checks.provenance --home .evdb --rules v1` exit 0——
  view 的每一列 `source_count ≥ 1`，且每一列的 `entity_id` 用
  `evdb --home .evdb timeline <entity_id> --json` 查得到至少一個 `source_url` 非空的事件。

### 可購性

- **A16.** `python -m sauce.checks.availability --home .evdb --rules v1` exit 0——
  每一列的 `us_availability` 值在 enum 內；值不是 `mention_only` 或 `unknown` 的列，
  `evidence_url` 必須非空。

### 召回率（產品層的核心關卡）

- **A17.** `python -m sauce.coverage --home .evdb --rules v1 --probe sauce/probe/probe-v1.csv` exit 0——
  probe 清單的 recall ≥ **0.90**，低於門檻 exit 1；不論通過與否都寫出 `reports/sauce-coverage.md`，
  逐筆列出命中與未命中，未命中要標明「哪一個來源階層本來應該收到它」。
- **A18.** probe 是 held-out 的，不是拿來訓練抓取規則的：
  `git grep -n "probe" -- sauce/ ":!sauce/coverage.py" ":!sauce/probe/"` 回傳空。
  `sauce/probe/probe-v1.csv` 進版控，n ≥ 60，每列帶 `name`、`brand`、`origin`
  （`supabase_sauces` / `shelf_photo` / `reddit_walk` 三種之一），且人工建立於 harvest 設定定稿之前。

### 評論庫：來源正當性

- **A19.** **零 YouTube**：
  `git grep -niE "youtube|youtu\.be|timedtext|yt[-_]?dlp|youtube[-_]transcript|pytube" -- sauce/ tests/sauce/ fixtures/sauce/ requirements-sauce.txt`
  回傳空。Hot Ones 的選醬名單不得經由 YouTube 取得（來源見資料契約表）。
- **A20.** **零 user review**：`python -m sauce.checks.no_ugc --home .evdb` exit 0——
  庫裡沒有任何 `sauce.review.*` 事件的 `source` 落在 UGC 來源集合
  `{reddit, retailer_widget, marketplace, forum_ugc}` 內。
  UGC 來源只准產生 `sauce.observation.mention`（只有名字，沒有評語）。
- **A21.** **outlet 白名單可稽核**：`python -m sauce.checks.outlets --home .evdb` exit 0——
  每個 `sauce.review.published` 事件的 `outlet` 都在 `fixtures/sauce/outlets.csv`；
  該檔每一列帶 `outlet`、`domain`、`admitted_on`、`admission_basis`、`evidence_url`，
  `admission_basis` ∈ `{masthead, named_author_series, methodology_page}`，
  且 `evidence_url` 非空。白名單筆數 ≥ **40**。
- **A22.** **不含 ASR、不含付費轉錄**：
  `git grep -niE "whisper|deepgram|assemblyai|speech[-_]to[-_]text|transcribe" -- sauce/ requirements-sauce.txt`
  回傳空。口說來源只取**發布者自己公開的逐字稿**（見資料契約表的 `podcast_transcript`）。

### 評論庫：資料保真（這一層是 AI 分析的命脈）

- **A23.** **正文逐字保存、不進 payload**：`python -m sauce.checks.bodies --home .evdb` exit 0——
  每個 `sauce.review.published` 事件的 `payload` 正規化後 ≤ **4 KB** 且 `raw_ref` 非空；
  `raw_ref` 指到的 `<HOME>/raw/` 檔案讀得回來，且其 sha256 等於 payload 裡記的 `body_sha256`。
- **A24.** **評語是原句，不是改寫**：`python -m sauce.checks.quotes --home .evdb` exit 0——
  每筆 `sauce.review.verdict` 的 `quote` 經過統一空白正規化後，是其 `review_id` 對應正文的子字串；
  `quote` 長度 ≤ 500 字元且 ≥ 20 字元。任何一筆不是子字串即 exit 1 並印出 `event_id`。
- **A25.** **原生分數不被改寫**：`python -m sauce.checks.scores --home .evdb` exit 0——
  有評分的 verdict 必須帶 `score_raw`（原文逐字，例如 `"8.5/10"`、`"★★★★☆"`、`"Best Overall"`）
  與 `score_scale`；`score_norm` 可為空，但若非空則必須能由 `(score_raw, score_scale)` 用
  `sauce/scores.py` 的規則重算出同值。**不得只留 `score_norm`。**
- **A26.** **孤兒不丟**：`python -m sauce.checks.orphans --home .evdb` exit 0——
  `evdb --home .evdb orphans --domain sauce --json` 回報的孤兒數，
  等於「沒有任何 verdict 連到任何 `sauce:` 實體」的 `sauce.review.published` 筆數。
  連不上產品的評論**留在庫裡**，不得因為連不上就不寫入。
- **A27.** **版控與輸出不外流長正文**：`python -m sauce.checks.export_safety` exit 0——
  `sauce/out/` 下任何 CSV 的任何欄位長度 ≤ **500** 字元；
  `git ls-files sauce/ | Select-String "raw/"` 回傳空（正文不進版控）。

### 評論庫：覆蓋率與可讀性

- **A28.** `python -m sauce.reviews_report --home .evdb --rules v1` exit 0，寫出 `reports/sauce-reviews.md`，
  內含四張表：每個 outlet 的評論筆數與時間跨度；被評到的產品數與佔目錄比例；
  每款被評產品的 verdict 數分佈；孤兒評論清單（標明為什麼連不上）。
  **這份報告不設通過門檻**——它的作用是把「多數產品沒有專業評論」這件事變成看得見的數字。
- **A29.** 評論規模：`python -m sauce.checks.review_scale --home .evdb` exit 0——
  `sauce.review.published` ≥ **1,200** 筆、`sauce.review.verdict` ≥ **3,000** 筆、
  被至少一筆 verdict 連到的 distinct 產品 ≥ **400**。任一未達即 exit 1。

### 可重放與輸出

- **A30.** view 可重算：連續跑兩次
  `evdb --home .evdb derive sauce.views:build --rules v1` 與
  `evdb --home .evdb derive sauce.views:reviews --rules v1`，
  四份 `manifest.json` 對應的 `rows_sha256` 兩兩相同。
- **A31.** 半年重跑的作業書可執行：從空的 `.evdb` 開始，照 `RUNBOOK-sauce-refresh.md` 逐步執行到底，
  每一步 exit 0，最後 A5–A30 全部重驗通過。作業書裡的每個指令都必須可直接複製貼上執行。

### 禮貌抓取與密鑰

- **A32.** 沒有繞過共用 session 的直接請求：
  `git grep -nE "requests\.(get|post)\(|httpx\.(get|post)\(|urlopen\(" -- sauce/ ":!sauce/net.py"` 回傳空。
  `python -m pytest tests/sauce/test_net.py -q` exit 0，涵蓋 robots.txt 遵守、每主機速率限制、
  非 2xx 不寫事件三項。
- **A33.** 沒有密鑰進版控：
  `git grep -nE "SUPABASE_KEY|service_role|eyJ[A-Za-z0-9_-]{20,}" -- sauce/ tests/sauce/ fixtures/sauce/` 回傳空。
  probe 匯出腳本對 Supabase 只讀：`git grep -nE "\.(insert|update|upsert|delete)\(" -- sauce/probe/` 回傳空。

### 主要路徑（真人實際會做的那件事）

- **A34.** `python -m sauce.query "Secret Aardvark"` 回傳**恰好一列**，
  含非空的 `brand`、`product`、`us_availability`，以及至少一個 URL 欄位非空；exit 0。
  加 `--reviews` 時，同一指令列出該產品所有 verdict 的
  `outlet`、`published_at`、`stance`、`score_raw`、`quote`、`url`，依 `published_at` 排序。
  查一個不存在的字串（`python -m sauce.query "zzzz-not-a-sauce"`）回傳 0 列且 exit 0（查無不是錯誤）。

---

## GRAPH

**Routing gate：多節點。** 觸發到四項——
(a) 跨執行層交接（`script` 抓取 → `bridge` 抽取 → `script` 比對）；
(b) 四條抓取工作流寫入路徑互不重疊，可平行；
(c) 驗證必須對抗式，產出者不能自己打分（A10/A14/A17/A24 全是它自己做的東西）；
(d) 單一來源失效不得汙染其他來源。

```text
                        ┌──────────────────────┐
                        │ N1 recon             │  layer: claude（唯讀）
                        │ 凍結事件契約          │
                        └──────────┬───────────┘
                        ┌──────────▼───────────┐
                        │ N2 scaffold          │  layer: claude
                        │ 套件/註冊表/net/白名單│
                        └──────────┬───────────┘
         ┌───────────┬─────────────┼─────────────┬───────────┐   parallel
         │           gate: state.nodes.N2.status == "done"    │
   ┌─────▼──────┐ ┌──▼─────────┐ ┌─▼──────────┐ ┌──▼─────────┐
   │ N3a bulk   │ │ N3b store  │ │ N3c roster │ │ N3d reviews│  layer: script
   │ FDC / OFF  │ │ Shopify/Woo│ │ awards/wiki│ │ outlet 白  │
   │ path: bulk │ │ path: sdk  │ │ /Hot Ones  │ │ 名單抓取    │
   └─────┬──────┘ └──┬─────────┘ └─┬──────────┘ └──┬─────────┘
         └───────────┴─────────────┼─────────────┴───────────┘
              join: 四者 status 皆為 done 或 degraded
                        ┌──────────▼───────────┐
                        │ N4 extract           │  layer: bridge
                        │ 4a 產品：標題→brand  │  degraded_ok: false
                        │ 4b 評論：正文→verdict│
                        └──────────┬───────────┘
                        ┌──────────▼───────────┐
                        │ N5 match + views     │  layer: script
                        │ 身分規則 v1          │
                        │ sauce_catalog        │
                        │ sauce_reviews        │
                        └──────────┬───────────┘
                        ┌──────────▼───────────┐
                        │ N6 verify            │  layer: claude（唯讀、對抗式）
                        │ A5–A30 逐條跑        │
                        └─────┬──────────┬─────┘
             FAIL ────────────┘          └──────── PASS
             （回 N4 或 N5，cap 2 次）              │
                                        ┌──────────▼───────────┐
                                        │ N7 report            │  layer: claude
                                        └──────────────────────┘
```

### 節點定義

每個節點在 `.claude/agents/sauce-<name>.md` 定義一次，跨 phase 重用，不得中途改寫定義。

| 節點 | layer | 可寫路徑 | 可寫 state key | 驗證指令 |
|---|---|---|---|---|
| N1 recon | claude | `docs/sauce-recon.md` | `nodes.N1`, `contract`, `decisions[]` | A2（N1 凍結的契約就是 A2 驗的那份註冊表；不得留 TBD） |
| N2 scaffold | claude | `sauce/**`, `tests/sauce/**`, `fixtures/sauce/**`, `requirements-sauce.txt` | `nodes.N2`, `decisions[]` | A1, A2, A18, A19, A21, A22, A32, A33 |
| N3a bulk | script | `state/snapshot-*/fdc/**`, `state/snapshot-*/off/**`, `<HOME>/spool/bulk-*` | `nodes.N3a`, `sources[]`, `known_issues[]` | A5 |
| N3b storefronts | script | `state/snapshot-*/shopify/**`, `<HOME>/spool/sdk-shopify*` | `nodes.N3b`, `sources[]`, `known_issues[]` | A32 |
| N3c rosters | script | `state/snapshot-*/roster/**`, `<HOME>/spool/sdk-roster*` | `nodes.N3c`, `sources[]`, `known_issues[]` | A19, A32 |
| N3d reviews | script | `state/snapshot-*/reviews/**`, `<HOME>/raw/**`, `<HOME>/spool/sdk-review*` | `nodes.N3d`, `sources[]`, `known_issues[]` | A20, A21, A23, A32 |
| N4 extract | bridge | `<HOME>/spool/extract-*`, `sauce/pilot/**` | `nodes.N4`, `decisions[]` | A10(1,2), A11, A12, A24, A25 |
| N5 match+views | script | `<HOME>/views/**`, `sauce/out/**` | `nodes.N5`, `decisions[]` | A13–A16, A26, A27, A30 |
| N6 verify | claude（唯讀） | `reports/**`, `KNOWN_ISSUES.md` | `nodes.N6`, `verdicts[]`, `known_issues[]` | A5–A30 逐條，附原始輸出 |
| N7 report | claude | `ACCEPTANCE.md`, `REQUEST_CHECK.md`, `DECISIONS.md`, `RUNBOOK-sauce-refresh.md` | `nodes.N7` | A31, A34 |

N6 唯讀：它不得修改 `sauce/**`。裁決是 PASS/FAIL 加 `file:line` 證據，寫進 `state.verdicts[]`；
修是 N4 或 N5 的事，N6 只重驗失敗的那一項。

### State

一份 `state/graph-state.json`，N1 建立，N7 最後一次寫入。每個節點動工前讀、完工後寫。
只追加或更新，不刪除。**state 只放路由需要的判斷值與指向產物的指標——路徑、id、雜湊、筆數；
絕不放產物本身**（不放評論正文、不放抓回來的 HTML、不放 view 的列）。

| key | kind | 寫入者 | 內容 |
|---|---|---|---|
| `run_id` | exclusive | N1 | 本次執行識別碼 |
| `snapshot_id` | exclusive | N1 | 來源快照目錄名，半年重跑時換新的 |
| `contract` | exclusive | N1 | 命名空間、source 清單、event_type 清單、entity_id 模板 |
| `nodes.<id>.status` | exclusive | 該節點自己 | `pending` / `running` / `done` / `degraded` / `failed` |
| `nodes.<id>.counts` | exclusive | 該節點自己 | 筆數摘要（rows_in / events / rejects） |
| `sources[]` | append-only | N3a–N3d | `{source, snapshot_path, fetched_at, records, sha256}` |
| `handoffs[]` | append-only | 全部 | `{from, to, task, inputs, acceptance_items_covered, status}`，status ∈ `sent`/`accepted`/`bounced` |
| `decisions[]` | append-only | 全部 | 與 `DECISIONS.md` 一對一 |
| `known_issues[]` | append-only | 全部 | 與 `KNOWN_ISSUES.md` 一對一 |
| `verdicts[]` | append-only | N6 | `{a_item, verdict, evidence}` |

`sources[]`、`handoffs[]`、`decisions[]`、`known_issues[]`、`verdicts[]` 是 append-only collection：
多個寫入者、以串接合併、順序不具意義，任何讀取它的程式必須容忍任意順序。
其餘為 exclusive：單一寫入者、後寫覆蓋；出現第二個寫入者是缺陷，不是要去解的競態。

### 跨層交接的 schema

圖上有五條邊跨執行層。跨層的一邊看不到另一邊的脈絡，所以交接一律是可序列化的清單加輸出 schema：

```text
N2  → N3*  JSON，state.contract（命名空間／source／event_type／entity_id 模板）
           + fixtures/sauce/storefronts.csv 與 fixtures/sauce/outlets.csv 的絕對路徑 + snapshot_id
N3abc → N4a  JSONL，每行 {event_id, source, raw_title, raw_brand, raw_url, snapshot_path}
N3d   → N4b  JSONL，每行 {event_id, review_id, outlet, url, published_at, body_path, body_sha256}
              （**只給正文的路徑，不給正文**——跨層交接不搬 body）
N4  → N5   JSONL，產品行 {event_id, brand, product, variant, heat_shu, us_availability,
                          evidence_url, model_id, prompt_version, confidence}
                  評論行 {event_id, review_id, sauce_name_raw, stance, score_raw, score_scale,
                          quote, quote_offset, model_id, prompt_version}
N5  → N6   JSON，{catalog_manifest_path, reviews_manifest_path, rows, rows_sha256,
                  a_items: ["A5",…,"A30"]}
```

N4 收到交接後對照自己的定義檢查，設 `handoffs[].status`；服務不了的退回 `bounced` 並附理由，
寫進 `DECISIONS.md`，不得默默改寫語意。

---

## 資料契約（N1 凍結，其餘節點不得改）

### 命名空間

```text
sauce    一款產品（不分瓶容量）   sauce:<brand_key>|<product_key>
brand    一個品牌/製造商           brand:<brand_key>
gtin     GTIN-14（含 UPC 補零）    gtin:<14 位數字>
review   一篇專業評論              review:<outlet_key>:<url_sha1_12>
outlet   一個評論發布單位          outlet:<outlet_key>
src      核心預設：來源本地識別碼  src:<source>:<key>
```

`brand_key` / `product_key` 的折疊規則（`sauce/names.py`，版本 `sauce-names-1`）：
小寫、去除商標符號與標點、合併空白、移除尾綴詞（`hot sauce`, `sauce`, `LLC`, `Inc`, `Co`, `Foods`, `Company`）。
折疊規則有版本；版本變了就是新的 view 目錄，舊的不覆寫。

### 來源

**產品層（決定母體）**

| source | 階層 | 取得方式 | 為什麼收它 |
|---|---|---|---|
| `fdc` | 1 母體 | USDA FoodData Central Branded Foods 批次檔（CSV，免金鑰） | 帶 GTIN 的品牌食品母體，身分骨幹 |
| `off` | 1 母體 | Open Food Facts 美國產品匯出 | 補 FDC 漏掉的進口與小廠，同樣帶 barcode |
| `shopify` | 2 長尾 | 種子網域清單的 `/products.json`（公開端點，分頁） | 獨立辣醬品牌與專賣零售幾乎都在 Shopify，長尾主力 |
| `woo` | 2 長尾 | WooCommerce Store API `?rest_route=/wc/store/products` | 同上，非 Shopify 的那部分 |
| `wikidata` | 3 名單 | SPARQL：hot sauce 類別的品項與品牌 | 結構化、可列舉、跨語言別名 |
| `wikipedia` | 3 名單 | `List of hot sauces` 等條目 | 老牌與歷史品項，零售端已下架的仍在 |
| `awards` | 3 名單 | Scovie Awards、World Hot Sauce Awards、NYC Hot Sauce Expo 得獎名單 | 逐年逐項列舉，涵蓋沒有電商的小廠 |
| `hotones` | 3 名單 | **不經 YouTube。** 名單來自 Heatonist 的各季 season pack 商品頁（Shopify 目錄）＋ 編輯型報導／wiki 條目 | 每季 10 款的名單本身就是產品 metadata；新一集上了就會出現在這兩個地方 |
| `reddit` | 4 提及 | Reddit 官方 Data API（OAuth） | **只用來發現名字**，見下方限制 |

**評論層（決定判斷）**

| source | 取得方式 | 限制 |
|---|---|---|
| `outlet_web` | `fixtures/sauce/outlets.csv` 白名單內各站的評論文章（robots.txt 遵守、每主機速率限制） | 只收白名單內的 outlet |
| `podcast_transcript` | Podcast RSS 中**發布者自己公開的逐字稿**（`<podcast:transcript>` 標籤或節目頁上的 transcript 連結） | 不轉錄、不 ASR、不抓字幕 |
| `print_archive` | 有公開線上版的雜誌／報紙評論 | 同白名單規則 |

**outlet 白名單的准入規則**（`fixtures/sauce/outlets.csv`，A21 驗）——一個 outlet 只在滿足下列其一時准入，
且必須附上證據 URL：

1. `masthead`——站上有可查的編輯團隊／編輯政策頁；
2. `named_author_series`——同一位掛名作者在該站有 ≥ 10 篇、跨 ≥ 2 年的辣醬／調味料評論；
3. `methodology_page`——該站公開說明其評測方法（怎麼試、誰試、幾款、是否盲測）。

**准入是人做的判斷，但判斷結果是資料。** 白名單進版控、每列有 `admitted_on` 與 `evidence_url`，
半年重跑時可以檢討；抓取端只認白名單，不在執行時即時判斷「這站專不專業」。

**UGC 的角色，講死：** `reddit` 與任何零售站的評論外掛（Judge.me / Yotpo / Loox 等）
**只准產生 `sauce.observation.mention`**——只有「有人提到這個名字」，沒有評語、沒有分數、沒有正文。
它們存在的唯一理由是補產品召回率（有些新品只有 Reddit 講過）。A20 把這件事變成擋得住的斷言。

### event_type

```text
sauce.observation.product       一筆目錄型來源記錄（FDC/OFF/Shopify/Woo）
sauce.observation.mention       一次提及，只有名字（wikidata/wikipedia/awards/hotones/reddit）
sauce.observation.availability  一次在美國零售/品牌官網看到上架
sauce.observation.lineup        Hot Ones 某季某集的選醬名單（含第幾棒、標榜 SHU）
sauce.review.published          一篇專業評論（payload 只放 metadata，正文在 raw store）
sauce.review.verdict            該評論對某一款醬的評語（一篇多款就多筆；帶 quote 與 score_raw）
sauce.extraction.parsed         模型對某筆觀察的解析結果（帶 model_id + prompt_version）
sauce.entity.linked             比對器把觀察/評論連到 sauce/brand 實體
                                （related 角色：product, brand, observation, review）
```

`sauce.entity.linked` 的實際字串在 N1 對照 `1-github/evdb/domains/ma/match.py` 的 `LINK_EVENT` 慣例後定案，
不一致就在 `DECISIONS.md` 記一筆並以本 spec 為準。

### `sauce.review.published` 的 payload（≤ 4 KB，A23 驗）

```text
review_id, outlet, outlet_key, url, title, authors[], published_at, updated_at,
language, modality (text|spoken_transcript), article_kind (single|roundup|ranking|guide),
items_reviewed_count, disclosure (samples_provided|purchased|undisclosed|affiliate),
body_sha256, body_bytes, body_chars, paywalled (bool), retrieved_at
```

正文本身經 `Recorder.store_raw()` 寫進 `<HOME>/raw/`，`raw_ref` 指過去。
`disclosure` 這欄看起來瑣碎，但它是日後任何「這些評價可信嗎」的分析唯一的抓手——
沒有它，收了錢的開箱跟自費試吃在庫裡長得一模一樣。

### `sauce.review.verdict` 的 payload

```text
review_id, sauce_entity_id, sauce_name_raw,        # 原文怎麼稱呼它，逐字
stance (positive|mixed|negative|descriptive),
score_raw, score_scale, score_norm,                # A25：score_raw 逐字，score_norm 可空
rank_in_article, of_total,                         # 排行文章用：第 3 名／共 12 款
quote, quote_offset, quote_len,                    # A24：quote 必須是正文子字串
descriptors[],                                     # 原文用過的風味詞，逐字，不正規化
model_id, prompt_version
```

`descriptors[]` 逐字保留不正規化，是刻意的：「smoky」「campfire」「burnt rubber」在不同人筆下
可能指同一件事也可能不是，現在就併成同義詞等於替日後的分析先做了一個沒人驗證過的決定。

### 比對規則 `sauce-match-1`（保守）

只在下列任一條件成立時把兩筆觀察合併成同一個 `sauce:` 實體：
1. 兩筆的 GTIN-14 相同；或
2. 折疊後的 `brand_key` 與 `product_key` 兩者都完全相同。

其餘一律各自成列。`product_key` 相同但 `brand_key` 不同、或編輯距離 ≤ 2 的，
在 view 上標 `duplicate_candidate = true` 並把對造的 `entity_id` 寫進 `duplicate_of_candidates`，
**不合併**。

**評論連到產品用不同的規則 `sauce-reviewlink-1`，而且更保守：**
評論裡的 `sauce_name_raw` 必須折疊後與某個 `sauce:` 實體的 `product_key` 完全相同、
且 `brand_key` 相同或評論正文中出現該品牌名，才建立 `sauce.entity.linked`。
連不上的**保留為孤兒**（A26），不猜、不模糊比對——猜錯的代價是把 A 的評價掛到 B 身上，
而那在庫裡看起來和正確連結一模一樣。

### views

**`sauce_catalog`（`sauce/views.py:build`，rules `v1`）**

```text
entity_id, brand_key, brand, product_key, product, variant,
gtin, heat_shu, heat_basis, us_availability, evidence_url,
source_count, sources, tiers, first_observed_at, last_observed_at,
duplicate_candidate, duplicate_of_candidates, corroboration,
hotones_seasons,                      # 出現在哪幾季，"S24|S26" 形式
review_count, review_outlets, review_stance_mix,   # 只有計數與摘要，正文不進 view
names_version, matcher_version, prompt_version, rules_version
```

**`sauce_reviews`（`sauce/views.py:reviews`，rules `v1`）**——一列一筆 verdict

```text
verdict_id, review_id, outlet, url, published_at, authors, article_kind, disclosure,
sauce_entity_id, sauce_name_raw, brand, product,
stance, score_raw, score_scale, score_norm, rank_in_article, of_total,
quote, descriptors, modality, language,
link_rule_version, prompt_version, rules_version
```

`quote` 是 view 裡唯一的長文字欄位，上限 500 字元（A27）。要看全文就用 `review_id`
到 raw store 取——**view 是索引，不是語料本身**。

`corroboration` 沿用 madb 的判準精神：**只有一個來源的產品不代表錯，但無法判斷是真的**——
把這件事寫成欄位，不要在收錄階段替使用者決定。

---

## INTERVIEW（一批問完，每題都有預設；沒回答就走預設）

- **Q1.** evdb 怎麼裝進 Scout？ — 預設：`requirements-sauce.txt` 寫一行 `-e ../1-github/evdb`，不 vendor、不 fork、不改 evdb。
- **Q2.** view 怎麼註冊？ — 預設：用 `module:function` 形式
  `evdb --home .evdb derive sauce.views:build --rules v1`，**不**替 Scout 加 `pyproject.toml`。
- **Q3.** `.evdb` 放哪、什麼進版控？ — 預設：`Scout/.evdb/` 進 `.gitignore`（含 `raw/`，A27）；
  兩份 view 各另存一份 `sauce/out/sauce_catalog-v1.csv`、`sauce/out/sauce_reviews-v1.csv` 進版控；
  `state/snapshot-*/` 進 `.gitignore`，但 `state/snapshot-*/MANIFEST.json` 進版控。
- **Q4.** 產品規模門檻？ — 預設：≥ 4,000 products、≥ 800 brands（A8）。
- **Q5.** 評論規模門檻？ — 預設：≥ 1,200 篇、≥ 3,000 筆 verdict、≥ 400 款被評到（A29）；
  outlet 白名單 ≥ 40（A21）。
- **Q6.** probe 大小與 recall 門檻？ — 預設：n ≥ 60、recall ≥ 0.90（A17、A18）。
- **Q7.** pilot 樣本大小？ — 預設：n ≥ 40，其中 ≥ 15 筆是 verdict（A11）。
- **Q8.** storefront 種子網域怎麼來、要幾個？ — 預設：≥ 150 個網域，由名單階層自動抽出品牌官網再加人工補，
  存 `fixtures/sauce/storefronts.csv` 並進版控。
- **Q9.** 抽取用哪一層模型？ — 預設：llm-bridge 的便宜層跑產品標題解析；
  **評論 verdict 抽取用判斷力較強的那一層**（要判斷 stance 與挑出代表句）；
  pinned model id 寫進 `prompt_version`；兩者皆 `degraded_ok: false`（A12）。
- **Q10.** 半年更新怎麼觸發？ — 預設：純手動 `python -m sauce.load --home .evdb --refresh`，不排程。
- **Q11.** Scoville 怎麼處理？ — 預設：只記 claimed SHU 與它的出處（`heat_basis`），不做真值裁決。
- **Q12.** 要不要碰 Supabase？ — 預設：**不寫**。只在建 probe 時唯讀匯出現有 `sauces` 表（A33）。
- **Q13.** Python 版本？ — 預設：3.12（與 evdb 一致）。
- **Q14.** 非英文的專業評論收不收？ — 預設：**收**，`language` 欄位記原文語言，
  `quote` 保留原文不翻譯；抽取 prompt 要能處理多語。

---

## BOUNDS

**Loop-back cap：2。** N6 FAIL → N4 或 N5 修 → N6 只重驗失敗項。第 2 次仍 FAIL 就往下走，
寫進 `KNOWN_ISSUES.md`，並把對應的 A 項在最終報告標 FAIL——**整個 run 即報告為失敗**。

**Scope-cut order（先砍哪個）：**
`print_archive` → `podcast_transcript` → `reddit` → `woo` → `wikipedia`
砍掉的來源要在 `DECISIONS.md` 記一筆，並在 `reports/sauce-coverage.md` 或
`reports/sauce-reviews.md` 標明它本來要蓋的缺口。

**Never cut（砍這些等於改 spec，必須先改 A 表並記進 `DECISIONS.md`）：**
`fdc` 與 `off` 的母體骨幹、`shopify` 長尾、`awards` 與 `hotones` 名單、`outlet_web` 評論層、
A10 的驗證器、A17 的 probe recall 關卡、A6/A7 的冪等與只追加、A14 的不過度合併、
**A23–A27 的評論保真五條**（正文、原句、原生分數、孤兒、不外流）。

**外部依賴（stub 起來，不得假裝可用）：**

| 項目 | 前置時間 | 做法 |
|---|---|---|
| FDC 批次檔下載（數百 MB） | 一次數十分鐘 | 下載到 `state/snapshot-*/fdc/`，斷線可續；**先在本機過濾成候選列再 import**，不整份進庫 |
| Reddit Data API OAuth | 數分鐘（自助註冊） | 介面 `sauce/sources/reddit.py:fetch()`；沒有憑證時回傳空並把節點標 `degraded`，不得改用網頁抓取 |
| Supabase 專案可能被自動暫停 | 人工在後台喚醒 | 只影響 probe 建立；暫停時用已匯出的 `probe-v1.csv` 繼續 |
| 目標站台 robots.txt 禁止 | 立即 | 記進 `KNOWN_ISSUES.md` 並跳過該網域，**不得改 user-agent 或繞過** |
| outlet 付費牆 | 立即 | `paywalled: true`，只存可公開取得的部分；**不得用任何方式繞過付費牆** |

**規模上限（A9）：** `evdb derive` 會把全部事件讀進記憶體。事件總數超過 800,000 時
N3a 必須收緊 FDC 的候選過濾規則（規則寫進 `sauce/sources/fdc.py`，有版本），
而不是放寬 `derive`。**給 evdb 的 streaming derive 提案寫進 `KNOWN_ISSUES.md`
（`Store.rows()` 已經是現成的 SQL 入口，缺的是 derive 那層的串流版本與同樣的 manifest 契約），
但本任務不實作、不繞過、不在 Scout 這邊複製一份 derive。**

---

## EXECUTION RULES

1. **只問一次。** 問題在開工前一批問完，每題附預設值；沒回答就走預設。開工之後遇到卡點不停下來問——
   寫成 `DECISIONS.md` 一筆（卡在什麼、假設了什麼、怎麼回頭改），然後繼續。
2. **驗證器說了算，不看感覺。** 節點的驗證指令 exit 0 才算完成。質性的疑慮寫成
   `KNOWN_ISSUES.md` 的建議事項；**只有指令可判定的發現才可以把工作退回**。
   大量產出（A10、A24 這類每筆一樣規則產生的東西）一律由可執行的檢查器判定，
   同一個檢查器先跑 20 筆當試樣、再跑全量當驗收——不准用文字描述「好的輸出長什麼樣」來代替。
3. **審查節點唯讀且抱持懷疑。** N6 不得修改 `sauce/**`。裁決是 PASS/FAIL 加 `file:line` 證據並寫進 state。
   產出者負責修，審查者只重驗失敗的那一塊。
4. **失敗隔離。** 重試在節點內部完成。下游節點以上游的 `status: done`（或 `degraded`，若該節點允許）為門檻，
   不得讀取 `running` 節點的產物。
5. **上限先講清楚。** loop-back 上限 2；scope-cut 順序與不可砍清單如上；
   外部依賴一律以介面 stub 並標示前置時間，不得偽造、不得回報成「已經可用」。
6. **產物。** `ACCEPTANCE.md`（A1–A34 逐條 PASS/FAIL 加原始指令輸出）、
   `state/graph-state.json`、`DECISIONS.md`、`KNOWN_ISSUES.md`、
   `RUNBOOK-sauce-refresh.md`、`reports/sauce-coverage.md`、`reports/sauce-reviews.md`，
   以及最終報告——第一節就是驗收 PASS/FAIL 表與原始輸出。
   **任何一項 FAIL，整個 run 報告為失敗**，不論產出多少列。
7. **先偵察再動工。** 動手前先把 Scout 讀過一遍（`CLAUDE.md`、`context.md`、
   `buylist/spec-buylist-sauce-tab.md`、`buylist/buylist-schema.sql`、`specs/README.md`）
   與 evdb 讀過一遍（`README.md`、`evdb/schema.py`、`evdb/registry.py`、`evdb/bulk/importer.py`、
   `evdb/sdk/__init__.py`、`domains/ma/` 全部）。共用型別只放一處；同一個型別定義兩次是缺陷。
   **Scout 的 `CLAUDE.md` 要求每次 session 先讀 `context.md` 並檢查是否牴觸既有 ADR——照辦；
   本 spec 與既有 ADR 牴觸時先提出來，不要默默 supersede。**
8. **收尾報告對照的是原始請求，不是這份 spec。** 最後產出 `REQUEST_CHECK.md`，
   基準是 Stanley 寫的原話——
   「comprehensive… from all sources」、「manually, maybe once every half a year」、
   「build it into scout」、「use the database logic of madb (keenodb)」、
   「all the reviews every written/spoken regarding each product」、
   「comprehensive enough for future ai analysis」、
   以及後續限縮：「我不要抓任何 youtube 評論，zero」、「只用現成字幕，不花錢」、
   「只收就是專業評論，不是 user review」——**不是** A 表。
   三份清單，每行標明在哪裡驗的：**有要求且已交付** / **有要求但缺席**（附原因）/
   **沒要求但做了**。請求裡有、而 A 表沒有任何一條對應的約束，即使 A 表全過也要進第二份清單。
   只寫分歧；一致的地方一行帶過。每個發現都要指到檔案與行號。

---

## NON-GOALS

明確不做。做了就是超出範圍，要退回。

- **不碰 YouTube，一行都不碰**（A19）。不抓留言、不抓字幕、不抓逐字稿、不用 `youtube-transcript-api`、
  不用 `yt-dlp`、不呼叫 YouTube Data API。Hot Ones 的選醬名單從 Heatonist 商品頁與編輯型報導取得。
- **不收 user review**（A20）。Reddit、零售站評論外掛（Judge.me / Yotpo / Loox）、
  Amazon 與任何 marketplace 的評價，一律不得成為 `sauce.review.*` 事件。
  Reddit 只用來發現名字，產生 `sauce.observation.mention`。
- **不做語音轉文字**（A22）。不跑 Whisper、不呼叫任何付費 ASR、不從影音檔產生逐字稿。
  口說內容只在**發布者自己公開逐字稿**時才收。
- **不繞過付費牆、不繞過 robots.txt、不偽裝 user-agent、不碰需要登入的站台。**
- **不在收錄階段做摘要或情緒分數取代原文。** `score_norm` 只能是 `score_raw` 的附加欄位，不得取代它。
- **不正規化風味詞。** `descriptors[]` 逐字存。
- **不模糊比對評論與產品。** 連不上就當孤兒（A26）。
- **不動 buylist 的 UI 與 `sauces` 表。** 頂層 tab、評分、Realtime、`index.html` 一行都不改。
  這份語料庫怎麼接進 UI 是下一份 spec 的事。
- **不寫任何東西進 Supabase。** 只在建 probe 時唯讀匯出。
- **不追價格、不追庫存、不追運費。** 可購性只到「有沒有在美國賣」這個粒度。
- **不做 SKU 層。** 一款產品一列，瓶身容量與包裝規格放 payload。
- **不裁決 Scoville 真值。** 只記 claimed 值與出處。
- **不做持續更新、不排程、不跑背景服務、不做 CDC。** 半年一次，手動觸發。
- **不收只在美國以外買得到的辣醬。** 但「來源說在美國賣過、現在查不到」要收，標 `discontinued`。
- **不處理圖片。** 不下載、不存、不做 OCR。
- **不改 evdb**（A3、A4）。streaming derive 的需求記進 `KNOWN_ISSUES.md` 交給 evdb 自己的 spec；
  **也不准在 Scout 這邊自己複製一份 derive 來繞過**。
- **不建 Vue/React 前端、不開新 repo、不新增部署目標。**

---

## CHECKLIST ANSWERED

**1. 沒寫這份程式的人能不能逐條驗 A 項？**
能。A1–A34 每一條都是一行可貼上執行的指令，判定依據是 exit code 或 `git grep` 是否為空。
唯一需要人的是 A11 的裁決欄位填寫（第一次執行的交付物）、A21 白名單的准入判斷（結果進版控，可事後稽核）
與 A31 作業書的逐步執行。其餘不需要讀過任何程式碼。

**2. 有沒有東西宣稱可用、其實卡在外部核准？**
有五項，全部已移到 BOUNDS 的 stub 表並標了前置時間：FDC 批次檔下載、Reddit OAuth、
Supabase 自動暫停、robots.txt 禁止、outlet 付費牆。五項都不擋主線：
前三項降級後節點標 `degraded` 仍可往下走，後兩項直接跳過並記 `KNOWN_ISSUES.md`。
**五項都不得偽造資料充數，也不得用繞過的方式「解決」。**

**3. scope-cut 順序有沒有保護 A 表？**
有。可砍的五個來源（print_archive / podcast_transcript / reddit / woo / wikipedia）
砍掉會壓低 A17 的 recall 與 A29 的評論規模，但不會讓任何一條 A 項失去驗證對象。
A8/A17 由不可砍的 `fdc`/`off`/`shopify`/`awards`/`hotones` 撐住；
A29 由不可砍的 `outlet_web` 撐住。
**砍掉任何一條 A 項是 spec 修訂，要寫進 `DECISIONS.md` 並在最終報告點名，不准默默拿掉。**

**4. 來源系統（evdb）的表面有沒有逐項歸位？**

| evdb 表面 | 歸類 |
|---|---|
| `evdb/schema.py` Event 契約、content hash、append-only | 範圍內（整份建立在上面） |
| `evdb/registry.py` 命名空間／來源白名單 | 範圍內（A2） |
| `evdb/bulk/` CSV 匯入 + rejects | 範圍內（N3a、A5） |
| `evdb/sdk/` 行程內 Recorder、`store_raw()` | 範圍內（N3b–N3d；評論正文靠 `store_raw()` 落地，A23） |
| `evdb/ingest.py`、`evdb/spool.py` | 範圍內 |
| `evdb/derive.py` 版本化視圖 | 範圍內（N5、A30），**但有記憶體天花板，見 A9** |
| `evdb/validate.py` 全庫體檢 | 範圍內（A2） |
| `evdb/query.py` `timeline` / `orphans` / compact | 範圍內（A15 用 timeline、A26 用 orphans） |
| `evdb/store.py` `Store.rows(sql)` | **延後**——它是 streaming derive 的現成入口，但本任務不走它（不複製 derive） |
| `evdb/export.py` Parquet 全庫匯出 | **延後**——`derive` 已同時產 CSV 與 Parquet，全庫匯出目前沒有消費者 |
| `evdb/cdc/` | **Non-goal**——半年一次的手動作業沒有 CDC 的對象 |
| `evdb/home.py` 的 `EVDB_ENABLED` hook 開關 | **Non-goal**——那是舊 madb 的 hook 機制，Scout 沒有等價的舊系統 |
| `domains/ma/` 全部 | **參考樣板，不重用程式碼**。目錄骨架、pilot／coverage 的做法照抄，M&A 的規則不照抄 |
| evdb repo 本身 | **唯讀**（A3、A4） |
| Scout 的 `sauces` 表與 buylist UI | **Non-goal**，唯一例外是 probe 的唯讀匯出 |
| Scout 的 `specs/README.md` 索引表 | **範圍內**——完工後補一列，Status 依它的規矩標，AC 框不准自己勾 |

**5. 沒讀過 Graph Protocol 的人能不能執行這份 spec？**
能。loop-back 上限、驗證器說了算、審查節點唯讀、必須產出哪些檔案、state 的 key 與合併規則、
跨層交接的 schema，全部寫在本文裡，沒有一條是指向外部文件的引用。

**6. 讀寫個人或租戶資料的面，有沒有「憑證錯了會被拒絕」的 A 項？**
這份任務有兩個這種面：
- probe 建立時讀 Scout 的 Supabase `sauces` 表——A33 斷言密鑰不得進版控，
  且 probe 腳本對 Supabase 沒有任何 `insert`/`update`/`upsert`/`delete` 路徑。
- 評論正文是第三方的著作——A27 斷言正文不進版控、view 的任何欄位 ≤ 500 字元，
  也就是**這個語料庫的任何一份可分享產物都不會夾帶全文**。這不是存取權杖問題，
  但它是同一類的東西：一個「全部功能都正常」也看不出來的外流面。

其餘資料全部來自公開端點，沒有使用者帳號、沒有租戶邊界。
**額外提醒：現行 `sauces` 表的 RLS 對 anon 全開（`buylist-schema.sql:73-76`）——
這是既有狀態，本任務不修、也不依賴它以外的權限；若要收緊，另開 spec。**

**7. 全部 A 項都過了，系統還是有可能難用嗎？走一次真人路徑，指出哪一步沒有斷言蓋到。**
走一次：「朋友說 Secret Aardvark 很好吃」→ 查總表 → 看懂的人怎麼講 → 決定買不買。

A34 蓋住查詢、「恰好一列」與 `--reviews` 的輸出。原本有三個缺口，各補了一條：
- **列數達標但全是垃圾。** 由 A13（GTIN 不重複）＋A14（不過度合併）＋A15（每列可追溯）夾住。
- **查得到但買不到。** 由 A16 補上：非 `mention_only`/`unknown` 的列必須有 `evidence_url`。
- **評語是模型掰的。** 由 A24（quote 必須是正文子字串）＋A25（原生分數不得被改寫）夾住。

**仍然沒有斷言蓋到、必須在最終報告誠實寫出來的兩件事：**

- **欄位以外的可讀性。** 沒有任何 A 項能保證 `product` 欄位讀起來像人話——
  `"Original Hot Sauce 5oz 2pk Value"` 完全可以通過 A10 的三層（它確實是來源字串的子字串）。
  這是 A11 的 pilot 樣本存在的真正理由：人看那 40 筆時要看的不是「模型有沒有亂編」，
  而是「這 40 個名字我唸得出來嗎」。N7 必須附 20 筆隨機抽樣的 `brand` + `product` 原樣。
- **代表句選得好不好。** A24 只能證明 `quote` 出自原文，不能證明它是那篇評論的**重點**。
  一篇說「it's fine but the vinegar dominates」的評論，抽到「it's fine」也會通過 A24。
  這正是 A11 要求 pilot 樣本裡至少 15 筆是 verdict 的理由。
  N7 必須另附 10 筆 `(quote, 原文連結)` 對照，讓人自己判斷抽句品質，
  並在報告裡明說：**這一項目前沒有自動化的守門員。**

---

Written under GRAPH_PROTOCOL v2.7.
