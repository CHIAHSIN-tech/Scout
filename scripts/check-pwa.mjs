// check-pwa.mjs — PWA 設定的驗收。
//
//   node scripts/check-pwa.mjs
//
// 只用 Node 內建模組。驗兩件事：
//   1. 安裝條件齊備（manifest 必要欄位、192/512 圖示、SW 有 fetch 監聽器）
//   2. **service worker 沒有做任何快取** — 這是本專案刻意的決策，
//      因為被「線上跑舊版」坑過一次，會快取的 SW 只會讓那個坑更深。
//      這一條是本腳本存在的主要理由：將來有人「順手加個快取」會被擋下來。

import { readFileSync, existsSync, statSync } from "node:fs";

const root = new URL("../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
const exists = (p) => existsSync(new URL(p, root));

const results = [];
const ck = (cond, msg) => { results.push({ ok: !!cond, msg }); return !!cond; };

// ── manifest ──
let m = null;
try { m = JSON.parse(read("web/manifest.json")); } catch (e) { ck(false, "manifest.json 是合法 JSON：" + e.message); }

if (m) {
  ["name", "short_name", "start_url", "scope", "display", "background_color", "theme_color"]
    .forEach((f) => ck(m[f], `manifest 有 ${f}（${m[f]}）`));
  ck(m.display === "standalone", "display 是 standalone（開起來沒有網址列）");
  ck(m.lang === "zh-Hant", "lang 是 zh-Hant");

  const bySize = (s, purpose) => (m.icons || []).find(
    (i) => i.sizes === `${s}x${s}` && (i.purpose || "any").includes(purpose));
  [192, 512].forEach((s) => {
    ck(bySize(s, "any"), `有 ${s}x${s} 一般圖示`);
    ck(bySize(s, "maskable"), `有 ${s}x${s} maskable 圖示（Android 會裁形狀）`);
  });
  (m.icons || []).forEach((i) => {
    ck(exists("web/" + i.src), `圖示檔存在：${i.src}`);
    if (exists("web/" + i.src)) {
      ck(statSync(new URL("web/" + i.src, root)).size > 200, `圖示檔非空：${i.src}`);
    }
  });
}

// ── service worker ──
const swRaw = read("web/sw.js");
// 只看程式碼：sw.js 的註解本來就會提到 respondWith / 快取（在解釋為什麼不做），
// 不剝掉的話這裡會抓到自己的說明文字。
const sw = swRaw.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

ck(/addEventListener\(\s*["']fetch["']/.test(sw), "SW 有 fetch 監聽器（Chrome 的安裝條件）");

// 這幾條就是「不做快取」的守門員
ck(!/caches\.open/.test(sw), "SW 沒有 caches.open（不建立快取）");
ck(!/cache\.put|cache\.add|addAll/.test(sw), "SW 沒有寫入快取");
ck(!/caches\.match/.test(sw), "SW 沒有從快取回應");
ck(!/respondWith/.test(sw), "SW 從不呼叫 respondWith（完全不介入請求）");
ck(/caches\.delete/.test(sw), "SW 會清掉殘留的舊快取（防止有人加過又移除）");

// ── HTML 接線 ──
const html = read("web/index.html");
ck(/<link[^>]+rel="manifest"[^>]+href="manifest\.json"/.test(html), "index.html 連到 manifest");
ck(/<meta[^>]+name="theme-color"/.test(html), "有 theme-color");
ck(/apple-touch-icon/.test(html), "有 apple-touch-icon（iOS 加到主畫面用）");
ck(/apple-mobile-web-app-capable/.test(html), "有 apple-mobile-web-app-capable（iOS 全螢幕）");
ck(/navigator\.serviceWorker\.register\(\s*["']sw\.js["']\s*\)/.test(html), "有註冊 sw.js");
ck(/location\.protocol === ['"]https:['"]/.test(html),
  "只在 https 註冊（本機以 file:// 或 http 開不會亂裝）");
ck(/\.catch\(/.test(html.slice(html.indexOf("serviceWorker.register"))),
  "註冊失敗有吞掉，不干擾使用者");

// theme-color 與 manifest 一致，避免改一邊忘另一邊
if (m) {
  const meta = (html.match(/name="theme-color"\s+content="([^"]+)"/) || [])[1];
  ck(meta && meta.toLowerCase() === String(m.theme_color).toLowerCase(),
    `theme-color 兩邊同值（html=${meta} manifest=${m.theme_color}）`);
}

let failed = 0;
for (const r of results) { if (!r.ok) failed++; console.log(`${r.ok ? "  ok  " : "  FAIL"}  ${r.msg}`); }
console.log(failed === 0 ? `全部通過（${results.length} 項）` : `${failed} / ${results.length} 項失敗`);
process.exit(failed === 0 ? 0 : 1);
