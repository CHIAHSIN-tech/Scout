// check-exports.mjs — 匯出格式驗收（TASK-ui-unify-and-calendar-maps-export 的 A5–A9）
//
// 只用 Node 內建模組。web/export-formats.js 是給瀏覽器的傳統 <script>，
// 這裡用 node:vm 餵一個假的 window 求值後取出純函式——同一份實作，不另寫一套。
//
//   node scripts/check-exports.mjs --ics         A5
//   node scripts/check-exports.mjs --ics-times   A6
//   node scripts/check-exports.mjs --gcal-link   A7
//   node scripts/check-exports.mjs --csv         A8
//   node scripts/check-exports.mjs --maps-link   A9
//   node scripts/check-exports.mjs               全部

import { readFileSync } from "node:fs";
import { createContext, runInContext } from "node:vm";

// ── 載入待測的純函式 ──
const src = readFileSync(new URL("../web/export-formats.js", import.meta.url), "utf8");
const sandbox = { window: {}, URLSearchParams, URL, Date, console };
createContext(sandbox);
runInContext(src, sandbox, { filename: "web/export-formats.js" });
const X = sandbox.window.ScoutExport;
if (!X) { console.error("FAIL：export-formats.js 沒有掛上 window.ScoutExport"); process.exit(1); }

// ── 固定測試資料（與畫面無關，任何人複製即可重跑）──
const TRIP = { id: 7, name: "沖繩四日", start_date: "2026-09-01", end_date: "2026-09-04" };
const ITEMS = [
  { id: 1, day_number: 1, name: "美麗海水族館", start_time: "10:00", duration_minutes: 120,
    location: "沖縄美ら海水族館", notes: "先買票", booking_ref: "" },
  { id: 2, day_number: 1, name: "居酒屋, 一番",            // 逗號 → CSV 要跳脫
    start_time: "18:30", duration_minutes: null,           // 缺 duration → 預設 60 分
    location: "国際通り", notes: '櫃檯說 "六點半" 到', booking_ref: "R-2211" },
  { id: 3, day_number: 3, name: "殘波岬", start_time: null, duration_minutes: 45,  // 缺時間 → 預設 09:00
    location: "残波岬", notes: "", booking_ref: "" },
  { id: 4, day_number: 2, name: "飯店休息", start_time: "15:00", duration_minutes: 90,
    location: "", notes: "沒有地點，不該進地圖 CSV", booking_ref: "" },   // 無 location
  { id: 5, day_number: null, name: "琉球村（還沒排）", start_time: null, duration_minutes: null,
    location: "琉球村", notes: "候選", booking_ref: "" },                 // 候選 → 不進 .ics、要進 CSV
];
const SCHEDULED = ITEMS.filter((i) => i.day_number != null);
const NOW = new Date(Date.UTC(2026, 7, 16, 3, 0, 0));   // 固定時間，讓 DTSTAMP 可重現

const results = [];
const check = (id, cond, msg) => { results.push({ id, ok: !!cond, msg }); return !!cond; };

// 把 YYYYMMDDTHHMMSS 轉成「分鐘」，用來驗 DTEND - DTSTART
function stampToMinutes(s) {
  const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$/.exec(s);
  if (!m) return null;
  return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]) / 60000;
}

function a5_ics() {
  const ics = X.buildIcs(TRIP, ITEMS, NOW);
  const n = (ics.match(/BEGIN:VEVENT/g) || []).length;
  check("A5", ics.includes("BEGIN:VCALENDAR"), "含 BEGIN:VCALENDAR");
  check("A5", /^VERSION:2\.0$/m.test(ics.replace(/\r/g, "")), "含 VERSION:2.0");
  check("A5", n === SCHEDULED.length, `VEVENT 數 ${n} == 已排入項目數 ${SCHEDULED.length}`);
  check("A5", !ics.includes("琉球村"), "候選項目沒有變成事件");
}

