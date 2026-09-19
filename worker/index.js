// worker/index.js — Scout 的後端，一支 Worker 取代原本四支 Netlify Function。
//
// 為什麼合成一支：Cloudflare 的 Worker 本來就是「一個 fetch handler 自己分路由」，
// 而排程（scheduled）也必須掛在同一支 Worker 上。硬要維持「一支 function 一個檔」
// 會變成用 wrangler 的多 entry 去模擬 Netlify 的目錄慣例，多一層沒有好處的間接。
// 四支的**內容**仍然一段一段分開，行為與錯誤訊息與 Netlify 版逐字等價。
//
// 路由（靜態資產由平台先處理，對不上才進得來這裡）：
//   POST /api/ai-parse    Gemini 行程解析 proxy
//   POST /api/ai-suggest  Gemini 生成行程 proxy
//   GET  /api/share       購物清單唯讀分享
//   其餘                  404
//
// 舊網址 /.netlify/functions/* 由 web/_redirects 轉過來，已發出去的連結不會死。

// 共用核心：prompt 組裝的唯一一份實作，瀏覽器的 <script> 與這裡用同一個檔案。
// Netlify 版是用 node:fs + node:vm 讀它——**Workers 沒有 fs 也沒有 vm**，
// 所以改成 side-effect import，讓它把 ScoutAiSuggest 掛上 globalThis 之後再取。
import "../web/ai-suggest-core.js";

// ── Supabase 保活的目標（原 keepalive.js）──
// 兩邊的 URL 與 publishable key 本來就寫死在前端原始碼裡（設計上即公開，
// 真正的存取邊界是網址本身——ADR-013）。這裡沿用同一組值當預設，
// 要換的時候用 Worker 環境變數覆蓋，不必改程式。
function keepaliveTargets(env) {
  return [
    {
      name: "行程（Chia 的專案）",
      url: env.CHECKLIST_SUPABASE_URL || "https://uarkccyqcqvgxukjcrey.supabase.co",
      key: env.CHECKLIST_SUPABASE_ANON_KEY || "sb_publishable_CPg7D4iO0uBA0gnfd-rlFA_2Ia-9P4V", // gitleaks:allow
      table: "trips",
    },
    {
      name: "購物（Stanley 的專案）",
      url: env.BUYLIST_SUPABASE_URL || "https://kdmmjlaajqxjmiahfvos.supabase.co",
      key: env.BUYLIST_SUPABASE_ANON_KEY || "sb_publishable_iuUz3RtUoTErjeAunr0FJw_31jB7AAu", // gitleaks:allow
      table: "buylist_budget",
    },
  ];
}

const SHARE_FALLBACK_URL = "https://kdmmjlaajqxjmiahfvos.supabase.co";
const SHARE_FALLBACK_KEY = "sb_publishable_iuUz3RtUoTErjeAunr0FJw_31jB7AAu"; // gitleaks:allow — 與前端同一把公開 key

// share 出得去的欄位。加欄位要在這裡明確加，預設不外流。
const PUBLIC_FIELDS = ["id", "name", "price", "quantity", "category", "tag", "note", "link", "urgency"];
const URGENCY_LABEL = { need: "很想要", want: "想要", maybe: "還在考慮" };

function json(status, payload, extraHeaders) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: Object.assign({ "Content-Type": "application/json; charset=utf-8" }, extraHeaders || {}),
  });
}

function geminiUrl(env, key) {
  const model = env.GEMINI_MODEL || "gemini-2.5-flash";
  return `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`;
}

// Gemini 回應裡把 candidates[0] 的文字段落串起來。兩支 proxy 共用。
function geminiText(data) {
  const parts = (data && data.candidates && data.candidates[0] && data.candidates[0].content
    && data.candidates[0].content.parts) || [];
  return parts.map((p) => (p && p.text) || "").join("");
}

// ── /api/ai-parse（原 ai-parse.js）──
// 目的：把 Gemini 金鑰藏在後端，前端不接觸金鑰。前端 POST { text, totalDays }，
// 回傳 { raw }（原始文字，交給前端解析）。
async function aiParse(request, env) {
  if (request.method !== "POST") {
    return json(405, { error: "只接受 POST" });
  }
  const key = env.GEMINI_API_KEY;
  if (!key) {
    return json(500, { error: "伺服器未設定 GEMINI_API_KEY（請到 Cloudflare Worker 的 secret 設定）" });
  }

  let text = "";
  let totalDays = 0;
  try {
    const b = JSON.parse((await request.text()) || "{}");
    text = String(b.text || "").trim();
    totalDays = parseInt(b.totalDays, 10) || 0;
  } catch (_) {
    return json(400, { error: "請求格式錯誤（需 JSON）" });
  }
  if (!text) {
    return json(400, { error: "缺少行程文字" });
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

  try {
    const res = await fetch(geminiUrl(env, key), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.2, responseMimeType: "application/json" },
      }),
    });
    const body = await res.text();
    if (!res.ok) {
      return json(502, { error: `Gemini 回應 ${res.status}：${body.slice(0, 300)}` });
    }
    return json(200, { raw: geminiText(JSON.parse(body)) });
  } catch (e) {
    return json(502, { error: "呼叫 Gemini 失敗：" + (e && e.message ? e.message : String(e)) });
  }
}

