// ai-suggest.js — AI 生成行程 proxy（Netlify Function）。
//
// 為什麼不沿用 ai-parse.js：兩者的 prompt 與輸出契約不同——
// ai-parse 是「把既有文字解析成項目」，這支是「從六個答案從零生成整份行程」。
// 塞進同一支會變成靠參數分支的雙形態 function（spec Q5）。
//
// 金鑰：process.env.GEMINI_API_KEY，只存在於後端（ADR-011）。前端不接觸。
// 金鑰設定：Netlify 站台 Site settings → Environment variables 加 GEMINI_API_KEY。
//
// prompt 組裝不在這裡，在 web/ai-suggest-core.js——那是前端、後端、驗證腳本共用的唯一一份。

const fs = require("fs");
const path = require("path");
const vm = require("vm");

// 用 vm 載入共用核心：它是給瀏覽器的傳統 script，掛在全域物件上。
// 這樣 prompt 的五條規則只有一份，不會前後端各寫一次然後慢慢分岔。
function loadCore() {
  const candidates = [
    path.join(__dirname, "..", "..", "ai-suggest-core.js"),  // 本機：web/netlify/functions → web/
    path.join(__dirname, "ai-suggest-core.js"),              // 打包後可能被搬到同層
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(fs.readFileSync(p, "utf8"), sandbox, { filename: p });
      if (sandbox.window.ScoutAiSuggest) return sandbox.window.ScoutAiSuggest;
    }
  }
  return null;
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return json(405, { error: "只接受 POST" });
  }

  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    return json(500, {
      error: "伺服器未設定 GEMINI_API_KEY。請到 Netlify 站台的 Environment variables 加上這個變數後重新部署。",
    });
  }

  let answers;
  try {
    const body = JSON.parse(event.body || "{}");
    answers = body.answers || {};
  } catch (_) {
    return json(400, { error: "請求格式錯誤（需 JSON）" });
  }
  if (!String(answers.destination || "").trim()) {
    return json(400, { error: "缺少目的地。至少要知道去哪裡才生得出行程。" });
  }

  const core = loadCore();
  if (!core) {
    return json(500, { error: "伺服器找不到 ai-suggest-core.js，無法組出 prompt。" });
  }

  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`;

  try {
    const res = await fetch(url, {
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
    const data = JSON.parse(body);
    const parts = (data && data.candidates && data.candidates[0] && data.candidates[0].content
      && data.candidates[0].content.parts) || [];
    const raw = parts.map((p) => (p && p.text) || "").join("");
    // 原始文字交給前端解析——解析邏輯同樣在共用核心，前端與驗證腳本共用同一份
    return json(200, { raw });
  } catch (e) {
    return json(502, { error: "呼叫 Gemini 失敗：" + (e && e.message ? e.message : String(e)) });
  }
};

function json(statusCode, payload) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify(payload),
  };
}
