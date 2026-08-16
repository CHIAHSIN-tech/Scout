# Scout MCP Server

讓 Claude（Claude Code / Claude Desktop）直接讀寫 Scout 的行程與購物資料，
不用再在對話和網頁之間手動抄來抄去。

規格：[`specs/spec-scout-mcp-server.md`](../specs/spec-scout-mcp-server.md)

---

## 這個 server 能做什麼

| 工具 | 做什麼 |
|---|---|
| `list_trips` | 列出所有旅程 |
| `create_trip` | 建立一趟新旅程 |
| `list_itinerary_items` | 列出某趟旅程的項目（可篩：某一天／只看候選／只看未確認） |
| `add_itinerary_item` | 新增行程項目，不給 `day_number` 就是候選 |
| `update_itinerary_item` | 排入某天、改時間、標記確認、退回候選、改欄位 |
| `list_wishlist` | 列出購物清單（可篩 pending / purchased） |
| `add_wishlist_item` | 加一個想買的東西 |
| `update_wishlist_item` | 改購物項目，最常用的是標記已買 |

**沒有刪除工具，這是刻意的。** 底層 HTTP client 的動詞允許清單只有 GET / POST / PATCH，
連組出一個移除請求的機會都沒有。要刪東西請到 Scout 網頁介面做，那裡有二次確認。

## ⚠️ 兩個 Supabase 專案（不是設定錯誤）

Scout 的行程與購物**存在兩個不同的 Supabase 專案**，這是既有架構決策（ADR-012 不合併），
所以本 server 需要**四個**連線環境變數而不是兩個：

| 資料 | 表 | 網頁對應 | 環境變數 |
|---|---|---|---|
| 行程 | `trips`、`itinerary_items` | 🗺️ 行程 Tab | `SCOUT_SUPABASE_URL` / `SCOUT_SUPABASE_KEY` |
| 購物 | `buylist_items` | 🛒 購物 Tab | `SCOUT_BUYLIST_URL` / `SCOUT_BUYLIST_KEY` |

> 註：`supabase_schema.sql` 裡還有一張 `wishlist` 表，那是 Streamlit 時代的遺留，
> **現在的購物 Tab 不讀它**。購物工具接的是 `buylist_items`，工具名稱則沿用規格的
> wishlist 用語。詳見 `for-chia-mcp-server.md`。

## 環境變數

| 變數 | 必填 | 說明 |
|---|---|---|
| `SCOUT_SUPABASE_URL` | ✅ | 行程專案網址，例：`https://xxxx.supabase.co` |
| `SCOUT_SUPABASE_KEY` | ✅ | 行程專案的 publishable / anon key |
| `SCOUT_BUYLIST_URL` | ✅ | 購物專案網址 |
| `SCOUT_BUYLIST_KEY` | ✅ | 購物專案的 publishable / anon key |
| `SCOUT_USERNAME` | — | 寫入時記在「誰加的」欄位，預設 `stanley` |

缺任何一個必填變數，server 會以非零 exit code 結束，並在 stderr 印出缺哪一個、該填什麼、範例值。

值從哪裡拿：本機的 `web/config.js`（未進版控），或 Supabase 專案設定頁的 API 區塊。
**不要把值寫進本資料夾的任何程式碼或 commit 進 repo。**

---

## 安裝與設定（Stanley：Claude Code）

