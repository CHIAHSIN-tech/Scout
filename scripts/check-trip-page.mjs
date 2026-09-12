// check-trip-page.mjs — 行程表頁面的驗收（spec-scout-trip-page.md 的 A7、A9、A10）。
//
//   node scripts/check-trip-page.mjs --consistency   A7  改一處，多處一起改（＋建置決定性）
//   node scripts/check-trip-page.mjs --offline       A9  自含單檔，斷網可開
//   node scripts/check-trip-page.mjs --mobile        A10 375px 寬不橫向溢位
//   node scripts/check-trip-page.mjs                 全部
//
// 只用 Node 內建模組（本 repo 無 build step）。渲染器是 Python，
// 這裡透過 `python -m scout_mcp.travel.page` 呼叫它——驗收不進渲染器內部，
// 只看它吐出來的 HTML，這樣改實作不會連帶改到驗收標準。

import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = new URL("../", import.meta.url);
const toPath = (u) => decodeURIComponent(new URL(u, root).pathname).replace(/^\/([A-Za-z]:)/, "$1");
const MCP = toPath("mcp-server/");
const FIXTURE = toPath("mcp-server/tests/fixtures/trip-fixture.json");

const results = [];
const ck = (id, cond, msg) => { results.push({ id, ok: !!cond, msg }); return !!cond; };

const tmp = mkdtempSync(join(tmpdir(), "scout-trip-"));

function build(tripPath, outName) {
  const out = join(tmp, outName);
  execFileSync("uv", ["run", "python", "-m", "scout_mcp.travel.page", tripPath, out],
    { cwd: MCP, stdio: ["ignore", "ignore", "inherit"] });
  return readFileSync(out, "utf8");
}

// ── 從產出的 HTML 抓出「同一筆資訊出現的那幾個地方」──
// 用結構上的錨點（section / tbody / nav 的 id 與 class），不是行號，
// 這樣改版面不會讓驗收失效。
const REGIONS = {
  時間軸: (h) => (h.match(/<section class="day"[\s\S]*?<\/section>/g) || []).join("\n"),
  當日標題摘要: (h) => (h.match(/<p class="daysum">[\s\S]*?<\/p>/g) || []).join("\n"),
  快捷nav: (h) => (h.match(/<nav class="days"[\s\S]*?<\/nav>/) || [""])[0],
  地圖文字轉乘表: (h) => {
    const m = h.match(/var MAPDATA = (\{[\s\S]*?\});\n/);
    if (!m) return "";
    const d = JSON.parse(m[1]).DAYS || {};
    return Object.keys(d).sort().map((k) => k + ":" + JSON.stringify(d[k].legs)).join("\n");
  },
  正餐一覽表: (h) => (h.match(/<tbody id="meal-rows">[\s\S]*?<\/tbody>/) || [""])[0],
};

// ── A7 ──
function consistency() {
  const before = build(FIXTURE, "before.html");

  // 同樣的輸入建兩次必須位元相同：build 不得含時間戳或亂數
  const again = build(FIXTURE, "before2.html");
  ck("A7", before === again, `同樣輸入建兩次位元相同（${before.length} vs ${again.length} bytes）`);

  // 把一個 event 的時間由 15:30 改 16:30，並且換一天
  const trip = JSON.parse(readFileSync(FIXTURE, "utf8"));
  const ev = trip.events.find((e) => e.time === "15:30");
  if (!ck("A7", !!ev, "fixture 裡有一筆 15:30 的行程可以改")) return;
  const movedFrom = ev.day;
  ev.time = "16:30";
  ev.day = ev.day + 1;
  const movedTo = ev.day;
  const p2 = join(tmp, "after-trip.json");
  writeFileSync(p2, JSON.stringify(trip, null, 2), "utf8");
  const after = build(p2, "after.html");

  ck("A7", before !== after, `改一個 event 之後整份頁面有變（第 ${movedFrom} 天 → 第 ${movedTo} 天）`);
  for (const [name, pick] of Object.entries(REGIONS)) {
    const a = pick(before), b = pick(after);
    ck("A7", a !== "" && a !== b, `${name} 跟著變了`);
  }
}

