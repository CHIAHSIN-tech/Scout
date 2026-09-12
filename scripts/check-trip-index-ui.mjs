// check-trip-index-ui.mjs — 行程 Tab 的行程表列表接線驗收（spec-scout-trip-page.md 的 A14）。
//
//   node scripts/check-trip-index-ui.mjs
//
// 只用 Node 內建模組。
//
// 驗的重點不只是「有沒有接上」，更是「**不依賴 config.js**」——
// config.js 是 gitignored 的 Supabase 設定，本機沒有它時 checklist 整段會停在載入中。
// 行程表列表讀的是靜態 JSON，所以在那種情況下仍然要顯示得出來。

import { readFileSync, existsSync } from "node:fs";

const root = new URL("../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
const exists = (p) => existsSync(new URL(p, root));

const results = [];
const ck = (cond, msg) => { results.push({ ok: !!cond, msg }); return !!cond; };

const html = read("web/index.html");

// #panel-trip 的範圍
const start = html.indexOf('<div id="panel-trip"');
const end = html.indexOf("<!-- /panel-trip -->");
ck(start !== -1 && end > start, "index.html 有 #panel-trip 區塊");
const panel = start !== -1 && end > start ? html.slice(start, end) : "";

ck(panel.includes('id="trip-pages"'), "#panel-trip 內有 id=\"trip-pages\" 區塊");
ck(html.includes('<script src="trip-pages.js">'), "index.html 載入 web/trip-pages.js");
ck(exists("web/trip-pages.js"), "web/trip-pages.js 存在");

const js = exists("web/trip-pages.js") ? read("web/trip-pages.js") : "";
ck(js.includes('getElementById("trip-pages")'), "trip-pages.js 掛在 #trip-pages 上");
ck(js.includes("trips/index.json"), "trip-pages.js 讀的是靜態的 trips/index.json");

// 只看程式碼：檔頭註解本來就會提到 config.js 與 Supabase（在解釋為什麼不用），
// 不剝掉註解的話下面兩條會抓到自己的說明文字。
const code = js.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

// 不依賴 config.js：不得引用 SCOUT_CONFIG / SUPABASE 之類的全域設定
const configRefs = (code.match(/SCOUT_CONFIG|SUPABASE_URL|SUPABASE_ANON|window\.CONFIG/g) || []);
ck(configRefs.length === 0, `trip-pages.js 不引用 config.js 的任何東西（命中：${configRefs.join(",") || "無"}）`);
// 也不該跟 Supabase 有任何往來
ck(!/supabase/i.test(code), "trip-pages.js 的程式碼完全不碰 Supabase");

// 載入順序：trip-pages.js 不需要排在 checklist.js 之前或之後，但確認兩者是分開的檔案，
// 不是把列表塞進 checklist.js（N3 / N4 的寫入邊界，也讓 Supabase 掛掉時列表還在）
const checklist = exists("web/checklist.js") ? read("web/checklist.js") : "";
ck(!checklist.includes("trips/index.json"), "checklist.js 沒有第二份行程表列表實作");

// 空狀態：沒有任何行程表時要講人話，不是一片空白
ck(/tp-empty/.test(js), "沒有任何行程表時有空狀態訊息");
// 失敗路徑：讀不到 JSON 不該噴紅字（那不是錯誤，是還沒建置過）
ck(/onerror/.test(js) && /render\(\[\]\)/.test(js), "讀不到索引時退回空狀態，不顯示錯誤");

// 樣式在 checklist.css 裡，走既有 token
const css = read("web/checklist.css");
ck(css.includes("#panel-trip .tp-list"), "checklist.css 有 .tp-list 的樣式（作用域限定在 #panel-trip）");

let failed = 0;
for (const r of results) { if (!r.ok) failed++; console.log(`${r.ok ? "  ok  " : "  FAIL"} A14  ${r.msg}`); }
console.log(failed === 0 ? `全部通過（${results.length} 項斷言）` : `${failed} / ${results.length} 項斷言失敗`);
process.exit(failed === 0 ? 0 : 1);
