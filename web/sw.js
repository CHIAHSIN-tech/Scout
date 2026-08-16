// sw.js — Scout 的 service worker。
//
// ⚠️ 這支刻意「什麼都不做」，那是設計，不是還沒寫完。
//
// 它存在的唯一理由：Chrome 要求有註冊 service worker（且含 fetch 監聽器）
// 才會提供「安裝到主畫面」。裝好之後 Scout 有自己的 icon、開起來全螢幕、
// 沒有瀏覽器網址列——這就是本專案要 PWA 的全部目的。
//
// **不做離線快取，這是已定案的決策**（2026-08-17）：
//   1. 離線本身已明確不做——兩人即時共用，離線各改一份之後怎麼合是更大的題目。
//   2. 更現實的理由：這個專案被「線上跑舊版」坑過一次
//      （見 for-chia-deploy.md：手動拖拉部署造成線上是舊版）。
//      會快取的 service worker 只會讓那個坑更深——使用者會卡在舊版且不知道為什麼，
//      連重新整理都救不回來。
//
// 所以下面的 fetch 監聽器故意是空的：有監聽器（滿足安裝條件），
// 但從不呼叫 respondWith，每一個請求都原封不動交給瀏覽器走網路。

self.addEventListener("install", () => {
  // 不預先快取任何東西，直接接手
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    // 保險：若之前任何版本留下過快取，一律清掉。
    // 這行是給「將來有人加了快取又移除」的情境用的——殘留的舊快取會繼續生效。
    const names = await caches.keys();
    await Promise.all(names.map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

// 故意留空：不呼叫 respondWith ＝ 完全不介入，請求照常走網路。
self.addEventListener("fetch", () => {});
