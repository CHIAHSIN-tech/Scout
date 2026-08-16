// share.js — 願望清單唯讀分享（Netlify Function）。
//
// 為什麼需要後端：現行安全模型是 ADR-013「網址即憑證」——前端那把 anon key
// 可讀、可寫、可刪。把它直接給家人＝把整份清單的寫入權也給出去。
// 這支 function 是唯一的「唯讀出口」：它在伺服器端查 Supabase，
// 只回吐白名單欄位、只回吐指定情境標籤的未購項目，前端拿不到 key。
//
// 刻意的限制（都在這裡強制，不靠呼叫端自律）：
//   * 只接受 GET，只接受一個參數 tag，且必須完全比對（不接受任意 filter）
//   * 只回未購項目（bought=false）——已買的是消費紀錄，不是願望
//   * 欄位白名單，預算 / 誰加的 / 實付金額 / 已買狀態一律不出去
//
// 金鑰：優先讀環境變數；沒設就用與前端相同的 publishable key。
// 後者不算洩漏——那把 key 本來就寫在 buylist.js 裡、隨頁面公開，
// 這支 function 的價值在於「不給寫入路徑」，不在於藏 key。

const FALLBACK_URL = "https://kdmmjlaajqxjmiahfvos.supabase.co";
const FALLBACK_KEY = "sb_publishable_iuUz3RtUoTErjeAunr0FJw_31jB7AAu"; // gitleaks:allow — 與前端同一把公開 key

// 出得去的欄位。加欄位要在這裡明確加，預設不外流。
const PUBLIC_FIELDS = ["id", "name", "price", "quantity", "category", "tag", "note", "link", "urgency"];

const URGENCY_LABEL = { need: "很想要", want: "想要", maybe: "還在考慮" };

exports.handler = async (event) => {
  if (event.httpMethod !== "GET") {
    return json(405, { error: "只接受 GET" });
  }

  const tag = String((event.queryStringParameters || {}).tag || "").trim();
  if (!tag) {
    return json(400, { error: "缺少 tag 參數。分享連結必須指定一個情境標籤，不提供整份清單。" });
  }
  if (tag.length > 60) {
    return json(400, { error: "tag 過長" });
  }

  const base = (process.env.SCOUT_BUYLIST_URL || FALLBACK_URL).replace(/\/$/, "");
  const key = process.env.SCOUT_BUYLIST_KEY || FALLBACK_KEY;

  // 欄位與條件都寫死在這裡；tag 走 encodeURIComponent，呼叫端無法插入額外的 filter
  const url = `${base}/rest/v1/buylist_items` +
    `?select=${PUBLIC_FIELDS.join(",")}` +
    `&bought=eq.false` +
    `&tag=eq.${encodeURIComponent(tag)}` +
    `&order=price.desc`;

  try {
    const res = await fetch(url, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
    });
    if (!res.ok) {
      const body = await res.text();
      return json(502, { error: `讀取清單失敗（${res.status}）：${body.slice(0, 200)}` });
    }
    const rows = await res.json();

    // 再過濾一次欄位：即使上游多回了什麼，也不會漏出去
    const items = (Array.isArray(rows) ? rows : []).map((r) => {
      const out = {};
      for (const f of PUBLIC_FIELDS) out[f] = r[f];
      out.urgency_label = URGENCY_LABEL[r.urgency] || "";
      return out;
    });

    return json(200, { tag, count: items.length, items }, {
      // 唯讀公開頁，允許被任何來源讀（分享出去就是要讓人打得開）
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=60",
    });
  } catch (e) {
    return json(502, { error: "讀取清單失敗：" + (e && e.message ? e.message : String(e)) });
  }
};

function json(statusCode, payload, extraHeaders) {
  return {
    statusCode,
    headers: Object.assign({ "Content-Type": "application/json; charset=utf-8" }, extraHeaders || {}),
    body: JSON.stringify(payload),
  };
}
