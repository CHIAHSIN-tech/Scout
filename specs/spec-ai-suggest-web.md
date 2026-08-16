# TASK: AI 生成行程（web 端）

> **Status**：draft → 執行中
> **Date**：2026-08-17
> **需求來源**：`buylist/BACKLOG.md` 第十章 A「AI 生成行程」，2026-08-17 Stanley 拍板要做且 **web 端要做**。
> **參照系統的盤點**：[`inventory-ai-suggest.md`](inventory-ai-suggest.md)（Phase 1 產物，證據在那裡，本檔不重述）

## OBJECTIVE

在合併版 web app 的行程 Tab 裡，使用者回答六題之後能拿到一份依天分好的行程建議，勾選後直接寫進該旅程，全程手機可用且 Gemini 金鑰不進前端。

## WHY IT MATTERS

Streamlit 退役（ADR-010）之後，「多輪問答生成整份行程」是**唯一沒有任何替代品**的能力——`buylist/BACKLOG.md` 自 2026-08-08 起就把它列為唯一重大缺口。現在規劃新旅程只能一筆一筆手動加，或貼現成的文字讓 AI 解析（`aiParseItinerary`），但那需要先有一份行程；從零開始規劃這件事現在做不到。

MCP server（ADR-016）讓 Claude 可以直接寫入行程，實質上已經覆蓋桌面情境。但 MCP 是本機 stdio 程序，**手機上的 Claude 連不到**，而本專案第一原則是手機優先（`CLAUDE.md`）。只靠 MCP 等於「規劃行程只能開筆電」，那是相對於 Streamlit 時代的功能倒退。做錯的代價：兩人在外面用手機想調整行程時無法生成，只能回家開電腦。

## SUCCESS MEASURED BY

> 全部從 repo 根目錄執行。驗證腳本只用 Node 內建模組。

- **A1.** 三支相關 JS 通過語法檢查。
  check：`node --check web/checklist.js && node --check web/netlify/functions/ai-suggest.js && node --check web/ai-suggest-core.js` exits 0
- **A2.** 六題依序存在，第 4 題是多選且恰有 10 個選項，題目文字與參照系統一致。
  check：`node scripts/check-ai-suggest.mjs --questions` exits 0
- **A3.** 組出的 prompt 帶入全部六個答案，且包含參照系統的五條規則與七個輸出欄位名。未填的答案以「未提供」出現（`extra` 為「無」）。
  check：`node scripts/check-ai-suggest.mjs --prompt` exits 0
- **A4.** 回應正規化：`category` 不在白名單 → `other`；`day` 夾到 `1..totalDays`；`start_time` 不合 `HH:MM` → `09:00`；`duration_minutes` 缺值 → `60`；`confirm_required` 與 `is_confirmed` 一律寫 `false`（不得為 null）。
  check：`node scripts/check-ai-suggest.mjs --normalise` exits 0
