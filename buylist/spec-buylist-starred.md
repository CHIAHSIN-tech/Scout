# Spec — BuyList 已買星號收藏（可再買）＋ 全站改用 Scout CIS 配色

> **狀態說明**：本文取代 `spec-buylist-want-bought.md` 與其 Kickoff Prompt（已刪除）。
> 原規格假設的技術棧（Vue + Firebase、想買/已買雙分頁）與實際已完工的 app（vanilla HTML/JS + Supabase、單一清單 + 篩選）不符，予以廢棄。
> 本文對準 `BUYLIST_STATE.md` 描述的真實現況撰寫，分兩部分：
> - **Part A**：已買星號收藏功能（小型增量）
> - **Part B**：全站配色從現行的 blue/green/amber 系統改為 Scout 品牌 CIS 的 sage/linen/wheat 系統（範疇較大，在星號功能討論中追加）

---

## 0. Meta
- **Appetite**：Part A 半天可完工；Part B 因為要盤點並改動全部色彩定義點，抓 1 天
- **Status**：done（Part A + Part B 皆已落地，commit `de84c78`）
- **Date**：2026-07-12
- **Assignee**：Stanley（實作，延續既有 one-shot 執行模式）/ CHIA（審核 & 決策）
- **Technology Stack**：Vanilla HTML/CSS/JS（單檔 `index.html`，無 build）/ Supabase（專案 `kdmmjlaajqxjmiahfvos`，表 `buylist_items`）
- **Repo**：private `Scout` repo，`buylist/index.html`（本機執行，雙擊 `run.bat`/`run.command`）
- **對應現有文件**：本規格內容應併入 `Scout/specs/buylist-handoff.md`（SSOT），並更新 `BUYLIST_STATE.md` §5/§6
- **CIS 參考來源**：`Scout/scout_cis.html`（品牌色彩/字型系統文件）

---

# Part A — 已買星號收藏（可再買）

## 1. Problem Statement

**背景**  
BuyList 已買項目目前只有「打勾（`bought`）+ 刪除線」的單一狀態，無法標記「這個東西買了之後，好用到還想再買」。

**現狀**  
已買項目全部長得一樣，想回顧「哪些東西值得回購」時，只能一個個點開連結、回想。

**目標**  
在已買項目上加一個「星號」標記，代表「這個可以再買一次」，方便未來快速篩選出真正值得回購的東西。

---

## 2. JTBD

當我勾選某個東西已買，之後發現它很好用，我想標記「這個值得再買」，所以我未來想回購時能快速找到它。

---

## 3. Success Criteria

- [ ] 星號只能在 `bought = true` 的項目上切換；未打勾的項目看不到或無法點擊星號
- [ ] 若項目被「移回未買」（取消打勾），星號狀態視覺上不影響清單邏輯，但依 4.1 規則處理資料
- [ ] 視覺與現有 app 一致（沿用既有 CSS 變數，不新增色票系統）

---

## 4. MoSCoW

### Must
- [ ] `buylist_items` 新增欄位 `starred boolean default false`
- [ ] 已買項目（`item.bought === true`）卡片上顯示星號圖示，可點擊切換
- [ ] 未打勾（`bought === false`）的項目不顯示星號切換按鈕（或顯示但不可點擊，兩者擇一，建議直接不渲染較乾淨）
- [ ] 點擊星號 → 呼叫 Supabase `update({starred: val})`，即時生效，失敗時比照現有 `toggleBought` 的錯誤處理模式（`setStatus('更新失敗：'+error.message,'err')`）
- [ ] 星號狀態透過既有 Realtime 訂閱機制自動同步給另一位使用者（沿用現有機制，不用另外設計）
- [ ] 篩選列（`#f-status`）新增「已買・星號」選項，只顯示 `bought === true 且 starred === true` 的項目

### Should
- （無，MVP 已是完整功能）

### Could
- [ ] 已買星號項目在清單排序上優先顯示

### Won't
- [ ] 未打勾項目也能加星（已由你確認排除）
- [ ] 星號有多重程度（例如 1-5 星）——維持單純的開/關兩態，比照 `bought` 的簡單布林設計

