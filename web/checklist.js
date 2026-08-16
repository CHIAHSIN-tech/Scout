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
let curTrips = [];          // 所有旅程，供下拉選單用（因 Streamlit 退役而加）
let curItems = [];
let currentView = "checklist";   // checklist | dayplan | timeline
let TRIP_CTX = { totalDays: 0, dayLabel: (d) => `Day ${d}` };

// ── 旅程身分 ──
// 原本只認網址的 ?trip=<id>，而 id 只能從 Streamlit 建立旅程後去 Supabase 撈。
// Streamlit 退役後那條路沒了（ADR-010），所以改成：網址優先 → 退回 localStorage。
// 網址仍然優先，既有的分享連結才不會失效（AC-11）。
const TRIP_KEY = "scout_trip_id";

function getTripId() {
  const fromUrl = new URLSearchParams(location.search).get("trip");
  if (fromUrl) { setTripId(fromUrl); return fromUrl; }
  let saved = null;
  try { saved = localStorage.getItem(TRIP_KEY); } catch (e) { return null; }
  // 從 localStorage 還原時也要把 ?trip= 寫回網址，否則直接複製網址列會少掉旅程，
  // 對方打開只會看到選擇畫面（或他自己上次看的那趟）。
  if (saved) setTripId(saved);
  return saved;
}

function setTripId(id) {
  try { localStorage.setItem(TRIP_KEY, String(id)); } catch (e) { /* 無痕模式會擋 */ }
  // 同步網址，讓當下這頁隨時可以直接複製成分享連結
  const u = new URL(location.href);
  u.searchParams.set("trip", String(id));
  history.replaceState(null, "", u);
}

function clearTripId() {
  try { localStorage.removeItem(TRIP_KEY); } catch (e) { /* 同上 */ }
  const u = new URL(location.href);
  u.searchParams.delete("trip");
  history.replaceState(null, "", u);
}

// ── 小工具 ──

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

// 所有旅程（下拉選單用）。最近出發的排前面。
async function loadTrips() {
  const res = await sb(`trips?select=id,name,start_date,end_date&order=start_date.desc`);
  return res.json();
}