// ── A9：自含單檔，斷網可開 ──
function offline() {
  const h = build(FIXTURE, "offline.html");
  const forbidden = [
    [/<script[^>]+src=/i, "<script src="],
    [/<link[^>]+rel=["']stylesheet["']/i, '<link rel="stylesheet"'],
    [/@import/i, "@import"],
    [/url\(\s*["']?https?:/i, "CSS 的 url(http"],
    [/<img[^>]+src=["']https?:/i, '<img src="http'],
    [/\bfetch\s*\(/, "fetch("],
    [/XMLHttpRequest/, "XMLHttpRequest"],
    [/<iframe/i, "<iframe"],
    [/<link[^>]+rel=["']preconnect["']/i, "preconnect"],
  ];
  for (const [re, label] of forbidden) {
    ck("A9", !re.test(h), `產出不含 ${label}`);
  }

  // 唯一允許外部網址的位置是 <a href>。把所有 <a href="http..."> 挖掉之後，
  // 整份文件不該再有任何 http(s):// 出現——包括註解、CSS、JS 字串。
  const stripped = h.replace(/<a\s+href="https?:\/\/[^"]*"/g, "<a");
  const leftovers = [...stripped.matchAll(/https?:\/\/[^\s"'<>)]+/g)].map((m) => m[0]);
  // xmlns 是 XML 命名空間宣告，不是會被載入的資源
  const real = leftovers.filter((u) => !u.startsWith("http://www.w3.org/"));
  ck("A9", real.length === 0, `外部網址只出現在 <a href>（其餘殘留：${real.slice(0, 3).join(" ") || "無"}）`);

  // 有東西可看：空殼頁面也會通過上面每一條
  ck("A9", h.includes("<style>") && h.length > 20000, `產出是完整頁面（${h.length} bytes）`);
}

// ── A10：375px 寬不橫向溢位（靜態規則，不跑瀏覽器）──
function mobile() {
  const h = build(FIXTURE, "mobile.html");
  const css = (h.match(/<style>([\s\S]*?)<\/style>/) || [, ""])[1];

  // (a) 每個 <table> 都在 overflow-x:auto 的容器裡，或有卡片化規則
  const wrapped = [...h.matchAll(/<div class="tbl([^"]*)"><table>/g)];
  const tables = (h.match(/<table>/g) || []).length;
  ck("A10a", tables > 0 && wrapped.length === tables,
    `${tables} 個 <table> 全部包在 .tbl 容器裡（實際包住 ${wrapped.length} 個）`);
  ck("A10a", /\.tbl\{[^}]*overflow-x:\s*auto/.test(css), ".tbl 有 overflow-x:auto");
  ck("A10a", /\.tbl\.stack thead\{display:none\}/.test(css) &&
             /\.tbl\.stack tr\{display:grid/.test(css),
    ".tbl.stack 在窄螢幕轉成卡片（thead 隱藏 + tr 用 grid）");
  ck("A10a", /@media \(max-width:640px\)/.test(css), "卡片化規則在 max-width 媒體查詢裡");
  const unstacked = wrapped.filter((m) => !m[1].includes("stack"));
  ck("A10a", unstacked.length === 0,
    `每個表格都標了 stack，窄螢幕會轉卡片（沒標的：${unstacked.length} 個）`);

  // (b) 地圖 svg 在可橫向捲動的容器裡
  ck("A10b", /<div class="mapbox"><svg id="map-svg"/.test(h), "地圖 svg 包在 .mapbox 裡");
  ck("A10b", /\.mapbox\{[^}]*overflow-x:\s*auto/.test(css), ".mapbox 有 overflow-x:auto");

  // (c) 沒有作用在非容器元素、min-width 大於 360px 的規則
  const CONTAINERS = [".tbl", ".mapbox", "#map-svg", ".wrap"];
  const bad = [];
  for (const m of css.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
    const sel = m[1].trim(), body = m[2];
    for (const mw of body.matchAll(/(?:^|;)\s*min-width:\s*(\d+(?:\.\d+)?)px/g)) {
      if (parseFloat(mw[1]) > 360 && !CONTAINERS.some((c) => sel.includes(c))) {
        bad.push(`${sel} { min-width:${mw[1]}px }`);
      }
    }
  }
  ck("A10c", bad.length === 0, `沒有 min-width > 360px 的非容器規則（違規：${bad.join("; ") || "無"}）`);

  // (d) 不得靠 body{overflow-x:hidden} 蒙混
  ck("A10d", !/body\{[^}]*overflow-x:\s*hidden/.test(css),
    "沒有用 body{overflow-x:hidden} 把溢位藏起來");

  // 補強：固定像素寬度也會溢位
  const wide = [];
  for (const m of css.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
    const sel = m[1].trim(), body = m[2];
    for (const w of body.matchAll(/(?:^|;)\s*width:\s*(\d+(?:\.\d+)?)px/g)) {
      if (parseFloat(w[1]) > 360 && !CONTAINERS.some((c) => sel.includes(c))) {
        wide.push(`${sel} { width:${w[1]}px }`);
      }
    }
  }
  ck("A10c", wide.length === 0, `沒有固定寬度 > 360px 的非容器規則（違規：${wide.join("; ") || "無"}）`);
}

const args = process.argv.slice(2);
const run = (f) => args.length === 0 || args.includes(f);
if (run("--consistency")) consistency();
if (run("--offline")) offline();
if (run("--mobile")) mobile();

let failed = 0;
for (const r of results) { if (!r.ok) failed++; console.log(`${r.ok ? "  ok  " : "  FAIL"} ${r.id}  ${r.msg}`); }
console.log(failed === 0 ? `全部通過（${results.length} 項斷言）` : `${failed} / ${results.length} 項斷言失敗`);
process.exit(failed === 0 ? 0 : 1);