// ── /api/ai-suggest（原 ai-suggest.js）──
// 與 ai-parse 分開的理由沒變：兩者的 prompt 與輸出契約不同，塞進同一支會變成
// 靠參數分支的雙形態端點。prompt 組裝不在這裡，在 web/ai-suggest-core.js。
async function aiSuggest(request, env) {
  if (request.method !== "POST") {
    return json(405, { error: "只接受 POST" });
  }
  const key = env.GEMINI_API_KEY;
  if (!key) {
    return json(500, {
      error: "伺服器未設定 GEMINI_API_KEY。請用 wrangler secret put GEMINI_API_KEY 設定後重新部署。",
    });
  }

  let answers;
  try {
    const body = JSON.parse((await request.text()) || "{}");
    answers = body.answers || {};
  } catch (_) {
    return json(400, { error: "請求格式錯誤（需 JSON）" });
  }
  if (!String(answers.destination || "").trim()) {
    return json(400, { error: "缺少目的地。至少要知道去哪裡才生得出行程。" });
  }

  const core = globalThis.ScoutAiSuggest;
  if (!core) {
    return json(500, { error: "伺服器找不到 ai-suggest-core.js，無法組出 prompt。" });
  }

  try {
    const res = await fetch(geminiUrl(env, key), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: core.buildPrompt(answers) }] }],
        // 溫度沿用參照系統的 0.7：行程建議要有一點變化，不是抽取任務
        generationConfig: { temperature: 0.7, maxOutputTokens: 2048, responseMimeType: "application/json" },
      }),
    });
    const body = await res.text();
    if (!res.ok) {
      return json(502, { error: `Gemini 回應 ${res.status}：${body.slice(0, 300)}` });
    }
    return json(200, { raw: geminiText(JSON.parse(body)) });
  } catch (e) {
    return json(502, { error: "呼叫 Gemini 失敗：" + (e && e.message ? e.message : String(e)) });
  }
}

