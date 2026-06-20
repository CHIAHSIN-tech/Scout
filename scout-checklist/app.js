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

// ── 範例模式 ──
// 加 ?demo=1 即可在「沒有 Supabase」的情況下預覽整個畫面，按鈕也能動（純記憶體，不連網）。
// 用途：讓你先看到長相與互動，確認 UI 沒問題，再去接真正的 Supabase。
const DEMO = new URLSearchParams(location.search).get("demo") === "1";
const DEMO_TRIP = {
  id: 0, name: "（範例）沖繩 5 天",
  start_date: "2026-07-01", end_date: "2026-07-05",
};
let DEMO_ITEMS = [
  { id: 1, name: "國際通燒肉（要訂位）", category: "restaurant", day_number: null, start_time: null, duration_minutes: 90, notes: "人氣店，建議提前訂位", booking_ref: "", confirm_required: true,  is_confirmed: false },
  { id: 5, name: "山原溫泉（需預約）",   category: "other",      day_number: null, start_time: null, duration_minutes: 60, notes: "",               booking_ref: "", confirm_required: true,  is_confirmed: false },
  { id: 2, name: "那霸麗思飯店",         category: "hotel",      day_number: 1, start_time: "15:00", duration_minutes: 30, notes: "",            booking_ref: "CONF-88123", confirm_required: true, is_confirmed: true },
  { id: 3, name: "美麗海水族館",         category: "attraction", day_number: 2, start_time: "10:00", duration_minutes: 120, notes: "",            booking_ref: "", confirm_required: false, is_confirmed: false },
  { id: 4, name: "古宇利大橋兜風",       category: "transport",  day_number: null, start_time: null, duration_minutes: 60, notes: "租車順路",     booking_ref: "", confirm_required: false, is_confirmed: false },
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

const setConfirmed    = (id, v)        => patchItem(id, { is_confirmed: v });
const scheduleItem    = (id, day, time) => patchItem(id, { day_number: day, start_time: time });
const unscheduleItem  = (id)           => patchItem(id, { day_number: null, start_time: null });

// ── 渲染 ──
function renderBanner(type, html) {
  return `<div class="banner ${type}">${html}</div>`;
}

function scheduleControl(it) {
  // 候選中 → 顯示「排入行程」；已排定 → 顯示「退回候選」
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

function render(trip, items) {
  TRIP_CTX = buildTripCtx(trip);

  const mustItems = items.filter((i) => i.confirm_required);
  const mustUnconfirmed = mustItems.filter((i) => !i.is_confirmed);
  const mustConfirmed = mustItems.filter((i) => i.is_confirmed);
  const flexible = items.filter((i) => !i.confirm_required);

  const updated = new Date().toLocaleTimeString("zh-Hant", {
    hour: "2-digit", minute: "2-digit",
  });

  let html = `
    <div class="header">
      <div class="title">${escapeHtml(trip ? trip.name : "確認清單")}</div>
      <div class="sub">出發前確認清單</div>
    </div>
    ${DEMO ? renderBanner("warn", "🧪 範例模式：這是假資料，按鈕只在本機作用、不會連到 Supabase。") : ""}
    <div class="toolbar">
      <button class="refresh-btn" id="refresh">↻ 重新整理</button>
      <span class="updated">更新於 ${updated}</span>
    </div>
  `;

  // ── 優先：必須確認 + 未確認 ──
  const zero = mustUnconfirmed.length === 0 ? "zero" : "";
  html += `<div class="section-title">⚠️ 必須確認
            <span class="count ${zero}">${mustUnconfirmed.length}</span></div>`;
  if (mustUnconfirmed.length === 0) {
    html += renderBanner("ok", "✅ 必訂項目都確認完成了，可以安心出發");
  } else {
    html += renderBanner("warn",
      `還有 ${mustUnconfirmed.length} 個項目需要訂位 / 預約 / 確認`);
    html += mustUnconfirmed.map((it) => renderCard(it, "priority")).join("");
  }

  // ── 必須確認 + 已確認（可折疊） ──
  if (mustConfirmed.length > 0) {
    html += `<details class="done-group">
      <summary>✅ 已確認（${mustConfirmed.length}）</summary>`;
    html += mustConfirmed.map((it) => renderCard(it, "done")).join("");
    html += `</details>`;
  }

  // ── 可以彈性 ──
  html += `<div class="section-title">🟢 可以彈性
            <span class="section-hint">　就算沒排定也不算遺漏</span></div>`;
  if (flexible.length === 0) {
    html += `<div class="empty">沒有彈性項目</div>`;
  } else {
    html += flexible.map((it) => renderCard(it, "flexible")).join("");
  }

  app.innerHTML = html;
  wireEvents();
}

function wireEvents() {
  const refresh = document.getElementById("refresh");
  if (refresh) refresh.addEventListener("click", () => load());

  // 切換「已確認」
  document.querySelectorAll(".check").forEach((btn) => {
    btn.addEventListener("click", () => guard(btn,
      () => setConfirmed(btn.dataset.id, btn.dataset.confirmed !== "1")));
  });

  // 排入某天某時段
  document.querySelectorAll(".sched-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const day = Number(document.getElementById(`sched-day-${id}`).value);
      const time = document.getElementById(`sched-time-${id}`).value;
      if (!/^\d{2}:\d{2}$/.test(time)) { alert("請輸入正確時間（HH:MM）"); return; }
      guard(btn, () => scheduleItem(id, day, time));
    });
  });

  // 退回候選
  document.querySelectorAll(".unsched-btn").forEach((btn) => {
    btn.addEventListener("click", () => guard(btn,
      () => unscheduleItem(btn.dataset.id)));
  });
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
