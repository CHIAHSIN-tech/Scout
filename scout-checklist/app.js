// app.js — Scout 確認清單網頁版
//
// 資料來源：Supabase REST（PostgREST），與 Streamlit 後端共用同一個資料庫。
// 身分機制：網址帶 ?trip=<trip_id>，trip_id 即存取憑證（不做帳號系統）。
// 同步機制：手動「重新整理」按鈕（不訂閱 Realtime）。
//
// 兩軸模型（沿用既有命名）：
//   confirm_required  → 必須確認 / 可以彈性
//   is_confirmed      → 已確認 / 未確認
// 「必須確認 + 未確認」= 出發前不能遺漏的重點，放在最上面最顯眼處。
//
// 候選 ↔ 已排定：day_number 為 NULL = 候選中。網頁版也能把候選排入某天某時段
// （📅 排入行程），或把已排定的退回候選（↩）。與 Streamlit 端共用同一份資料。
//
// 兩個頂層視圖（spec-scout-checklist-itinerary-view）：
//   ✅ 確認清單  → 既有兩軸儀表板（手機資訊架構：必須確認置頂、其他區塊收合）
//   🗓️ 行程表    → 依 Day 分組的清單 + 可拖曳調整時間的時間軸 + AI 文字匯入

const CATEGORY_LABEL = {
  restaurant: "🍽️ 餐廳",
  hotel:      "🏨 住宿",
  attraction: "🏛️ 景點",
  shopping:   "🛍️ 購物",
  transport:  "🚆 交通",
  other:      "📌 其他",
};

const app = document.getElementById("app");

// 旅程的天數資訊（render 時依 trip 起訖日算出，供排程下拉選單使用）
let TRIP_CTX = { totalDays: 0, dayLabel: (d) => `Day ${d}` };

// ── 視圖狀態（記憶體層級，切換不需重新打 API）──
let VIEW = "confirm";       // "confirm" | "itinerary"
let ITIN_MODE = "list";     // 行程表內：「list」清單 / 「timeline」時間軸
let TL_DAY = null;          // 時間軸目前聚焦的第幾天
let AI_OPEN = false;        // AI 匯入面板是否展開
let LAST = { trip: null, items: [] }; // 最近一次載入的資料（供切換視圖時免重撈）

// 時間軸刻度：6:00–24:00，每分鐘 PXPM 像素
const TL_START = 6;   // 起始小時
const TL_END = 24;    // 結束小時
const PXPM = 1.1;     // pixels per minute

// ── 範例模式 ──
// 加 ?demo=1 即可在「沒有 Supabase」的情況下預覽整個畫面，按鈕也能動（純記憶體，不連網）。
// 用途：開發 / 預覽 UI 與互動，不影響正式網址。正式網址（無 ?demo=1）即直接讀寫 Supabase。
const DEMO = new URLSearchParams(location.search).get("demo") === "1";
const DEMO_TRIP = {
  id: 0, name: "（範例）沖繩 5 天",
  start_date: "2026-06-29", end_date: "2026-07-03",
};
let DEMO_ITEMS = [
  { id: 1, name: "國際通燒肉（要訂位）", category: "restaurant", day_number: null, start_time: null, duration_minutes: 90, location: "國際通", notes: "人氣店，建議提前訂位", booking_ref: "", confirm_required: true,  is_confirmed: false },
  { id: 5, name: "山原溫泉（需預約）",   category: "other",      day_number: null, start_time: null, duration_minutes: 60, location: "本部町",  notes: "",               booking_ref: "", confirm_required: true,  is_confirmed: false },
  { id: 2, name: "那霸麗思飯店",         category: "hotel",      day_number: 1, start_time: "15:00", duration_minutes: 30, location: "那霸",   notes: "",            booking_ref: "CONF-88123", confirm_required: true, is_confirmed: true },
  { id: 3, name: "美麗海水族館",         category: "attraction", day_number: 2, start_time: "10:00", duration_minutes: 120, location: "本部町", notes: "",            booking_ref: "", confirm_required: false, is_confirmed: false },
  { id: 6, name: "海洋博公園散步",       category: "attraction", day_number: 2, start_time: "10:30", duration_minutes: 90, location: "本部町",  notes: "與水族館時段重疊（示範）", booking_ref: "", confirm_required: false, is_confirmed: false },
  { id: 7, name: "海葡萄丼午餐",         category: "restaurant", day_number: 2, start_time: "12:30", duration_minutes: 60, location: "本部町",  notes: "",            booking_ref: "", confirm_required: false, is_confirmed: false },
  { id: 4, name: "古宇利大橋兜風",       category: "transport",  day_number: null, start_time: null, duration_minutes: 60, location: "古宇利島", notes: "租車順路",     booking_ref: "", confirm_required: false, is_confirmed: false },
];

