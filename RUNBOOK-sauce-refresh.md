# 半年重跑作業書 — us-hot-sauce-corpus

> 每一行都可以直接複製貼上執行。從空的 `.evdb` 開始，跑到底，最後把驗收表重驗一次。
> 節奏是**手動、半年一次**——沒有排程、沒有背景服務、沒有 CDC。

環境：Windows + PowerShell，repo 根目錄 `C:\Users\luke_\Desktop\AI\Scout`。

---

## 0. 一次性設定（新機器才要做）

```powershell
cd C:\Users\luke_\Desktop\AI\Scout
py -3.14 -m venv .venv                      # 不要用 uv 裝的 3.12，見 DECISIONS D4
.venv\Scripts\python -m pip install -r requirements-sauce.txt
```

`requirements-sauce.txt` 會把隔壁的 evdb 以可編輯模式裝進來（`-e ../1-github/evdb`），
所以 `..\1-github\evdb` 必須存在。

**每次開新 shell 都要設一次**（`evdb` 這個指令列工具不會把目前目錄放進 import 路徑）：

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

沒設的話 `evdb derive sauce.views:build` 會說找不到 `sauce` 這個模組。
不想設的人可以把每一行的 `evdb` 換成 `.venv\Scripts\python -m evdb`，效果一樣。

## 1. 先確認契約還在

```powershell
.venv\Scripts\python -m pytest tests/sauce -q
.venv\Scripts\python -m sauce.load --home .evdb --register-only
.venv\Scripts\python -m evdb --home .evdb validate --json
```

三個都要 exit 0。第三個的 `rules_violated` 必須是空陣列。

## 2. 更新來源設定（這一步是人做的判斷，不是程式）

1. **FDC 換新版批次檔**：打開 <https://fdc.nal.usda.gov/download-datasets/>，
   把最新的 `FoodData_Central_branded_food_csv_<日期>.zip` 檔名填進
   `sauce/sources/fdc.py` 的 `DATASET`，並在 `DECISIONS-sauce-corpus.md` 記一筆。
2. **得獎名錄換新年度**：在 `fixtures/sauce/awards.csv` 加一列（award / year / url / format）。
3. **outlet 白名單重新稽核**：

   ```powershell
   .venv\Scripts\python -m sauce.admit                 # 逐站找證據頁與文章網址
   .venv\Scripts\python -m sauce.admit --emit          # 印成 outlets.csv 的列
   ```

   `--emit` 的輸出**不會自己寫進白名單**。人看過、確認每一列的 `evidence_url` 真的打得開
   再貼進 `fixtures/sauce/outlets.csv`。找不到證據的站就不要收——名單寧可短，不要假。
4. **店面名單重新推導**：

   ```powershell
   .venv\Scripts\python -m sauce.storefronts discover
   ```

## 3. 抓取（會跑很久，開背景跑）

```powershell
$env:SAUCE_MIN_INTERVAL = "1.0"     # 每主機的最小間隔（秒）；可以調慢，不可以調到 0
.venv\Scripts\python -m sauce.load --home .evdb --refresh
```

這一步會：開一個新的 `state/snapshot-<時間戳>/`、下載 FDC 與 OFF 的批次檔（各數百 MB，
可續傳；同名的檔案如果上一次已經抓過會直接沿用）、抓店面與名單、抓白名單內的評論文章，
然後 `evdb ingest`、跑規則抽取、比對、產生兩張視圖。

**把 `snapshot_id` 記下來**，後面幾步要用。

## 4. 評論 → 出處連結（**沒有模型**）

```powershell
.venv\Scripts\python -m sauce.references --home .evdb
.venv\Scripts\python -m sauce.load --home .evdb --stage ingest
```

2026-09-20 起這一步不用模型了（D27）：我們留的是**連結**，不是評論內容。
一篇文章對上幾個相異的醬名，就是「這是不是彙整型評比」的判準——
那是一個數字，不是一個判斷。

規則改過就要升 `RULES_VERSION`（`ref-1` → `ref-2` → …），
因為舊版的關聯永遠留在庫裡（只追加），視圖只收當前版本。

## 4b. 標籤照片 → 逐字轉錄 → 結構化欄位（v3）

這一段是 v3 加的，跟第 4 步一樣要過冷啟動閘，但走的是**另一個模型、另一份 prompt 資產**。

**先抓照片。這一步會跑幾小時**，因為一張圖一次請求：

```powershell
$env:SAUCE_MIN_INTERVAL = "0.4"
.venv\Scripts\python -m sauce.load --home .evdb --stage harvest --only off_image
```