---

## 4.1 資料規則

- **星號依附於「已買」狀態，但不因取消打勾而自動清除。** 若使用者誤打勾又取消，`starred` 欄位維持原值不變（不做自動清空）。理由：避免使用者手滑取消打勾時，連帶把已經標記的星號弄丟；如果要清掉星號，使用者可以自己再點一次星號取消
- **UI 層面**：只有 `bought === true` 時才顯示/允許操作星號按鈕；`bought === false` 時，即使資料庫裡 `starred` 仍是 `true`，UI 也不顯示星號（因為按鈕本身不渲染），這不影響資料正確性，只是不給操作入口

---

## 5. Scope & Interfaces

### 涉及的檔案
- `buylist/index.html`（唯一檔案，單檔架構）
  - CSS：新增 `.star` 相關樣式（緊鄰現有 `.chk` 樣式）
  - JS：`renderList()` 函式內，在已買項目的卡片渲染邏輯加入星號按鈕；新增 `toggleStarred(id, val)` 函式，比照現有 `toggleBought(id, val)` 寫法
- `buylist/buylist-schema.sql`：新增一行 `alter table ... add column if not exists starred boolean default false;`（冪等寫法，比照現有慣例）

### 視覺規格（沿用現有 CSS 變數，不新增色票）

**星號顏色**：使用既有 `--amber`（`#E08A4A`，目前用於「想要」標籤與「後續成本」提示的暖色調）作為星號填色，`--faint`（`#9AA0A8`，目前用於未啟用圖示/淡化文字）作為未收藏的空心狀態。**（已確認）**

**建議位置與樣式**：比照 `.chk`（打勾按鈕，26×26px 圓形）的視覺語言，星號按鈕可以放在打勾按鈕旁邊或項目卡片右側（靠近刪除鈕），尺寸略小（例如 20-22px），未啟用時空心、`--faint` 描邊；啟用時 `--amber` 填色。

```css
/* 建議樣式，緊鄰 .chk 樣式之後 */
.star{flex:none;width:22px;height:22px;border:none;background:none;cursor:pointer;
  color:var(--faint);font-size:18px;padding:0;margin-top:2px;display:none;}
.item.bought .star{display:inline-flex;align-items:center;justify-content:center;}
.star.on{color:var(--amber);}
.star:hover{color:var(--amber);}
```

### Out of Scope
- 多重評分、評語
- 星號篩選（列為 Could，非本次 Must）
- 任何 UI 框架遷移（維持 vanilla HTML/JS 單檔架構，不因為這個小功能引入 build tool）

---

## 6. Acceptance Criteria

- [ ] **AC-1**：`buylist_items` 表新增 `starred` 欄位，預設值 `false`，既有資料自動補上預設值（`alter table ... add column if not exists`，不影響既有列）
- [ ] **AC-2**：未打勾的項目，卡片上不出現星號按鈕
- [ ] **AC-3**：打勾（已買）的項目，卡片上出現星號按鈕，初始為空心（`--faint`）
- [ ] **AC-4**：點擊星號 → 變為實心 `--amber`，且 Supabase 對應列 `starred` 更新為 `true`
- [ ] **AC-5**：再點一次 → 變回空心，`starred` 更新為 `false`
- [ ] **AC-6**：取消打勾（移回未買）→ 星號按鈕消失，但 `starred` 欄位值不變（重新打勾後星號狀態會恢復顯示原本的值）
- [ ] **AC-7**：兩個使用者同時開啟頁面，一方切換星號，另一方畫面透過既有 Realtime 訂閱在數秒內同步更新
- [ ] **AC-8**：Supabase 寫入失敗時（如離線），出現錯誤提示（比照 `toggleBought` 的 `setStatus(..., 'err')` 模式），不可靜默失敗
- [ ] **AC-9**：篩選列出現「已買・星號」選項；點選後，清單只顯示 `bought === true 且 starred === true` 的項目
- [ ] **AC-10**：切換回「全部」/「本月」/「已買」等其他篩選 → 「已買・星號」篩選解除，清單恢復對應篩選結果

