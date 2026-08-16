# ACCEPTANCE — Scout MCP Server

規格：[`specs/spec-scout-mcp-server.md`](specs/spec-scout-mcp-server.md)
執行日期：2026-08-16

## 驗收表

| AC | 內容 | 結果 |
|---|---|---|
| AC-1 | 「列出我的旅程」回傳既有旅程 | ⏳ **待真實環境驗**（離線對照已通過） |
| AC-2 | 「加進當候選」→ `day_number IS NULL` | ⏳ **待真實環境驗**（離線對照已通過） |
| AC-3 | 「排到第 2 天 14:00 並確認」 | ⏳ **待真實環境驗**（離線對照已通過） |
| AC-4 | 「某商品買到了」→ 網頁購物 Tab 可見 | ⏳ **待真實環境驗**（離線對照已通過） |
| AC-5 | 缺變數 → 非零 exit ＋ stderr 人話 | ✅ PASS |
| AC-6 | 原始碼無移除動詞；允許清單只有 GET/POST/PATCH | ✅ PASS |
| AC-7 | 無網路 `pytest` exit 0 | ✅ PASS（79 項） |

**AC-1 ~ AC-4 我無法在這裡判定為 PASS。** 這個開發環境連不到 Supabase，
而且不該拿兩人的正式資料庫做寫入測試。離線我做到的是「同一段邏輯真的走過一次 MCP 協定、
資料真的被改到」，但沒有驗到「連得上、金鑰對、權限夠、網頁看得到」。做法見下方「待你驗」。

---

## 原始命令輸出

### AC-5 — 缺變數時的啟動行為

```
$ env -u SCOUT_SUPABASE_URL SCOUT_SUPABASE_KEY=k SCOUT_BUYLIST_URL=... uv run scout-mcp
exit code = 1

--- stdout（必須是空的）---
[結束]

--- stderr ---
Scout MCP server 無法啟動。

缺少環境變數 SCOUT_SUPABASE_URL（行程資料（trips / itinerary_items）的 Supabase 專案網址）。
請設定後重新啟動，例如：
    SCOUT_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
設定方式：在 .mcp.json 的 env 區塊填入，或在啟動 shell 先 export。
值可以從 web/config.js（本機設定檔，未進版控）或 Supabase 專案設定頁取得。
詳細步驟見 mcp-server/README.md。
```

四個必填變數各缺一次都測過（`test_config.py` 的 parametrize），訊息都指名自己並附範例。
stdout 全程為空——stdout 只屬於 JSON-RPC。

### AC-6 — 沒有移除能力

```
$ git grep -inE "\"DELETE\"|'DELETE'" -- mcp-server/src/
（空 → PASS）

$ git grep -inE "\"DELETE\"|'DELETE'" -- mcp-server/ ':!mcp-server/tests/'
（空 → PASS）
```

`tests/` 底下有兩處命中，都在 `test_rest_verbs.py`，且都是「驗證它被拒絕」的斷言——
規格 AC-6 本文即排除這類斷言。另有一處 `test_mcp_integration.py:66`
是 `assert "delete" not in tool.name.lower()`（驗沒有任何刪除工具），同屬此類。

> ⚠️ 第一次跑這個 grep 時回空、看似全過，其實是因為 `mcp-server/` 還沒進版控，
> 而 `git grep` 只搜尋已追蹤的檔案。**那是假的 PASS。** 上面的結果是 `git add` 之後重跑的。

保證機制不只 grep：`rest.py` 的 `ALLOWED_VERBS` 是正面表列的 `frozenset({"GET","POST","PATCH"})`，
清單外的動詞在組請求前就被擋下，`test_rest_verbs.py` 驗到「連一個請求都沒送出去」。

### AC-7 — 無網路測試

```
$ cd mcp-server && uv run pytest -q
........................................................................ [ 91%]
.......                                                                  [100%]
79 passed in 1.75s
```

| 測試檔 | 驗什麼 |
|---|---|
| `test_config.py` | 四個變數各缺一次、空白視同未設、AC-5 的完整 process 行為 |
| `test_rest_verbs.py` | 允許清單、移除動詞被拒且不發請求、三個允許動詞會到後端 |
| `test_itinerary_tools.py` | 三種篩選、候選語意、跨天、時間格式、天數範圍、矛盾參數 |
| `test_shopping_tools.py` | status 篩選、purchased ↔ bought 映射、預設值、非法列舉值 |
| `test_fake_fidelity.py` | **fake 不比真 PostgREST 寬鬆**：未知表/欄位/運算子、NOT NULL、預設值行為 |
| `test_mcp_integration.py` | 真的走 MCP 協定：工具註冊、output schema、§8 情境、錯誤散文到 agent |

---

## 過程中修掉的兩個「測試綠但其實錯」

1. **fake 沒有忠實重現 PostgREST。** 原本 fake 在 POST 時丟掉值為 `null` 的欄位，
   導致新增的候選項目在 fake 裡根本沒有 `day_number` 這個 key。真 PostgREST 回傳的列
   一定含有該表每一個欄位。修正後才發現第二個問題 ↓

2. **insert 送出明確的 `null` 會蓋掉資料表 DEFAULT。** 例如沒填 `duration_minutes` 時
   送 `null`，真資料庫會存 NULL 而不是 DEFAULT 的 60。改成「值為 None 的欄位整個不送」，
   讓 DEFAULT 生效。這個 bug 只有在 fake 忠實之後才浮得出來。

---

## 待你驗（AC-1 ~ AC-4）

1. 複製 `.mcp.json.example` 為 `.mcp.json`，填入四個值（來源見 `mcp-server/README.md`）。
2. `cd mcp-server && uv sync`
3. 重開 Claude Code，`/mcp` 應看到 `scout` connected。
4. 依序說這四句，每句之後照著括號裡的方式比對：

   | 說什麼 | 怎麼確認 |
   |---|---|
   | 「列出我的旅程」 | 回傳的旅程名稱與日期，跟網頁行程 Tab 的下拉選單一致（AC-1） |
   | 「把〈某店名〉加進〈某旅程〉當候選」 | 網頁行程 Tab 重新整理 → 出現在「可以彈性」區、標示「候選中」（AC-2） |
   | 「把它排到第 2 天 14:00 並標記已確認」 | 網頁上該項目變成「Day 2 14:00」且勾選呈綠色（AC-3） |
   | 「〈某商品〉買到了」 | 網頁購物 Tab → 該項目沉到底部、劃線（AC-4） |

5. 最後請把測試資料刪掉——**要用網頁介面刪，MCP 沒有刪除能力**（這是刻意的）。

**最可能卡住的地方**：四個環境變數對調（行程的 key 填到購物那一組）。
這種情況錯誤訊息會說「找不到 `trips`（HTTP 404）……行程與購物在兩個不同專案，設定容易對調」，
不會只給你一個裸的 404。