**斷了直接重跑就好**：事件每 25 張落盤一次，已經有事件的 GTIN 不重抓（見 DECISIONS D22）。
跑完 `--stage ingest` 把事件收進庫。

**再判讀。** 視覺模型是 `meta/llama-3.2-11b-vision-instruct`，跟評論抽取的文字模型不是同一個：

```powershell
.venv\Scripts\python -m sauce.labelread --home .evdb
```

同樣會停在冷啟動（exit 3）。**審之前先跑交叉驗證**——
`sauce.crosscheck` 會拿同一個 GTIN 在 OFF 上的成分文字比詞的回收率與精確率，
低分的那幾筆列在 `reports/sauce-label-crosscheck.md` 最前面，人先看那些就好。
promote 之後再跑一次。

**golden 一定要帶著 `item`**（llm-bridge 已經修好）：只留 `input` 的話，
暖啟動重播時圖片會不見，模型在沒有圖的情況下被要求轉錄，
一致率會掉到個位數——而那看起來像模型壞掉（D32）。

**最後把字變成欄位。這一步沒有模型**——純規則，同一段字跑兩次一定得到同一個答案：

```powershell
.venv\Scripts\python -m sauce.crosscheck --build-index      # 第一次才要，掃 1.27GB
.venv\Scripts\python -m sauce.crosscheck --home .evdb
.venv\Scripts\python -m sauce.composition --home .evdb
.venv\Scripts\python -m sauce.heat --home .evdb
.venv\Scripts\python -m sauce.load --home .evdb --stage ingest
.venv\Scripts\python -m sauce.heatrank --home .evdb
.venv\Scripts\python -m sauce.copackers --home .evdb
```

`heatrank` 要在 `heat` 的事件**進庫之後**才跑：它吃的是 `sauce.heat.claim` 事件，
不是 `heat.py` 的回傳值。

## 5. 試樣（第一次執行的交付物）

```powershell
.venv\Scripts\python -m sauce.pilot build --home .evdb --n 60
.venv\Scripts\python -m sauce.pilot check
```

產生 `sauce/pilot/sample-v1.jsonl`。人要看的是三件**機器驗不到**的事：
產品那幾筆的名字唸不唸得出來、評語那幾筆是不是那篇評論的重點、
標籤判讀那 20 筆把圖打開逐字對得上不對得上。
填完裁決之後，`sauce.validate` 的第三層下次就會啟用。

**標籤那 20 筆是這份試樣裡最不能省的**：評語至少還有「引文必須是正文的子字串」
（A25）在擋，標籤判讀的原文是一張圖，**連子字串都沒得比**。
詞庫覆蓋率（A39）只擋得住模型整批造字，擋不住順序錯、數字錯、漏掉一行。

## 6. 驗收（逐條，順序照這裡）

```powershell
.venv\Scripts\python -m pytest tests/sauce -q
.venv\Scripts\python -m evdb --home .evdb validate --json
.venv\Scripts\python -m sauce.checks.conservation --home .evdb
.venv\Scripts\python -m sauce.checks.ceiling --home .evdb
.venv\Scripts\python -m sauce.checks.scale --home .evdb --rules v1
.venv\Scripts\python -m sauce.validate --home .evdb
.venv\Scripts\python -m sauce.checks.dupes --home .evdb --rules v1
.venv\Scripts\python -m sauce.checks.confusables --home .evdb --rules v1
.venv\Scripts\python -m sauce.checks.provenance --home .evdb --rules v1
.venv\Scripts\python -m sauce.checks.availability --home .evdb --rules v1
.venv\Scripts\python -m sauce.coverage --home .evdb --rules v1 --probe sauce/probe/probe-v1.csv
.venv\Scripts\python -m sauce.checks.no_ugc --home .evdb
.venv\Scripts\python -m sauce.checks.outlets --home .evdb
.venv\Scripts\python -m sauce.checks.bodies --home .evdb
.venv\Scripts\python -m sauce.checks.quotes --home .evdb
.venv\Scripts\python -m sauce.checks.scores --home .evdb
.venv\Scripts\python -m sauce.checks.orphans --home .evdb
.venv\Scripts\python -m sauce.checks.export_safety
.venv\Scripts\python -m sauce.checks.review_scale --home .evdb
.venv\Scripts\python -m sauce.reviews_report --home .evdb --rules v1
```

v3 加的那幾條（標籤、成分、辣度、代工、輸出目錄）：