---

## 7. 給 Stanley 的實作筆記

這個功能足夠小，不需要拆多個 loop、也不需要正式的 Kickoff Prompt 文件——比照你們既有的執行模式（讀 `BUYLIST_STATE.md` + 這份 spec，直接動手）。

**具體改動點（對照現有程式碼行號，實際行號可能因版本略有出入）：**

1. **Schema**：在 `buylist-schema.sql` 加一行：
   ```sql
   alter table buylist_items add column if not exists starred boolean default false;
   ```
   在你自己的 Supabase SQL Editor 貼上執行（比照現有欄位的加法模式）。

2. **CSS**：在 `.chk` 樣式區塊（約第 76-78 行）後面加上星號按鈕樣式（見上方第 5 節建議樣式）。

3. **JS — `renderList()` 函式**（約第 252-273 行）：
   - 在卡片 HTML 組裝處，`.chk` 按鈕後面加一個星號按鈕，只在 `i.bought` 為真時渲染有意義的 `on` class：
     ```js
     +(i.bought ? '<button class="star '+(i.starred?'on':'')+'" data-id="'+i.id+'" data-s="'+(i.starred?1:0)+'" title="標記可回購">★</button>' : '')
     ```
   - 在 `box.querySelectorAll('.chk')...` 那行下面，新增對應的星號事件綁定：
     ```js
     box.querySelectorAll('.star').forEach(b=>b.addEventListener('click',()=>toggleStarred(b.dataset.id,b.dataset.s!=='1')));
     ```

4. **JS — 新增 `toggleStarred` 函式**，緊鄰現有 `toggleBought`（約第 302 行）：
   ```js
   async function toggleStarred(id,val){const {error}=await sb.from('buylist_items').update({starred:val}).eq('id',id);if(error)setStatus('更新失敗：'+error.message,'err');}
   ```

5. **HTML — 篩選列**（約第 152 行），在 `#f-status` 的按鈕群組裡加一個新選項：
   ```html
   <span class="seg" id="f-status">
     <button data-v="all" class="on">全部</button>
     <button data-v="month">本月</button>
     <button data-v="bought">已買</button>
     <button data-v="starred">已買・星號</button>
   </span>
   ```
   點擊事件已經是資料驅動（第 314 行的 `$('f-status').addEventListener` 讀取 `b.dataset.v`），這個按鈕不需要額外綁定事件。

6. **JS — `visibleItems()` 函式**（約第 234-237 行），加一個篩選條件：
   ```js
   if(fStatus==='starred' && !(i.bought && i.starred)) return false;
   ```
   加在現有 `if(fStatus==='bought' && !i.bought) return false;` 那行下面即可。

這六步做完，AC-1 ~ AC-10 應該都會通過（Realtime 同步、錯誤提示都是沿用既有機制，不用另外處理）。

---

---

# Part B — 全站配色改為 Scout CIS

## B.1 背景

在討論星號顏色時發現：`index.html` 目前的配色（`--blue`/`--green`/`--amber`/`--red` 系統）並未依照 `scout_cis.html` 定義的品牌色彩系統（sage/linen/wheat）製作。CHIA 決定這次順便把整站配色改成 CIS 標準，讓 BuyList 跟 Scout 品牌其他模組視覺一致。

## B.2 色彩對應決策（已定案）

CIS 只有 3 個色系（sage/linen/wheat），但現有 app 編碼了 6 種語意分類（迫切度 3 種 + 取得難易度 3 種）。三色系裝不下六種語意，經過討論，決定用「同色系不同深淺」處理大部分組別，並刻意保留一組撞色（因為語意本來就相近，靠文字標籤消除混淆）。

### 全域 Token 對應

