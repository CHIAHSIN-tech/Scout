// trip-pages.js — 行程 Tab 底部的「歷次行程表」列表。
//
// 為什麼是獨立一支、不塞進 checklist.js：
//   checklist.js 是 Supabase 那條線（旅程、行程項目、AI 匯入），這一段完全不碰網路，
//   只讀一份靜態的 trips/index.json。混在一起，「Supabase 掛了」就會連這份也看不到。
//
// 刻意不依賴 config.js：config.js 是 gitignored 的 Supabase 設定，本機沒有它時
// checklist 整段會停在「載入中」。這份列表讀的是靜態 JSON，沒有 config.js 也該顯示得出來。

(function () {
  "use strict";

  var mount = document.getElementById("trip-pages");
  if (!mount) return;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function render(rows) {
    if (!rows.length) {
      mount.innerHTML =
        '<div class="tp-empty">還沒有建置過的行程表。'
        + "行程表由 Claude 透過 Scout 的 MCP 工具產生（build_trip_page）。</div>";
      return;
    }
    var html = rows.map(function (r) {
      var range = esc(r.start_date) + (r.end_date ? " – " + esc(r.end_date) : "");
      var where = [r.city, r.country].filter(Boolean).map(esc).join(" · ");
      return '<a class="tp-item" href="' + esc(r.page_path) + '">'
        + '<span class="tp-title">' + esc(r.title || r.city || "行程表") + "</span>"
        + '<span class="tp-meta">' + where + "</span>"
        + '<span class="tp-date">' + range + "</span></a>";
    }).join("");
    mount.innerHTML = '<h3 class="tp-h">歷次行程表</h3><div class="tp-list">' + html + "</div>";
  }

  // 讀一份跟著網站一起部署的靜態 JSON。沒有這個檔（還沒建置過任何行程表）
  // 不是錯誤，所以失敗路徑是「顯示空狀態」，不是紅字。
  var req = new XMLHttpRequest();
  req.open("GET", "trips/index.json", true);
  req.onload = function () {
    if (req.status < 200 || req.status >= 300) { render([]); return; }
    var rows;
    try { rows = JSON.parse(req.responseText); } catch (e) { render([]); return; }
    render(Array.isArray(rows) ? rows : []);
  };
  req.onerror = function () { render([]); };
  req.send();
})();
