# 驗收表 — us-hot-sauce-corpus

`49` PASS　`1` FAIL　`1` BLOCKED（共 51 條）

**任何一項 FAIL 或 BLOCKED，整個 run 就是失敗**，不論產出多少列。
`BLOCKED` 的意思是「這一條這一輪驗不到」，不是「應該會過」。

| 項目 | 判定 | 內容 |
|---|---|---|
| A1 | PASS | 乾淨環境跑得起來、測試全綠 |
| A2 | PASS | 註冊表登記完整、全庫體檢無違規 |
| A3 | PASS | evdb 核心沒有被領域概念汙染 |
| A4 | PASS | evdb 工作樹沒有被這份任務改動 |
| A5 | PASS | 批次匯入不丟列 |
| A6 | PASS | 同一份快照跑兩次，事件數不變 |
| A7 | PASS | 只追加：舊事件都還在 |
| A8 | PASS | 產品規模 |
| A9 | PASS | 事件總數天花板 |
| A10 | PASS | 抽取不變式（三層） |
| A11 | PASS | 首輪試樣是交付物 |
| A12 | PASS | bridge 不吃降級輸出 |
| A13 | PASS | 同一個 GTIN 不出現在兩列 |
| A14 | PASS | 不過度合併 |
| A15 | PASS | 每一列可追溯 |
| A16 | PASS | 可購性值域與證據 |
| A17 | FAIL | 召回率 |
| A18 | PASS | 召回率清單是 held-out 的 |
| A19 | PASS | 零影音平台 |
| A20 | PASS | 零 user review |
| A21 | PASS | outlet 白名單可稽核 |
| A22 | PASS | 白名單是抓取端的擋牆 |
| A23 | PASS | 不含語音轉文字、不含付費轉錄 |
| A24 | PASS | 正文逐字保存、不進 payload |
| A25 | PASS | 評語是原句 |
| A26 | PASS | 原生分數不被改寫 |
| A27 | PASS | 孤兒不丟 |
| A28 | PASS | 版控與輸出不外流長正文 |
| A29 | PASS | 評論覆蓋率報告 |
| A30 | PASS | 評論規模 |
| A31 | PASS | 視圖可重算 |
| A32 | BLOCKED | 作業書可執行 |
| A33 | PASS | 沒有繞過共用 session 的直接請求 |
| A34 | PASS | 沒有密鑰進版控、probe 匯出唯讀 |
| A35 | PASS | 主要路徑：查得到、看得懂 |
| A36 | PASS | FDC 欄位齊、營養是每份且說得出怎麼算的 |
| A37 | PASS | 標籤照片可追溯、授權註記寫進事件 |
| A38 | PASS | 每一筆判讀都回溯得到那張照片 |
| A39 | PASS | 判讀不得憑空造字（詞庫覆蓋率） |
| A40 | PASS | 視覺節點也不吃降級輸出 |
| A41 | PASS | 試樣擴到 n≥60，含 ≥20 筆標籤判讀 |
| A42 | PASS | 成分推導是純規則，沒有模型 |
| A43 | PASS | 每個成分欄位說得出是誰說的，不一致兩值都留 |
| A44 | PASS | 辣度不得塌成一個數字 |
| A45 | PASS | 辣度上界：有萃取物就是 unbounded |
| A46 | PASS | 排序事實 <2 筆不給 rank，區間可重現 |
| A47 | PASS | 代工聚類的每個成員都附得出證據 |
| A48 | PASS | 每次執行有自己的輸出目錄，不覆蓋上一次 |
| A49 | PASS | 跨 run 趨勢報告 |
| A50 | PASS | 判讀要跟獨立來源對得上 |
| A51 | PASS | 出處只收彙整型，而且不是店家自己的商品頁 |

---

## 原始輸出