function a6_icsTimes() {
  const ics = X.buildIcs(TRIP, ITEMS, NOW).replace(/\r/g, "");
  const events = ics.split("BEGIN:VEVENT").slice(1);
  check("A6", events.length === SCHEDULED.length, `取到 ${events.length} 個 VEVENT`);
  for (const ev of events) {
    const start = /^DTSTART:(\S+)$/m.exec(ev), end = /^DTEND:(\S+)$/m.exec(ev);
    const name = (/^SUMMARY:(.*)$/m.exec(ev) || [, "?"])[1];
    if (!check("A6", start && end, `「${name}」同時有 DTSTART 與 DTEND`)) continue;
    const mins = stampToMinutes(end[1]) - stampToMinutes(start[1]);
    const item = SCHEDULED.find((i) => ev.includes(`UID:scout-${TRIP.id}-${i.id}@`));
    // 預設值寫死 60，不能引用 X.DEFAULT_DURATION——那是實作自己的常數，
    // 引用它等於「實作改成幾分都算過」，就驗不到規格 A6 要求的 60。
    const expect = item && item.duration_minutes > 0 ? item.duration_minutes : 60;
    check("A6", mins === expect, `「${name}」長度 ${mins} 分 == 預期 ${expect} 分`);
  }
  check("A6", X.DEFAULT_DURATION === 60, `duration 缺值時的預設為 60 分（實作是 ${X.DEFAULT_DURATION}）`);
  // duration 缺值走預設 60 分這條路真的被走到了才算數
  check("A6", SCHEDULED.some((i) => !i.duration_minutes), "測試資料涵蓋 duration_minutes 缺值");
}

function a7_gcal() {
  for (const it of SCHEDULED) {
    const url = X.gcalLink(TRIP, it);
    if (!check("A7", !!url, `「${it.name}」有產出連結`)) continue;
    check("A7", url.startsWith("https://calendar.google.com/calendar/render?action=TEMPLATE"),
      `「${it.name}」開頭為 render?action=TEMPLATE`);
    const q = new URL(url).searchParams;
    check("A7", q.get("text") === it.name, `「${it.name}」帶 text 參數`);
    check("A7", /^\d{8}T\d{6}\/\d{8}T\d{6}$/.test(q.get("dates") || ""),
      `「${it.name}」dates=${q.get("dates")} 形如 YYYYMMDDTHHMMSS/YYYYMMDDTHHMMSS`);
  }
  check("A7", X.gcalLink(TRIP, ITEMS[4]) === null, "候選項目不產生日曆連結");
}

function a8_csv() {
  const csv = X.buildMapsCsv(ITEMS);
  const lines = csv.replace(/\r/g, "").replace(/\n$/, "").split("\n");
  check("A8", lines[0] === "name,location,day,time,notes", `表頭為 ${JSON.stringify(lines[0])}`);
  const withLoc = ITEMS.filter((i) => String(i.location || "").trim());
  check("A8", lines.length - 1 === withLoc.length, `資料列 ${lines.length - 1} == 有 location 的項目數 ${withLoc.length}`);
  check("A8", !csv.includes("飯店休息"), "沒有 location 的項目不輸出");
  check("A8", csv.includes("琉球村"), "候選項目只要有 location 就輸出");
  check("A8", lines.some((l) => l.startsWith('"居酒屋, 一番"')), "含逗號的欄位有加引號");
  check("A8", lines.some((l) => l.includes('""六點半""')), "欄位內的引號有重複跳脫");
  // 每列的欄位數都要是 5（把跳脫算進去才數得對）
  const cells = (line) => (line.match(/(?:^|,)(?:"(?:[^"]|"")*"|[^,]*)/g) || []).length;
  check("A8", lines.every((l) => cells(l) === 5), "每列都是 5 個欄位");
}

function a9_maps() {
  for (const it of ITEMS) {
    const url = X.mapsLink(it);
    if (!String(it.location || "").trim()) { check("A9", url === null, `「${it.name}」無 location → 不產生連結`); continue; }
    check("A9", url === `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(it.location)}`,
      `「${it.name}」連結格式正確`);
  }
}

const RUN = { "--ics": a5_ics, "--ics-times": a6_icsTimes, "--gcal-link": a7_gcal, "--csv": a8_csv, "--maps-link": a9_maps };
const args = process.argv.slice(2);
for (const [flag, fn] of Object.entries(RUN)) if (args.length === 0 || args.includes(flag)) fn();

let failed = 0;
for (const r of results) {
  if (!r.ok) failed++;
  console.log(`${r.ok ? "  ok  " : "  FAIL"} ${r.id}  ${r.msg}`);
}
console.log(failed === 0 ? `全部通過（${results.length} 項斷言）` : `${failed} / ${results.length} 項斷言失敗`);
process.exit(failed === 0 ? 0 : 1);
