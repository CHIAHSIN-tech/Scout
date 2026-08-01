// shell.js — 外殼腳本。唯一職責：切換頂部雙 Tab，並記住上次選的。
// 刻意不放進任何一邊的 IIFE，也不碰兩邊的內部狀態——外殼只管顯示哪個 panel。

(function () {
  "use strict";

  var KEY = "scout_tab";            // localStorage 鍵；比照 buylist 既有的 buylist_me 存法
  var DEFAULT_PANEL = "shop";       // AC-1：預設落在購物 Tab

  var tabs = document.getElementById("shell-tabs");
  var panels = {
    shop: document.getElementById("panel-shop"),
    trip: document.getElementById("panel-trip")
  };

  function show(name) {
    if (!panels[name]) name = DEFAULT_PANEL;
    Object.keys(panels).forEach(function (k) {
      panels[k].classList.toggle("hidden", k !== name);
    });
    Array.prototype.forEach.call(tabs.querySelectorAll("button"), function (b) {
      b.classList.toggle("on", b.dataset.panel === name);
    });
    try { localStorage.setItem(KEY, name); } catch (e) { /* 無痕模式會擋，忽略即可 */ }
  }

  tabs.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (b && b.dataset.panel) show(b.dataset.panel);
  });

  // AC-8：重整後停在上次選的 Tab
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* 同上 */ }
  show(saved || DEFAULT_PANEL);
})();