### A1 — 乾淨環境跑得起來、測試全綠

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m pytest tests/sauce -q
```

```
........................................................................ [ 84%]
.............                                                            [100%]
85 passed in 4.02s
```

### A2 — 註冊表登記完整、全庫體檢無違規

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m evdb --home .evdb validate --json
```

```
{
 "events_checked": 156752,
 "rules_violated": [],
 "violations": {},
 "ok": true
}
```

### A3 — evdb 核心沒有被領域概念汙染

**判定：PASS**（exit 1）

```
git grep -niE sauce|scoville|capsaicin|pepper -- evdb/
```

> 在 ../1-github/evdb 執行

### A4 — evdb 工作樹沒有被這份任務改動

**判定：PASS**（exit 0）

```
git status --porcelain
```

> 在 ../1-github/evdb 執行

### A5 — 批次匯入不丟列

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.conservation --home .evdb
```

```
{
 "check": "A5 conservation",
 "ok": true,
 "files": 64,
 "rejects_total": 0,
 "detail": [
  {
   "file": "sauce-awards-22520-df4899cf.jsonl",
   "kind": "spool",
   "lines": 102,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-composition-12392-ef60b7cf.jsonl",
   "kind": "spool",
   "lines": 1211,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-composition-13152-b155e7cd.jsonl",
   "kind": "spool",
   "lines": 1211,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-composition-28472-f9f45e68.jsonl",
   "kind": "spool",
   "lines": 1211,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-composition-33648-fd87784e.jsonl",
   "kind": "spool",
   "lines": 1211,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-composition-36200-d676e20d.jsonl",
   "kind": "spool",
   "lines": 3171,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-composition-38832-1f08215d.jsonl",
   "kind": "spool",
   "lines": 1211,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-extract-rules-26688-7c42e2cc.jsonl",
   "kind": "spool",
   "lines": 16221,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-extract-rules-38072-e5f5bd6a.jsonl",
   "kind": "spool",
   "lines": 16065,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-fdc-38072-55d36cde.jsonl",
   "kind": "spool",
   "lines": 5032,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-heat-34848-5a5f9e79.jsonl",
   "kind": "spool",
   "lines": 7151,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-heat-38704-b4f6006b.jsonl",
   "kind": "spool",
   "lines": 7151,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-heat-42136-04378309.jsonl",
   "kind": "spool",
   "lines": 6999,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-heat-8048-f6e35a35.jsonl",
   "kind": "spool",
   "lines": 6999,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-heatrank-30888-5bf35e80.jsonl",
   "kind": "spool",
   "lines": 15,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-hotones-22520-24d372f3.jsonl",
   "kind": "spool",
   "lines": 13,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-label-images-11716-e9ced0bd.jsonl",
   "kind": "spool",
   "lines": 120,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-label-images-36540-53e54968.jsonl",
   "kind": "spool",
   "lines": 25,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-11356-6da8a495.jsonl",
   "kind": "spool",
   "lines": 32286,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-12916-f2fdcd93.jsonl",
   "kind": "spool",
   "lines": 32286,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-26688-ed6905b6.jsonl",
   "kind": "spool",
   "lines": 32286,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-28036-d1fa5ffe.jsonl",
   "kind": "spool",
   "lines": 32286,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-32044-09df9a1f.jsonl",
   "kind": "spool",
   "lines": 32286,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-32204-91005891.jsonl",
   "kind": "spool",
   "lines": 16065,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-38072-58a7aa34.jsonl",
   "kind": "spool",
   "lines": 16065,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-39232-29b80f58.jsonl",
   "kind": "spool",
   "lines": 32286,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
   "file": "sauce-match-39564-c9f1b759.jsonl",
   "kind": "spool",
   "lines": 32286,
   "missing_from_store": 0,
   "unparseable": 0
  },
  {
  
…（截斷）
```

### A6 — 同一份快照跑兩次，事件數不變

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.idempotent --home .evdb --snapshot state/snapshot-20260919T082412Z
```

```
{
 "check": "A6 idempotent",
 "ok": true,
 "events_before": 156752,
 "after_first": 156752,
 "after_second": 156752,
 "snapshot": "state/snapshot-20260919T082412Z"
}
```

### A7 — 只追加：舊事件都還在

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.append_only --home .evdb --baseline state/events-20260920T183500Z.txt
```

> 基準就是這一輪自己；真正的證據要等下一輪

```
{
 "check": "A7 append_only",
 "ok": true,
 "baseline_events": 120883,
 "events_now": 156752,
 "added": 35869,
 "missing": 0
}
```

### A8 — 產品規模

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.scale --home .evdb --rules v1
```

```
{
 "check": "A8 scale",
 "ok": true,
 "products": 7186,
 "brands": 2358,
 "min_products": 4000,
 "min_brands": 800
}
```

### A9 — 事件總數天花板

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.ceiling --home .evdb
```

```
{
 "check": "A9 ceiling",
 "ok": true,
 "events": 156752,
 "max_events": 800000,
 "by_source": {
  "evdb": 72717,
  "off": 27703,
  "shopify": 25735,
  "fdc": 24960,
  "woo": 2223,
  "outlet_web": 1827,
  "off_image": 838,
  "webshop": 473,
  "wikipedia": 161,
  "awards": 102,
  "hotones": 13
 }
}
```

### A10 — 抽取不變式（三層）

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.validate --home .evdb
```

```
{
 "events": 156752,
 "layer_1_schema": {
  "ok": true,
  "problems": [],
  "total": 0
 },
 "layer_2_invariants": {
  "ok": true,
  "problems": [],
  "total": 0
 },
 "layer_3_pilot": {
  "status": "skipped",
  "problems": [],
  "reason": "人工裁決只有 0 筆，未達 40；第一次執行時這是預期的（A41 的交付物）",
  "items": 60,
  "judged": 0
 },
 "ok": true
}
```

### A11 — 首輪試樣是交付物

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.pilot check
```

```
{
 "path": "C:\\Users\\luke_\\Desktop\\AI\\Scout\\sauce\\pilot\\sample-v1.jsonl",
 "items": 60,
 "verdicts": 0,
 "label_reads": 20,
 "judged_by_human": 0,
 "problems": [],
 "note": "裁決欄位空白是預期的：第一次執行時這份檔案是交付物，不是關卡",
 "ok": true
}
```

### A12 — bridge 不吃降級輸出

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.degraded --home .evdb
```

```
{
 "check": "A12 degraded",
 "ok": true,
 "model_id": "nvidia/this-model-does-not-exist",
 "exit": 1,
 "events_before": 156752,
 "events_after": 156752,
 "stderr_tail": "luke_\\Desktop\\AI\\2-local-only\\llm-bridge\\llm_bridge\\prompts.py\", line 99, in load_asset\n    raise PromptAssetMissing(f\"找不到 prompt 資產：{path}\")\nllm_bridge.prompts.PromptAssetMissing: 找不到 prompt 資產：C:\\Users\\luke_\\Desktop\\AI\\Scout\\sauce\\prompts\\sauce-review-verdict\\nvidia__this-model-does-not-exist.json"
}
```

### A13 — 同一個 GTIN 不出現在兩列

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.dupes --home .evdb --rules v1
```

```
{
 "check": "A13 dupes",
 "ok": true,
 "rows": 7186,
 "with_gtin": 5041,
 "duplicated_gtins": 0
}
```

### A14 — 不過度合併

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.confusables --home .evdb --rules v1
```

```
{
 "check": "A14 confusables",
 "ok": true,
 "groups": 18,
 "min_groups": 15,
 "groups_present_in_view": 10,
 "catalog_rows": 7186
}
```

### A15 — 每一列可追溯

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.provenance --home .evdb --rules v1
```

```
{
 "check": "A15 provenance",
 "ok": true,
 "rows": 7186,
 "rows_without_provenance": 0
}
```

### A16 — 可購性值域與證據

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.availability --home .evdb --rules v1
```

```
{
 "check": "A16 availability",
 "ok": true,
 "rows": 7186,
 "by_value": {
  "discontinued": 1,
  "retail_listing": 6630,
  "unknown": 555
 }
}
```

### A17 — 召回率

**判定：FAIL**（exit 1）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.coverage --home .evdb --rules v1 --probe sauce/probe/probe-v1.csv
```

```
{
 "check": "A17 coverage",
 "ok": false,
 "recall": 0.7838,
 "min_recall": 0.9,
 "list_entries": 74,
 "hits": 58,
 "misses": 16,
 "by_level": {
  "brand+overlap": 30,
  "brand+product": 19,
  "product_only": 9
 },
 "report": "C:\\Users\\luke_\\Desktop\\AI\\Scout\\reports\\sauce-coverage.md",
 "missed": [
  "Original Red Sauce",
  "Hotter Hot Sauce",
  "XXXtra Hot Habanero Sauce",
  "Bee Sting Honey",
  "Small Axe Peppers Bronx Greenmarket Hot Sauce",
  "Pineapple Jalapeno",
  "Hamajang",
  "Zombie Apocalypse",
  "Trinidad Scorpion",
  "Rogue Ghost Pepper",
  "Pineapple Express",
  "Hot Sauce Verde",
  "Salsa Valentina",
  "Salsa Búfalo Clásica",
  "Iguana Original Red",
  "Pain Is Good Batch 37"
 ]
}
```

### A18 — 召回率清單是 held-out 的

**判定：PASS**（exit 1）

```
git grep -n probe -- sauce/ :!sauce/coverage.py :!sauce/probe/ :!sauce/acceptance.py
```

### A19 — 零影音平台

**判定：PASS**（exit 1）

```
git grep -niE youtube\.com/watch|youtu\.be/|googlevideo|timedtext|yt[-_]?dlp|pytube|youtube[-_]transcript -- sauce/ tests/sauce/ fixtures/sauce/ requirements-sauce.txt :!sauce/acceptance.py
```

### A20 — 零 user review

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.no_ugc --home .evdb
```

```
{
 "check": "A20 no_ugc",
 "ok": true,
 "review_events": 1827,
 "ugc_events": 0,
 "ugc_sources": [
  "forum_ugc",
  "marketplace",
  "reddit",
  "retailer_widget"
 ]
}
```

### A21 — outlet 白名單可稽核

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.outlets --home .evdb
```

```
{
 "check": "A21 outlets",
 "ok": true,
 "whitelist_rows": 44,
 "min_rows": 40,
 "outlets_seen": 40
}
```

### A22 — 白名單是抓取端的擋牆

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m pytest tests/sauce/test_outlet_gate.py -q
```

```
......                                                                   [100%]
6 passed in 0.39s
```

### A23 — 不含語音轉文字、不含付費轉錄

**判定：PASS**（exit 1）

```
git grep -niE whisper|deepgram|assemblyai|speech[-_]to[-_]text|audio[-_]?transcri|rev\.ai|otter\.ai|speechmatics|pyaudio|ffmpeg -- sauce/ requirements-sauce.txt :!sauce/acceptance.py
```

### A24 — 正文逐字保存、不進 payload

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.bodies --home .evdb
```

```
{
 "check": "A24 bodies",
 "ok": true,
 "reviews": 1827,
 "max_payload_bytes": 4096,
 "avg_payload_bytes": 874
}
```

### A25 — 評語是原句

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.quotes --home .evdb
```

```
{
 "check": "A25 quotes",
 "ok": true,
 "verdicts": 0,
 "bodies": 1827
}
```

### A26 — 原生分數不被改寫

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.scores --home .evdb
```

```
{
 "check": "A26 scores",
 "ok": true,
 "verdicts": 0,
 "with_score": 0
}
```

### A27 — 孤兒不丟

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.orphans --home .evdb
```

```
{
 "check": "A27 orphans",
 "ok": true,
 "orphans_reported": 2855,
 "accounted_for": 2855,
 "reviews_published": 1827,
 "reviews_without_reference": 1827,
 "verdicts": 0,
 "non_review_orphans": {
  "sauce.observation.mention / awards": 102,
  "sauce.observation.product / fdc": 50,
  "sauce.observation.lineup / hotones": 2,
  "sauce.observation.mention / hotones": 11,
  "sauce.observation.product / off": 3,
  "sauce.label.image / off_image": 451,
  "sauce.observation.product / shopify": 240,
  "sauce.observation.product / webshop": 5,
  "sauce.observation.mention / wikipedia": 161,
  "sauce.observation.product / woo": 3
 }
}
```

### A28 — 版控與輸出不外流長正文

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.export_safety
```

```
{
 "check": "A28 export_safety",
 "ok": true,
 "csv_files": 3,
 "cells": 290400,
 "tracked_files": 89,
 "max_cell": 500
}
```

### A29 — 評論覆蓋率報告

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.reviews_report --home .evdb --rules v1
```

```
{
 "report": "C:\\Users\\luke_\\Desktop\\AI\\Scout\\reports\\sauce-reviews.md",
 "catalog_rows": 7186,
 "published": 1827,
 "verdicts": 0,
 "products_reviewed": 0,
 "orphans": 1827,
 "outlets": 40
}
```

### A30 — 評論規模

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.review_scale --home .evdb
```

```
{
 "check": "A30 review_scale",
 "ok": true,
 "reviews": 1827,
 "verdicts": 0,
 "roundups": 54,
 "sauces_with_reference": 212,
 "products_reviewed": 0,
 "thresholds": {
  "reviews": 1200,
  "roundups": 30,
  "sauces_with_reference": 150
 }
}
```

### A31 — 視圖可重算

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.reproducible --home .evdb --rules v1
```

```
{
 "check": "A31 reproducible",
 "ok": true,
 "sauce.views:build": {
  "rows_sha256": "0db98b8318755dc8dbe50a78350cbb8fb4e78118fc6d7d1f1ac3a11e0b3094cd",
  "runs": 2
 },
 "sauce.views:reviews": {
  "rows_sha256": "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
  "runs": 2
 }
}
```

### A32 — 作業書可執行

**判定：BLOCKED**

> 從空的 .evdb 照 RUNBOOK 跑到底

### A33 — 沒有繞過共用 session 的直接請求

**判定：PASS**（exit 1）

```
git grep -nE requests\.(get|post)\(|httpx\.(get|post)\(|urlopen\( -- sauce/ :!sauce/net.py
```

### A34 — 沒有密鑰進版控、probe 匯出唯讀

**判定：PASS**（exit 1）

```
git grep -nE SUPABASE_KEY|service_role|eyJ[A-Za-z0-9_-]{20,} -- sauce/ tests/sauce/ fixtures/sauce/ :!sauce/acceptance.py
```

### A35 — 主要路徑：查得到、看得懂

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.query Secret Aardvark --home .evdb --rules v1
```

```
Secret Aardvark Trading Co — Aardvark Habanero Hot Sauce
  entity_id      sauce:secret-aardvark-trading|aardvark-habanero
  可購性         retail_listing
  出處           http://world-en.openfoodfacts.org/product/0853393000030/aardvark-habanero-hot-sauce-secret-aardvark-trading-co
  來源           off（1 個，single_source:off）
  GTIN           00853393000030
  ⚠ 這一列有長得很像的鄰居（duplicate_candidate），沒有合併

（總表上另有 5 列長得很像但沒有合併；加 --all 看全部）
```

### A36 — FDC 欄位齊、營養是每份且說得出怎麼算的

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.fdc_fields --home .evdb
```

```
{
 "check": "A36 fdc_fields",
 "ok": true,
 "fdc_product_events": 5032,
 "with_nutrient_values": 4805,
 "required_keys": [
  "fdc_id",
  "gtin_upc",
  "brand_owner",
  "ingredients",
  "serving_size",
  "serving_size_unit",
  "household_serving_fulltext",
  "branded_food_category",
  "market_country",
  "data_source",
  "modified_date",
  "available_date",
  "discontinued_date",
  "nutrients"
 ]
}
```

### A37 — 標籤照片可追溯、授權註記寫進事件

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.label_images --home .evdb
```

```
{
 "check": "A37 label_images",
 "ok": true,
 "label_images": 451,
 "by_panel": {
  "front": 13,
  "nutrition": 11,
  "ingredients": 427
 },
 "tracked_files": 89
}
```

### A38 — 每一筆判讀都回溯得到那張照片

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.label_reads --home .evdb
```

```
{
 "check": "A38 label_reads",
 "ok": true,
 "label_reads": 387,
 "label_images": 450,
 "empty_transcripts": 0
}
```

### A39 — 判讀不得憑空造字（詞庫覆蓋率）

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.label_lexicon --home .evdb
```

```
{
 "check": "A39 label_lexicon",
 "ok": true,
 "ingredient_reads": 387,
 "tokens": 10553,
 "oov_tokens": 180,
 "oov_rate": 0.0171,
 "max_oov_rate": 0.08,
 "distinct_oov": 136,
 "report": "C:\\Users\\luke_\\Desktop\\AI\\Scout\\reports\\sauce-label-oov.md"
}
```

### A40 — 視覺節點也不吃降級輸出

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.label_degraded --home .evdb
```

```
{
 "check": "A40 label_degraded",
 "ok": true,
 "model_id": "meta/this-vision-model-does-not-exist",
 "exit": 1,
 "events_before": 156752,
 "events_after": 156752,
 "stderr_tail": "uke_\\Desktop\\AI\\2-local-only\\llm-bridge\\llm_bridge\\prompts.py\", line 99, in load_asset\n    raise PromptAssetMissing(f\"找不到 prompt 資產：{path}\")\nllm_bridge.prompts.PromptAssetMissing: 找不到 prompt 資產：C:\\Users\\luke_\\Desktop\\AI\\Scout\\sauce\\prompts\\sauce-label-read\\meta__this-vision-model-does-not-exist.json"
}
```

### A41 — 試樣擴到 n≥60，含 ≥20 筆標籤判讀

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.pilot check
```

```
{
 "path": "C:\\Users\\luke_\\Desktop\\AI\\Scout\\sauce\\pilot\\sample-v1.jsonl",
 "items": 60,
 "verdicts": 0,
 "label_reads": 20,
 "judged_by_human": 0,
 "problems": [],
 "note": "裁決欄位空白是預期的：第一次執行時這份檔案是交付物，不是關卡",
 "ok": true
}
```

### A42 — 成分推導是純規則，沒有模型

**判定：PASS**（exit 1）

```
git grep -nE llm|bridge|openai|anthropic|model_id -- sauce/composition.py
```

### A43 — 每個成分欄位說得出是誰說的，不一致兩值都留

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.composition --home .evdb
```

```
{
 "check": "A43 composition",
 "ok": true,
 "composition_rows": 14524,
 "by_primary_source": {
  "storefront_text": 2021,
  "fdc": 11938,
  "label_photo": 565
 },
 "cross_checked": 111,
 "disagreeing": 105,
 "never_cross_checked": 14413
}
```

### A44 — 辣度不得塌成一個數字

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.heat_layers --home .evdb --rules v1
```

```
{
 "check": "A44-A46 heat_layers",
 "ok": true,
 "rows": 7186,
 "with_ceiling": 953,
 "ranked": 15,
 "required_columns_present": [
  "shu_lab",
  "heat_ceiling_shu",
  "has_capsaicin_extract",
  "heat_rank",
  "heat_rank_ci_low",
  "heat_rank_ci_high",
  "heat_shu_claims",
  "heat_shu_disagreement",
  "heat_band_label",
  "brand_line_rank"
 ],
 "forbidden_columns_present": []
}
```

### A45 — 辣度上界：有萃取物就是 unbounded

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.heat_layers --home .evdb --rules v1
```

```
{
 "check": "A44-A46 heat_layers",
 "ok": true,
 "rows": 7186,
 "with_ceiling": 953,
 "ranked": 15,
 "required_columns_present": [
  "shu_lab",
  "heat_ceiling_shu",
  "has_capsaicin_extract",
  "heat_rank",
  "heat_rank_ci_low",
  "heat_rank_ci_high",
  "heat_shu_claims",
  "heat_shu_disagreement",
  "heat_band_label",
  "brand_line_rank"
 ],
 "forbidden_columns_present": []
}
```

### A46 — 排序事實 <2 筆不給 rank，區間可重現

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.heat_layers --home .evdb --rules v1
```

```
{
 "check": "A44-A46 heat_layers",
 "ok": true,
 "rows": 7186,
 "with_ceiling": 953,
 "ranked": 15,
 "required_columns_present": [
  "shu_lab",
  "heat_ceiling_shu",
  "has_capsaicin_extract",
  "heat_rank",
  "heat_rank_ci_low",
  "heat_rank_ci_high",
  "heat_shu_claims",
  "heat_shu_disagreement",
  "heat_band_label",
  "brand_line_rank"
 ],
 "forbidden_columns_present": []
}
```

### A47 — 代工聚類的每個成員都附得出證據

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.copackers --home .evdb
```

```
{
 "check": "A47 copackers",
 "ok": true,
 "clusters": 61,
 "members": 281,
 "products_considered": 2798,
 "rules_version": "copack-1",
 "min_brands_per_cluster": 2
}
```

### A48 — 每次執行有自己的輸出目錄，不覆蓋上一次

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.run_dirs --home .evdb
```

```
{
 "check": "A48 run_dirs",
 "ok": true,
 "runs": [
  "2026-09-20"
 ],
 "latest": "2026-09-20",
 "files_in_latest": [
  "manifest.json",
  "sauce_buyable-v1.csv",
  "sauce_catalog-v1.csv",
  "sauce_reviews-v1.csv"
 ]
}
```

### A49 — 跨 run 趨勢報告

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.trend
```

```
{
 "ok": true,
 "runs": [
  "2026-09-20"
 ],
 "note": "只有一個 run，無法比較",
 "report": "C:\\Users\\luke_\\Desktop\\AI\\Scout\\reports\\sauce-trend-single-run.md"
}
```

### A50 — 判讀要跟獨立來源對得上

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.crosscheck --home .evdb
```

```
{
 "check": "A50 crosscheck",
 "ok": true,
 "label_reads": 387,
 "cross_checked": 350,
 "no_reference": 37,
 "coverage": 0.904,
 "median_recall": 1.0,
 "median_precision": 1.0,
 "suspect": 50,
 "report": "C:\\Users\\luke_\\Desktop\\AI\\Scout\\reports\\sauce-label-crosscheck.md",
 "min_median_recall": 0.7,
 "min_median_precision": 0.6,
 "min_coverage": 0.3
}
```

### A51 — 出處只收彙整型，而且不是店家自己的商品頁

**判定：PASS**（exit 0）

```
C:\Users\luke_\Desktop\AI\Scout\.venv\Scripts\python.exe -m sauce.checks.references --home .evdb
```

```
{
 "check": "A51 references",
 "ok": true,
 "references": 445,
 "stale_version_ignored": 15101,
 "articles": 54,
 "sauces_with_reference": 212,
 "min_sauces_per_article": 5,
 "rules_version": "ref-3"
}
```

