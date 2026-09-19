# 偵察：動工前把兩個 repo 讀過一遍（N1）

> 對象：`spec-us-hot-sauce-corpus.md`（approved，2026-09-19）
> 範圍：Scout（本 repo）與 `../1-github/evdb`（唯讀）
> 這份只記「讀到什麼、因此凍結了什麼」。決策記在 `DECISIONS-sauce-corpus.md`。

---

## 1. evdb 的表面（唯讀，一行都不改）

| 檔 | 對這份任務的意義 |
|---|---|
| `evdb/schema.py` | `event_id` 是「除 event_id 外所有欄位」的 SHA-256。同內容＝同一筆，所以重跑天生冪等（A6）。 |
| `evdb/store.py` | 只追加。沒有任何改寫或刪除事件的路徑；同 id 不同內容會丟 `EventConflict`（A7 的地基）。 |
| `evdb/registry.py` | 命名空間與來源是白名單。沒登記的前綴會被 `validate` 擋下（A2）。 |
| `evdb/bulk/importer.py` | 每一列不是變成事件就是進 `rejects/`，兩者相加等於讀進來的列數（A5）。 |
| `evdb/sdk/__init__.py` | `store_raw()` 把原始內容落地、事件只留指標——評論正文就靠它（A24）。**注意 `record()` 要 `EVDB_ENABLED=1` 才會寫，`store_raw()` 不用。** |
| `evdb/derive.py` | 視圖由 `module:function` 或 entry point 解析；輸出目錄是 `views/<view 名把 : . 換成 _>/<rules>/`。`rows_sha256` 是 A31 比的東西。**會把全部事件讀進記憶體**（A9 的天花板就是為了它）。 |
| `evdb/query.py` | `orphans()` 有兩個硬條件：`entity_id LIKE 'src:%'`，而且連結事件的 `event_type` 必須**正好等於 `entity.linked`**。這兩條直接決定了本領域的識別碼設計（見 D1、D2）。 |
| `evdb/validate.py` | 全庫體檢：schema、event_id 雜湊、命名空間、來源、observed_at。 |
| `domains/ma/` | 參考樣板。目錄骨架、pilot／coverage 的做法照抄；M&A 的規則不照抄。`match.py` 的 `LINK_EVENT = "entity.linked"` 是本領域也要跟的慣例。 |

**延後不用的表面**：`Store.rows(sql)`（streaming derive 的入口，本任務不走）、
`export.py` 全庫 Parquet（derive 已經同時產 CSV 與 Parquet）、`cdc/`（半年一次沒有 CDC 的對象）、
`home.py` 的 `EVDB_ENABLED` hook 開關（Scout 沒有等價的舊系統）。

## 2. Scout 這一側

- `CLAUDE.md` 與 `context.md` §2.2 的 **Won't 清單寫著「自動爬蟲（由使用者主動貼連結）」**。
  這份任務整個就是一隻自動爬蟲，牴觸點已提出並取得授權補 superseding ADR（見 D8）。
- `buylist/buylist-schema.sql:73-76`：`sauces` 表的 RLS 對 anon 全開。這是既有狀態，
  本任務不修、也不依賴它以外的權限；只在建召回率清單時**唯讀**匯出。
- `state/graph-state.json` 已經被 `spec-scout-trip-page` 佔用。不覆寫（見 D3）。
- `specs/README.md` 的索引表與「AC 框不准自己勾」的規矩照辦。

## 3. 凍結的契約

寫在 `sauce/contract.py`，其餘節點從那裡讀，沒有第二份定義。

```
命名空間   sauce / brand / gtin / review / outlet（＋核心自帶的 src）
產品層來源 fdc off shopify woo wikidata wikipedia awards hotones reddit
評論層來源 outlet_web podcast_transcript print_archive
UGC 來源   reddit retailer_widget marketplace forum_ugc  ← 只准產生 mention（A20）
event_type sauce.observation.product / .mention / .availability / .lineup
           sauce.review.published / .verdict
           sauce.extraction.parsed
連結事件   entity.linked（核心慣例，不是 sauce.entity.linked —— 見 D1）
entity_id  sauce:<brand_key>|<product_key>   brand:<brand_key>   gtin:<14 位>
           review:<outlet_key>:<url_sha1_12> outlet:<outlet_key> src:<source>:<key>
```

## 4. 實測到的環境事實（會改變做法的那些）

| 發現 | 影響 |
|---|---|
| uv 裝的 CPython 3.12 在這台機器上 HTTPS 全掛（`OPENSSL_Uplink … no OPENSSL_Applink`） | 改用系統的 Python 3.14（evdb 要求 ≥3.12）。見 D4。 |
| Python 預設信任鏈拒絕 `query.wikidata.org`（"certificate has expired"），curl 與瀏覽器都沒事 | `sauce/net.py` 改用作業系統信任庫（truststore）→ certifi → 預設。**不是關掉驗證。** |
| `query.wikidata.org/robots.txt` 明文 `Disallow: /sparql` | Wikidata SPARQL 不能用。見 D5。 |
| `www.wikidata.org` / `en.wikipedia.org` 的 robots 擋掉 `/w/` 與 `/api/` | Wikimedia 的 Action API 不能用；只走 `/wiki/` 條目頁。 |
| `world.openfoodfacts.org/robots.txt` 明文 `Disallow: /api` | OFF 的 search API 不能用，改走官方公開的全量匯出（1.3 GB）。見 D6。 |
| FDC 同一個 GTIN 有多筆歷史版本（4,871 列只有 1,349 個 GTIN） | GTIN 合併會把歷史版本收成一款——這是對的，但也代表 FDC 只提供約 1,349 款母體，A8 的規模要靠 OFF 與長尾撐。 |
| 主流食媒（Dotdash Meredith、NYT、Condé Nast 一部分）對誠實 UA 回 403 | 不偽裝 UA、不繞過，所以這些站進不了白名單。A21 的名單要往專門站與地方媒體補。 |
| Scovie 得獎名錄是 PDF，而且字型把 `tt`／`ti` 連字丟成 `[` | 名字會出現 `GW Wa[s Sauce` 這種字。**不自動修**，標 `text_fidelity=ligature_loss`。 |
| buylist 的 `sauces` 表目前是空的（PostgREST 回 `[]`） | 召回率清單拿不到 `supabase_sauces` 這個來源。見 D7。 |