// ── 小工具 ──
function getTripId() {
  return new URLSearchParams(location.search).get("trip");
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// "HH:MM" → 分鐘數；無法解析回傳 null
function timeToMin(t) {
  if (!t) return null;
  const m = /^(\d{1,2}):(\d{2})/.exec(String(t));
  if (!m) return null;
  return (+m[1]) * 60 + (+m[2]);
}

// 分鐘數 → "HH:MM"（夾在 00:00–23:59）
function minToTime(min) {
  min = Math.max(0, Math.min(24 * 60 - 1, Math.round(min)));
  const h = Math.floor(min / 60), m = min % 60;
  return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
}

function whereLabel(it) {
  // 已排定顯示 Day N HH:MM；候選中沒有日期/時段
  if (it.day_number != null) {
    const t = it.start_time ? ` ${it.start_time}` : "";
    return `Day ${it.day_number}${t}`;
  }
  return "候選中";
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

// 「今天」是這趟旅程的第幾天；不在旅程區間內回傳 null
function todayDayNumber(trip) {
  if (!trip || !trip.start_date || !TRIP_CTX.totalDays) return null;
  const s = new Date(trip.start_date + "T00:00:00");
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diff = Math.round((today - s) / 86400000) + 1;
  return (diff >= 1 && diff <= TRIP_CTX.totalDays) ? diff : null;
}

function firstPlacedDay(items) {
  const ds = items.filter((i) => i.day_number != null).map((i) => i.day_number);
  return ds.length ? Math.min(...ds) : null;
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

// ── Supabase REST 呼叫 ──
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
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${body}`);
  }
  return res;
}

async function loadTrip(tripId) {
  const res = await sb(`trips?id=eq.${encodeURIComponent(tripId)}&select=*`);
  const data = await res.json();
  return data[0] || null;
}

async function loadItems(tripId) {
  // 排序：必須確認優先、未確認優先，再依天/時間
  const order = "confirm_required.desc,is_confirmed.asc,day_number.asc,start_time.asc";
  const res = await sb(
    `itinerary_items?trip_id=eq.${encodeURIComponent(tripId)}&select=*&order=${order}`
  );
  return res.json();
}

async function patchItem(itemId, fields) {
  if (DEMO) {
    // 範例模式：直接改記憶體裡的資料，不連網
    const it = DEMO_ITEMS.find((i) => String(i.id) === String(itemId));
    if (it) Object.assign(it, fields);
    return;
  }
  await sb(`itinerary_items?id=eq.${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    headers: { Prefer: "return=minimal" },
    body: JSON.stringify(fields),
  });
}

// AI 匯入：一次新增多筆項目
async function insertItems(tripId, recs) {
  const rows = recs.map((r) => ({
    trip_id: Number(tripId),
    day_number: (r.day === undefined ? null : r.day),
    name: r.name || "未命名",
    category: r.category || "other",
    start_time: r.start_time || null,
    duration_minutes: Number(r.duration_minutes) || 60,
    location: r.location || "",
    notes: r.notes || "",
    source: "ai",
  }));
  if (DEMO) {
    let nid = Math.max(0, ...DEMO_ITEMS.map((i) => i.id)) + 1;
    rows.forEach((r) => {
      DEMO_ITEMS.push({ booking_ref: "", confirm_required: false, is_confirmed: false, ...r, id: nid++ });
    });
    return;
  }
  await sb("itinerary_items", {
    method: "POST",
    headers: { Prefer: "return=minimal" },
    body: JSON.stringify(rows),
  });
}

const setConfirmed    = (id, v)         => patchItem(id, { is_confirmed: v });
const scheduleItem    = (id, day, time) => patchItem(id, { day_number: day, start_time: time });
const unscheduleItem  = (id)            => patchItem(id, { day_number: null, start_time: null });

// ── 時段重疊偵測（同一天內任兩項時間區間相交即標記）──
function itemInterval(it) {
  const s = timeToMin(it.start_time);
  if (s == null) return null;
  const d = Math.max(Number(it.duration_minutes) || 60, 15);
  return [s, s + d];
}

function computeConflicts(items) {
  const ids = new Set();
  const timed = items.filter((it) => itemInterval(it));
  for (let i = 0; i < timed.length; i++) {
    for (let j = i + 1; j < timed.length; j++) {
      const a = itemInterval(timed[i]), b = itemInterval(timed[j]);
      if (a[0] < b[1] && b[0] < a[1]) { ids.add(timed[i].id); ids.add(timed[j].id); }
    }
  }
  return ids;
}

// ── 時間軸排版：重疊項目分欄並排（行事曆式貪婪演算法）──
// 回傳每項 {it, start, end, col, cols}；同一群互相重疊的項目共享欄數 cols。
function layoutDay(items) {
  const evs = items
    .filter((it) => timeToMin(it.start_time) != null)
    .map((it) => {
      const s = timeToMin(it.start_time);
      const d = Math.max(Number(it.duration_minutes) || 60, 15);
      return { it, start: s, end: s + d, col: 0, cols: 1 };
    })
    .sort((a, b) => a.start - b.start || a.end - b.end);

  const result = [];
  let cluster = [];     // 目前這群互相重疊的事件
  let columns = [];     // 每欄目前的結束時間
  let clusterEnd = -1;  // 這群最晚的結束時間

  const flush = () => {
    const n = columns.length || 1;
    cluster.forEach((e) => { e.cols = n; result.push(e); });
    cluster = [];
    columns = [];
    clusterEnd = -1;
  };

  for (const e of evs) {
    // 與目前這群完全不重疊 → 先把上一群定案
    if (cluster.length && e.start >= clusterEnd) flush();
    // 找一個已結束的欄位放進去，否則新增一欄
    let placed = false;
    for (let c = 0; c < columns.length; c++) {
      if (columns[c] <= e.start) { columns[c] = e.end; e.col = c; placed = true; break; }
    }
    if (!placed) { e.col = columns.length; columns.push(e.end); }
    cluster.push(e);
    clusterEnd = Math.max(clusterEnd, e.end);
  }
  flush();
  return result;
}

// ── 渲染：共用片段 ──
function renderBanner(type, html) {
  return `<div class="banner ${type}">${html}</div>`;
}

function headerHtml(trip) {
  return `
    <div class="header">
      <div class="title">${escapeHtml(trip ? trip.name : "確認清單")}</div>
      <div class="sub">出發前確認清單</div>
    </div>
    ${DEMO ? renderBanner("warn", "🧪 範例模式：這是假資料，按鈕只在本機作用、不會連到 Supabase。") : ""}
  `;
}

function navHtml() {
  const tab = (id, label) =>
    `<button class="nav-tab ${VIEW === id ? "active" : ""}" data-view="${id}">${label}</button>`;
  return `<div class="nav">${tab("confirm", "✅ 確認清單")}${tab("itinerary", "🗓️ 行程表")}</div>`;
}

function toolbarHtml() {
  const updated = new Date().toLocaleTimeString("zh-Hant", { hour: "2-digit", minute: "2-digit" });
  return `
    <div class="toolbar">
      <button class="refresh-btn" id="refresh">↻ 重新整理</button>
      <span class="updated">更新於 ${updated}</span>
    </div>`;
}

// ── 確認清單視圖（含手機資訊架構：必須確認置頂、其餘收合）──
function scheduleControl(it) {
  if (it.day_number == null && TRIP_CTX.totalDays > 0) {
    let opts = "";
    for (let d = 1; d <= TRIP_CTX.totalDays; d++) {
      opts += `<option value="${d}">${TRIP_CTX.dayLabel(d)}</option>`;
    }
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
  if (it.day_number != null) {
    return `<button class="unsched-btn" data-id="${it.id}">↩ 退回候選</button>`;
  }
  return "";
}

function renderCard(it, kind) {
  // kind: "priority" | "done" | "flexible"
  const cat = CATEGORY_LABEL[it.category] || "📌 其他";
  const notes = it.notes ? `<div class="card-notes">${escapeHtml(it.notes)}</div>` : "";
  const booking = it.booking_ref
    ? `<div class="card-booking">📋 ${escapeHtml(it.booking_ref)}</div>` : "";
  const checked = it.is_confirmed ? "on" : "";
  const mark = it.is_confirmed ? "✓" : "";
  return `
    <div class="card ${kind}">
      <button class="check ${checked}" data-id="${it.id}" data-confirmed="${it.is_confirmed ? 1 : 0}"
              aria-label="切換已確認">${mark}</button>
      <div class="card-body">
        <div class="card-cat">${cat}　·　${escapeHtml(whereLabel(it))}</div>
        <div class="card-name">${escapeHtml(it.name)}</div>
        ${booking}${notes}
        <div class="card-sched">${scheduleControl(it)}</div>
      </div>
    </div>`;
}

function confirmViewHtml(items) {
  const must = items.filter((i) => i.confirm_required);
  const mustUn = must.filter((i) => !i.is_confirmed);
  const mustDone = must.filter((i) => i.is_confirmed);
  const flexible = items.filter((i) => !i.confirm_required);

  let html = "";

  // 必須確認 + 未確認（置頂、預設展開、數量摘要）
  const zero = mustUn.length === 0 ? "zero" : "";
  html += `<div class="section-title">⚠️ 必須確認
            <span class="count ${zero}">${mustUn.length}</span></div>`;
  if (mustUn.length === 0) {
    html += renderBanner("ok", "✅ 必訂項目都確認完成了，可以安心出發");
  } else {
    html += renderBanner("warn", `還有 ${mustUn.length} 個項目需要訂位 / 預約 / 確認`);
    html += mustUn.map((it) => renderCard(it, "priority")).join("");
  }

  // 必須確認 + 已確認（預設收合）
  if (mustDone.length > 0) {
    html += `<details class="done-group">
      <summary>✅ 已確認（${mustDone.length}）</summary>`;
    html += mustDone.map((it) => renderCard(it, "done")).join("");
    html += `</details>`;
  }

  // 可以彈性（預設收合，非緊急 → 不佔首屏）
  html += `<details class="flex-group">
    <summary>🟢 可以彈性（${flexible.length}）<span class="section-hint">　就算沒排定也不算遺漏</span></summary>`;
  html += flexible.length
    ? flexible.map((it) => renderCard(it, "flexible")).join("")
    : `<div class="empty">沒有彈性項目</div>`;
  html += `</details>`;

  return html;
}

// ── 行程表視圖 ──
function aiPanelHtml() {
  if (!AI_OPEN) {
    return `<button class="ai-toggle" id="ai-toggle">🤖 AI 匯入行程（貼文字）</button>`;
  }
  return `
    <div class="ai-panel">
      <div class="ai-title">🤖 貼上一段文字行程，AI 幫你拆解並排入</div>
      <textarea id="ai-text" class="ai-text" rows="6"
        placeholder="例：&#10;Day 1&#10;09:00 首里城&#10;12:00 國際通午餐&#10;15:00 入住飯店&#10;Day 2&#10;10:00 美麗海水族館"></textarea>
      <div class="ai-actions">
        <button class="ai-cancel" id="ai-cancel">取消</button>
        <button class="ai-submit" id="ai-submit">解析並排入</button>
      </div>
      <div class="ai-status" id="ai-status"></div>
    </div>`;
}

function itineraryViewHtml(trip, items) {
  const unplaced = items.filter((i) => i.day_number == null);
  let html = "";

  // AI 匯入
  html += aiPanelHtml();

  // 未排定提醒（AC-2）
  if (unplaced.length > 0) {
    html += renderBanner("warn",
      `還有 <b>${unplaced.length}</b> 項未排定（可到「確認清單」用 📅 排入行程，或用上方 AI 匯入）`);
  }

  // 清單 / 時間軸 切換
  html += `<div class="seg">
      <button class="seg-btn ${ITIN_MODE === "list" ? "active" : ""}" data-mode="list">📋 清單</button>
      <button class="seg-btn ${ITIN_MODE === "timeline" ? "active" : ""}" data-mode="timeline">🕐 時間軸</button>
    </div>`;

  html += ITIN_MODE === "list" ? dayListHtml(trip, items) : timelineHtml(trip, items);
  return html;
}

function itinListCard(it) {
  const cat = CATEGORY_LABEL[it.category] || "📌 其他";
  const time = it.start_time ? escapeHtml(it.start_time) : "未排時間";
  const loc = it.location ? ` · ${escapeHtml(it.location)}` : "";
  const notes = it.notes ? `<div class="ti-notes">${escapeHtml(it.notes)}</div>` : "";
  return `
    <div class="ti-card">
      <div class="ti-time ${it.start_time ? "" : "notime"}">${time}</div>
      <div class="ti-main">
        <div class="ti-name">${escapeHtml(it.name)}</div>
        <div class="ti-meta">${cat}${loc}</div>
        ${notes}
      </div>
    </div>`;
}

function dayListHtml(trip, items) {
  const today = todayDayNumber(trip);
  const placed = items.filter((i) => i.day_number != null);
  if (placed.length === 0) {
    return `<div class="empty">還沒有排定的行程。用上方「AI 匯入行程」，或到「確認清單」把候選項目排入某天。</div>`;
  }
  const byDay = {};
  placed.forEach((it) => { (byDay[it.day_number] = byDay[it.day_number] || []).push(it); });

  let html = "";
  Object.keys(byDay).map(Number).sort((a, b) => a - b).forEach((d) => {
    const arr = byDay[d].slice().sort((a, b) =>
      (timeToMin(a.start_time) ?? 1e9) - (timeToMin(b.start_time) ?? 1e9));
    const isToday = d === today;
    html += `<div class="day-head ${isToday ? "today" : ""}">
      ${escapeHtml(TRIP_CTX.dayLabel(d))}${isToday ? ' <span class="today-pill">今天</span>' : ""}</div>`;
    html += arr.map(itinListCard).join("");
  });
  return html;
}

function timelineHtml(trip, items) {
  const totalDays = TRIP_CTX.totalDays;
  const today = todayDayNumber(trip);

  // 預設聚焦：今天 → 第一個有排定的天 → Day 1
  if (TL_DAY == null || TL_DAY < 1 || TL_DAY > totalDays) {
    TL_DAY = today || firstPlacedDay(items) || 1;
  }

  // 天數切換 chips
  let chips = "";
  for (let d = 1; d <= totalDays; d++) {
    chips += `<button class="day-chip ${d === TL_DAY ? "active" : ""} ${d === today ? "is-today" : ""}"
      data-day="${d}">${d === today ? "⭐ " : ""}Day ${d}</button>`;
  }
  let html = `<div class="day-chips">${chips}</div>`;

  const dayItems = items.filter((i) => i.day_number === TL_DAY);
  const timed = dayItems.filter((i) => timeToMin(i.start_time) != null);
  const untimed = dayItems.filter((i) => timeToMin(i.start_time) == null);

  if (untimed.length) {
    html += `<div class="tl-untimed"><span>未排時間：</span>${
      untimed.map((it) => `<span class="tl-chip">${escapeHtml(it.name)}</span>`).join("")
    }</div>`;
  }

  if (timed.length === 0) {
    html += `<div class="empty">這天還沒有已排時間的項目。</div>`;
  } else {
    html += timelineTrackHtml(timed);
  }
  return html;
}

function timelineTrackHtml(items) {
  const conflicts = computeConflicts(items);
  const laid = layoutDay(items);
  const H = (TL_END - TL_START) * 60 * PXPM;

  // 小時格線 + 標籤
  let labels = "", lines = "";
  for (let h = TL_START; h <= TL_END; h++) {
    const y = ((h - TL_START) * 60) * PXPM;
    labels += `<div class="tl-hour" style="top:${y}px">${String(h).padStart(2, "0")}:00</div>`;
    lines += `<div class="tl-line" style="top:${y}px"></div>`;
  }

  // 事件方塊
  let ev = "";
  laid.forEach((e) => {
    const it = e.it;
    const top = (e.start - TL_START * 60) * PXPM;
    const h = Math.max((e.end - e.start) * PXPM, 30);
    const leftPct = (e.col / e.cols * 100).toFixed(4);
    const widthCalc = `calc(${(100 / e.cols).toFixed(4)}% - 6px)`;
    const cat = CATEGORY_LABEL[it.category] || "📌 其他";
    const conf = conflicts.has(it.id) ? "conflict" : "";
    ev += `
      <div class="tl-item ${conf}" data-id="${it.id}" data-dur="${Number(it.duration_minutes) || 60}"
           style="top:${top}px;height:${h}px;left:${leftPct}%;width:${widthCalc}">
        <div class="tl-item-time">${escapeHtml(it.start_time)}</div>
        <div class="tl-item-name">${escapeHtml(it.name)}</div>
        <div class="tl-item-cat">${cat}</div>
        ${conf ? '<div class="tl-flag">⚠️ 時段重疊</div>' : ""}
      </div>`;
  });

  const warnBanner = conflicts.size
    ? renderBanner("warn", "⚠️ 這天有時段重疊的項目（已並排顯示，拖曳可調整）")
    : "";

  return `${warnBanner}
    <div class="tl-hint">按住卡片上下拖曳即可改時間（放開自動儲存）</div>
    <div class="tl" style="height:${H}px">
      ${labels}
      <div class="tl-track" style="height:${H}px">${lines}${ev}</div>
    </div>`;
}

// ── 主渲染 ──
function render(trip, items) {
  TRIP_CTX = buildTripCtx(trip);
  LAST = { trip, items };

  let html = headerHtml(trip) + navHtml() + toolbarHtml();
  html += VIEW === "confirm" ? confirmViewHtml(items) : itineraryViewHtml(trip, items);

  app.innerHTML = html;
  wireEvents();
}

function rerender() {
  render(LAST.trip, LAST.items);
}

// ── 事件綁定 ──
function wireEvents() {
  const byId = (id) => document.getElementById(id);

  const refresh = byId("refresh");
  if (refresh) refresh.addEventListener("click", () => load());

  // 頂層視圖切換
  document.querySelectorAll(".nav-tab").forEach((b) =>
    b.addEventListener("click", () => { VIEW = b.dataset.view; rerender(); }));

  // 行程表清單 / 時間軸切換
  document.querySelectorAll(".seg-btn").forEach((b) =>
    b.addEventListener("click", () => { ITIN_MODE = b.dataset.mode; rerender(); }));

  // 時間軸天數切換
  document.querySelectorAll(".day-chip").forEach((b) =>
    b.addEventListener("click", () => { TL_DAY = Number(b.dataset.day); rerender(); }));

  // 切換「已確認」
  document.querySelectorAll(".check").forEach((btn) =>
    btn.addEventListener("click", () => guard(btn,
      () => setConfirmed(btn.dataset.id, btn.dataset.confirmed !== "1"))));

  // 排入某天某時段
  document.querySelectorAll(".sched-btn").forEach((btn) =>
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const day = Number(document.getElementById(`sched-day-${id}`).value);
      const time = document.getElementById(`sched-time-${id}`).value;
      if (!/^\d{2}:\d{2}$/.test(time)) { alert("請輸入正確時間（HH:MM）"); return; }
      guard(btn, () => scheduleItem(id, day, time));
    }));

  // 退回候選
  document.querySelectorAll(".unsched-btn").forEach((btn) =>
    btn.addEventListener("click", () => guard(btn,
      () => unscheduleItem(btn.dataset.id))));

  // AI 匯入
  const aiToggle = byId("ai-toggle");
  if (aiToggle) aiToggle.addEventListener("click", () => { AI_OPEN = true; rerender(); });
  const aiCancel = byId("ai-cancel");
  if (aiCancel) aiCancel.addEventListener("click", () => { AI_OPEN = false; rerender(); });
  const aiSubmit = byId("ai-submit");
  if (aiSubmit) aiSubmit.addEventListener("click", () => runAiImport());

  // 時間軸拖曳
  wireTimelineDrag();
}

