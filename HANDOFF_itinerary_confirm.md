# Handoff — 行程候選＋確認狀態整合

對應 spec：`spec-scout-confirm-integration.md`。分支：`feat/itinerary-confirm-integration`。

這份說明「要做什麼才能跑起來」與「怎麼驗收 5 條 AC」。程式碼已完成，但本機沒有
Supabase 金鑰，所以資料庫相關的部分需要你在有金鑰的環境跑一次。

---

## 1. 這次改了什麼

| 檔案 | 改動 |
|------|------|
| `supabase_schema.sql`（新） | Supabase schema 的單一真實來源：`day_number`/`start_time` 可 NULL（候選中）＋ `confirm_required`/`is_confirmed` 兩軸確認欄位＋索引＋RLS。冪等，可重跑。 |
| `db.py` | 新增候選/確認 CRUD：`add_candidate`、`get_candidates`、`get_scheduled_items`、`get_unconfirmed_required`、`schedule_item`、`unschedule_item`、`set_confirm_required`、`set_confirmed`、`update_items_schedule`、`update_item_full`。`add_item` 多了 `confirm_required` 參數。 |
| `itinerary.py` | `reorder_and_recalculate` / `adjust_with_cascade` 排除候選項目、對 NULL 時段安全（AC-2）。`apply_reorder` 改走 Supabase（修掉舊的 `get_conn` 崩潰）。 |
| `page_itinerary.py` | 新增「📋 候選 / 確認」分頁：優先儀表板＋候選清單＋排入行程＋確認切換。編輯表單加入兩軸確認，並修掉舊的 `get_conn` 崩潰。卡片顯示確認徽章。 |
| `requirements.txt` | 補上 `supabase`（先前漏了，會導致雲端部署失敗）。 |
| `db.py` + `supabase_schema.sql`（購物） | 重建購物 `wishlist` 表與 4 個函式（Supabase 重構時漏掉，首頁「購物」一進去就崩潰）。 |
| `tests/test_itinerary.py`（新） | 12 個純邏輯測試，不需 DB；涵蓋候選排除與 NULL 安全。 |
| `scout-checklist/`（新） | 網頁版確認清單雛形：Supabase REST、`?trip=<id>` 分享連結、兩軸儀表板、手動重新整理。 |

> 順手修掉的既有 bug（都在 spec Build Order #2 範圍內）：`itinerary.apply_reorder` 與
> `page_itinerary` 編輯儲存仍呼叫已被移除的 `db.get_conn()`（Supabase 重構後會直接崩潰）；
> `requirements.txt` 缺 `supabase`。

---

## 1.5 先看長相（完全不用 Supabase）

想立刻看到網頁版確認清單長怎樣、按鈕能不能動：開
`scout-checklist/index.html?demo=1` —— 這是**範例模式**，用假資料、按鈕只在本機作用、
不連任何資料庫。已驗證：勾「已確認」會把它移到已確認區、未確認數字會變；候選卡片
「📅 排入行程」可把它排到某天某時段。

## 2. 要你做的事（只剩「填 2 個值 + 跑一次 SQL」）

> 我已把檔案都備好，只差 Supabase 的「網址 + 金鑰」這兩個值——這兩個值只能你提供
> （向珈欣拿她現有專案的，或開新專案）。其餘都不用你手動弄。

1. **拿到 2 個值**：Supabase 後台 → Project Settings → API：
   - `Project URL`（像 `https://xxxx.supabase.co`）
   - `anon` / `public` key
2. **填進兩個已備好的檔（只改值，結構都做好了）**：
   - `.streamlit/secrets.toml` 最上面已幫你放好 `SUPABASE_URL` / `SUPABASE_KEY` 兩行，替換值即可。
   - `scout-checklist/config.js` 已建好，替換 `SUPABASE_URL` / `SUPABASE_ANON_KEY` 兩個值即可。
3. **跑 schema**：把 `supabase_schema.sql` 整份貼到 Supabase SQL Editor 按 Run。
   - 全新環境 → 直接建好；既有環境（珈欣已手建表）→ 一樣安全，只會補上可 NULL 與確認欄位。
4. **安裝相依**：`pip install -r requirements.txt`（會裝 supabase）。

完成後 `streamlit run app.py` 即可。網頁版用分享連結 `…/scout-checklist/?trip=<id>` 開。

---

## 3. 驗收 5 條 AC（端到端）

> 跑之前先完成第 2 節。`<trip_id>` 在 Streamlit 建立旅程後，可在 Supabase `trips` 表查到。

- **AC-1（候選不進 Kanban）**：Streamlit →「📋 候選 / 確認」分頁 → 新增候選項目（不填日期/時段）
  → 切到「📅 時間軸」確認**看不到**它。✅
- **AC-2（候選不弄壞排程）**：把幾個項目排進某天並用 ↑↓ 重排；即使有候選項目存在，
  重排/時間重算**不報錯**。（已由 `tests/test_itinerary.py` 自動驗證。）✅
- **AC-3（必須確認→優先提醒）**：把某項目標記「必須確認」但不確認 → 它出現在
  候選/確認分頁最上面的「⚠️ 必須確認」清單。✅
- **AC-4（雙端同一來源）**：網頁版（`scout-checklist/?trip=<id>`）把某項目標「已確認」
  → 回 Streamlit 重新整理，該項目徽章顯示「✅ 已確認」。✅
- **AC-5（多人手動同步）**：兩個瀏覽器/裝置各開網頁版改不同項目 → 互按「↻ 重新整理」
  都看得到對方的更動。✅

**spec §8 的完整劇本**：Streamlit 新增候選餐廳並標「必須確認」→ 網頁版重新整理看到它在
未確認清單 → 網頁版標「已確認」→ 回 Streamlit「候選 / 確認」分頁用「📅 排入行程」把它排進某天某時段
→ 時間軸看到它、確認徽章為已確認。

> 更新：**網頁版現在也能排程了**。每張候選卡片有「📅 排入行程」（選天 + 時間 → 排入），
> 已排定的可「↩ 退回候選」。所以 spec §8 整套劇本在網頁版即可完成，不再有先前的限制。

---

## 4. 暫存起來的 WIP（沒有遺失）

開工前，working tree 有一段未 commit 的購物/AI 舊改動（SQLite 時代，與 Supabase 重構衝突）。
已用 `git stash` 安全保存：

```
git stash list          # stash@{0}: ... WIP shopping/AI (SQLite-era) ...
git stash show -p stash@{0}   # 看內容
```

它看起來已被 origin/main 的 Supabase 重構取代，但我沒有擅自丟棄。你確認不需要後可：
`git stash drop stash@{0}`。

---

## 5. 順帶修好的、與後續

- ✅ **購物模組已修好**：`page_shopping.py` 原本呼叫 Supabase 版 `db.py` 已不存在的
  `get_wishlist` / `add_wishlist_item` / `update_wishlist_status` / `delete_wishlist_item`，
  一進「購物」就崩潰。已重建 `wishlist` 表與這 4 個函式（走 Supabase）。
  跑 `supabase_schema.sql` 時會一起建好。
- 若想讓分享連結更難猜，可把 `trips.id` 改 UUID（目前是流水號，spec 已接受此風險）。
- `budget`（月預算）表目前沒有任何程式碼在用，故未建；之後要做預算追蹤再加。
