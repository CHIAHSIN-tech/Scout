// check-share.mjs — 唯讀分享 function 的驗收（web/netlify/functions/share.js）。
//
//   node scripts/check-share.mjs
//
// 只用 Node 內建模組（本 repo 無 build step）。直接呼叫 handler，
// 不需要 Netlify、不需要真的 Supabase——fetch 被替換成假的 PostgREST。
//
// 驗的核心是「唯讀出口不能漏東西」：欄位白名單、只回未購、
// 以及呼叫端無法透過 tag 參數插入額外的查詢條件。
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const mod = require(new URL('../web/netlify/functions/share.js', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'));

const ROWS = [
  {id:1,name:'保溫瓶',price:1200,quantity:1,category:'生活',tag:'送禮-媽媽',note:'她說想要',link:'https://x',urgency:'need',
   bought:false, added_by:'Stanley', actual_price:999, starred:true, this_month:true},
  {id:2,name:'圍巾',price:800,quantity:1,category:'服飾',tag:'送禮-媽媽',note:'',link:'',urgency:'want',
   bought:false, added_by:'Chia', actual_price:null, starred:false, this_month:true},
];
let lastUrl='';
globalThis.fetch = async (url) => {
  lastUrl = String(url);
  const u = new URL(lastUrl);
  const sel = (u.searchParams.get('select')||'').split(',');
  const tagEq = (u.searchParams.get('tag')||'').replace('eq.','');
  const boughtEq = u.searchParams.get('bought');
  let rows = ROWS.filter(r => r.tag === decodeURIComponent(tagEq));
  if (boughtEq === 'eq.false') rows = rows.filter(r => !r.bought);
  // 模擬 PostgREST：只回 select 指定的欄位
  rows = rows.map(r => Object.fromEntries(sel.map(f => [f, r[f]])));
  return { ok:true, status:200, json: async () => rows, text: async () => JSON.stringify(rows) };
};

const call = (params, method='GET') =>
  mod.handler({ httpMethod: method, queryStringParameters: params });

const checks = [];
const ck = (name, cond, extra='') => checks.push({name, ok: !!cond, extra});

// 1. 正常情況
let r = await call({ tag:'送禮-媽媽' });
let body = JSON.parse(r.body);
ck('回 200', r.statusCode===200);
ck('回 2 筆', body.count===2);
ck('欄位白名單：沒有 added_by', !('added_by' in body.items[0]));
ck('欄位白名單：沒有 actual_price', !('actual_price' in body.items[0]));
ck('欄位白名單：沒有 bought', !('bought' in body.items[0]));
ck('欄位白名單：沒有 starred', !('starred' in body.items[0]));
ck('有中文迫切度標籤', body.items[0].urgency_label==='很想要', body.items[0].urgency_label);
ck('查詢一定帶 bought=eq.false', lastUrl.includes('bought=eq.false'));

// 2. 缺 tag
r = await call({});
ck('缺 tag → 400', r.statusCode===400);
ck('缺 tag 的訊息說明不提供整份清單', JSON.parse(r.body).error.includes('不提供整份清單'));

// 3. 非 GET
r = await call({tag:'x'}, 'POST');
ck('POST → 405', r.statusCode===405);

// 4. 注入嘗試：想多塞一個 filter
r = await call({ tag:'送禮-媽媽&bought=eq.true' });
ck('tag 有跳脫，不能插入額外 filter', lastUrl.includes('%26bought%3Deq.true'), lastUrl.split('&tag=')[1]);
ck('注入後仍強制 bought=eq.false', (lastUrl.match(/bought=eq\.false/g)||[]).length===1);

// 5. 過長 tag
r = await call({ tag:'x'.repeat(61) });
ck('過長 tag → 400', r.statusCode===400);

let fail=0;
for (const c of checks){ if(!c.ok) fail++; console.log((c.ok?'  ok  ':'  FAIL')+'  '+c.name+(c.extra?'  ['+c.extra+']':'')); }
console.log(fail? `\n${fail} 項失敗` : `\n全部通過（${checks.length} 項）`);
process.exit(fail?1:0);
