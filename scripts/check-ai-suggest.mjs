// check-ai-suggest.mjs — AI 生成行程的驗收（specs/spec-ai-suggest-web.md 的 A2–A5、A8）。
//
//   node scripts/check-ai-suggest.mjs --questions   A2
//   node scripts/check-ai-suggest.mjs --prompt      A3
//   node scripts/check-ai-suggest.mjs --normalise   A4
//   node scripts/check-ai-suggest.mjs --parse       A5
//   node scripts/check-ai-suggest.mjs --wiring      A8
//   node scripts/check-ai-suggest.mjs               全部
//
// 只用 Node 內建模組（本 repo 無 build step）。web/ai-suggest-core.js 是給瀏覽器的
// 傳統 script，這裡用 node:vm 餵假的 window 求值後取出純函式——同一份實作，不另寫一套。

import { readFileSync } from "node:fs";
import { createContext, runInContext } from "node:vm";

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

const sandbox = { window: {}, console };
createContext(sandbox);
runInContext(read("web/ai-suggest-core.js"), sandbox, { filename: "web/ai-suggest-core.js" });
const X = sandbox.window.ScoutAiSuggest;
if (!X) { console.error("FAIL：ai-suggest-core.js 沒有掛上 window.ScoutAiSuggest"); process.exit(1); }

const results = [];
const ck = (id, cond, msg) => { results.push({ id, ok: !!cond, msg }); return !!cond; };

// ── A2：六題 ──
function a2() {
  const q = X.QUESTIONS;
  ck("A2", Array.isArray(q) && q.length === 6, `恰好 6 題（實際 ${q && q.length}）`);
  const keys = q.map((x) => x.key).join(",");
  ck("A2", keys === "destination,days,people,preference,budget,extra",
    `題目順序正確：${keys}`);
  ck("A2", q[3].type === "multiselect", "第 4 題是多選");
  ck("A2", q[3].options.length === 10, `第 4 題恰有 10 個選項（實際 ${q[3].options.length}）`);
  // 與參照系統逐字比對（inventory §A）
  const expect = [
    "你們打算去哪裡旅行？", "預計幾天幾夜？", "幾個人一起去？有哪些成員？",
    "旅遊偏好是什麼？", "每人每天大約的預算是多少？", "還有什麼特別需求或想避開的？（可跳過）",
  ];
  q.forEach((x, i) => ck("A2", x.label === expect[i], `第 ${i + 1} 題題目與參照系統一致`));
  ck("A2", q[5].optional === true, "最後一題標記為可跳過");
}

// ── A3：prompt ──
function a3() {
  const answers = {
    destination: "沖繩", days: "4 天 3 夜", people: "2 大人",
    preference: "🍜 在地美食、🌿 自然風景", budget: "3000 台幣", extra: "",
  };
  const p = X.buildPrompt(answers);
  for (const [k, v] of Object.entries(answers)) {
    if (k === "extra") continue;
    ck("A3", p.includes(v), `prompt 帶入 ${k}：${v}`);
  }
  ck("A3", p.includes("特殊需求：無"), "extra 留空時填「無」");
  ck("A3", X.buildPrompt({ destination: "京都" }).includes("天數：未提供"), "其他欄位留空時填「未提供」");

  const rules = [
    "根據天數安排每天的行程，早上約 09:00 開始，合理分配時間",
    "景點大約 90-120 分鐘，餐廳 60-90 分鐘，購物 60-90 分鐘",
    "每天安排 4-6 個項目，包含早餐、午餐、晚餐和景點",
    "行程之間預留合理的移動時間",
    "只回傳 JSON 陣列，不要任何說明文字或 markdown",
  ];
  rules.forEach((r, i) => ck("A3", p.includes(r), `含參照系統第 ${i + 1} 條規則`));
  ["day", "name", "category", "start_time", "duration_minutes", "location", "notes"]
    .forEach((f) => ck("A3", p.includes(`"${f}"`), `輸出格式含欄位 ${f}`));
}

