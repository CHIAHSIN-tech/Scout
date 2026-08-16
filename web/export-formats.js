// export-formats.js — 行程匯出的格式組裝（純函式，無 DOM、無網路）
//
// 為什麼獨立成一支：同一套格式邏輯要同時被兩個地方用——
//   1. 瀏覽器（checklist.js 產檔／產連結）
//   2. scripts/check-exports.mjs（驗收腳本，用 node:vm 餵一個假的 window 求值）
// 規格明訂「同一個格式邏輯不得存在第二份實作」，所以這裡是唯一來源。
//
// 本 repo 刻意沒有 build step（ADR-010），所以不用 ESM／不用打包，
// 掛在全域物件上讓傳統 <script> 與 node:vm 都讀得到。
//
// 時區：一律 floating local time（DTSTART:20260901T100000，不帶 Z、不帶 TZID）。
// trips 表沒有時區欄位，start_time 是目的地當地時間；floating 讓「9:00」在使用者
// 日曆裡就顯示 9:00。代價寫在 DECISIONS.md（D1）。

(function (root) {
  "use strict";

  const DEFAULT_DURATION = 60;   // duration_minutes 缺值時的預設長度（規格 A6）
  const DEFAULT_TIME = "09:00";  // 已排入某天但沒填時間時的預設起始（DECISIONS D2）

  const pad2 = (n) => String(n).padStart(2, "0");

  // 「第 N 天」換算成實際日期。用 UTC 做加減，避免跨日光節約時區時多／少一天。
  function dayDate(startDate, day) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(startDate || ""));
    if (!m) return null;
    const base = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return new Date(base + (Math.max(1, Number(day) || 1) - 1) * 86400000);
  }

  function parseTime(t) {
    const m = /^(\d{1,2}):(\d{2})/.exec(String(t || ""));
    if (!m) return null;
    return { h: Number(m[1]), min: Number(m[2]) };
  }

  // 產生 YYYYMMDDTHHMMSS（floating，不帶 Z）
  function stampAt(date, minutesOfDay) {
    const d = new Date(date.getTime() + minutesOfDay * 60000);
    return `${d.getUTCFullYear()}${pad2(d.getUTCMonth() + 1)}${pad2(d.getUTCDate())}` +
           `T${pad2(d.getUTCHours())}${pad2(d.getUTCMinutes())}00`;
  }

  // 單一項目的起訖時間戳。回傳 null 代表這個項目不該成為日曆事件。
  function itemRange(trip, item) {
    if (!item || item.day_number == null) return null;      // 候選項目沒有日期，不能成為事件
    const date = dayDate(trip && trip.start_date, item.day_number);
    if (!date) return null;
    const t = parseTime(item.start_time) || parseTime(DEFAULT_TIME);
    const startMin = t.h * 60 + t.min;
    const dur = Number(item.duration_minutes);
    const durMin = Number.isFinite(dur) && dur > 0 ? dur : DEFAULT_DURATION;
    return { start: stampAt(date, startMin), end: stampAt(date, startMin + durMin) };
  }

  // ── .ics ──
  // RFC5545 的跳脫：反斜線、分號、逗號、換行。
  function icsEscape(s) {
    return String(s == null ? "" : s)
      .replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,")
      .replace(/\r?\n/g, "\\n");
  }

  function utcStamp(d) {
    return `${d.getUTCFullYear()}${pad2(d.getUTCMonth() + 1)}${pad2(d.getUTCDate())}` +
           `T${pad2(d.getUTCHours())}${pad2(d.getUTCMinutes())}${pad2(d.getUTCSeconds())}Z`;
  }

  function buildIcs(trip, items, now) {
    if (!trip || !trip.start_date) throw new Error("這趟旅程沒有填開始日期，無法換算成日曆事件。");
    const dtstamp = utcStamp(now instanceof Date ? now : new Date());
    const lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Scout//Itinerary Export//ZH-TW",
      "CALSCALE:GREGORIAN",
      `X-WR-CALNAME:${icsEscape(trip.name || "Scout 行程")}`,
    ];
    for (const it of items || []) {
      const r = itemRange(trip, it);
      if (!r) continue;                       // 候選項目直接跳過（規格 A5）
      lines.push("BEGIN:VEVENT");
      lines.push(`UID:scout-${trip.id}-${it.id}@scout.local`);
      lines.push(`DTSTAMP:${dtstamp}`);
      lines.push(`DTSTART:${r.start}`);
      lines.push(`DTEND:${r.end}`);
      lines.push(`SUMMARY:${icsEscape(it.name)}`);
      if (it.location) lines.push(`LOCATION:${icsEscape(it.location)}`);
      if (it.notes || it.booking_ref) {
        const desc = [it.booking_ref ? `預約編號：${it.booking_ref}` : "", it.notes || ""]
          .filter(Boolean).join("\n");
        lines.push(`DESCRIPTION:${icsEscape(desc)}`);
      }
      lines.push("END:VEVENT");
    }
    lines.push("END:VCALENDAR");
    return lines.join("\r\n") + "\r\n";
  }

  // ── Google 日曆單筆連結（手機也能用，.ics 不行）──
  function gcalLink(trip, item) {
    const r = itemRange(trip, item);
    if (!r) return null;
    const p = new URLSearchParams();
    p.set("text", String(item.name || ""));
    p.set("dates", `${r.start}/${r.end}`);
    const details = [item.booking_ref ? `預約編號：${item.booking_ref}` : "", item.notes || ""]
      .filter(Boolean).join("\n");
    if (details) p.set("details", details);
    if (item.location) p.set("location", String(item.location));
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&${p.toString()}`;
  }

  // ── My Maps CSV ──
  // RFC4180：含逗號／引號／換行就整格加引號，內部引號重複一次。
  function csvEscape(v) {
    const s = String(v == null ? "" : v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }

  const CSV_HEADER = ["name", "location", "day", "time", "notes"];

  function buildMapsCsv(items) {
    const rows = [CSV_HEADER.join(",")];
    for (const it of items || []) {
      // 沒有地點的項目在地圖上沒有意義，直接不輸出（規格 A8）
      if (!it || !String(it.location || "").trim()) continue;
      // 候選項目照樣輸出，day / time 留空（規格 INTERVIEW Q4）
      rows.push([
        csvEscape(it.name),
        csvEscape(it.location),
        csvEscape(it.day_number == null ? "" : it.day_number),
        csvEscape(it.day_number == null ? "" : (it.start_time || "")),
        csvEscape(it.notes),
      ].join(","));
    }
    return rows.join("\r\n") + "\r\n";
  }

  // ── Google Maps 單筆導航連結 ──
  function mapsLink(item) {
    const loc = String((item && item.location) || "").trim();
    if (!loc) return null;
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(loc)}`;
  }

  root.ScoutExport = {
    DEFAULT_DURATION, DEFAULT_TIME, CSV_HEADER,
    dayDate, itemRange, buildIcs, gcalLink, buildMapsCsv, mapsLink,
  };
})(typeof window !== "undefined" ? window : this);