| 用途 | 原 Token | 原值 | 新值（CIS） |
|---|---|---|---|
| 頁面背景 | `--bg` | `#F5F6F8` | `#F5F0EA`（linen-50） |
| 卡片背景 | `--card` | `#FFFFFF` | `#FFFFFF`（不變） |
| 主要文字 | `--ink` | `#1A1C1F` | `#3C3830`（linen-900） |
| 次要文字 | `--muted` | `#6B7079` | `#6B6558`（linen-700） |
| 淡化文字 | `--faint` | `#9AA0A8` | `#A8A298`（linen-400） |
| 邊框 | `--line` | `#E7E9ED` | `#DCD8D0`（linen-200） |
| 邊框（淺） | `--line-soft` | `#EFF1F4` | `#F5F0EA`（linen-50） |
| 主要動作/啟用態 | `--blue` | `#29ABE2` | `#3D6B54`（sage-800） |
| 主要動作 hover | `--blue-d` | `#1f8fc0` | `#2A4D3A`（sage-900） |
| 已買打勾 | `--green` | `#21A67A` | `#5C8C72`（sage-600） |
| 想要／星號 | `--amber` | `#E08A4A` | `#C4915A`（wheat-400） |
| 需要／警示／爆預算 | `--red` | `#C0392B` | `#7A5230`（wheat-700） |
| 需要（迫切度按鈕態） | `--need` | `#C0392B` | `#7A5230`（wheat-700） |
| 想要（迫切度按鈕態） | `--want` | `#E08A4A` | `#C4915A`（wheat-400） |

### 標籤與矩陣的個別對應（非 CSS 變數，寫死在 class 裡）

| 標籤 | 原背景 / 文字 | 新背景 / 文字 |
|---|---|---|
| 迫切度：需要 | `#FBEAE8` / `var(--need)` | `#E8C898`（wheat-200） / `#7A5230`（wheat-700） |
| 迫切度：想要 | `#FCEFDD` / `#A8602A` | `#FBF0E0`（wheat-50） / `#C4915A`（wheat-400） |
| 迫切度：再看看 | `#EEF0F2` / `var(--muted)` | `#F5F0EA`（linen-50） / `#6B6558`（linen-700，即改完的 `--muted`，此項不用動，會自動繼承） |
| 取得：台灣易 | `#E6F2EA` / `#1B7A52` | `#EAF2ED`（sage-50） / `#5C8C72`（sage-600） |
| 取得：需國外 | `#EAF1FB` / `#2B6CB0` | `#F5F0EA`（linen-50） / `#3C3830`（linen-900，用深色中性拉開跟「再看看」的層次） |
| 取得：稀有難找 | `#F3E8F5` / `#8E44AD` | `#FBF0E0`（wheat-50） / `#7A5230`（wheat-700，**刻意跟「需要」同色系**，語意相近，文字標籤已足夠區分） |
| 分類標籤 | `#F0EFEA` / `#7A6A2A` | `#F5F0EA`（linen-50） / `#A8A298`（linen-400） |
| 本月想買 | `#EAF1FB` / `var(--blue)` | `#EAF2ED`（sage-50） / `#3D6B54`（sage-800，此項改完 `--blue` 會自動繼承，只需改背景） |
| 之後再說 | `#EEF0F2` / `var(--muted)` | `#F5F0EA`（linen-50，此項只需改背景，文字繼承 `--muted`） |
| 2×2矩陣：高迫切+高價 | 底 `#FBEEEC` 邊 `#F0D5D0` | 底 `#E8C898`（wheat-200） 邊 `#C4915A`（wheat-400） |
| 2×2矩陣：高迫切+低價 | 底 `#FCF4ED` 邊 `#F2E2D0` | 底 `#FBF0E0`（wheat-50） 邊 `#E8C898`（wheat-200） |

### rgba 焦點光暈（非 hex，需另外處理）

輸入框 focus 狀態用的是 `rgba(41,171,226,.15)`（藍色透明版本），CSS 變數換色不會自動更新這個，需要手動改成 `rgba(61,107,84,.15)`（sage-800 的 RGB 版本）。

---

## B.3 給 Stanley 的精確改動清單（對照現有 `index.html` 行號）

> 行號以目前上傳版本為準，實際版本可能因後續改動略有出入，請以內容比對為準，不要單純依賴行號。

