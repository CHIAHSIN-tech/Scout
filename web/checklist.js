// checklist.js — Scout 確認清單（合併版的「行程」Tab）
//
// 來源：witsper-stanley/scout-checklist 的 app.js @ 9bf6a62，搬進合併版時做了三處改動：
//   1. 整包用 IIFE 包起來——原檔滿地 top-level 變數（app / curTrip / sb / …），
//      與同頁的 buylist.js 會互撞（spec-scout-app-merge.md §5.2）。
//   2. 移除 ?demo=1 範例模式（spec §4.1 決策：合併版一律接真實 Supabase）。
//   3. 其餘邏輯一字未改。
//
// 資料來源：Supabase REST（PostgREST）。身分：網址 ?trip=<trip_id>。同步：手動重新整理。
// 兩軸：confirm_required（必須確認/可以彈性）× is_confirmed（已確認/未確認）。
// day_number 為 NULL = 候選中（未排定）。
//
// 三個檢視（tab）：確認清單 / 行程表(Day 分組) / 時間軸(拖曳調時間)。＋ AI 貼文字匯入。

(function () {
"use strict";

const CATEGORY_LABEL = {
  restaurant: "🍽️ 餐廳",
  hotel:      "🏨 住宿",
  attraction: "🏛️ 景點",
  shopping:   "🛍️ 購物",
  transport:  "🚆 交通",
  other:      "📌 其他",
};

const app = document.getElementById("app");

// ── Supabase 連線（寫死；anon key 可公開）──
// 目的：一 pull 就能用，不必自己弄 config.js。
// 若本機有 config.js（gitignored），它可覆寫這裡、或補上 GEMINI_API_KEY（AI 匯入要用）。
window.SCOUT_CONFIG = Object.assign({
  SUPABASE_URL: "https://uarkccyqcqvgxukjcrey.supabase.co",
  SUPABASE_ANON_KEY: "sb_publishable_CPg7D4iO0uBA0gnfd-rlFA_2Ia-9P4V", // gitleaks:allow — Supabase publishable key，設計上即公開，靠 RLS 保護
}, window.SCOUT_CONFIG || {});

// ── 持久全域狀態（供三個 view 共用；load() 後填入）──
let curTrip = null;
let curItems = [];
let currentView = "checklist";   // checklist | dayplan | timeline
let TRIP_CTX = { totalDays: 0, dayLabel: (d) => `Day ${d}` };

// ── 小工具 ──
function getTripId() { return new URLSearchParams(location.search).get("trip"); }

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function whereLabel(it) {
  if (it.day_number != null) {
    const t = it.start_time ? ` ${it.start_time}` : "";
    return `Day ${it.day_number}${t}`;
  }
  return "候選中";
}

function categoryIcon(category) {
  const label = CATEGORY_LABEL[category] || CATEGORY_LABEL.other;
  return label.split(" ")[0];   // "🍽️ 餐廳" → "🍽️"
}

function buildTripCtx(trip) {
  if (!trip || !trip.start_date || !trip.end_date) {
    return { totalDays: 0, dayLabel: (d) => `Day ${d}` };
  }
  const s = new Date(trip.start_date + "T00:00:00");
  const e = new Date(trip.end_date + "T00:00:00");
  const totalDays = Math.round((e - s) / 86400000) + 1;
  const dayLabel = (d) => {
    const dt = new Date(s.getTime() + (d - 1) * 86400000);
    const mm = String(dt.getMonth() + 1).padStart(2, "0");
    const dd = String(dt.getDate()).padStart(2, "0");
    return `Day ${d} (${mm}/${dd})`;
  };
  return { totalDays, dayLabel };
}

function configError() {
  const cfg = window.SCOUT_CONFIG || {};
  if (!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY ||
      cfg.SUPABASE_URL.includes("your-project") ||
      cfg.SUPABASE_ANON_KEY.includes("your-anon-key")) {
    return "尚未設定 Supabase 連線。請複製 config.example.js 為 config.js 並填入 SUPABASE_URL 與 SUPABASE_ANON_KEY。";
  }
  return null;
}

// ── Supabase REST ──
async function sb(path, opts = {}) {
  const cfg = window.SCOUT_CONFIG;
  const res = await fetch(`${cfg.SUPABASE_URL}/rest/v1/${path}`, {
    ...opts,
    headers: {
      apikey: cfg.SUPABASE_ANON_KEY,
      Authorization: `Bearer ${cfg.SUPABASE_ANON_KEY}`,
      "Content-Type": "application/json",
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) { const body = await res.text(); throw new Error(`${res.status} ${body}`); }
  return res;
}

async function loadTrip(tripId) {
  const res = await sb(`trips?id=eq.${encodeURIComponent(tripId)}&select=*`);
  const data = await res.json();
  return data[0] || null;
}

async function loadItems(tripId) {
  const order = "confirm_required.desc,is_confirmed.asc,day_number.asc,start_time.asc";
  const res = await sb(`itinerary_items?trip_id=eq.${encodeURIComponent(tripId)}&select=*&order=${order}`);
  return res.json();
}

async function patchItem(itemId, fields) {
  await sb(`itinerary_items?id=eq.${encodeURIComponent(itemId)}`, {
    method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify(fields),
  });
}

// 新增一筆項目（AI 匯入用）
async function addItem(fields) {
  await sb(`itinerary_items`, {
    method: "POST", headers: { Prefer: "return=minimal" },
    body: JSON.stringify({ trip_id: getTripId(), ...fields }),
  });
}

const setConfirmed    = (id, v)         => patchItem(id, { is_confirmed: v });
const scheduleItem    = (id, day, time) => patchItem(id, { day_number: day, start_time: time });
const unscheduleItem  = (id)            => patchItem(id, { day_number: null, start_time: null });

// ══════════════════════════════════════════════════════════
//  App 外殼：頁首 + toolbar + tab 列 + #view 容器
// ══════════════════════════════════════════════════════════
function renderBanner(type, html) { return `<div class="banner ${type}">${html}</div>`; }

const VIEWS = [
  { key: "checklist", label: "確認清單" },
  { key: "dayplan",   label: "行程表" },
  { key: "timeline",  label: "時間軸" },
];

function renderApp() {
  TRIP_CTX = buildTripCtx(curTrip);
  const updated = new Date().toLocaleTimeString("zh-Hant", { hour: "2-digit", minute: "2-digit" });
  app.innerHTML = `
    <div class="header">
      <div class="title">${escapeHtml(curTrip ? curTrip.name : "確認清單")}</div>
      <div class="sub">出發前確認清單</div>
    </div>
    <div class="toolbar">
      <button class="refresh-btn" id="refresh">↻ 重新整理</button>
      <button class="ai-import-btn" id="ai-import-open">✨ AI 匯入行程</button>
      <span class="updated">更新於 ${updated}</span>
    </div>
    <div class="tabbar" id="tabbar">
      ${VIEWS.map((v) => `<button data-view="${v.key}" class="${v.key === currentView ? "on" : ""}">${v.label}</button>`).join("")}
    </div>
    <div id="view"></div>
  `;
  wireShell();
  renderCurrentView();
}

function switchView(v) {
  if (!VIEWS.some((x) => x.key === v)) return;
  currentView = v;
  document.querySelectorAll("#tabbar button").forEach((b) => b.classList.toggle("on", b.dataset.view === v));
  renderCurrentView();
}

function renderCurrentView() {
  const view = document.getElementById("view");
  if (!view) return;
  if (currentView === "checklist") {
    view.innerHTML = renderChecklistSections(curItems);
    wireEvents();
  } else if (currentView === "dayplan") {
    renderDayView();
  } else if (currentView === "timeline") {
    renderTimeline();
  }
}

function wireShell() {
  const refresh = document.getElementById("refresh");
  if (refresh) refresh.addEventListener("click", () => load());
  const aiBtn = document.getElementById("ai-import-open");
  if (aiBtn) aiBtn.addEventListener("click", openAiImportModal);
  document.querySelectorAll("#tabbar button").forEach((b) =>
    b.addEventListener("click", () => switchView(b.dataset.view)));
}

// ── 確認清單 view（三段；手機收合，AC-7）──
function scheduleControl(it) {
  if (it.day_number == null && TRIP_CTX.totalDays > 0) {
    let opts = "";
    for (let d = 1; d <= TRIP_CTX.totalDays; d++) opts += `<option value="${d}">${TRIP_CTX.dayLabel(d)}</option>`;
    return `
      <details class="sched">
        <summary>📅 排入行程</summary>
        <div class="sched-row">
          <select id="sched-day-${it.id}" aria-label="排到第幾天">${opts}</select>
          <input id="sched-time-${it.id}" type="time" value="09:00" aria-label="開始時間">
          <button class="sched-btn" data-id="${it.id}">排入</button>
        </div>
      </details>`;
  }
  if (it.day_number != null) return `<button class="unsched-btn" data-id="${it.id}">↩ 退回候選</button>`;
  return "";
}

function renderCard(it, kind) {
  const cat = CATEGORY_LABEL[it.category] || "📌 其他";
  const notes = it.notes ? `<div class="card-notes">${escapeHtml(it.notes)}</div>` : "";
  const booking = it.booking_ref ? `<div class="card-booking">📋 ${escapeHtml(it.booking_ref)}</div>` : "";
  const checked = it.is_confirmed ? "on" : "";
  const mark = it.is_confirmed ? "✓" : "";
  return `
    <div class="card ${kind}">
      <button class="check ${checked}" data-id="${it.id}" data-confirmed="${it.is_confirmed ? 1 : 0}" aria-label="切換已確認">${mark}</button>
      <div class="card-body">
        <div class="card-cat">${cat}　·　${escapeHtml(whereLabel(it))}</div>
        <div class="card-name">${escapeHtml(it.name)}</div>
        ${booking}${notes}
        <div class="card-sched">${scheduleControl(it)}</div>
      </div>
    </div>`;
}

// 資訊架構（手機優先）：必須確認置頂+永遠展開+數量摘要；已確認/可以彈性 預設收合(<details>)。
function renderChecklistSections(list) {
  const mustItems       = list.filter((i) => i.confirm_required);
  const mustUnconfirmed = mustItems.filter((i) => !i.is_confirmed);
  const mustConfirmed   = mustItems.filter((i) => i.is_confirmed);
  const flexible        = list.filter((i) => !i.confirm_required);

  let html = "";
  const zero = mustUnconfirmed.length === 0 ? "zero" : "";
  html += `<div class="section-title">⚠️ 必須確認 <span class="count ${zero}">${mustUnconfirmed.length}</span></div>`;
  if (mustUnconfirmed.length === 0) {
    html += renderBanner("ok", "✅ 必訂項目都確認完成了，可以安心出發");
  } else {
    html += renderBanner("warn", `還有 ${mustUnconfirmed.length} 個項目需要訂位 / 預約 / 確認`);
    html += mustUnconfirmed.map((it) => renderCard(it, "priority")).join("");
  }
  if (mustConfirmed.length > 0) {
    html += `<details class="done-group"><summary>✅ 已確認 <span class="count">${mustConfirmed.length}</span></summary>`;
    html += mustConfirmed.map((it) => renderCard(it, "done")).join("");
    html += `</details>`;
  }
  html += `<details class="flex-group"><summary>🟢 可以彈性 <span class="count">${flexible.length}</span>` +
          `<span class="section-hint">就算沒排定也不算遺漏</span></summary>`;
  html += flexible.length === 0 ? `<div class="empty">沒有彈性項目</div>`
                                : flexible.map((it) => renderCard(it, "flexible")).join("");
  html += `</details>`;
  return html;
}

function wireEvents() {
  document.querySelectorAll(".check").forEach((btn) => {
    btn.addEventListener("click", () => guard(btn, () => setConfirmed(btn.dataset.id, btn.dataset.confirmed !== "1")));
  });
  document.querySelectorAll(".sched-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const day = Number(document.getElementById(`sched-day-${id}`).value);
      const time = document.getElementById(`sched-time-${id}`).value;
      if (!/^\d{2}:\d{2}$/.test(time)) { alert("請輸入正確時間（HH:MM）"); return; }
      guard(btn, () => scheduleItem(id, day, time));
    });
  });
  document.querySelectorAll(".unsched-btn").forEach((btn) => {
    btn.addEventListener("click", () => guard(btn, () => unscheduleItem(btn.dataset.id)));
  });
}

async function guard(btn, action) {
  btn.disabled = true;
  try { await action(); await load(); }
  catch (e) { btn.disabled = false; showError(e); }
}

// ══════════════════════════════════════════════════════════
//  行程表（Day 分組）view — AC-1 / AC-2
// ══════════════════════════════════════════════════════════
function planPlace(it) {
  if (it.notes) return escapeHtml(it.notes);
  if (it.booking_ref) return "📋 " + escapeHtml(it.booking_ref);
  return "";
}
function renderPlanRow(it) {
  const icon = categoryIcon(it.category);
  const time = it.start_time ? `<div class="plan-time">${escapeHtml(it.start_time)}</div>`
                             : `<div class="plan-time none">—</div>`;
  const place = planPlace(it);
  const placeHtml = place ? `<div class="plan-place">${place}</div>` : "";
  return `
    <div class="plan-row">
      ${time}
      <div class="plan-icon">${icon}</div>
      <div class="plan-body"><div class="plan-name">${escapeHtml(it.name)}</div>${placeHtml}</div>
    </div>`;
}
function renderDayView() {
  const host = document.getElementById("view");
  if (!host) return;
  const scheduled = curItems.filter((i) => i.day_number != null);
  const unscheduled = curItems.filter((i) => i.day_number == null);
  const byTime = (a, b) => {
    const ta = a.start_time || "99:99", tb = b.start_time || "99:99";
    return ta < tb ? -1 : ta > tb ? 1 : 0;
  };
  let html = "";
  const nLeft = unscheduled.length;
  if (nLeft > 0) {
    html += `<button class="dayplan-alert" id="dayplan-goto-candidates">
        <span>📋 還有 ${nLeft} 項未排定，點這裡去安排</span><span class="arrow">→</span></button>`;
  } else {
    html += `<div class="dayplan-alert zero">✅ 所有項目都已排入行程</div>`;
  }
  let totalDays = TRIP_CTX.totalDays;
  if (totalDays <= 0) totalDays = scheduled.reduce((m, i) => Math.max(m, i.day_number || 0), 0);
  for (let d = 1; d <= totalDays; d++) {
    const dayItems = scheduled.filter((i) => i.day_number === d).sort(byTime);
    html += `<div class="day-block"><div class="day-head">${escapeHtml(TRIP_CTX.dayLabel(d))}` +
      (dayItems.length ? `<span class="day-count">${dayItems.length} 項</span>` : ``) + `</div>`;
    html += dayItems.length === 0 ? `<div class="day-empty">這天還沒安排</div>`
                                  : dayItems.map(renderPlanRow).join("");
    html += `</div>`;
  }
  if (totalDays === 0) html += `<div class="empty">還沒有天數資訊，也還沒有已排定的項目。</div>`;
  host.innerHTML = html;
  const goto = document.getElementById("dayplan-goto-candidates");
  if (goto) goto.addEventListener("click", () => switchView("checklist"));
}

// ══════════════════════════════════════════════════════════
//  時間軸 view — AC-3,4,5,6（拖曳調時間 / 重疊並排 / 衝突警告 / 今天高亮）
// ══════════════════════════════════════════════════════════
const TL_START_MIN = 8 * 60, TL_END_MIN = 22 * 60, TL_PX_PER_MIN = 1, TL_SNAP = 5, TL_MIN_H = 26;
let tlDay = null;

function tlToMin(t) {
  if (!t || !/^\d{1,2}:\d{2}$/.test(t)) return null;
  const [h, m] = t.split(":").map(Number); return h * 60 + m;
}
function tlToStr(min) {
  min = Math.max(0, Math.min(24 * 60 - 1, Math.round(min)));
  return `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;
}
function tlDateOfDay(day) {
  if (!curTrip || !curTrip.start_date) return null;
  const s = new Date(curTrip.start_date + "T00:00:00");
  if (isNaN(s)) return null;
  return new Date(s.getTime() + (day - 1) * 86400000);
}
function tlIsToday(day) {
  const d = tlDateOfDay(day); if (!d) return false;
  const now = new Date();
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
}
function tlFindTodayDay() {
  const total = (TRIP_CTX && TRIP_CTX.totalDays) || 0;
  for (let d = 1; d <= total; d++) if (tlIsToday(d)) return d;
  return null;
}
function tlOverlaps(a, b) {
  const as = tlToMin(a.start_time), bs = tlToMin(b.start_time);
  if (as == null || bs == null) return false;
  return as < bs + (b.duration_minutes || 0) && bs < as + (a.duration_minutes || 0);
}
function tlPackColumns(dayItems) {
  const sorted = dayItems.slice().sort((a, b) => (tlToMin(a.start_time) ?? 0) - (tlToMin(b.start_time) ?? 0));
  const layout = new Map();
  let cluster = [], clusterEnd = -1;
  const flush = () => {
    if (!cluster.length) return;
    const cols = [];
    for (const it of cluster) {
      let placed = false;
      for (let c = 0; c < cols.length; c++) {
        if (!cols[c].some((o) => tlOverlaps(o, it))) { cols[c].push(it); layout.set(it.id, { col: c }); placed = true; break; }
      }
      if (!placed) { cols.push([it]); layout.set(it.id, { col: cols.length - 1 }); }
    }
    for (const it of cluster) layout.get(it.id).cols = cols.length;
    cluster = []; clusterEnd = -1;
  };
  for (const it of sorted) {
    const s = tlToMin(it.start_time), e = s + (it.duration_minutes || 0);
    if (cluster.length && s >= clusterEnd) flush();
    cluster.push(it); clusterEnd = Math.max(clusterEnd, e);
  }
  flush();
  return layout;
}
function renderTimeline() {
  const root = document.getElementById("view");
  if (!root) return;
  const total = (TRIP_CTX && TRIP_CTX.totalDays) || 0;
  if (tlDay == null || tlDay < 1 || (total && tlDay > total)) tlDay = tlFindTodayDay() || 1;

  let opts = "";
  const dayCount = total || 1;
  for (let d = 1; d <= dayCount; d++) {
    const todayMark = tlIsToday(d) ? " ·今天" : "";
    opts += `<option value="${d}" ${d === tlDay ? "selected" : ""}>${escapeHtml(TRIP_CTX.dayLabel(d))}${todayMark}</option>`;
  }
  const isToday = tlIsToday(tlDay);
  let html = `
    <div class="tl-head">
      <select id="tl-daysel" class="tl-daysel ${isToday ? "is-today" : ""}" aria-label="選擇天數">${opts}</select>
      ${isToday ? `<span class="tl-today-badge">今天</span>` : ""}
      <span class="tl-hint">拖曳卡片可改時間</span>
    </div>`;

  const dayItems = curItems.filter((it) => it.day_number === tlDay && tlToMin(it.start_time) != null);
  const layout = tlPackColumns(dayItems);
  const gridH = (TL_END_MIN - TL_START_MIN) * TL_PX_PER_MIN;

  let lines = "";
  for (let mn = TL_START_MIN; mn <= TL_END_MIN; mn += 60) {
    const top = (mn - TL_START_MIN) * TL_PX_PER_MIN;
    lines += `<div class="tl-hourlabel" style="top:${top}px">${tlToStr(mn)}</div>`;
    lines += `<div class="tl-hourline" style="top:${top}px"></div>`;
  }
  let evs = "";
  for (const it of dayItems) {
    const s = tlToMin(it.start_time);
    const dur = Math.max(TL_SNAP, it.duration_minutes || 30);
    const top = (s - TL_START_MIN) * TL_PX_PER_MIN;
    const h = Math.max(TL_MIN_H, dur * TL_PX_PER_MIN);
    const pack = layout.get(it.id) || { col: 0, cols: 1 };
    const gapPct = 1.5;
    const widthPct = (100 - gapPct * (pack.cols - 1)) / pack.cols;
    const leftPct = (widthPct + gapPct) * pack.col;
    const conflict = dayItems.some((o) => o.id !== it.id && tlOverlaps(o, it));
    const icon = categoryIcon(it.category);
    evs += `
      <div class="tl-item ${conflict ? "conflict" : ""}" data-id="${it.id}" data-start="${s}" data-dur="${dur}"
           style="top:${top}px;height:${h}px;left:${leftPct}%;width:${widthPct}%">
        <div class="tl-item-time">${conflict ? '<span class="tl-item-warn">⚠️ </span>' : ""}${tlToStr(s)}–${tlToStr(s + dur)}</div>
        <div class="tl-item-name">${icon} ${escapeHtml(it.name)}</div>
      </div>`;
  }
  html += `<div class="tl-grid ${isToday ? "is-today" : ""}" style="height:${gridH}px">${lines}
      <div class="tl-track" style="height:${gridH}px">${evs}</div></div>`;
  if (dayItems.length === 0) html += `<div class="tl-empty">這天還沒有排定時間的行程</div>`;

  root.innerHTML = html;
  const sel = root.querySelector("#tl-daysel");
  if (sel) sel.addEventListener("change", () => { tlDay = Number(sel.value); renderTimeline(); });
  root.querySelectorAll(".tl-item").forEach((el) => tlAttachDrag(el));
}
function tlAttachDrag(el) {
  let startY = 0, baseTop = 0, startMin = 0, moved = false, dur = 0;
  const clampTop = (topPx) => {
    const maxTop = (TL_END_MIN - TL_START_MIN - dur) * TL_PX_PER_MIN;
    return Math.max(0, Math.min(maxTop, topPx));
  };
  const onDown = (e) => {
    if (e.button != null && e.button !== 0) return;
    startY = e.clientY; baseTop = parseFloat(el.style.top) || 0;
    startMin = Number(el.dataset.start); dur = Number(el.dataset.dur); moved = false;
    el.classList.add("dragging"); el.setPointerCapture(e.pointerId);
    el.addEventListener("pointermove", onMove); el.addEventListener("pointerup", onUp); el.addEventListener("pointercancel", onUp);
    e.preventDefault();
  };
  const onMove = (e) => {
    const dy = e.clientY - startY; if (Math.abs(dy) > 2) moved = true;
    el.style.top = clampTop(baseTop + dy) + "px";
  };
  const onUp = async (e) => {
    el.classList.remove("dragging");
    el.removeEventListener("pointermove", onMove); el.removeEventListener("pointerup", onUp); el.removeEventListener("pointercancel", onUp);
    try { el.releasePointerCapture(e.pointerId); } catch (_) {}
    if (!moved) return;
    let newMin = TL_START_MIN + clampTop(parseFloat(el.style.top) || 0) / TL_PX_PER_MIN;
    newMin = Math.round(newMin / TL_SNAP) * TL_SNAP;
    if (newMin === startMin) { renderTimeline(); return; }
    const id = el.dataset.id, newTime = tlToStr(newMin);
    const it = curItems.find((x) => String(x.id) === String(id));
    const prevTime = it ? it.start_time : null;
    if (it) it.start_time = newTime;
    renderTimeline();
    try { await scheduleItem(id, it ? it.day_number : tlDay, newTime); }
    catch (err) { if (it) it.start_time = prevTime; renderTimeline(); alert("時間更新失敗，已還原：\n" + (err && err.message ? err.message : err)); }
  };
  el.addEventListener("pointerdown", onDown);
}

// ══════════════════════════════════════════════════════════
//  AI 貼文字匯入 — AC-8
// ══════════════════════════════════════════════════════════
const AI_VALID_CATEGORIES = ["restaurant", "hotel", "attraction", "transport", "shopping", "other"];

async function aiParseItinerary(text) {
  const totalDays = (TRIP_CTX && TRIP_CTX.totalDays) ? TRIP_CTX.totalDays : 0;
  const raw = await aiGeminiRaw(text, totalDays);
  if (!raw.trim()) throw new Error("AI 沒有回傳內容，請換段文字再試。");
  const parsed = extractJsonArray(raw);
  if (!Array.isArray(parsed)) throw new Error("AI 回傳格式無法解析成行程清單。");
  return parsed;
}

// 取得 Gemini 原始回傳。
// 優先走部署版 proxy（/.netlify/functions/ai-parse；金鑰在後端環境變數，不外露到前端）；
// 本機（無 functions，proxy 回 404）落回 config.js 的金鑰直接呼叫，方便開發。
async function aiGeminiRaw(text, totalDays) {
  // 1) proxy（Netlify Function）
  try {
    const res = await fetch("/.netlify/functions/ai-parse", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, totalDays }),
    });
    if (res.ok) { const d = await res.json(); return d.raw || ""; }
    if (res.status !== 404) {  // proxy 存在但回錯 → 明確丟出，不要靜默落 fallback
      let msg = ""; try { msg = (await res.json()).error || ""; } catch (_) {}
      throw new Error(`AI 服務錯誤（${res.status}）${msg ? "：" + msg : ""}`);
    }
    // 404 = 本機沒有 functions → 往下走 fallback
  } catch (e) {
    if (e instanceof Error && e.message.startsWith("AI 服務錯誤")) throw e;
    // 其餘（連線層失敗，通常是本機無 proxy）→ 落 fallback
  }

  // 2) fallback：本機開發用 config.js 的金鑰直接打 Gemini
  const cfg = window.SCOUT_CONFIG || {};
  const key = cfg.GEMINI_API_KEY;
  if (!key || key.includes("your-") || key.trim() === "") {
    throw new Error("AI 服務未就緒：部署版由後端 proxy 提供；本機開發請在 config.js 填 GEMINI_API_KEY。");
  }
  const dayHint = totalDays > 0 ? `本趟共 ${totalDays} 天，day 請落在 1~${totalDays}。` : "";
  const prompt =
    "你是行程解析器。將以下文字整理成 JSON 陣列，每個元素代表一個行程項目。\n" +
    "只輸出 JSON 陣列本身，不要說明文字、不要 markdown 程式碼框。\n" +
    "每個元素固定包含：\n" +
    "  name: 字串，景點/餐廳/活動名稱（必填）\n" +
    "  day: 整數，第幾天（不確定就用 1）。" + dayHint + "\n" +
    '  time: 字串 "HH:MM" 24 小時制（不確定就用 "09:00"）\n' +
    "  category: restaurant/hotel/attraction/transport/shopping/other 之一\n" +
    "  location: 字串，地點或店名（沒有就空字串）\n" +
    "文字如下：\n" + text;
  const model = cfg.GEMINI_MODEL || "gemini-2.5-flash";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`;
  let res;
  try {
    res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.2, responseMimeType: "application/json" } }),
    });
  } catch (e) { throw new Error("無法連線到 Gemini：" + e.message); }
  if (!res.ok) { const body = await res.text().catch(() => ""); throw new Error(`Gemini 回應 ${res.status}：${body.slice(0, 300)}`); }
  const data = await res.json();
  return data?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") ?? "";
}
function extractJsonArray(raw) {
  const cleaned = raw.replace(/```json/gi, "").replace(/```/g, "").trim();
  try { return JSON.parse(cleaned); }
  catch (_) {
    const s = cleaned.indexOf("["), e = cleaned.lastIndexOf("]");
    if (s !== -1 && e !== -1 && e > s) { try { return JSON.parse(cleaned.slice(s, e + 1)); } catch (_) {} }
    return null;
  }
}
function aiRowToFields(row) {
  const name = String(row?.name ?? "").trim();
  if (!name) return null;
  let day = parseInt(row?.day, 10);
  if (!Number.isFinite(day) || day < 1) day = 1;
  const total = (TRIP_CTX && TRIP_CTX.totalDays) ? TRIP_CTX.totalDays : 0;
  if (total > 0 && day > total) day = total;
  let time = String(row?.time ?? "").trim();
  if (!/^\d{1,2}:\d{2}$/.test(time)) time = "09:00";
  else { const [h, m] = time.split(":"); time = `${String(h).padStart(2, "0")}:${m}`; }
  let category = String(row?.category ?? "").trim().toLowerCase();
  if (!AI_VALID_CATEGORIES.includes(category)) category = "other";
  const location = String(row?.location ?? "").trim();
  return { name, category, day_number: day, start_time: time, duration_minutes: 60,
    is_confirmed: false, confirm_required: false, notes: location ? `地點：${location}` : "", booking_ref: "" };
}
function openAiImportModal() {
  const bd = document.getElementById("ai-import-backdrop"); if (!bd) return;
  bd.classList.remove("hidden");
  const msg = document.getElementById("ai-import-msg");
  if (msg) { msg.textContent = ""; msg.className = "ai-msg"; }
  const ta = document.getElementById("ai-import-text");
  if (ta) setTimeout(() => ta.focus(), 50);
}
function closeAiImportModal() {
  const bd = document.getElementById("ai-import-backdrop"); if (bd) bd.classList.add("hidden");
}
async function runAiImport() {
  const ta = document.getElementById("ai-import-text");
  const msg = document.getElementById("ai-import-msg");
  const runBtn = document.getElementById("ai-import-run");
  const cancelBtn = document.getElementById("ai-import-cancel");
  if (!ta || !msg || !runBtn) return;
  const text = ta.value.trim();
  if (!text) { msg.className = "ai-msg err"; msg.textContent = "請先貼上行程文字。"; return; }
  runBtn.disabled = true; if (cancelBtn) cancelBtn.disabled = true;
  msg.className = "ai-msg busy"; msg.textContent = "AI 解析中…";
  try {
    const rows = await aiParseItinerary(text);
    const fieldsList = rows.map(aiRowToFields).filter(Boolean);
    if (fieldsList.length === 0) throw new Error("AI 沒有從這段文字抓到可加入的行程項目。");
    msg.textContent = `解析出 ${fieldsList.length} 筆，寫入中…`;
    let ok = 0, fail = 0;
    for (const f of fieldsList) { try { await addItem(f); ok++; } catch (_) { fail++; } }
    if (ok === 0) throw new Error("項目寫入 Supabase 全部失敗，請確認連線與資料表權限。");
    msg.className = "ai-msg ok";
    msg.textContent = `已加入 ${ok} 筆` + (fail > 0 ? `（${fail} 筆失敗）` : "") + "，重新載入中…";
    setTimeout(async () => { closeAiImportModal(); ta.value = ""; await load(); }, 700);
  } catch (e) {
    msg.className = "ai-msg err"; msg.textContent = "匯入失敗：" + e.message;
  } finally {
    runBtn.disabled = false; if (cancelBtn) cancelBtn.disabled = false;
  }
}
function wireAiImportModalOnce() {
  const closeX = document.getElementById("ai-import-close");
  const cancel = document.getElementById("ai-import-cancel");
  const run = document.getElementById("ai-import-run");
  const bd = document.getElementById("ai-import-backdrop");
  if (closeX) closeX.addEventListener("click", closeAiImportModal);
  if (cancel) cancel.addEventListener("click", closeAiImportModal);
  if (run) run.addEventListener("click", runAiImport);
  if (bd) bd.addEventListener("click", (e) => { if (e.target === bd) closeAiImportModal(); });
}

function showError(err) {
  app.innerHTML = renderBanner("error",
    `操作失敗：<br><code>${escapeHtml(err.message)}</code><br><br>` +
    `請確認 config.js 的 SUPABASE_URL / anon key 正確、且 itinerary_items 表已對 anon 開放存取。`);
}

// ── 進入點 ──
async function load() {
  const cfgErr = configError();
  if (cfgErr) { app.innerHTML = renderBanner("error", escapeHtml(cfgErr)); return; }
  const tripId = getTripId();
  if (!tripId) {
    app.innerHTML = renderBanner("error", "網址缺少 ?trip=&lt;旅程編號&gt;。請使用分享連結開啟，例如 index.html?trip=1");
    return;
  }
  app.innerHTML = `<div class="status">載入中…</div>`;
  try {
    const [trip, itemsData] = await Promise.all([loadTrip(tripId), loadItems(tripId)]);
    curTrip = trip; curItems = itemsData;
    renderApp();
  } catch (e) { showError(e); }
}

wireAiImportModalOnce();  // modal 是靜態 DOM，只綁一次
load();

})();