// ── A4：正規化（這裡就是「不移植參照系統缺陷」的驗證點）──
function a4() {
  const TOTAL = 4;
  const n = (row) => X.normaliseItem(row, TOTAL);

  ck("A4", n({ name: "X", category: "美食" }).category === "other",
    "category 不在白名單 → other（參照系統缺陷 1，不移植）");
  ck("A4", n({ name: "X", category: "RESTAURANT" }).category === "restaurant",
    "category 大小寫不敏感");
  ck("A4", n({ name: "X", day: 9 }).day_number === TOTAL,
    `day 超過旅程天數 → 夾到 ${TOTAL}（參照系統缺陷 2，不移植）`);
  ck("A4", n({ name: "X", day: 0 }).day_number === 1, "day 小於 1 → 1");
  ck("A4", n({ name: "X", day: "3" }).day_number === 3, "day 是字串也能吃");
  ck("A4", n({ name: "X" }).day_number === 1, "day 缺值 → 1");

  ck("A4", n({ name: "X", start_time: "25:00" }).start_time === "09:00", "時間不合法 → 09:00");
  ck("A4", n({ name: "X", start_time: "上午九點" }).start_time === "09:00", "非 HH:MM → 09:00");
  ck("A4", n({ name: "X", start_time: "9:30" }).start_time === "09:30", "個位數小時補零");
  ck("A4", n({ name: "X" }).start_time === "09:00", "時間缺值 → 09:00");

  ck("A4", n({ name: "X" }).duration_minutes === 60, "duration 缺值 → 60");
  ck("A4", n({ name: "X", duration_minutes: 0 }).duration_minutes === 60, "duration 為 0 → 60");
  ck("A4", n({ name: "X", duration_minutes: 90 }).duration_minutes === 90, "duration 有值時照用");

  const item = n({ name: "X" });
  ck("A4", item.confirm_required === false && item.is_confirmed === false,
    "確認兩軸明確寫 false，不留 null（參照系統缺陷 3，不移植）");
  ck("A4", item.source === "ai", "source 標記為 ai");
  ck("A4", n({ name: "   " }) === null, "沒有名稱的項目直接丟掉，不寫「未命名」進資料庫");
  ck("A4", X.normaliseAll([{ name: "A" }, { name: "" }, { name: "B" }], TOTAL).length === 2,
    "normaliseAll 會濾掉無名項目");
  // totalDays 為 0（旅程沒填日期）時不該把 day 夾成 0
  ck("A4", X.normaliseItem({ name: "X", day: 5 }, 0).day_number === 5,
    "旅程沒有天數資訊時不夾 day");
}

// ── A5：解析容錯 ──
function a5() {
  const good = '[{"day":1,"name":"美麗海水族館"}]';
  ck("A5", X.parseSuggestions(good).items.length === 1, "純 JSON 可解析");
  ck("A5", X.parseSuggestions("```json\n" + good + "\n```").items.length === 1,
    "帶 ```json 圍欄可解析");
  ck("A5", X.parseSuggestions("這是你的行程：\n" + good).items.length === 1,
    "前面多一句話仍可解析");

  const errs = {
    empty: X.parseSuggestions("").error,
    notArray: X.parseSuggestions('{"day":1}').error,
    unparsable: X.parseSuggestions("完全不是 JSON").error,
    emptyArray: X.parseSuggestions("[]").error,
  };
  Object.entries(errs).forEach(([k, v]) => ck("A5", !!v, `${k} 產生錯誤訊息`));
  const uniq = new Set(Object.values(errs));
  ck("A5", uniq.size === 4, `四種失敗各有不同訊息（實際 ${uniq.size} 種）`);
  Object.entries(errs).forEach(([k, v]) =>
    ck("A5", /重新生成|再試一次|具體/.test(v), `${k} 的訊息說明下一步`));
}

// ── A8：接線 ──
function a8() {
  const html = read("web/index.html");
  const js = read("web/checklist.js");
  ck("A8", html.includes('src="ai-suggest-core.js"'), "index.html 載入共用核心");
  ck("A8", html.indexOf('ai-suggest-core.js') < html.indexOf('src="checklist.js"'),
    "共用核心排在 checklist.js 之前");
  ck("A8", html.includes('id="ai-suggest-backdrop"'), "modal 容器存在");
  ck("A8", html.includes('id="ai-suggest-body"'), "modal 內容容器存在");
  ck("A8", js.includes('id="ai-suggest-open"'), "toolbar 有進入點");
  ck("A8", js.includes("openAiSuggestModal"), "進入點有對應的開啟函式");
  ck("A8", js.includes("asQuestionHtml") && js.includes("asResultHtml"), "問答與結果兩階段都有渲染函式");
  // 生成路徑不得有前端金鑰 fallback
  ck("A8", !/asCallBackend[\s\S]{0,800}GEMINI_API_KEY/.test(js),
    "生成路徑不走前端金鑰，只走 Netlify Function");
}

const RUN = { "--questions": a2, "--prompt": a3, "--normalise": a4, "--parse": a5, "--wiring": a8 };
const args = process.argv.slice(2);
for (const [flag, fn] of Object.entries(RUN)) if (args.length === 0 || args.includes(flag)) fn();

let failed = 0;
for (const r of results) { if (!r.ok) failed++; console.log(`${r.ok ? "  ok  " : "  FAIL"} ${r.id}  ${r.msg}`); }
console.log(failed === 0 ? `全部通過（${results.length} 項斷言）` : `${failed} / ${results.length} 項斷言失敗`);
process.exit(failed === 0 ? 0 : 1);