**1. 根變數區塊（約第 11-14 行）** — 改這裡之後，大部分下游樣式（`.budget input:focus`、`.addbtn`、`.chk`、`.filters .seg button.on`、`.viewtabs button.on`、`.imeta a`、`.idel:hover`、`.status .dot` 等）會自動繼承新色，不用逐一手動改：
```css
:root{
  --bg:#F5F0EA; --card:#FFFFFF; --ink:#3C3830; --muted:#6B6558; --faint:#A8A298;
  --line:#DCD8D0; --line-soft:#F5F0EA; --blue:#3D6B54; --blue-d:#2A4D3A;
  --green:#5C8C72; --amber:#C4915A; --red:#7A5230;
  --need:#7A5230; --want:#C4915A; --maybe:#6B6558;
  --r-lg:18px; --r-md:12px; --font:'Noto Sans TC',sans-serif;
}
```

**2. Focus 光暈（約第 39、50 行）** — 兩處 `rgba(41,171,226,.15)` 都改成 `rgba(61,107,84,.15)`

**3. 迫切度／取得難易度／分類／時間標籤（約第 85-88 行）**：
```css
.tag.u-need{background:#E8C898;color:var(--need);} .tag.u-want{background:#FBF0E0;color:var(--want);} .tag.u-maybe{background:#F5F0EA;color:var(--muted);}
.tag.a-easy{background:#EAF2ED;color:#5C8C72;} .tag.a-os{background:#F5F0EA;color:#3C3830;} .tag.a-rare{background:#FBF0E0;color:#7A5230;}
.tag.cat{background:#F5F0EA;color:#A8A298;}
.tag.tm{background:#EAF2ED;color:var(--blue);} .tag.later{background:#F5F0EA;color:var(--muted);}
```
（`u-want` 的文字色我從原本寫死的 `#A8602A` 改成直接用 `var(--want)`，跟 `u-need` 用 `var(--need)` 的寫法一致，減少一個寫死的色碼）

**4. 2×2 矩陣格底色（約第 101 行）**：
```css
.quad.q-hi-need{background:#E8C898;border-color:#C4915A;} .quad.q-lo-need{background:#FBF0E0;border-color:#E8C898;}
```

**5. 星號功能（Part A）** 的顏色本來就已經定案用 `wheat-400`/`wheat-700`，跟這次全站換色是同一套值，不用重複改。

---

## B.4 Acceptance Criteria（Part B）

- [ ] **AC-B1**：`:root` 區塊的顏色變數全部改為 CIS 對應值，畫面整體從藍/綠/橘調變成 sage 綠/wheat 棕/linen 米色調
- [ ] **AC-B2**：所有標籤（迫切度、取得難易度、分類、本月/之後）改用新色，肉眼比對跟上方 B.2 對照表一致
- [ ] **AC-B3**：2×2 矩陣視圖的格子底色改用新色
- [ ] **AC-B4**：輸入框 focus 狀態的光暈顏色改成 sage 色調，不再是藍色
- [ ] **AC-B5**：星號功能（Part A）用的 `wheat-400`/`wheat-700` 跟這次全站換色視覺一致，不會有兩套 wheat 色調混用的違和感
- [ ] **AC-B6**：實測「需要」標籤跟「稀有難找」標籤顏色相近（刻意保留），但文字仍清楚可辨（分別是「需要」「稀有難找」，不會混淆）
- [ ] **AC-B7**：手機寬度下畫面無跑版，換色不影響版面結構

---

## B.5 Open Questions（Part B）

（無，本輪待決定問題已全數定案：主色對應、警示色用 wheat-700、迫切度/取得難易度各自成階梯、保留「需要」與「稀有難找」撞色）

---

**簽核欄**

- [x] CHIA 確認 Part A（星號功能）規格與顏色選擇無誤
- [x] CHIA 確認 Part B（全站 CIS 換色）色彩對應表無誤
- [ ] 可交給 Stanley 開始實作（Part A + Part B 可一併進行，或分開處理，由 Stanley 視工作量決定）
