// check-cf-migration.mjs — Cloudflare 遷移的驗收（spec-scout-trip-page.md 的 A20–A25）。
//
//   node scripts/check-cf-migration.mjs            A20 ＋ A23 ＋ A25（純靜態檢查，不需要網路）
//   node scripts/check-cf-migration.mjs --history  A24（可回退：Netlify 設定必須最後才刪）
//   node scripts/check-cf-migration.mjs --worker   A22 的假 fetch 部分＋路由行為（真的把 Worker import 進來跑）
//   node scripts/check-cf-migration.mjs --live[=port]  A21／A22 的實跑部分（需要先開著 wrangler dev）
//   node scripts/check-cf-migration.mjs --all      以上全部
//
// 只用 Node 內建模組（本 repo 無 build step）。
//
// --worker 模式為什麼做得到：worker/index.js 是標準 ESM，只用 Request / Response / URL /
// fetch 這些 Node 26 也有的全域物件。所以可以直接 import 進來、把 globalThis.fetch 換成
// 假的，斷言它打了哪些 URL——不需要 Cloudflare 帳號，也不需要真的 Supabase。

import { readFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";

const root = new URL("../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
const exists = (p) => existsSync(new URL(p, root));

const results = [];
const ck = (id, cond, msg) => { results.push({ id, ok: !!cond, msg }); return !!cond; };

const args = process.argv.slice(2);
const has = (f) => args.includes(f) || args.includes("--all");
const liveArg = args.find((a) => a.startsWith("--live"));
const LIVE_PORT = liveArg && liveArg.includes("=") ? liveArg.split("=")[1] : "8788";

const git = (...a) => execFileSync("git", a, { cwd: new URL(".", root).pathname.replace(/^\/([A-Za-z]:)/, "$1"), encoding: "utf8" });

// ── A20：四支 Function 全數等價移植，沒有殘留的 Netlify 路徑 ──
function a20() {
  const worker = exists("worker/index.js") ? read("worker/index.js") : "";
  ck("A20a", worker.includes('"/api/ai-parse"'), "worker 路由涵蓋 /api/ai-parse");
  ck("A20a", worker.includes('"/api/ai-suggest"'), "worker 路由涵蓋 /api/ai-suggest");
  ck("A20a", worker.includes('"/api/share"'), "worker 路由涵蓋 /api/share");

  // (b) web/ 的 js / html 裡不得再有 .netlify/functions；_redirects 沒有副檔名，天生排除在外
  const leftovers = [];
  for (const f of ["web/index.html", "web/share.html", "web/checklist.js", "web/buylist.js",
                   "web/shell.js", "web/export-formats.js", "web/ai-suggest-core.js", "web/sw.js"]) {
    if (exists(f) && read(f).includes(".netlify/functions")) leftovers.push(f);
  }
  ck("A20b", leftovers.length === 0, `web/ 的 js/html 沒有殘留 .netlify/functions（殘留：${leftovers.join(",") || "無"}）`);
  ck("A20b", exists("web/_redirects"), "web/_redirects 存在（舊網址的相容轉址）");
  if (exists("web/_redirects")) {
    const r = read("web/_redirects");
    ck("A20b", /^\/\.netlify\/functions\/\*\s+\/api\/:splat\s+30[18]\s*$/m.test(r),
      "轉址規則是 /.netlify/functions/* → /api/:splat（308，保留方法與 body）");
    const rules = r.split("\n").filter((l) => l.trim() && !l.trim().startsWith("#"));
    ck("A20b", rules.length === 1, `只有一條轉址規則，沒有開放式轉址（實際 ${rules.length} 條）`);
  }

  // (c) wrangler.toml 的必要區塊
  const toml = exists("wrangler.toml") ? read("wrangler.toml") : "";
  ck("A20c", /^\[assets\]/m.test(toml), "wrangler.toml 有 [assets]");
  ck("A20c", /^directory\s*=\s*"\.\/web"/m.test(toml), "[assets] 指向 ./web");
  ck("A20c", /^\[triggers\]/m.test(toml) && /^crons\s*=/m.test(toml), "wrangler.toml 有 [triggers] crons");

  // (d) 兩個 handler
  ck("A20d", /async fetch\(/.test(worker), "worker 匯出 fetch handler");
  ck("A20d", /async scheduled\(/.test(worker), "worker 匯出 scheduled handler");
  ck("A20d", /export default\s*\{/.test(worker), "以 export default 物件匯出（Workers 的模組格式）");

  // 錯誤訊息等價：四支原始 function 的關鍵字串必須還在
  for (const s of ["只接受 POST", "只接受 GET", "缺少行程文字", "缺少目的地",
                   "不提供整份清單", "tag 過長", "[keepalive]"]) {
    ck("A20", worker.includes(s), `錯誤訊息等價：保留「${s}」`);
  }
}

// ── A22：保活排程等價（靜態部分）──
function a22static() {
  const toml = exists("wrangler.toml") ? read("wrangler.toml") : "";
  ck("A22", toml.includes('crons = ["17 3 * * 1,4"]'),
    "cron 值與 netlify.toml 逐字相同：17 3 * * 1,4（台灣時間週一、四 11:17）");
}

// ── A23：ai-suggest-core.js 只有一份實作 ──
function a23() {
  const core = exists("web/ai-suggest-core.js") ? read("web/ai-suggest-core.js") : "";
  const worker = exists("worker/index.js") ? read("worker/index.js") : "";
  ck("A23", (core.match(/ScoutAiSuggest/g) || []).length >= 1, "web/ai-suggest-core.js 掛出 ScoutAiSuggest");
  ck("A23", worker.includes('import "../web/ai-suggest-core.js"'),
    "worker 以 side-effect import 載入同一個檔案（Workers 沒有 fs／vm）");
  ck("A23", worker.includes("globalThis.ScoutAiSuggest"), "worker 從 globalThis 取共用核心");
  // 這個檔案要同時被 <script>、node:vm 與 Worker 讀，所以不能有模組語法
  ck("A23", !/^\s*(import|export)\s/m.test(core), "共用核心不含 import/export 語法（三邊共用的前提）");
  ck("A23", core.includes('typeof window !== "undefined" ? window : globalThis'),
    "掛載目標優先 window、其次 globalThis（vm 沙箱餵的是 window，Worker 只有 globalThis）");
  // 只看程式碼：worker 的檔頭本來就會提到 node:fs／node:vm（在解釋為什麼不能用），
  // 不剝掉註解的話這裡會抓到自己的說明文字。
  const workerCode = worker.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  ck("A23", !/require\(|node:fs|node:vm/.test(workerCode), "worker 的程式碼不含 node:fs／node:vm 相依");
  // 第二份實作的守門員
  const dupes = ["web/checklist.js", "worker/index.js"].filter(
    (f) => exists(f) && /function buildPrompt\s*\(/.test(read(f)));
  ck("A23", dupes.length === 0, `buildPrompt 只有一份實作（重複出現於：${dupes.join(",") || "無"}）`);
}

// ── A25：金鑰沒有進版控 ──
function a25() {
  let hits = "";
  try {
    hits = git("grep", "-nE", "GEMINI_API_KEY\\s*[:=]\\s*['\"][A-Za-z0-9_-]{10,}", "--", ".", ":!*.example");
  } catch (e) {
    hits = ""; // git grep 找不到東西時 exit 1，那正是我們要的
  }
  ck("A25", hits.trim() === "", `版控裡沒有 GEMINI_API_KEY 的值（命中：${hits.trim() || "無"}）`);
  const toml = exists("wrangler.toml") ? read("wrangler.toml") : "";
  ck("A25", !/[A-Za-z0-9_-]{25,}/.test(toml.replace(/^#.*$/gm, "")),
    "wrangler.toml 的非註解部分沒有任何像金鑰的長字串");
  ck("A25", /wrangler secret put/.test(toml), "wrangler.toml 註明金鑰走 wrangler secret put");
}

// ── A24：可回退——Netlify 設定必須在最後一個 commit 才刪 ──
function a24() {
  const log = git("log", "--oneline", "--", "netlify.toml", "web/netlify/").trim();
  ck("A24", log !== "", "netlify.toml / web/netlify/ 在 git 歷史中存在過");

  // 找出「刪掉 Netlify 設定」的那個 commit（如果已經發生）
  const removals = git("log", "--diff-filter=D", "--format=%H|%s", "--", "netlify.toml")
    .trim().split("\n").filter(Boolean);
  if (removals.length === 0) {
    ck("A24", exists("netlify.toml"),
      "Netlify 設定仍在（還沒走到拆除那一步）——此時可回退的條件自動成立");
    return;
  }
  const [sha, subject] = removals[0].split("|");
  ck("A24", subject.includes("chore: 移除 Netlify 設定"),
    `拆除 commit 的訊息含「chore: 移除 Netlify 設定」（實際：${subject}）`);
  // 「拆除是最後一個 commit」的**本意**是「驗證通過之前不准拆」，不是「這個 repo
  // 從此不准再有任何 commit」。照字面驗的話，遷移之後任何一次提交都會讓這條永久變紅，
  // 那不是驗收條件，那是地雷。所以改驗三件真正代表本意的事：
  //   (1) 拆除的那個 commit 裡，驗收表已經在了 → 驗證先於拆除
  //   (2) 拆除是最後一個動到 Netlify 設定的 commit → 沒有人又偷偷加回來
  //   (3) 拆除之後沒有任何 commit 重新引入 Netlify 相依
  try {
    git("cat-file", "-e", `${sha}:ACCEPTANCE-trip-page.md`);
    ck("A24", true, "拆除的那個 commit 裡驗收表已經存在（驗證先於拆除）");
  } catch (_) {
    ck("A24", false, "拆除時驗收表還不存在——那代表先拆了才驗");
  }
  const touchedAfter = git("log", "--format=%h %s", `${sha}..HEAD`, "--",
    "netlify.toml", "web/netlify/").trim();
  ck("A24", touchedAfter === "",
    `拆除之後沒有 commit 再動過 Netlify 設定（實際：${touchedAfter || "無"}）`);
  ck("A24", !exists("netlify.toml") && !exists("web/netlify"),
    "現在的工作區裡確實沒有 Netlify 設定了");
  // 從「netlify.toml 被加進來」那一刻起，到拆除為止，每個 commit 它都必須還在。
  // 起點取 --diff-filter=A 的那個 commit，不是 repo 的第一個 commit——
  // netlify.toml 是 2026-09-05 才加的，在那之前沒有它是正常的，不是可回退性被破壞。
  const adds = git("log", "--diff-filter=A", "--format=%H", "--", "netlify.toml")
    .trim().split("\n").filter(Boolean);
  const addSha = adds[adds.length - 1];
  if (!ck("A24", !!addSha, "找得到 netlify.toml 被加進來的那個 commit")) return;
  const between = git("rev-list", `${addSha}..${sha}^`).trim().split("\n").filter(Boolean);
  let missing = 0;
  for (const c of between) {
    try { git("cat-file", "-e", `${c}:netlify.toml`); } catch (_) { missing++; }
  }
  ck("A24", missing === 0,
    `從加入到拆除之間的 ${between.length} 個 commit 裡，netlify.toml 都還在（缺少 ${missing} 個）`);
}

// ── A22 的「假 fetch 斷言打了兩個 Supabase URL」＋ 路由行為 ──
async function worker() {
  const mod = (await import(new URL("worker/index.js", root).href)).default;
  const realFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push(String(url));
    return new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try {
    // scheduled()：兩個 Supabase 專案各打一次最輕量查詢
    await mod.scheduled({ cron: "17 3 * * 1,4" }, {}, { waitUntil: () => {} });
    ck("A22", calls.length === 2, `scheduled() 打了 2 次（實際 ${calls.length}）`);
    ck("A22", calls.some((u) => u.includes("uarkccyqcqvgxukjcrey.supabase.co/rest/v1/trips")),
      "打到行程專案（Chia 的 Supabase）");
    ck("A22", calls.some((u) => u.includes("kdmmjlaajqxjmiahfvos.supabase.co/rest/v1/buylist_budget")),
      "打到購物專案（Stanley 的 Supabase）");
    ck("A22", calls.every((u) => u.includes("select=id&limit=1")), "兩次都是最輕量查詢 select=id&limit=1");

    // 環境變數可覆蓋（換專案不必改程式）
    calls.length = 0;
    await mod.scheduled({}, { CHECKLIST_SUPABASE_URL: "https://x.example" }, null);
    ck("A22", calls.some((u) => u.startsWith("https://x.example/")), "目標 URL 可由環境變數覆蓋");

    // fetch() 路由與錯誤行為，與 Netlify 版逐字等價
    const call = (path, init) => mod.fetch(new Request("https://scout.test" + path, init), {});
    let r = await call("/api/ai-parse", { method: "GET" });
    ck("A20", r.status === 405 && (await r.json()).error === "只接受 POST", "GET /api/ai-parse → 405「只接受 POST」");
    r = await call("/api/ai-suggest", { method: "GET" });
    ck("A20", r.status === 405, "GET /api/ai-suggest → 405");
    r = await call("/api/share", { method: "POST" });
    ck("A20", r.status === 405, "POST /api/share → 405");
    r = await call("/api/ai-parse", { method: "POST", body: JSON.stringify({ text: "x" }) });
    ck("A20", r.status === 500 && /GEMINI_API_KEY/.test((await r.json()).error),
      "沒有金鑰時回 500 並指名 GEMINI_API_KEY（與 Netlify 版同語意）");
    r = await call("/api/share?tag=", { method: "GET" });
    ck("A20", r.status === 400, "share 缺 tag → 400");
    r = await call("/api/share?tag=" + "x".repeat(61), { method: "GET" });
    ck("A20", r.status === 400, "share 的 tag 過長 → 400");
    calls.length = 0;
    r = await call("/api/share?tag=" + encodeURIComponent("送禮-媽媽&bought=eq.true"), { method: "GET" });
    ck("A20", calls[0] && (calls[0].match(/bought=eq\.false/g) || []).length === 1 && !calls[0].includes("bought=eq.true"),
      "tag 有跳脫，呼叫端插不進額外的 filter（唯讀出口的核心保證）");
    r = await call("/nope", { method: "GET" });
    ck("A20", r.status === 404, "未知路徑 → 404（靜態資產由平台先處理，走不到這裡）");

    // ai-suggest 的共用核心真的載進來了
    ck("A23", typeof globalThis.ScoutAiSuggest?.buildPrompt === "function",
      "import worker 之後 globalThis.ScoutAiSuggest.buildPrompt 可用");
  } finally {
    globalThis.fetch = realFetch;
  }
}

// ── A21／A22 的實跑部分（需要 wrangler dev 已經開著）──
async function live() {
  const base = `http://127.0.0.1:${LIVE_PORT}`;
  const get = async (p, init) => {
    try { return await fetch(base + p, init); } catch (e) { return { status: 0, _err: e.message }; }
  };

  // 靜態資產優先於 Worker：/ 與 /index.html 都必須是真的頁面，不是 Worker 的 JSON 404。
  // 註：Workers static assets 預設 html_handling = auto-trailing-slash，
  // /index.html 會 307 到 /，所以這裡跟著轉址（redirect: follow 是 fetch 預設）。
  const idx = await get("/index.html");
  const html = idx.status ? await idx.text() : "";
  ck("A21", html.includes("<title>Scout</title>"), `GET /index.html 拿到 Scout 首頁（status=${idx.status}）`);
  const rootRes = await get("/");
  ck("A21", rootRes.status === 200, `GET / → 200（實際 ${rootRes.status}）`);

  const share = await get("/api/share?tag=__nonexistent__");
  const shareBody = share.status ? await share.text() : "";
  ck("A21", shareBody.includes('"items"'), `GET /api/share 回傳含 items（status=${share.status}）`);

  const parse = await get("/api/ai-parse", { method: "GET" });
  ck("A21", parse.status === 405, `GET /api/ai-parse → 405（實際 ${parse.status}）`);

  // 舊網址相容
  const legacy = await get("/.netlify/functions/share?tag=__nonexistent__");
  const legacyBody = legacy.status ? await legacy.text() : "";
  ck("A20b", legacyBody.includes('"items"'), `舊網址 /.netlify/functions/share 仍然通（status=${legacy.status}）`);

  // 排程真的觸發得起來
  const sched = await get("/__scheduled?cron=17+3+*+*+1,4");
  ck("A22", sched.status >= 200 && sched.status < 300, `__scheduled 觸發回 2xx（實際 ${sched.status}）`);
}

// ── 執行 ──
const onlyFlags = args.filter((a) => a.startsWith("--"));
const runStatic = onlyFlags.length === 0 || args.includes("--all") ||
  onlyFlags.every((f) => !["--history", "--worker"].includes(f) && !f.startsWith("--live"));

if (runStatic) { a20(); a22static(); a23(); a25(); }
if (has("--history")) a24();
if (has("--worker") || args.includes("--all")) await worker();
if (liveArg || args.includes("--all")) await live();

let failed = 0;
for (const r of results) { if (!r.ok) failed++; console.log(`${r.ok ? "  ok  " : "  FAIL"} ${r.id}  ${r.msg}`); }
console.log(failed === 0 ? `全部通過（${results.length} 項斷言）` : `${failed} / ${results.length} 項斷言失敗`);
process.exit(failed === 0 ? 0 : 1);