需要 [uv](https://docs.astral.sh/uv/)。在 repo 根目錄：

```bash
cd mcp-server && uv sync
```

然後在 **repo 根目錄** 建立 `.mcp.json`（此檔已被 `.gitignore` 排除，不會進版控）：

```json
{
  "mcpServers": {
    "scout": {
      "command": "uv",
      "args": ["run", "--directory", "mcp-server", "scout-mcp"],
      "env": {
        "SCOUT_SUPABASE_URL": "https://填入行程專案.supabase.co",
        "SCOUT_SUPABASE_KEY": "填入行程專案的 key",
        "SCOUT_BUYLIST_URL": "https://填入購物專案.supabase.co",
        "SCOUT_BUYLIST_KEY": "填入購物專案的 key",
        "SCOUT_USERNAME": "stanley"
      }
    }
  }
}
```

重開 Claude Code，用 `/mcp` 確認 `scout` 是 connected。

---

## 非開發者設定步驟（Chia：Claude Desktop）

這一段不需要懂程式，但需要打開一次終端機和一個設定檔。

**1. 裝 uv**（只需一次）

開啟「終端機」（Mac）或「PowerShell」（Windows），貼上並執行：

- Mac：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows：`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

**2. 取得 Scout 專案**

如果還沒有，向 Stanley 要 repo 的位置。把整個資料夾放在你找得到的地方，
例如 `~/Documents/Scout`。**記下這個完整路徑**，下一步要用。

**3. 編輯 Claude Desktop 的設定檔**

Claude Desktop → 設定 → 開發者 → 「編輯設定」，會打開 `claude_desktop_config.json`。
把下面這段貼進去（如果檔案裡已經有 `mcpServers`，就只把 `"scout": {...}` 這一塊加進去）：

```json
{
  "mcpServers": {
    "scout": {
      "command": "uv",
      "args": ["run", "--directory", "/你的路徑/Scout/mcp-server", "scout-mcp"],
      "env": {
        "SCOUT_SUPABASE_URL": "Stanley 給你的行程網址",
        "SCOUT_SUPABASE_KEY": "Stanley 給你的行程 key",
        "SCOUT_BUYLIST_URL": "Stanley 給你的購物網址",
        "SCOUT_BUYLIST_KEY": "Stanley 給你的購物 key",
        "SCOUT_USERNAME": "chia"
      }
    }
  }
}
```

把 `/你的路徑/Scout/mcp-server` 換成第 2 步記下的路徑再加上 `/mcp-server`。
四個網址與 key 向 Stanley 要——**不要貼到聊天室或任何公開的地方**。

**4. 完全關閉 Claude Desktop 再重開**

之後就可以直接說「列出我的旅程」「把某某店加進沖繩那趟當候選」。

**如果沒反應**：Claude Desktop 的設定裡有 MCP 記錄檔可以看。
最常見的原因是第 3 步的路徑打錯，或四個變數少填一個——
錯誤訊息會直接告訴你缺哪一個。

---

## 開發

```bash
cd mcp-server
uv run pytest          # 79 項測試，全程無網路（接 fake Supabase）
```

測試不會碰到任何真實資料庫。`tests/fake_supabase.py` 是 PostgREST 的替身，
刻意**不比真的寬鬆**——不存在的表回 404、不存在的欄位回 400、NOT NULL 缺值回 400。
`tests/test_fake_fidelity.py` 就是在釘這件事，避免 fake 隨時間變成「什麼都收」的許願池。

### 檔案結構

| 檔案 | 職責 |
|---|---|
| `config.py` | 環境變數 → 設定物件；缺變數時產生人話錯誤 |
| `rest.py` | PostgREST 的 HTTP client。**動詞允許清單在這裡** |
| `contracts.py` | 輸入／輸出 schema 與本地預檢，單點定義 |
| `errors.py` | 錯誤散文政策（重試有沒有用 ＋ 下一步） |
| `instructions.py` | 連線時給 agent 的三條規則 |
| `service.py` | 工具的實際邏輯，只依賴 client 介面（好測試） |
| `tools.py` | 把 service 註冊成 MCP 工具，很薄 |
| `server.py` | 進入點。stdout 只屬於 JSON-RPC |

---

## 驗收狀態

AC-5、AC-6、AC-7 可由命令判定，已通過（見 `../ACCEPTANCE-mcp-server.md`）。

**AC-1 ~ AC-4 需要真實環境才算數**：要在 Claude Code 裡對真正的 Supabase 跑一次。
離線測試只驗到「邏輯正確」，沒有驗到「連得上、權限夠、網頁看得到」。
驗收腳本與逐步做法見 `../ACCEPTANCE-mcp-server.md` 的「待你驗」一節。