- **A5.** 解析容錯：帶 ```` ```json ```` 圍欄的回應能解析；非陣列、無法解析、空回應三種情況各自產生不同的中文錯誤訊息，且訊息都說明下一步。
  check：`node scripts/check-ai-suggest.mjs --parse` exits 0
- **A6.** 前端不含任何 Gemini 金鑰字面值。
  check：`git grep -nE "AIza[0-9A-Za-z_-]{10,}" -- web/ scripts/` 回空（exit 1 即通過）
- **A7.** 未引入建置相依。
  check：`test ! -f package.json && test ! -d web/node_modules` exits 0
- **A8.** 行程 Tab 有進入點，且問答與結果兩個階段的 DOM 都存在。
  check：`node scripts/check-ai-suggest.mjs --wiring` exits 0

## GRAPH

**Routing gate：無觸發 → 單節點（single node, single verifier）。**

逐項對照：兩塊工作（前端問答 UI、Netlify Function proxy）都是同一個人用同一套工具寫，無專業分工；寫入路徑不互斥（`checklist.js` 兩邊都要動），本來就該循序；驗證全是命令式檢查，不是產出者自評印象；無階段失敗會污染其他階段；路由無需稽核。依 §2「a node that could be inlined is not a node」，本任務為單一 agent 迴圈，不畫多節點圖、不建 `state/graph-state.json`。

## INTERVIEW（一批問完，每題帶預設；沉默即採預設）

- **Q1.** 六題要不要精簡？ — **預設：全數移植，一題不刪。** 盤點時沒有任何使用紀錄可以判斷哪一題沒用（inventory「無法觀察的部分」第 2 點），憑感覺刪題是拿掉別人可能在用的東西。題數過長列為待觀察。
- **Q2.** 生成的項目要直接排入某天，還是先進候選？ — **預設：依 AI 給的 `day` 直接排入。** 參照系統就是這樣，而且候選的語意是「想去但還沒決定哪天」，AI 已經決定了哪天。
- **Q3.** 勾選預設全勾還是全不勾？ — **預設：全不勾**（同參照系統）。多勾一個要刪很麻煩（刪除要另外操作），少勾一個只要再按一次。
- **Q4.** 生成失敗時已填的答案要保留嗎？ — **預設：保留。** 六題重填的成本很高，失敗多半是暫時性的。
- **Q5.** 要不要沿用既有的 `ai-parse` function 而不是新開一支？ — **預設：新開 `ai-suggest.js`。** 兩者 prompt 與輸出契約不同（一個解析既有文字、一個從零生成），塞進同一支會變成靠參數分支的雙形態 function。

## BOUNDS

- **Loop-back cap：** 每階段最多 2 次退回；用盡後繼續前進，記入 `KNOWN_ISSUES.md`，對應 A-item 標 **FAIL**。
- **Scope-cut order（先砍前面）：** 「全選 / 取消全選」兩顆按鈕 → 已答題目的回顧顯示 → 「重新開始 / 重來」 → 其餘不砍。
  理由：這三項都是便利性，砍掉核心流程（問答 → 生成 → 勾選 → 寫入）仍完整。
- **Never cut：** 六題問答（A2）、prompt 五規則（A3）、回應正規化（A4）、金鑰不進前端（A6）、無 build step（A7）。
- **砍任何 A-item 等同修改規格**，必須寫入 `DECISIONS.md`，不得靜默移除。
- **External dependencies stubbed：** Gemini API 金鑰必須由**人**在 Netlify 環境變數設定（`GEMINI_API_KEY`），本 session 無法代勞。因此「線上真的生成得出行程」**不列入自動驗收**；A-item 只驗到「function 收到請求後會用正確的 prompt 呼叫 Gemini、並正確處理它的回應」，用假的 fetch 驗。**不得宣稱線上已可用。**

## EXECUTION RULES

1. **一次訪談。** 問題只在開始問，一批問完，每題帶預設；沉默即採預設。之後遇到阻礙不再回頭問，改寫入 `DECISIONS.md`（什麼卡住、假設了什麼、如何回復）後繼續。
2. **驗證器優先於印象。** 一個階段完成的定義是它的驗證命令 exit 0。主觀疑慮（「這個間距看起來怪」）寫進 `KNOWN_ISSUES.md` 當建議，只有命令可檢測的失敗才退回重做。
3. **審查只讀且抱持懷疑。** 判定只有 PASS/FAIL 並附 `檔案:行號` 證據。修正由產出方進行，複查只重驗失敗的部分。
4. **失敗隔離。** 重試在階段內部完成；後續階段以前一階段完成為前提。
5. **必要產出物：** `ACCEPTANCE-ai-suggest.md`、`DECISIONS.md`（沿用既有檔，append）、`KNOWN_ISSUES.md`（同）、以及最終報告——第一節必須是 A1–A8 的 PASS/FAIL 表格與原始命令輸出。任一項 FAIL，整趟報告為失敗。
6. **不得偽造通過。** 驗證腳本不得為了通過而放寬條件；做不到就標 FAIL 並說明。
7. **先偵察後施工。** 動手前先讀 `web/checklist.js` 既有的 AI 匯入路徑（`aiParseItinerary`／`aiGeminiRaw`／`aiRowToFields`）與 `web/netlify/functions/ai-parse.js`。**共用邏輯只能有一份**：正規化與 prompt 組裝集中在新檔 `web/ai-suggest-core.js`，由 `checklist.js` 與驗證腳本共用，不得存在第二份實作。

**技術限制（違反即等於任務失敗）：**
- 本 repo 刻意無 build step（ADR-010）。驗證腳本放 `scripts/`，只用 Node 內建模組，不得新增 `package.json`。
- `web/ai-suggest-core.js` 必須同時能被瀏覽器的傳統 `<script>` 與 Node 驗證腳本讀取——掛載到全域物件，Node 端用 `node:vm` 以假的 `window` 求值（同 `web/export-formats.js` 的既有做法）。
- 金鑰只能存在於 Netlify Function 的 `process.env`（ADR-011）。前端不得有金鑰字面值。

## NON-GOALS

以下明確不做，在本次執行中出現一律視為越界：

- **不做 Streamlit 的視覺 parity**。參照系統跑不起來（inventory「無法觀察的部分」第 1 點），間距與視覺表現無從比對，只做**行為** parity。
- **不移植參照系統的四個缺陷**（`category` 無白名單、`day` 未夾範圍、確認兩軸未設、勾選狀態雙軌）。詳見 inventory「參照系統本身的缺陷」。
- **不做 503 自動重試**。參照系統的 `ai.py` 有，但無任何日誌證明它被觸發過，且現行 `ai-parse.js` 沒有重試也運作正常。延後。
- **不精簡題數**（見 Q1）。
- **不改資料表結構**，不新增欄位、不跑 DDL。
- **不動購物 Tab**、不動 MCP server、不動既有的「AI 匯入行程」（貼文字解析）——那是另一條路徑，兩者並存。
- **不做生成結果的編輯**。勾選加入後要改，用既有的卡片編輯功能（`spec-itinerary-restore-edit-delete` 已完成）。
- **不做多輪對話式修正**（「幫我把第二天改成輕鬆一點」）。這版是一次性問答 → 生成。

## CHECKLIST ANSWERED

> §6 五問，逐項書面作答。

**1. 沒寫這段程式的人能否逐項檢查每個 A-item？**
能。A1 是三個 `node --check`；A6 是一行 `git grep`；A7 是兩個檔案系統斷言；A2–A5、A8 是 `scripts/check-ai-suggest.mjs` 的五個旗標，以固定測試資料執行、與畫面無關。所有命令都寫在 A-item 旁，複製即可執行。

**2. 是否有任何宣稱可用、實則依賴外部核准的東西？**
有一項，已誠實標示：**Gemini 金鑰必須由人在 Netlify 環境變數設定**，本 session 做不到。因此 A-item 只驗「prompt 組裝正確、回應處理正確」（用假 fetch），**不驗**「線上真的生成得出行程」。後者不在本 session 能力範圍，不得宣稱通過。另有一項既有阻塞：Netlify 的 Git 自動部署目前是壞的（2026-08-17 實測 deploy preview 失敗），所以就算金鑰設好，這個功能也要等部署修好才會上線。

**3. Scope-cut order 是否保護驗收表？**
是。砍除順序（全選鈕 → 已答回顧 → 重新開始）**完全不對應任何 A-item**——三者都是便利性功能，砍掉之後 A1–A8 仍全部可驗。Never-cut 清單直接對應 A2/A3/A4/A6/A7。砍任一 A-item 需寫入 `DECISIONS.md`。

**4. 參照系統的表面是否每一項都落進「做／不做／延後」三個桶之一？**
是，逐項對照見 [`inventory-ai-suggest.md`](inventory-ai-suggest.md) 的「桶總表」。在範圍內：A 問題清單全部、B 互動行為全部、C prompt 全部、D 解析前四項、E 結果階段全部、F 寫入欄位全部、G 分類對照。不做：session_state 結構、視覺 parity、四個缺陷。延後：503 重試、題數精簡。**沒有任何一項落在三個桶之外**。

**5. 沒讀過 Graph Protocol 的人能否執行這份規格？**
能。執行規則（一次訪談、驗證器 exit 0 才算完成、只有命令可檢測的失敗才退回、退回上限 2 次、必要產出物、報告首節為 PASS/FAIL 表）已完整重述於 EXECUTION RULES 與 BOUNDS，不是引用。技術限制（無 build step、腳本只用內建模組、共用邏輯只能一份、金鑰只在後端）亦寫在規格內。本規格可獨立貼出執行，不需附上 protocol。

---

Written under GRAPH_PROTOCOL v2.2.