```powershell
.venv\Scripts\python -m sauce.checks.fdc_fields --home .evdb
.venv\Scripts\python -m sauce.checks.label_images --home .evdb
.venv\Scripts\python -m sauce.checks.label_reads --home .evdb
.venv\Scripts\python -m sauce.checks.label_lexicon --home .evdb
.venv\Scripts\python -m sauce.checks.label_degraded --home .evdb
.venv\Scripts\python -m sauce.checks.composition --home .evdb
.venv\Scripts\python -m sauce.checks.heat_layers --home .evdb --rules v1
.venv\Scripts\python -m sauce.checks.copackers --home .evdb
.venv\Scripts\python -m sauce.checks.run_dirs --home .evdb
```

或者一次跑完整張表（**這是主要的用法**，會寫出 `ACCEPTANCE-sauce-corpus.md`）：

```powershell
.venv\Scripts\python -m sauce.acceptance --home .evdb --rules v1
```

靜態的那幾條（不需要跑資料）：

```powershell
git grep -niE "sauce|scoville|capsaicin|pepper" -- ../1-github/evdb/evdb/
git -C ..\1-github\evdb status --porcelain
git grep -n "probe" -- sauce/ ":!sauce/coverage.py" ":!sauce/probe/"
git grep -niE "youtube|youtu\.be|timedtext|yt[-_]?dlp|pytube" -- sauce/ tests/sauce/ fixtures/sauce/ requirements-sauce.txt
git grep -niE "whisper|deepgram|assemblyai|speech[-_]to[-_]text|transcribe" -- sauce/ requirements-sauce.txt
git grep -nE "requests\.(get|post)\(|httpx\.(get|post)\(|urlopen\(" -- sauce/ ":!sauce/net.py"
git grep -nE "SUPABASE_KEY|service_role|eyJ[A-Za-z0-9_-]{20,}" -- sauce/ tests/sauce/ fixtures/sauce/
git grep -nE "\.(insert|update|upsert|delete)\(" -- sauce/probe/
```

全部都要**沒有輸出**。

## 7. 只追加與冪等（這一輪與上一輪之間的關係）

第一次跑完之後先存基準：

```powershell
.venv\Scripts\python -m sauce.checks.append_only --home .evdb --write-baseline state/events-<snapshot_id>.txt
```

半年後跑完新的一輪，再驗一次：

```powershell
.venv\Scripts\python -m sauce.checks.append_only --home .evdb --baseline state/events-<上一輪的 snapshot_id>.txt
```

冪等的驗法是同一份快照重放兩次，事件總數不變：

```powershell
.venv\Scripts\python -m sauce.load --home .evdb --snapshot state/snapshot-<id>
.venv\Scripts\python -m evdb --home .evdb stats --json    # 記下 events
.venv\Scripts\python -m sauce.load --home .evdb --snapshot state/snapshot-<id>
.venv\Scripts\python -m evdb --home .evdb stats --json    # 必須完全相同
```

## 8. 視圖可重算

```powershell
.venv\Scripts\python -m evdb --home .evdb derive sauce.views:build --rules v1
.venv\Scripts\python -m evdb --home .evdb derive sauce.views:reviews --rules v1
```

連續跑兩次，四份 `manifest.json` 的 `rows_sha256` 要兩兩相同。

## 9. 產出給人看的東西

```powershell
.venv\Scripts\python -m sauce.export --home .evdb --rules v1
.venv\Scripts\python -m sauce.checks.run_dirs --home .evdb
.venv\Scripts\python -m sauce.checks.export_safety
.venv\Scripts\python -m sauce.trend
.venv\Scripts\python -m sauce.query "Secret Aardvark" --reviews --composition --heat
```

`sauce.export` 會把兩張表寫進 `sauce/out/<執行日期>/`，**每次執行一個目錄**。
不覆蓋上一次是刻意的：半年後要回答「這款醬是這次才出現的，還是上次漏抓」，
唯一的辦法就是兩次的輸出都還在（A48）。`sauce.trend` 就是拿這些目錄互相比對，
只有一個 run 的時候它會照實說「無法比較」並 exit 0——**不是失敗，是還沒有可比的東西**。

`sauce/out/` 進版控，`.evdb/`（含 `raw/` 裡的評論正文與標籤照片）與
`state/snapshot-*/` 不進；`state/snapshot-*/MANIFEST.json` 要進——
半年後要靠它分辨「這是新出的辣醬」還是「我們這次抓法不一樣」。

**標籤照片一張都不進版控、一張都不重新散布**：它們是 CC BY-SA 3.0，
而且授權不涵蓋包裝上的商標與設計（見 DECISIONS D20）。
