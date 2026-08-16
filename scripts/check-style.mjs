// check-style.mjs — 樣式驗收（TASK-ui-unify-and-calendar-maps-export 的 A2 / A3）
//
// 只用 Node 內建模組，不需要 npm install、不需要 package.json（本 repo 無 build step）。
// 放在 scripts/ 而不是 web/，才不會被部署出去。
//
//   node scripts/check-style.mjs --no-raw-hex     A2：checklist.css 的 token 區塊外沒有裸 hex
//   node scripts/check-style.mjs --token-parity   A3：#panel-shop 與 #panel-trip 同名 token 同值
//   node scripts/check-style.mjs                  兩項都跑

import { readFileSync } from "node:fs";

const TRIP_CSS = "web/checklist.css";
const SHOP_CSS = "web/buylist.css";

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

// 取出 `<selector>{ ... }` 這個宣告區塊的內容（token 定義區塊都是檔案裡該選擇器的第一段）
function block(css, selector) {
  const start = css.indexOf(selector + "{");
  if (start === -1) throw new Error(`找不到 ${selector}{ 區塊`);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  if (close === -1) throw new Error(`${selector} 區塊沒有結束的 }`);
  return { body: css.slice(open + 1, close), end: close + 1 };
}

// 解析 --name: value;
function tokens(body) {
  const out = new Map();
  for (const m of body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    out.set(m[1], m[2].split("/*")[0].trim().toLowerCase());
  }
  return out;
}

function checkNoRawHex() {
  const css = read(TRIP_CSS);
  const { end } = block(css, "#panel-trip");
  const rest = css.slice(end);
  // 只看「宣告的值」裡的 hex：屬性名: ... #xxxxxx。
  // 這樣才不會把 #app / #trip-sel 這類選擇器誤判成顏色。
  const bad = [];
  const lineOffset = (css.slice(0, end).match(/\n/g) || []).length;   // rest 的第一行在原檔的行號
  rest.split("\n").forEach((line, i) => {
    const code = line.split("/*")[0];
    for (const m of code.matchAll(/[\w-]+\s*:[^;{}]*?(#[0-9a-fA-F]{3,8})\b/g)) {
      bad.push(`${TRIP_CSS}:${lineOffset + i + 1}  ${m[1]}  →  ${line.trim()}`);
    }
  });
  if (bad.length) {
    console.error(`A2 FAIL：token 區塊外還有 ${bad.length} 個裸露 hex 色碼`);
    bad.forEach((b) => console.error("  " + b));
    return false;
  }
  console.log("A2 PASS：checklist.css 的 token 區塊外沒有裸露 hex 色碼");
  return true;
}

function checkTokenParity() {
  const trip = tokens(block(read(TRIP_CSS), "#panel-trip").body);
  const shop = tokens(block(read(SHOP_CSS), "#panel-shop").body);
  const shared = [...trip.keys()].filter((k) => shop.has(k)).sort();
  const norm = (v) => {                       // #abc 與 #aabbcc 視為同值
    const m = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/.exec(v);
    return m ? `#${m[1]}${m[1]}${m[2]}${m[2]}${m[3]}${m[3]}` : v;
  };
  const bad = shared.filter((k) => norm(trip.get(k)) !== norm(shop.get(k)));
  if (bad.length) {
    console.error(`A3 FAIL：${bad.length} 個同名 token 在兩個 panel 值不同`);
    bad.forEach((k) => console.error(`  ${k}: #panel-trip=${trip.get(k)}  #panel-shop=${shop.get(k)}`));
    return false;
  }
  console.log(`A3 PASS：${shared.length} 個同名 token 兩邊同值（${shared.join(", ")}）`);
  return true;
}

const args = process.argv.slice(2);
const run = (flag) => args.length === 0 || args.includes(flag);
let ok = true;
if (run("--no-raw-hex")) ok = checkNoRawHex() && ok;
if (run("--token-parity")) ok = checkTokenParity() && ok;
process.exit(ok ? 0 : 1);