// 共用：按下後鎖住按鈕、執行寫入、重新載入；失敗則解鎖並顯示錯誤
async function guard(btn, action) {
  btn.disabled = true;
  try {
    await action();
    await load();
  } catch (e) {
    btn.disabled = false;
    showError(e);
  }
}

// ── 時間軸拖曳調整時間（AC-4 / AC-5）──
function wireTimelineDrag() {
  const H = (TL_END - TL_START) * 60 * PXPM;
  document.querySelectorAll(".tl-item").forEach((el) => {
    let dragging = false, startY = 0, origTop = 0, moved = false;

    const onDown = (e) => {
      dragging = true; moved = false;
      startY = e.clientY;
      origTop = parseFloat(el.style.top) || 0;
      el.classList.add("dragging");
      if (el.setPointerCapture) el.setPointerCapture(e.pointerId);
      e.preventDefault();
    };

    const onMove = (e) => {
      if (!dragging) return;
      const dy = e.clientY - startY;
      if (Math.abs(dy) > 3) moved = true;
      const itemH = parseFloat(el.style.height) || 30;
      let nt = Math.max(0, Math.min(H - itemH, origTop + dy));
      el.style.top = nt + "px";
      const min = TL_START * 60 + nt / PXPM;
      const lbl = el.querySelector(".tl-item-time");
      if (lbl) lbl.textContent = minToTime(min);
      e.preventDefault();
    };

    const onUp = async () => {
      if (!dragging) return;
      dragging = false;
      el.classList.remove("dragging");
      if (!moved) return; // 只是點一下，不動
      const nt = parseFloat(el.style.top) || 0;
      const newTime = minToTime(TL_START * 60 + nt / PXPM);
      try {
        await patchItem(el.dataset.id, { start_time: newTime });
        await load();
      } catch (err) {
        showError(err);
      }
    };

    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);
  });
}

