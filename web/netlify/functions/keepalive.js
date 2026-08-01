// keepalive.js — Supabase 保活（Netlify Scheduled Function）。
//
// 為什麼需要：Supabase 免費方案閒置 7 天就自動暫停。購物專案天天用不會中招；
// 行程專案是「規劃旅行才用」的季節性用途，2026-07 與 2026-08 已被暫停兩次，
// 每次都要人工到後台 un-pause（spec-scout-app-merge.md §6.5、R6）。
// 每週一、四各打一次最輕量的查詢，用 API 活動把閒置計時器歸零。
// （不排每 7 天一次：那等於零餘裕，單次延遲或失敗就會被暫停。理由詳見 netlify.toml。）
//
// 排程寫在 repo 根目錄的 netlify.toml（[functions."keepalive"]），不在這裡，
// 這樣就不需要 @netlify/functions 套件、不需要 package.json、維持零 build step。
//
// ⚠️ 尚未驗證：Supabase 判定「活動」的規則沒有公開到能保證的程度。
//    驗證方式是部署後隔 10 天再開行程 Tab，不用 un-pause 才算成功。
//    在那之前不要把手動 un-pause 當成不需要的退路。

// 兩邊的 URL 與 anon key 本來就寫死在前端原始碼裡（publishable key，設計上即公開，
// 真正的存取邊界是網址本身——ADR-013）。這裡沿用同一組值，不另外增加要維護的環境變數；
// 若哪天需要換，可用 Netlify 環境變數覆蓋，不必改程式。
const TARGETS = [
  {
    name: "行程（Chia 的專案）",
    url: process.env.CHECKLIST_SUPABASE_URL || "https://uarkccyqcqvgxukjcrey.supabase.co",
    key: process.env.CHECKLIST_SUPABASE_ANON_KEY || "sb_publishable_CPg7D4iO0uBA0gnfd-rlFA_2Ia-9P4V", // gitleaks:allow
    table: "trips",
  },
  {
    name: "購物（Stanley 的專案）",
    url: process.env.BUYLIST_SUPABASE_URL || "https://kdmmjlaajqxjmiahfvos.supabase.co",
    key: process.env.BUYLIST_SUPABASE_ANON_KEY || "sb_publishable_iuUz3RtUoTErjeAunr0FJw_31jB7AAu", // gitleaks:allow
    table: "buylist_budget",
  },
];

async function ping(t) {
  // select=id&limit=1：回應體積接近零，不吃額度。
  const url = `${t.url}/rest/v1/${t.table}?select=id&limit=1`;
  const started = Date.now();
  try {
    const res = await fetch(url, {
      headers: { apikey: t.key, Authorization: `Bearer ${t.key}` },
    });
    const ms = Date.now() - started;
    // 200 = 活著。其他狀態碼也代表連得到（例如 401/404），但值得記下來看。
    return { name: t.name, ok: res.ok, status: res.status, ms };
  } catch (e) {
    // 連不上（DNS 解析不到＝專案已暫停或已刪除，就是我們想偵測的狀況）
    return { name: t.name, ok: false, status: null, ms: Date.now() - started,
             error: e && e.message ? e.message : String(e) };
  }
}

exports.handler = async () => {
  const results = await Promise.all(TARGETS.map(ping));

  // 印進 Netlify function log。真的被暫停時，這裡會是唯一看得到的訊號，
  // 所以失敗要印得夠明顯（前端不會顯示任何東西）。
  results.forEach((r) => {
    const tag = r.ok ? "OK " : "FAIL";
    console.log(`[keepalive] ${tag} ${r.name} status=${r.status} ${r.ms}ms${r.error ? " error=" + r.error : ""}`);
  });

  const allOk = results.every((r) => r.ok);
  if (!allOk) console.error("[keepalive] 有專案沒回應——可能已被暫停，請到 Supabase 後台確認。");

  // 排程 function 的回傳值沒人看，但給個明確狀態碼方便從 Netlify 後台掃歷史紀錄。
  return {
    statusCode: allOk ? 200 : 500,
    body: JSON.stringify({ ok: allOk, results }),
  };
};
