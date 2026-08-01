// ai-parse.js — Gemini 行程解析 proxy（Netlify Function）。
//
// 目的：把 Gemini 金鑰藏在後端環境變數，前端不接觸金鑰（公開部署也不外露）。
// 前端 POST { text, totalDays } 到 /.netlify/functions/ai-parse，
// 這裡用 process.env.GEMINI_API_KEY 呼叫 Gemini，回傳 { raw }（原始文字，交給前端解析）。
//
// 金鑰設定：Netlify 站台 Site settings → Environment variables 加 GEMINI_API_KEY（可選 GEMINI_MODEL）。

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ error: "只接受 POST" }) };
  }
  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    return { statusCode: 500, body: JSON.stringify({ error: "伺服器未設定 GEMINI_API_KEY（請到 Netlify 環境變數設定）" }) };
  }

  let text = "", totalDays = 0;
  try {
    const b = JSON.parse(event.body || "{}");
    text = String(b.text || "").trim();
    totalDays = parseInt(b.totalDays, 10) || 0;
  } catch (_) {
    return { statusCode: 400, body: JSON.stringify({ error: "請求格式錯誤（需 JSON）" }) };
  }
  if (!text) {
    return { statusCode: 400, body: JSON.stringify({ error: "缺少行程文字" }) };
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

  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.2, responseMimeType: "application/json" },
      }),
    });
    const body = await res.text();
    if (!res.ok) {
      return { statusCode: 502, body: JSON.stringify({ error: `Gemini 回應 ${res.status}：${body.slice(0, 300)}` }) };
    }
    const data = JSON.parse(body);
    const raw = (data && data.candidates && data.candidates[0] && data.candidates[0].content
      && data.candidates[0].content.parts || []).map((p) => (p && p.text) || "").join("");
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ raw }) };
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: "呼叫 Gemini 失敗：" + (e && e.message ? e.message : String(e)) }) };
  }
};