// 建立旅程。username 是 NOT NULL，沿用 buylist 的「我是誰」設定；沒設就記 unknown。
async function createTrip(fields) {
  let who = "";
  try { who = localStorage.getItem("buylist_me") || ""; } catch (e) { /* 無痕模式 */ }
  const res = await sb(`trips`, {
    method: "POST",
    headers: { Prefer: "return=representation" },
    body: JSON.stringify({ username: who || "unknown", notes: "", ...fields }),
  });
  const rows = await res.json();
  return rows[0];
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

// 刪除單一行程項目。破壞性且不可復原，呼叫端必須先做二次確認。
async function deleteItem(itemId) {
  await sb(`itinerary_items?id=eq.${encodeURIComponent(itemId)}`, { method: "DELETE" });
}

// 刪除旅程。先刪自己的項目再刪旅程本身——
// 珈欣的 Supabase 上外鍵有沒有設 CASCADE 無法從這裡確認（spec §10 R1），
// 先刪子表在「有 CASCADE」與「沒有」兩種情況下都正確，不會留孤兒或撞外鍵錯誤。
async function deleteTrip(tripId) {
  await sb(`itinerary_items?trip_id=eq.${encodeURIComponent(tripId)}`, { method: "DELETE" });
  await sb(`trips?id=eq.${encodeURIComponent(tripId)}`, { method: "DELETE" });
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

// ── 旅程選擇列（切換旅程 ＋ 建立旅程）──
// Streamlit 退役後，這裡是唯一能開新旅程的地方（spec §6.2）。
function renderTripBar() {
  const opts = curTrips.map((t) =>
    `<option value="${t.id}"${curTrip && String(t.id) === String(curTrip.id) ? " selected" : ""}>${escapeHtml(t.name)}</option>`
  ).join("");
  return `
    <div class="tripbar">
      <select id="trip-sel" aria-label="選擇旅程">
        ${curTrip ? "" : `<option value="">— 選一趟旅程 —</option>`}
        ${opts}
      </select>
      <details class="tripnew">
        <summary>＋ 新旅程</summary>
        <div class="mini-form">
          <input type="text" id="trip-name" placeholder="旅程名稱（必填）" autocomplete="off">
          <input type="date" id="trip-start" aria-label="開始日期">
          <input type="date" id="trip-end" aria-label="結束日期">
          <button type="button" class="sched-btn" id="trip-create">建立</button>
        </div>
        <div class="mini-msg" id="trip-msg" aria-live="polite"></div>
      </details>
      ${curTrip ? `<button type="button" class="trip-del" id="trip-del">🗑️ 刪除旅程</button>` : ""}
      <div class="mini-msg" id="tripbar-msg" aria-live="polite"></div>
    </div>`;
}

// ── 手動新增行程項目 ──
// 原本只有 AI 匯入能新增（addItem 的註解就是這樣寫的），Streamlit 退役後必須補手動路徑。
function renderAddItem() {
  if (!curTrip) return "";
  let dayOpts = `<option value="">候選（先不排日期）</option>`;
  for (let d = 1; d <= TRIP_CTX.totalDays; d++) dayOpts += `<option value="${d}">${TRIP_CTX.dayLabel(d)}</option>`;
  const catOpts = Object.keys(CATEGORY_LABEL)
    .map((k) => `<option value="${k}"${k === "attraction" ? " selected" : ""}>${CATEGORY_LABEL[k]}</option>`).join("");
  return `
    <details class="additem">
      <summary>＋ 新增項目</summary>
      <div class="mini-form">
        <input type="text" id="add-name" placeholder="景點 / 餐廳 / 活動名稱（必填）" autocomplete="off">
        <select id="add-cat" aria-label="分類">${catOpts}</select>
        <select id="add-day" aria-label="第幾天">${dayOpts}</select>
        <input type="time" id="add-time" aria-label="開始時間">
        <label class="mini-check"><input type="checkbox" id="add-req">必須確認</label>
        <button type="button" class="sched-btn" id="add-go">加入</button>
      </div>
      <div class="mini-msg" id="add-msg" aria-live="polite"></div>
    </details>`;
}

// ── 匯出到 Google 日曆 / Google Maps ──
// 格式組裝全部在 web/export-formats.js（同一份實作，驗證腳本共用），這裡只管 UI 與下載。
// 不呼叫任何 Google API、不做 OAuth：.ics 與 CSV 是本地產檔，兩種連結是純字串組裝。
function renderExportBar() {
  if (!curTrip) return "";
  return `
    <div class="exportbar">
      <button type="button" class="exp-btn" id="exp-ics">⬇ 匯出 .ics</button>
      <button type="button" class="exp-btn" id="exp-csv">⬇ 匯出地圖 CSV</button>
      <div class="exp-hint">
        .ics 只能用<b>電腦版瀏覽器</b>匯入 Google 日曆，手機匯不進去；
        手機請用每個項目的「📅 加到日曆」。CSV 是給 Google My Maps 手動上傳用的。
      </div>
      <div class="mini-msg" id="exp-msg" aria-live="polite"></div>
    </div>`;
}

// 檔名用旅程名稱，把檔案系統會有意見的字元換掉
function safeFileName(s) {
  return String(s || "行程").replace(/[\\/:*?"<>|]/g, "-").trim() || "行程";
}

function downloadText(filename, text, mime) {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function wireExportBar() {
  const ics = document.getElementById("exp-ics");
  if (ics) ics.addEventListener("click", () => {
    try {
      const n = curItems.filter((i) => i.day_number != null).length;
      if (n === 0) return miniMsg("exp-msg", "還沒有排入行程的項目，.ics 會是空的。", "err");
      downloadText(`${safeFileName(curTrip.name)}.ics`,
        window.ScoutExport.buildIcs(curTrip, curItems), "text/calendar;charset=utf-8");
      miniMsg("exp-msg", `已產生 ${n} 個日曆事件的 .ics。`, "");
    } catch (e) {
      miniMsg("exp-msg", "匯出失敗：" + (e && e.message ? e.message : String(e)), "err");
    }
  });

  const csv = document.getElementById("exp-csv");
  if (csv) csv.addEventListener("click", () => {
    try {
      const n = curItems.filter((i) => String(i.location || "").trim()).length;
      if (n === 0) return miniMsg("exp-msg", "沒有任何項目填了「地點」，地圖 CSV 會是空的。", "err");
      downloadText(`${safeFileName(curTrip.name)}-地點.csv`,
        window.ScoutExport.buildMapsCsv(curItems), "text/csv;charset=utf-8");
      miniMsg("exp-msg", `已匯出 ${n} 個地點的 CSV。`, "");
    } catch (e) {
      miniMsg("exp-msg", "匯出失敗：" + (e && e.message ? e.message : String(e)), "err");
    }
  });
}

function renderApp() {
  TRIP_CTX = buildTripCtx(curTrip);
  const updated = new Date().toLocaleTimeString("zh-Hant", { hour: "2-digit", minute: "2-digit" });

  // 還沒選旅程：只給選擇列，不渲染 tab 與清單（沒有 trip_id 什麼都查不了）
  if (!curTrip) {
    app.innerHTML = `
      <div class="header">
        <div class="title">確認清單</div>
        <div class="sub">出發前確認清單</div>
      </div>
      ${renderTripBar()}
      ${renderBanner("warn", curTrips.length
        ? "上面選一趟旅程開始，或按「＋ 新旅程」建立一趟。"
        : "還沒有任何旅程。按「＋ 新旅程」建立第一趟。")}
    `;
    wireShell();
    return;
  }

  app.innerHTML = `
    <div class="header">
      <div class="title">${escapeHtml(curTrip.name)}</div>
      <div class="sub">出發前確認清單</div>
    </div>
    ${renderTripBar()}
    <div class="toolbar">
      <button class="refresh-btn" id="refresh">↻ 重新整理</button>
      <button class="ai-import-btn" id="ai-import-open">✨ AI 匯入行程</button>
      <span class="updated">更新於 ${updated}</span>
    </div>
    ${renderExportBar()}
    ${renderAddItem()}
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
  wireTripBar();
  wireAddItem();
  wireExportBar();
}

// 小表單的訊息列：失敗一律紅字，不靜默失敗（比照 buylist 的 setStatus 慣例）
function miniMsg(id, text, cls) {
  const el = document.getElementById(id);
  if (el) { el.textContent = text; el.className = "mini-msg" + (cls ? " " + cls : ""); }
}

function wireTripBar() {
  const sel = document.getElementById("trip-sel");
  if (sel) sel.addEventListener("change", () => {
    if (!sel.value) return;
    setTripId(sel.value);
    currentView = "checklist";   // 換旅程回到預設檢視，避免停在空的時間軸
    load();
  });

  // 刪除旅程：確認訊息必須明講會連同行程項目一起消失（spec AC-7）
  const del = document.getElementById("trip-del");
  if (del) del.addEventListener("click", async () => {
    if (!curTrip) return;
    const n = curItems.length;
    if (!confirm(`確定要刪除旅程「${curTrip.name}」嗎？\n` +
                 `它底下的 ${n} 個行程項目也會一併刪除，無法復原。`)) return;
    del.disabled = true;
    try {
      await deleteTrip(curTrip.id);
      clearTripId();
      curTrip = null; curItems = [];
      await load();                 // 回到「未選旅程」畫面
    } catch (e) {
      del.disabled = false;
      // 用 tripbar 上的訊息列，不用 trip-msg——後者在收合的「＋ 新旅程」裡，錯誤會看不到
      miniMsg("tripbar-msg", "刪除旅程失敗：" + (e && e.message ? e.message : String(e)), "err");
    }
  });

  const btn = document.getElementById("trip-create");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const name = (document.getElementById("trip-name").value || "").trim();
    const start = document.getElementById("trip-start").value;
    const end = document.getElementById("trip-end").value;
    if (!name)          return miniMsg("trip-msg", "請填旅程名稱。", "err");
    if (!start || !end) return miniMsg("trip-msg", "請填開始與結束日期（行程表與時間軸要靠它算天數）。", "err");
    if (end < start)    return miniMsg("trip-msg", "結束日期不能早於開始日期。", "err");

    btn.disabled = true;
    miniMsg("trip-msg", "建立中…", "busy");
    try {
      const row = await createTrip({ name, start_date: start, end_date: end });
      if (!row || !row.id) throw new Error("Supabase 沒有回傳新旅程的 id");
      setTripId(row.id);
      currentView = "checklist";
      await load();
    } catch (e) {
      btn.disabled = false;
      miniMsg("trip-msg", "建立失敗：" + (e && e.message ? e.message : String(e)), "err");
    }
  });
}

function wireAddItem() {
  const btn = document.getElementById("add-go");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const name = (document.getElementById("add-name").value || "").trim();
    if (!name) return miniMsg("add-msg", "請填名稱。", "err");
    const day = document.getElementById("add-day").value;
    const time = document.getElementById("add-time").value;

    btn.disabled = true;
    miniMsg("add-msg", "加入中…", "busy");
    try {
      await addItem({
        name,
        category: document.getElementById("add-cat").value,
        // 沒選天數 = 候選中（day_number 為 NULL），時間也一併留空才不會自相矛盾
        day_number: day ? Number(day) : null,
        start_time: day && time ? time : null,
        confirm_required: document.getElementById("add-req").checked,
        is_confirmed: false,
        source: "manual",
      });
      await load();
    } catch (e) {
      btn.disabled = false;
      miniMsg("add-msg", "加入失敗：" + (e && e.message ? e.message : String(e)), "err");
    }
  });
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

// 每張卡片上的兩個連結。這兩個是手機上真正會用的路徑（.ics 手機匯不進去），
// 所以規格把它們列為 never-cut。沒有日期／沒有地點的項目就不長出對應的連結。
function renderItemLinks(it) {
  const X = window.ScoutExport;
  if (!X) return "";
  const cal = X.gcalLink(curTrip, it);
  const map = X.mapsLink(it);
  if (!cal && !map) return "";
  const a = (href, text) =>
    `<a class="item-link" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${text}</a>`;
  return `<div class="card-links">${cal ? a(cal, "📅 加到日曆") : ""}${map ? a(map, "🗺️ 開地圖") : ""}</div>`;
}

// ── 編輯 / 刪除（Streamlit `_render_items()` 的 ✏️ 展開表單）──
// 收在 <details> 裡：卡片預設維持原本的乾淨樣子，要改才展開。
// 「第幾天」放在這裡就順便補回了跨天移動（Streamlit 的 new_day_label）。
function renderEditForm(it) {
  const attr = (v) => escapeHtml(v ?? "");
  let dayOpts = `<option value=""${it.day_number == null ? " selected" : ""}>候選（未排定）</option>`;
  // 沒填旅程日期時 totalDays 是 0，至少要讓目前這天留在選單裡，否則一存檔就被打回候選
  const maxDay = Math.max(TRIP_CTX.totalDays, it.day_number || 0);
  for (let d = 1; d <= maxDay; d++) {
    dayOpts += `<option value="${d}"${it.day_number === d ? " selected" : ""}>${TRIP_CTX.dayLabel(d)}</option>`;
  }
  const catOpts = Object.keys(CATEGORY_LABEL)
    .map((k) => `<option value="${k}"${k === it.category ? " selected" : ""}>${CATEGORY_LABEL[k]}</option>`).join("");
  return `
    <details class="edititem">
      <summary>✏️ 編輯</summary>
      <div class="mini-form">
        <input type="text" id="ed-name-${it.id}" value="${attr(it.name)}" placeholder="名稱（必填）" autocomplete="off">
        <select id="ed-cat-${it.id}" aria-label="分類">${catOpts}</select>
        <select id="ed-day-${it.id}" aria-label="第幾天">${dayOpts}</select>
        <input type="time" id="ed-time-${it.id}" value="${attr(it.start_time)}" aria-label="開始時間">
        <input type="number" id="ed-dur-${it.id}" value="${attr(it.duration_minutes)}" min="5" step="5" placeholder="停留分鐘" aria-label="停留分鐘">
        <input type="text" id="ed-loc-${it.id}" value="${attr(it.location)}" placeholder="地點 / 店名" autocomplete="off">
        <input type="text" id="ed-addr-${it.id}" value="${attr(it.address)}" placeholder="地址" autocomplete="off">
        <input type="text" id="ed-book-${it.id}" value="${attr(it.booking_ref)}" placeholder="預約編號" autocomplete="off">
        <textarea id="ed-notes-${it.id}" class="ed-notes" rows="2" placeholder="備註">${attr(it.notes)}</textarea>
      </div>
      <div class="ed-actions">
        <button type="button" class="ed-save" data-id="${it.id}">儲存</button>
        <button type="button" class="ed-del" data-id="${it.id}" data-name="${attr(it.name)}">🗑️ 刪除</button>
      </div>
      <div class="mini-msg" id="ed-msg-${it.id}" aria-live="polite"></div>
    </details>`;
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
        ${renderItemLinks(it)}
        <div class="card-sched">${scheduleControl(it)}</div>
        ${renderEditForm(it)}
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
  // 限定在 #view 內：外殼的「建立旅程」「加入項目」也用 .sched-btn 這個樣式 class，
  // 不限定的話它們會被綁上這裡的排入邏輯，一按就找不到 sched-day-undefined 而丟錯。
  document.querySelectorAll("#view .sched-btn").forEach((btn) => {
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
  document.querySelectorAll(".ed-save").forEach((btn) => {
    btn.addEventListener("click", () => saveEdit(btn, btn.dataset.id));
  });
  document.querySelectorAll(".ed-del").forEach((btn) => {
    btn.addEventListener("click", () => removeItem(btn, btn.dataset.id, btn.dataset.name));
  });
}

// 儲存編輯。一次 PATCH 全部欄位（含 day_number，所以跨天移動也走這條）。
async function saveEdit(btn, id) {
  const el = (f) => document.getElementById(`ed-${f}-${id}`);
  const val = (f) => (el(f).value || "").trim();
  const name = val("name");
  if (!name) return miniMsg(`ed-msg-${id}`, "請填名稱。", "err");

  const day = el("day").value;
  const time = el("time").value;
  const dur = parseInt(el("dur").value, 10);
  // 空字串一律寫回 null，而不是留下空字串——否則欄位「清空」後查詢與顯示會不一致
  const fields = {
    name,
    category: el("cat").value,
    day_number: day ? Number(day) : null,
    // 退回候選就不該還留著時間（與 unscheduleItem 的規則一致）
    start_time: day && time ? time : null,
    duration_minutes: Number.isFinite(dur) && dur > 0 ? dur : null,
    location: val("loc") || null,
    address: val("addr") || null,
    booking_ref: val("book") || null,
    notes: val("notes") || null,
  };

  btn.disabled = true;
  miniMsg(`ed-msg-${id}`, "儲存中…", "busy");
  try {
    await patchItem(id, fields);
    await load();
  } catch (e) {
    btn.disabled = false;
    miniMsg(`ed-msg-${id}`, "儲存失敗：" + (e && e.message ? e.message : String(e)), "err");
  }
}

// 刪除項目。二次確認是唯一的保護（spec §10 R2：不做軟刪除／垃圾桶）。
async function removeItem(btn, id, name) {
  if (!confirm(`確定要刪除「${name}」嗎？\n刪除後無法復原。`)) return;
  btn.disabled = true;
  miniMsg(`ed-msg-${id}`, "刪除中…", "busy");
  try {
    await deleteItem(id);
    await load();
  } catch (e) {
    btn.disabled = false;
    miniMsg(`ed-msg-${id}`, "刪除失敗：" + (e && e.message ? e.message : String(e)), "err");
  }
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
  app.innerHTML = `<div class="status">載入中…</div>`;
  try {
    curTrips = await loadTrips();
    const tripId = getTripId();
    // 存的 id 可能指向已被刪掉的旅程，所以要對照清單確認它還在
    const exists = tripId && curTrips.some((t) => String(t.id) === String(tripId));
    if (!exists) {
      if (tripId) clearTripId();          // 髒資料，清掉免得每次都撞
      curTrip = null; curItems = [];
      renderApp();                        // 渲染旅程選擇畫面，不是錯誤畫面
      return;
    }
    const [trip, itemsData] = await Promise.all([loadTrip(tripId), loadItems(tripId)]);
    curTrip = trip; curItems = itemsData;
    renderApp();
  } catch (e) { showError(e); }
}

wireAiImportModalOnce();  // modal 是靜態 DOM，只綁一次
load();

})();