// ── AI 匯入：解析文字 → INSERT ──
function buildParsePrompt(text, totalDays) {
  const dayHint = totalDays ? `1~${totalDays}` : "N";
  return `你是行程解析助手。使用者會貼上一段旅遊行程文字，請把它拆解成結構化的行程項目。
這趟旅程共 ${totalDays || "未知"} 天。
請只回傳一個 JSON 陣列，每個元素格式如下：
{"day":1,"name":"名稱","category":"restaurant|hotel|attraction|shopping|transport|other","start_time":"HH:MM","duration_minutes":90,"location":"地點","notes":"備註"}
規則：
1. day 為第幾天的整數（${dayHint}）。若完全無法判斷是第幾天，day 設為 null。
2. start_time 為 24 小時制 HH:MM。若無法判斷時間，設為 null。
3. category 從上列六選一，依語意判斷（餐廳/住宿/景點/購物/交通/其他）。
4. duration_minutes 估一個合理值（景點 90、餐廳 60、其他 60）。
5. 只輸出 JSON 陣列本身，不要 markdown、不要任何說明文字。
行程文字：
"""${text}"""`;
}

function parseJsonArray(raw) {
  let s = String(raw || "").trim();
  if (s.startsWith("```")) {
    s = s.replace(/^```[a-zA-Z]*\s*/, "").replace(/```\s*$/, "").trim();
  }
  const i = s.indexOf("["), j = s.lastIndexOf("]");
  if (i >= 0 && j > i) s = s.slice(i, j + 1);
  const arr = JSON.parse(s);
  if (!Array.isArray(arr)) throw new Error("AI 回傳格式不正確");
  return arr;
}