// ── /api/share（原 share.js）──
// 這是唯一的「唯讀出口」：伺服器端查 Supabase，只回吐白名單欄位、只回吐指定情境標籤
// 的未購項目，前端拿不到 key。限制都在這裡強制，不靠呼叫端自律。
async function share(request, env) {
  if (request.method !== "GET") {
    return json(405, { error: "只接受 GET" });
  }

  const tag = String(new URL(request.url).searchParams.get("tag") || "").trim();
  if (!tag) {
    return json(400, { error: "缺少 tag 參數。分享連結必須指定一個情境標籤，不提供整份清單。" });
  }
  if (tag.length > 60) {
    return json(400, { error: "tag 過長" });
  }

  const base = (env.SCOUT_BUYLIST_URL || SHARE_FALLBACK_URL).replace(/\/$/, "");
  const key = env.SCOUT_BUYLIST_KEY || SHARE_FALLBACK_KEY;

  // 欄位與條件都寫死在這裡；tag 走 encodeURIComponent，呼叫端無法插入額外的 filter
  const url = `${base}/rest/v1/buylist_items` +
    `?select=${PUBLIC_FIELDS.join(",")}` +
    `&bought=eq.false` +
    `&tag=eq.${encodeURIComponent(tag)}` +
    `&order=price.desc`;

  try {
    const res = await fetch(url, { headers: { apikey: key, Authorization: `Bearer ${key}` } });
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
}

// ── 排程：Supabase 保活（原 keepalive.js）──
async function ping(t) {
  // select=id&limit=1：回應體積接近零，不吃額度。
  const url = `${t.url}/rest/v1/${t.table}?select=id&limit=1`;
  const started = Date.now();
  try {
    const res = await fetch(url, { headers: { apikey: t.key, Authorization: `Bearer ${t.key}` } });
    // 200 = 活著。其他狀態碼也代表連得到（例如 401/404），但值得記下來看。
    return { name: t.name, ok: res.ok, status: res.status, ms: Date.now() - started };
  } catch (e) {
    // 連不上（DNS 解析不到＝專案已暫停或已刪除，就是我們想偵測的狀況）
    return { name: t.name, ok: false, status: null, ms: Date.now() - started,
             error: e && e.message ? e.message : String(e) };
  }
}

async function keepalive(env) {
  const targets = keepaliveTargets(env);
  const results = await Promise.all(targets.map(ping));

  // 印進 Worker 的 log。真的被暫停時，這裡會是唯一看得到的訊號（前端不會顯示任何東西），
  // 所以失敗要印得夠明顯。
  results.forEach((r) => {
    const tag = r.ok ? "OK " : "FAIL";
    console.log(`[keepalive] ${tag} ${r.name} status=${r.status} ${r.ms}ms${r.error ? " error=" + r.error : ""}`);
  });

  const allOk = results.every((r) => r.ok);
  if (!allOk) {
    // 這行是「有人終於去看 log」時唯一的線索，所以要直接給得出下一步，不能只說「失敗了」。
    const dead = results.filter((r) => !r.ok).map((r) => {
      const t = targets.find((x) => x.name === r.name);
      const m = /^https?:\/\/([a-z0-9]+)\.supabase\.co/i.exec((t && t.url) || "");
      const dash = m ? `https://supabase.com/dashboard/project/${m[1]}` : "https://supabase.com/dashboard";
      return `  ${r.name} → ${dash}`;
    });
    console.error([
      "[keepalive] 有專案沒回應，很可能已被 Supabase 自動暫停。",
      "keepalive 只能『防止』暫停，無法『喚醒』已暫停的專案——",
      "必須有人到後台按 Resume project（資料不會遺失）。",
      ...dead,
    ].join("\n"));
  }

  return { ok: allOk, results };
}

// 找不到頁面。刻意不回顯路徑——路徑是使用者可控的字串，放進 HTML 就得處理跳脫，
// 而回顯它對看的人沒有幫助。
function notFoundPage() {
  const html = `<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>找不到這一頁 — Scout</title>
<style>
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:#F5F0EA;color:#3C3830;
       font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif}
  main{text-align:center;padding:2rem}
  h1{font-size:1.4rem;margin:0 0 .6rem}
  p{color:#6B6558;margin:0 0 1.4rem;line-height:1.7}
  a{display:inline-block;padding:.6rem 1.4rem;border-radius:999px;background:#3D6B54;color:#fff;text-decoration:none}
</style></head>
<body><main>
  <h1>找不到這一頁</h1>
  <p>連結可能打錯了，或是後面多黏了標點符號。</p>
  <a href="/">回 Scout 首頁</a>
</main></body></html>`;
  return new Response(html, {
    status: 404,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

// ── /api/attachments — 訂房截圖、PDF 這類附件 ──
//
// 存在 Workers KV，不是 R2：R2 要綁信用卡，KV 在 Workers 免費方案內就有
// （1 GB 總量、單筆 25 MB）。附件也會在 build_trip_page 時嵌一份進離線單檔，
// 所以就算 KV 或網路掛了，飛機上那份還是打得開。
//
// 保護：一組 UPLOAD_KEY（wrangler secret）。這延續 ADR-013 的「網址即憑證」模型，
// 只是把憑證從網址換成一把金鑰——Chia 不必註冊任何帳號，知道金鑰就能上傳。
// **讀跟寫都要金鑰**：訂房截圖含真名與訂房編號，不能像購物清單那樣匿名可讀。
const MAX_ATTACHMENT = 24 * 1024 * 1024;   // KV 單筆上限 25 MB，留一點餘裕

function authed(request, env) {
  if (!env.UPLOAD_KEY) return false;
  const url = new URL(request.url);
  const given = request.headers.get("X-Scout-Key") || url.searchParams.get("k") || "";
  // 長度先比，再逐字元比；兩者都不是常數時間，但這裡擋的是隨手試，不是計時攻擊
  return given.length === env.UPLOAD_KEY.length && given === env.UPLOAD_KEY;
}

async function attachments(request, env) {
  if (!env.ATTACHMENTS) {
    return json(500, { error: "伺服器沒有綁 ATTACHMENTS KV，附件功能不可用。" });
  }
  if (!authed(request, env)) {
    return json(401, { error: "需要上傳金鑰。在上傳頁面輸入金鑰，或在網址加上 ?k=<金鑰>。" });
  }

  const url = new URL(request.url);
  const id = url.pathname.replace(/^\/api\/attachments\/?/, "");

  if (request.method === "GET" && !id) {
    // 列出某一趟的附件。KV 的 list 只給 key 與 metadata，不含內容，所以很輕
    const slug = url.searchParams.get("trip") || "";
    if (!slug) return json(400, { error: "缺少 trip 參數。" });
    const out = await env.ATTACHMENTS.list({ prefix: `${slug}/` });
    return json(200, {
      trip: slug,
      items: out.keys.map((k) => ({ id: k.name, ...(k.metadata || {}) })),
    });
  }

  if (request.method === "GET") {
    const got = await env.ATTACHMENTS.getWithMetadata(id, { type: "arrayBuffer" });
    if (!got || !got.value) return json(404, { error: "找不到這個附件。" });
    const meta = got.metadata || {};
    return new Response(got.value, {
      headers: {
        "Content-Type": meta.type || "application/octet-stream",
        // 附件是私人內容，不讓任何中間層留快取
        "Cache-Control": "private, no-store",
      },
    });
  }

  if (request.method === "POST") {
    const form = await request.formData();
    const slug = String(form.get("trip") || "").trim();
    const file = form.get("file");
    const label = String(form.get("label") || "").trim();
    if (!/^\d{4}-\d{2}-[a-z]{2}-[a-z0-9-]+$/.test(slug)) {
      return json(400, { error: "trip 必須是旅程資料夾名稱，例如 2026-09-kr-seoul。" });
    }
    if (!file || typeof file === "string") return json(400, { error: "沒有選擇檔案。" });
    const buf = await file.arrayBuffer();
    if (buf.byteLength > MAX_ATTACHMENT) {
      return json(413, { error: `檔案太大（${Math.round(buf.byteLength / 1048576)} MB），上限 24 MB。` });
    }
    // 檔名由伺服器決定：使用者的檔名可能含路徑分隔字元或奇怪字元，
    // 直接拿來當 key 會讓「一趟旅程一個前綴」這件事失守
    const ext = (file.name || "").split(".").pop();
    const safeExt = /^[A-Za-z0-9]{1,5}$/.test(ext || "") ? `.${ext.toLowerCase()}` : "";
    const key = `${slug}/${crypto.randomUUID()}${safeExt}`;
    await env.ATTACHMENTS.put(key, buf, {
      metadata: {
        name: String(file.name || "attachment").slice(0, 120),
        label: label.slice(0, 120),
        type: file.type || "application/octet-stream",
        size: buf.byteLength,
        at: new Date().toISOString().slice(0, 10),
      },
    });
    return json(200, { id: key, size: buf.byteLength });
  }

  if (request.method === "DELETE") {
    // 這裡**有**刪除，和 MCP server 的「沒有刪除能力」不衝突：
    // 那條規則保護的是行程與購物資料（誤刪救不回來，要走網頁的二次確認）。
    // 附件是隨手上傳的東西，傳錯一張截圖卻只能永遠留著，才是壞設計。
    if (!id) return json(400, { error: "缺少附件 id。" });
    await env.ATTACHMENTS.delete(id);
    return json(200, { deleted: id });
  }

  return json(405, { error: "只接受 GET、POST 或 DELETE" });
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path === "/api/ai-parse") return aiParse(request, env);
    if (path === "/api/ai-suggest") return aiSuggest(request, env);
    if (path === "/api/share") return share(request, env);
    if (path === "/api/attachments" || path.startsWith("/api/attachments/")) {
      return attachments(request, env);
    }
    // config.js 是選用的（Supabase 連線寫死在各自的 js 裡，那是 publishable key）。
    // 但 index.html 一定會去載它，沒有檔案就每次載入噴一個 404 紅字。
    // 靜態資產優先於 Worker，所以真的放了 config.js 時這段不會被執行。
    if (path === "/config.js") {
      return new Response("/* 沒有 config.js：連線設定已寫死在 checklist.js / buylist.js。 */", {
        headers: { "Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "no-store" },
      });
    }
    // 靜態資產由平台先處理；走到這裡代表既不是資產也不是已知端點。
    // /api/* 給程式呼叫，維持 JSON；其他路徑是人點錯連結，給看得懂的頁面。
    // （2026-09-13 實際發生過：連結後面黏了標點，打開只看到一串 {"error":...}。）
    if (path.startsWith("/api/")) {
      return json(404, { error: `沒有這個端點：${path}` });
    }
    return notFoundPage();
  },

  async scheduled(event, env, ctx) {
    // waitUntil 讓排程在 handler 回傳後仍能跑完；沒有 ctx（例如測試直接呼叫）就直接 await。
    const work = keepalive(env);
    if (ctx && typeof ctx.waitUntil === "function") ctx.waitUntil(work);
    await work;
  },
};
