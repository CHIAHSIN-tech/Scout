// check-trip-index.mjs — 行程表索引的驗收（spec-scout-trip-page.md 的 A6、A15）。
//
//   node scripts/check-trip-index.mjs                A6  索引與磁碟一致
//   node scripts/check-trip-index.mjs --unguessable  A15 部署路徑不可猜
//   node scripts/check-trip-index.mjs --all          兩項都跑
//
// 只用 Node 內建模組。
//
// 注意：`trips/` 目前被 .gitignore 擋著（repo 是公開的，trip.json 含訂位編號與旅館地址，
// 見 DECISIONS-trip-page.md）。所以在乾淨的 clone 上這支會回報「沒有任何旅程」——
// 那是正確的狀態，不是失敗。有資料時才逐條比對。

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";

const root = new URL("../", import.meta.url);
const path = (p) => new URL(p, root);
const read = (p) => readFileSync(path(p), "utf8");
const exists = (p) => existsSync(path(p));

const results = [];
const ck = (id, cond, msg) => { results.push({ id, ok: !!cond, msg }); return !!cond; };

function dirs(p) {
  if (!exists(p)) return [];
  return readdirSync(path(p))
    .filter((n) => !n.startsWith("_") && !n.startsWith("."))
    .filter((n) => statSync(new URL(p + "/" + n, root)).isDirectory());
}

// ── A6：索引的條目集合 == 已建置過的旅程集合 ──
function a6() {
  const built = dirs("trips").filter((slug) => exists(`trips/${slug}/trip.json`))
    .map((slug) => {
      const t = JSON.parse(read(`trips/${slug}/trip.json`));
      return { slug, meta: t.trip || {} };
    })
    .filter((r) => r.meta.page_slug && exists(`web/trips/${r.meta.page_slug}/index.html`));

  if (!exists("web/trips/index.json")) {
    ck("A6", built.length === 0,
      `沒有 web/trips/index.json，而磁碟上也沒有任何建置過的旅程（實際 ${built.length} 趟）`);
    return;
  }

  let rows;
  try { rows = JSON.parse(read("web/trips/index.json")); }
  catch (e) { ck("A6", false, "index.json 不是合法 JSON：" + e.message); return; }
  ck("A6", Array.isArray(rows), "index.json 是陣列");
  if (!Array.isArray(rows)) return;

  const wantPaths = new Set(built.map((r) => `trips/${r.meta.page_slug}/index.html`));
  const gotPaths = new Set(rows.map((r) => r.page_path));
  const missing = [...wantPaths].filter((p) => !gotPaths.has(p));
  const extra = [...gotPaths].filter((p) => !wantPaths.has(p));
  ck("A6", missing.length === 0, `索引沒有漏掉建置過的旅程（漏：${missing.join(",") || "無"}）`);
  ck("A6", extra.length === 0, `索引沒有多列不存在的旅程（多：${extra.join(",") || "無"}）`);

  for (const r of rows) {
    for (const f of ["country", "city", "start_date", "end_date", "title", "page_path"]) {
      ck("A6", r[f] != null && r[f] !== "", `${r.page_path || "(某筆)"} 有 ${f}`);
    }
    ck("A6", exists("web/" + r.page_path), `${r.page_path} 這個檔真的存在`);
  }

  const dates = rows.map((r) => r.start_date);
  const sorted = [...dates].sort().reverse();
  ck("A6", JSON.stringify(dates) === JSON.stringify(sorted),
    `依 start_date 新到舊排序（實際 ${dates.join(",") || "空"}）`);
}

// ── A15：部署路徑不可猜 ──
function a15() {
  const deployed = dirs("web/trips");
  for (const d of deployed) {
    ck("A15", /-[0-9a-f]{6,}$/.test(d), `web/trips/${d} 以 6 碼以上的十六進位亂碼結尾`);
  }
  if (deployed.length === 0) {
    ck("A15", true, "web/trips/ 底下還沒有建置產物（沒有可猜的路徑）");
  }

  // 亂碼是不是真的亂數產生的——不是的話，格式對也沒有意義
  let found = false;
  const walk = (p) => {
    for (const n of readdirSync(path(p))) {
      const child = p + "/" + n;
      if (statSync(new URL(child, root)).isDirectory()) { walk(child); continue; }
      if (n.endsWith(".py") && read(child).includes("secrets.token_hex")) found = true;
    }
  };
  walk("mcp-server/src/scout_mcp/travel");
  ck("A15", found, "亂碼來自 secrets.token_hex（不是可預測的雜湊或流水號）");
}

const args = process.argv.slice(2);
if (args.length === 0 || args.includes("--all") || !args.includes("--unguessable")) a6();
if (args.includes("--unguessable") || args.includes("--all")) a15();

let failed = 0;
for (const r of results) { if (!r.ok) failed++; console.log(`${r.ok ? "  ok  " : "  FAIL"} ${r.id}  ${r.msg}`); }
console.log(failed === 0 ? `全部通過（${results.length} 項斷言）` : `${failed} / ${results.length} 項斷言失敗`);
process.exit(failed === 0 ? 0 : 1);