async function geminiParseItinerary(text) {
  const cfg = window.SCOUT_CONFIG || {};
  if (!cfg.GEMINI_API_KEY || cfg.GEMINI_API_KEY.includes("your-")) {
    throw new Error("尚未設定 Gemini 金鑰，請在 config.js 補上 GEMINI_API_KEY。");
  }
  const model = cfg.GEMINI_MODEL || "gemini-3-flash-preview";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(cfg.GEMINI_API_KEY)}`;
  const prompt = buildParsePrompt(text, TRIP_CTX.totalDays);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.4, maxOutputTokens: 2048 },
    }),
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  const data = await res.json();
  const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
  return parseJsonArray(raw);
}

// 範例模式：本地啟發式解析（不連網，供開發 / 預覽）
function guessCat(name) {
  if (/餐|食堂|丼|拉麵|燒肉|咖啡|café|cafe|壽司|午餐|晚餐|早餐/.test(name)) return "restaurant";
  if (/飯店|旅館|hotel|民宿|入住|溫泉旅/.test(name)) return "hotel";
  if (/購物|outlet|商店街|免稅|逛街|市場/.test(name)) return "shopping";
  if (/機場|港|渡輪|巴士|地鐵|電車|租車|搭車|車站/.test(name)) return "transport";
  if (/城|館|寺|公園|海灘|展望|神社|大橋|水族|景點|公園|花園/.test(name)) return "attraction";
  return "other";
}

function localParseItinerary(text) {
  const lines = text.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  let day = null;
  const out = [];
  for (const ln of lines) {
    const dm = /day\s*(\d+)/i.exec(ln) || /第\s*(\d+)\s*天/.exec(ln);
    // 純粹的「Day N」分隔行（除了標記外幾乎沒別的字）→ 只切換天數
    if (dm) {
      const rest = ln.replace(dm[0], "").replace(/[：:、,，\-\s]/g, "");
      day = +dm[1];
      if (rest.length < 2 && !/\d{1,2}:\d{2}/.test(ln)) continue;
    }
    const tm = /(\d{1,2}):(\d{2})/.exec(ln);
    const time = tm ? `${String(+tm[1]).padStart(2, "0")}:${tm[2]}` : null;
    let name = ln
      .replace(/^day\s*\d+/i, "")
      .replace(/第\s*\d+\s*天/, "")
      .replace(/(\d{1,2}):(\d{2})/, "")
      .replace(/^[\s\-,，、:：]+/, "")
      .trim();
    if (!name) continue;
    out.push({
      day: day === null ? null : day,
      name,
      category: guessCat(name),
      start_time: time,
      duration_minutes: 90,
      location: "",
      notes: "",
    });
  }
  return out;
}

async function runAiImport() {
  const ta = document.getElementById("ai-text");
  const status = document.getElementById("ai-status");
  const submit = document.getElementById("ai-submit");
  const text = (ta && ta.value || "").trim();
  if (!text) { if (status) status.textContent = "請先貼上行程文字。"; return; }

  if (submit) submit.disabled = true;
  if (status) status.textContent = "AI 解析中…";
  try {
    const parsed = DEMO ? localParseItinerary(text) : await geminiParseItinerary(text);
    if (!parsed.length) {
      if (status) status.textContent = "沒有解析到任何項目，換個格式再試試。";
      if (submit) submit.disabled = false;
      return;
    }
    await insertItems(getTripId(), parsed);
    AI_OPEN = false;
    await load();
  } catch (err) {
    if (status) status.textContent = "匯入失敗：" + err.message;
    if (submit) submit.disabled = false;
  }
}

function showError(err) {
  app.innerHTML = renderBanner("error",
    `操作失敗：<br><code>${escapeHtml(err.message)}</code><br><br>` +
    `請確認 config.js 的 SUPABASE_URL / anon key 正確、` +
    `且 itinerary_items 表已對 anon 開放存取（見 supabase_schema.sql 的 RLS 區段）。`);
}

// ── 進入點 ──
async function load() {
  if (DEMO) {
    render(DEMO_TRIP, DEMO_ITEMS);
    return;
  }
  const cfgErr = configError();
  if (cfgErr) {
    app.innerHTML = renderBanner("error", escapeHtml(cfgErr));
    return;
  }
  const tripId = getTripId();
  if (!tripId) {
    app.innerHTML = renderBanner("error",
      "網址缺少 ?trip=&lt;旅程編號&gt;。請使用分享連結開啟，例如 index.html?trip=1");
    return;
  }
  app.innerHTML = `<div class="status">載入中…</div>`;
  try {
    const [trip, items] = await Promise.all([loadTrip(tripId), loadItems(tripId)]);
    render(trip, items);
  } catch (e) {
    showError(e);
  }
}

load();
