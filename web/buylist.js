// buylist.js — 從 buylist/index.html 的 <script> 原樣搬出（本來就是 IIFE，不需再包）。
// 唯一改動：DOM id 'status' / 'statusText' 與 checklist 撞名，改為 'bl-status' / 'bl-statusText'。
(function(){
  "use strict";
  const SUPABASE_URL='https://kdmmjlaajqxjmiahfvos.supabase.co';
  const SUPABASE_KEY='sb_publishable_iuUz3RtUoTErjeAunr0FJw_31jB7AAu';
  // Gemini 金鑰從 gitignored 的 config.js 讀（不寫死進版控）
  const GEMINI_KEY=(window.BUYLIST_CONFIG&&window.BUYLIST_CONFIG.GEMINI_API_KEY)||'';
  const GEMINI_MODEL=(window.BUYLIST_CONFIG&&window.BUYLIST_CONFIG.GEMINI_MODEL)||'gemini-2.5-flash';

  const URG={need:{label:'需要',cls:'u-need'},want:{label:'想要',cls:'u-want'},maybe:{label:'再看看',cls:'u-maybe'}};
  const ACC={tw_easy:{label:'台灣容易',cls:'a-easy'},overseas:{label:'需國外',cls:'a-os'},rare:{label:'稀有難找',cls:'a-rare'}};
  const CATS=['3C','家電','服飾','美妝','食品','生活','書籍','其他'];
  // 辣醬庫評分維度（回購度是列表預設排序鍵）
  const SDIMS=[{k:'spiciness',label:'辣度'},{k:'aroma',label:'香氣'},{k:'cp',label:'CP值'},{k:'repurchase',label:'回購度'}];

  const $=id=>document.getElementById(id);
  const statusEl=$('bl-status'), statusText=$('bl-statusText');
  function setStatus(t,cls){statusText.textContent=t;statusEl.className='status'+(cls?' '+cls:'');}
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
  function money(n){return 'NT$ '+(Math.round(+n||0)).toLocaleString('en-US');}
  function daysSince(iso){const d=Math.floor((Date.now()-new Date(iso).getTime())/86400000);return d<=0?'今天加入':('想買了 '+d+' 天');}
  function ageDays(iso){return Math.floor((Date.now()-new Date(iso).getTime())/86400000);}

  if(!window.supabase||!window.supabase.createClient){setStatus('Supabase 函式庫未載入','err');return;}
  const sb=window.supabase.createClient(SUPABASE_URL,SUPABASE_KEY);

  let items=[], budget=0, view='list';
  let me=localStorage.getItem('buylist_me')||'';
  let addUrg='maybe', addAcc='tw_easy';
  let addingItem=false;
  let fStatus='all', fCat='all', fSort='default', fTag='all', fSearch='';
  // 辣醬庫狀態（獨立資料域，不與購物清單相干）
  let sauces=[], activeTab='buy', scSearch='';
  let newSauce={spiciness:0, aroma:0, cp:0, repurchase:0};

  // 下拉選單填充
  $('bl-cat').innerHTML=CATS.map(c=>'<option value="'+c+'">'+c+'</option>').join('');
  $('bl-cat').value='其他';
  $('f-cat').innerHTML='<option value="all">全部分類</option>'+CATS.map(c=>'<option value="'+c+'">'+c+'</option>').join('');

  function renderWho(){document.querySelectorAll('#whoSel button').forEach(b=>b.classList.toggle('on',b.dataset.me===me));}

  // ── 載入（含月初自動清已買）──
  async function loadAll(){
    const r2=await sb.from('buylist_budget').select('*').eq('id',1).maybeSingle();
    let brow=(r2 && !r2.error)?r2.data:null;
    const ym=new Date().toISOString().slice(0,7);
    if(brow){
      const lc=brow.last_cleared||'';
      if(lc && lc!==ym){ await sb.from('buylist_items').delete().eq('bought',true); }   // 跨月→清掉上月已買
      if(lc!==ym){ await sb.from('buylist_budget').update({last_cleared:ym}).eq('id',1); brow.last_cleared=ym; }
    }
    budget=brow?(+brow.monthly_budget||0):0;
    const r1=await sb.from('buylist_items').select('*').order('created_at');
    if(r1.error){setStatus('讀取失敗：'+r1.error.message,'err');return;}
    items=r1.data||[];
    renderAll();
  }

  function thisMonthUnbought(){return items.filter(i=>i.this_month && !i.bought);}

  function renderBudget(){
    const tmu=thisMonthUnbought();
    const total=tmu.reduce((s,i)=>s+(+i.price||0),0);
    $('bl-total').textContent=money(total);
    const bInput=$('bl-budget');
    if(document.activeElement!==bInput) bInput.value=budget?budget:'';
    const rem=$('bl-remain');
    if(!budget){rem.textContent='—';rem.className='big remain';}
    else{const diff=budget-total; if(diff>=0){rem.textContent=money(diff);rem.className='big remain ok';}
      else{rem.textContent='超支 '+money(-diff);rem.className='big remain over';}}
    const recur=tmu.reduce((s,i)=>s+(+i.recurring_cost||0),0);
    $('bl-recur').textContent=recur?('＋ 這些買下去每月後續成本約 '+money(recur)):'';
  }

  function tag(cls,txt){return '<span class="tag '+cls+'">'+txt+'</span>';}
  // 關鍵字搜尋：名稱／備註／情境標籤／分類 任一命中即可。
  // 大小寫不敏感（英文商品名常大小寫混用），中文不受影響。
  function matchSearch(i){
    const q=fSearch.trim().toLowerCase();
    if(!q) return true;
    return [i.name,i.note,i.tag,i.category].some(v=>String(v||'').toLowerCase().includes(q));
  }
  function visibleItems(){
    let arr=items.filter(i=>{
      if(!matchSearch(i)) return false;
      if(fStatus==='month' && !(i.this_month && !i.bought)) return false;
      if(fStatus==='bought' && !i.bought) return false;
      if(fStatus==='starred' && !(i.bought && i.starred)) return false;   // 已買且加星
      if(fCat!=='all' && (i.category||'其他')!==fCat) return false;
      if(fTag!=='all' && (i.tag||'').trim()!==fTag) return false;
      return true;
    });
    const urgRank={need:0,want:1,maybe:2};
    // 已買永遠沉底：抽成套在三種排序之上的主鍵（未購 0 在前、已買 1 在後），群內再照各自排序鍵
    const boughtRank=i=>i.bought?1:0;
    if(fSort==='price') arr.sort((a,b)=>boughtRank(a)-boughtRank(b) || (+b.price||0)-(+a.price||0));
    else if(fSort==='days') arr.sort((a,b)=>boughtRank(a)-boughtRank(b) || ageDays(b.created_at)-ageDays(a.created_at));
    else arr.sort((a,b)=>{
      if(a.bought!==b.bought) return boughtRank(a)-boughtRank(b);   // 已買沉底（主鍵）
      if((a.this_month&&!a.bought)!==(b.this_month&&!b.bought)) return (b.this_month&&!b.bought)-(a.this_month&&!a.bought);
      if((urgRank[a.urgency]??9)!==(urgRank[b.urgency]??9)) return (urgRank[a.urgency]??9)-(urgRank[b.urgency]??9);
      return new Date(b.created_at)-new Date(a.created_at);
    });
    return arr;
  }
  // 差額文字：實付 vs 估價（未填＝不顯示；省=綠、超=紅、持平=灰）
  function diffText(price,actual){
    if(actual==null) return '';
    const p=+price||0, a=+actual||0;
    if(a===p) return '<span class="pdiff even">持平</span>';
    return a<p ? '<span class="pdiff save">省 '+money(p-a)+'</span>'
              : '<span class="pdiff over">超 '+money(a-p)+'</span>';
  }
  // 已買項目的「實付」inline 輸入＋差額；預設帶入估價（降低誤填 0）
  function actualPriceHtml(i){
    const val=(i.actual_price!=null? i.actual_price : (+i.price||0));
    return '<div class="actual">實付 <input type="number" class="ainput" data-id="'+i.id+'" value="'+val+'" min="0" step="1">'
      +diffText(i.price,i.actual_price)+'</div>';
  }
  // 單張項目卡片。抽出來是因為「清單」與「分類分組」兩個檢視都要用（第二個使用點才抽）。
  function itemCardHtml(i){
    {
      const u=URG[i.urgency]||URG.maybe, a=ACC[i.accessibility]||ACC.tw_easy;
      const tags=tag(u.cls,u.label)+tag(a.cls,a.label)+tag('cat',esc(i.category||'其他'))
        +((i.tag||'').trim()?tag('ctx','📍'+esc(i.tag.trim())):'')
        +(i.this_month?tag('tm','本月想買'):tag('later','之後再說'))+tag('days',daysSince(i.created_at));
      const meta=[];
      if(i.added_by) meta.push(esc(i.added_by)+' 加的');
      if(+i.recurring_cost>0) meta.push('<span class="irecur">每月後續 '+money(i.recurring_cost)+'</span>');
      if(i.link) meta.push('<a href="'+esc(i.link)+'" target="_blank" rel="noopener">🔗 連結</a>');
      return '<div class="item '+(i.bought?'bought':'')+'">'
        +'<button class="chk '+(i.bought?'on':'')+'" data-id="'+i.id+'" data-b="'+(i.bought?1:0)+'" title="標記已買">'+(i.bought?'✓':'')+'</button>'
        +(i.bought?'<button class="star '+(i.starred?'on':'')+'" data-id="'+i.id+'" data-s="'+(i.starred?1:0)+'" title="標記可回購">★</button>':'')
        +'<div class="ibody">'
          +'<div class="itop"><span class="iname">'+esc(i.name)+'</span>'+((+i.quantity>1)?'<span class="iqty">×'+(+i.quantity)+'</span>':'')+(i.price?'<span class="iprice">'+money(i.price)+'</span>':'')+'</div>'
          +'<div class="itags">'+tags+'</div>'
          +(meta.length?'<div class="imeta">'+meta.join('')+'</div>':'')
          +(i.note?'<div class="inote">'+esc(i.note)+'</div>':'')
          +(i.bought?actualPriceHtml(i):'')
        +'</div><button class="idel" data-del="'+i.id+'" title="刪除">✕</button></div>';
    }
  }
  // 卡片上的互動綁定。兩個檢視共用，所以跟著卡片一起抽出來。
  function wireItemEvents(box){
    box.querySelectorAll('.chk').forEach(b=>b.addEventListener('click',()=>toggleBought(b.dataset.id,b.dataset.b!=='1')));
    box.querySelectorAll('.star').forEach(b=>b.addEventListener('click',()=>toggleStarred(b.dataset.id,b.dataset.s!=='1')));
    box.querySelectorAll('.ainput').forEach(inp=>inp.addEventListener('change',()=>updateActualPrice(inp.dataset.id,inp.value)));
    box.querySelectorAll('.idel').forEach(b=>b.addEventListener('click',()=>delItem(b.dataset.del)));
  }
  const EMPTY_HTML='<div class="empty">沒有符合的項目。<br>上面加一個，或換個篩選看看。</div>';

  function renderList(){
    const box=$('list'); const arr=visibleItems();
    box.innerHTML = arr.length ? arr.map(itemCardHtml).join('') : EMPTY_HTML;
    wireItemEvents(box);
  }

  // 依分類分區折疊。分類是寫死的八類（CATS），所以分組順序固定、不隨資料跳動；
  // 有東西的類別才顯示，預設全部展開（收合狀態由使用者自己決定，不記憶）。
  function renderCatGroups(){
    const box=$('catlist'); const arr=visibleItems();
    if(!arr.length){box.innerHTML=EMPTY_HTML; return;}
    const order=[...CATS];
    // 資料裡出現過但不在 CATS 的分類（例如舊資料）也要顯示，不能默默吃掉
    arr.forEach(i=>{const c=i.category||'其他'; if(!order.includes(c)) order.push(c);});
    box.innerHTML=order.map(cat=>{
      const group=arr.filter(i=>(i.category||'其他')===cat);
      if(!group.length) return '';
      const unbought=group.filter(i=>!i.bought).length;
      const sum=group.filter(i=>!i.bought).reduce((s,i)=>s+(+i.price||0),0);
      return '<details class="catgroup" open><summary>'+esc(cat)
        +'<span class="cgcount">'+group.length+' 項</span>'
        +(unbought?'<span class="cgsum">未購 '+money(sum)+'</span>':'<span class="cgsum done">都買齊了</span>')
        +'</summary>'+group.map(itemCardHtml).join('')+'</details>';
    }).join('');
    wireItemEvents(box);
  }
  function renderMatrix(){
    const data=thisMonthUnbought();
    const prices=data.map(i=>+i.price||0).sort((a,b)=>a-b);
    const med=prices.length?prices[Math.floor(prices.length/2)]:0;
    const hiUrg=i=>i.urgency==='need'||i.urgency==='want';
    const hiPrice=i=>(+i.price||0)>=med && med>0;
    const cells={'lo-need':[],'hi-need':[],'lo-low':[],'hi-low':[]};
    data.forEach(i=>cells[(hiPrice(i)?'hi':'lo')+'-'+(hiUrg(i)?'need':'low')].push(i));
    const q=(k,t,c)=>{const l=cells[k].map(i=>'<div class="chip"><span>'+esc(i.name)+'</span><span class="cp">'+(i.price?money(i.price):'')+'</span></div>').join('')||'<div style="font-size:11px;color:var(--faint);">（空）</div>';return '<div class="quad'+c+'"><div class="qh">'+t+'</div>'+l+'</div>';};
    $('matrix').innerHTML=q('lo-need','迫切高 · 價格低',' q-lo-need')+q('hi-need','迫切高 · 價格高',' q-hi-need')+q('lo-low','迫切低 · 價格低','')+q('hi-low','迫切低 · 價格高','');
  }
  // 目前資料裡出現過的情境標籤（去空白、去重、排序）；分類是寫死的，情境是使用者自訂所以動態算
  function distinctTags(){return [...new Set(items.map(i=>(i.tag||'').trim()).filter(Boolean))].sort();}
  // 依現有資料重建「情境」篩選下拉與 autocomplete；保留當前選擇，選的標籤若消失則退回「全部情境」
  function renderTagOptions(){
    const tags=distinctTags();
    if(fTag!=='all' && !tags.includes(fTag)) fTag='all';
    $('f-tag').innerHTML='<option value="all">全部情境</option>'+tags.map(t=>'<option value="'+esc(t)+'">'+esc(t)+'</option>').join('');
    $('f-tag').value=fTag;
    $('tag-list').innerHTML=tags.map(t=>'<option value="'+esc(t)+'">').join('');
  }
  function renderAll(){renderTagOptions();renderBudget();renderList();renderCatGroups();renderMatrix();}

  // ── 快速複製常買清單 ──
  // 「星號」在既有語意裡就是「已買且可回購」（spec-buylist-starred），所以重買的來源直接用它，
  // 不另外發明一個「常買」欄位。
  function repeatCandidates(){
    return items.filter(i=>i.bought && i.starred)
                .sort((a,b)=>new Date(b.created_at)-new Date(a.created_at));
  }
  function renderRepeat(){
    const box=$('rplist'), arr=repeatCandidates();
    if(!arr.length){
      box.innerHTML='<div class="empty">還沒有星號收藏。<br>把買過、之後還會再買的東西按 ★ 標起來，這裡就會出現。</div>';
      return;
    }
    box.innerHTML=arr.map(i=>'<label class="rpitem"><input type="checkbox" value="'+i.id+'">'
      +'<span class="rpname">'+esc(i.name)+'</span>'
      +(i.price?'<span class="rpprice">'+money(i.price)+'</span>':'')
      +((i.tag||'').trim()?'<span class="rptag">📍'+esc(i.tag.trim())+'</span>':'')+'</label>').join('');
  }
  function toggleRepeat(show){
    $('repeat-box').classList.toggle('hidden',!show);
    $('rp-msg').textContent='';
    if(show) renderRepeat();
  }
  async function repeatAdd(){
    const picked=[...$('rplist').querySelectorAll('input:checked')].map(c=>c.value);
    if(!picked.length){$('rp-msg').textContent='先勾幾樣。';$('rp-msg').className='rpmsg err';return;}
    // 複製既有設定（價格/分類/情境/迫切度…），但重置成「還沒買」的新一筆：
    // 不帶 bought / starred / actual_price，created_at 讓資料庫給新的（想買 N 天要從現在算）
    const rows=picked.map(id=>{
      const s=items.find(x=>String(x.id)===String(id))||{};
      return {name:s.name, price:s.price||0, quantity:s.quantity||1, category:s.category||'其他',
              tag:s.tag||'', urgency:s.urgency||'maybe', accessibility:s.accessibility||'tw_easy',
              recurring_cost:s.recurring_cost||0, link:s.link||'', note:s.note||'',
              this_month:true, bought:false, starred:false, actual_price:null, added_by:me||''};
    });
    $('rp-go').disabled=true;
    $('rp-msg').className='rpmsg'; $('rp-msg').textContent='加入中…';
    const {error}=await sb.from('buylist_items').insert(rows);
    $('rp-go').disabled=false;
    if(error){$('rp-msg').className='rpmsg err';$('rp-msg').textContent='加入失敗：'+error.message;return;}
    $('rp-msg').textContent='';
    toggleRepeat(false);
    setStatus('已把 '+rows.length+' 樣加回待買清單','live');
  }

  // ── 動作 ──
  async function addItem(){
    if(addingItem) return;
    const name=($('bl-name').value||'').trim(); if(!name)return;
    addingItem=true;
    const rec={name, price:parseFloat($('bl-price').value)||0, urgency:addUrg, accessibility:addAcc,
      category:$('bl-cat').value||'其他', this_month:$('bl-tm').checked, bought:false,
      added_by:me||'', note:($('bl-note').value||'').trim(), link:($('bl-link').value||'').trim(),
      recurring_cost:parseFloat($('bl-recur').value)||0, quantity:parseInt($('bl-qty').value,10)||1,
      tag:($('bl-tag').value||'').trim()};
    ['bl-name','bl-price','bl-qty','bl-note','bl-link','bl-recur','bl-tag'].forEach(id=>$(id).value=''); $('bl-name').focus();
    const {error}=await sb.from('buylist_items').insert(rec);
    if(error)setStatus('新增失敗：'+error.message,'err');
    addingItem=false;
  }
  // ── 批次貼多行新增：以換行/頓號/逗號拆分，每筆只帶名稱走預設，一次 insert 陣列 ──
  let bulking=false;
  async function bulkAdd(){
    if(bulking) return;
    const raw=$('bl-bulk').value||'';
    // 分隔符：換行、頓號、半形逗號、全形逗號（可混用、連續視為一個）
    const names=raw.split(/[\n,、，]+/).map(s=>s.trim()).filter(Boolean);
    // 本次貼上內部去重（保序）；不與清單既有項目比對
    const seen=new Set(), uniq=[];
    for(const n of names){ if(!seen.has(n)){ seen.add(n); uniq.push(n); } }
    if(!uniq.length){ setStatus('沒有可新增的項目（內容是空的）','err'); return; }
    bulking=true;
    const rows=uniq.map(name=>({name, price:0, urgency:'maybe', accessibility:'tw_easy',
      category:'其他', this_month:true, bought:false, added_by:me||'', note:'', link:'', recurring_cost:0, quantity:1}));
    const {error}=await sb.from('buylist_items').insert(rows);
    if(error) setStatus('批次新增失敗：'+error.message,'err');
    else { $('bl-bulk').value=''; setStatus('已加入 '+rows.length+' 筆','live'); }
    bulking=false;
  }
  async function toggleBought(id,val){const {error}=await sb.from('buylist_items').update({bought:val}).eq('id',id);if(error)setStatus('更新失敗：'+error.message,'err');}
  async function toggleStarred(id,val){const {error}=await sb.from('buylist_items').update({starred:val}).eq('id',id);if(error)setStatus('更新失敗：'+error.message,'err');}
  // 實付寫回：空字串＝null（未填）、其餘存數字（0＝真的免費）；不影響總價加總
  async function updateActualPrice(id,val){const num=(val===''||val==null)?null:(+val||0);const {error}=await sb.from('buylist_items').update({actual_price:num}).eq('id',id);if(error)setStatus('更新失敗：'+error.message,'err');}
  async function delItem(id){const {error}=await sb.from('buylist_items').delete().eq('id',id);if(error)setStatus('刪除失敗：'+error.message,'err');}
  async function saveBudget(v){budget=+v||0;const {error}=await sb.from('buylist_budget').upsert({id:1,monthly_budget:budget});if(error)setStatus('預算儲存失敗：'+error.message,'err');}

  // ── 貼連結自動帶入：呼叫 Gemini 讀商品頁，抽出名稱+價格填進表單（不自動送出，讓使用者確認後再按加入）──
  let importing=false;
  async function importFromLink(){
    if(importing) return;
    const url=($('bl-link').value||'').trim();
    if(!url){ setStatus('請先把商品連結貼到「連結」欄','err'); $('bl-link').focus(); return; }
    if(!GEMINI_KEY){ setStatus('尚未設定 Gemini 金鑰（buylist/config.js）','err'); return; }
    importing=true;
    const btn=$('bl-import'), old=btn.textContent;
    btn.disabled=true; btn.textContent='讀取中…'; setStatus('讀取商品資訊中…','');
    try{
      const prompt='你是購物助手。請讀取這個商品網址的內容，抽出「商品名稱」與「售價」。\n網址：'+url+
        '\n只回一個 JSON 物件，不要 markdown、不要多餘文字，格式：{"name":"商品名稱（簡潔、去掉行銷贅字）","price":售價數字}。'+
        'price 請填新台幣整數；若原頁是外幣請概略換算成台幣；抓不到價格就填 0。若讀不到該頁，name 盡量從網址推斷、price 填 0。';
      const body={contents:[{parts:[{text:prompt}]}],tools:[{url_context:{}}]};
      const resp=await fetch('https://generativelanguage.googleapis.com/v1beta/models/'+GEMINI_MODEL+':generateContent?key='+encodeURIComponent(GEMINI_KEY),
        {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if(!resp.ok){ const t=await resp.text(); throw new Error('API '+resp.status+'：'+t.slice(0,120)); }
      const data=await resp.json();
      const cand=(data.candidates&&data.candidates[0])||{};
      const parts=(cand.content&&cand.content.parts)||[];
      const text=parts.map(p=>(p&&p.text)||'').join('');
      const m=text.match(/\{[\s\S]*\}/);
      if(!m) throw new Error('無法解析回應');
      const obj=JSON.parse(m[0]);
      if(obj.name) $('bl-name').value=String(obj.name).trim();
      if(+obj.price>0) $('bl-price').value=Math.round(+obj.price);
      setStatus('已帶入，請確認後按「＋ 加入」','live');
      $('bl-name').focus();
    }catch(e){
      setStatus('抓取失敗：'+e.message,'err');
    }finally{
      importing=false; btn.disabled=false; btn.textContent=old;
    }
  }

  // ── Markdown 匯出：依情境分段、匯出全部（不受篩選影響）──
  function buildMarkdown(){
    // 依 tag 分組；未分情境（空 tag）永遠放最後一段
    const groups={};
    items.forEach(i=>{ const t=(i.tag||'').trim(); (groups[t]=groups[t]||[]).push(i); });
    const named=Object.keys(groups).filter(Boolean).sort();
    const order=named.concat(groups['']?['']:[]);
    const urgLabel=u=>(URG[u]||URG.maybe).label;
    const lines=[];
    order.forEach(t=>{
      lines.push('## '+(t||'未分情境'));
      // 段內：未購在前、已買在後（已買劃線集中段尾）
      groups[t].slice().sort((a,b)=>(a.bought?1:0)-(b.bought?1:0)).forEach(i=>{
        const qty=(+i.quantity>1)?('　×'+(+i.quantity)):'';
        const nm=i.bought?('~~'+i.name+'~~'):i.name;
        lines.push('- '+nm+'　'+money(i.price)+qty+'　['+urgLabel(i.urgency)+']');
      });
      lines.push('');
    });
    const unboughtTotal=items.filter(i=>!i.bought).reduce((s,i)=>s+(+i.price||0),0);
    lines.push('> 共 '+items.length+' 項，未購合計 '+money(unboughtTotal));
    return lines.join('\n');
  }
  function exportMd(){
    if(!items.length){ setStatus('清單是空的，沒東西可匯出','err'); return; }
    const d=new Date();
    const ymd=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
    const blob=new Blob([buildMarkdown()],{type:'text/markdown;charset=utf-8'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a'); a.href=url; a.download='buylist-'+ymd+'.md';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    setStatus('已匯出 buylist-'+ymd+'.md','live');
  }

  // ══ 辣醬庫（Hot Sauce Library）— buylist 的第二個資料域，靠頂層 tab 切換 ══
  async function loadSauces(){
    const r=await sb.from('sauces').select('*').order('repurchase',{ascending:false}).order('created_at',{ascending:false});
    if(r.error){setStatus('辣醬讀取失敗：'+r.error.message,'err');return;}
    sauces=r.data||[]; renderSauces();
  }
  function renderSauces(){
    const box=$('sc-list'); const kw=scSearch.trim().toLowerCase();
    const arr=sauces.filter(s=>!kw || String(s.name||'').toLowerCase().includes(kw));
    if(!arr.length){box.innerHTML='<div class="empty">'+(kw?'沒有符合的辣醬。':'還沒有辣醬。<br>上面加一瓶吧。')+'</div>';return;}
    box.innerHTML=arr.map(s=>{
      const meta=SDIMS.map(d=>'<span class="rd'+(d.k==='repurchase'?' key':'')+'">'+d.label+' <b>'+(+s[d.k]||0)+'</b>★</span>').join('');
      const bits=[];
      if(s.url) bits.push('<a href="'+esc(s.url)+'" target="_blank" rel="noopener">🔗 連結</a>');
      if(s.added_by) bits.push(esc(s.added_by)+' 加的');
      return '<div class="item"><div class="ibody">'
        +'<div class="itop"><span class="iname">'+esc(s.name)+'</span></div>'
        +'<div class="scmeta">'+meta+'</div>'
        +(bits.length?'<div class="imeta">'+bits.join('　')+'</div>':'')
        +'</div><button class="idel" data-scdel="'+s.id+'" title="刪除">✕</button></div>';
    }).join('');
    box.querySelectorAll('.idel').forEach(b=>b.addEventListener('click',()=>delSauce(b.dataset.scdel)));
  }
  // 新增表單的星級選擇器（反映 newSauce；點第 n 顆 = 設該維度為 n）
  function renderRatingPicker(){
    $('sc-ratings').innerHTML=SDIMS.map(d=>{
      const v=newSauce[d.k]||0;
      const stars=[1,2,3,4,5].map(n=>'<span class="st'+(n<=v?' on':'')+'" data-dim="'+d.k+'" data-n="'+n+'">★</span>').join('');
      return '<div class="ratingrow"><span class="rlabel">'+d.label+'</span><span class="stars">'+stars+'</span></div>';
    }).join('');
  }
  async function addSauce(){
    const name=($('sc-name').value||'').trim();
    if(!name){setStatus('辣醬名稱必填','err');$('sc-name').focus();return;}
    if(SDIMS.some(d=>!newSauce[d.k])){setStatus('4 個評分都要選（1–5 星）','err');return;}
    const rec={name, url:($('sc-url').value||'').trim(), spiciness:newSauce.spiciness,
      aroma:newSauce.aroma, cp:newSauce.cp, repurchase:newSauce.repurchase, added_by:me||''};
    const {error}=await sb.from('sauces').insert(rec);
    if(error){setStatus('辣醬新增失敗：'+error.message,'err');return;}
    $('sc-name').value=''; $('sc-url').value=''; newSauce={spiciness:0,aroma:0,cp:0,repurchase:0}; renderRatingPicker();
    setStatus('已加入辣醬','live'); $('sc-name').focus();
  }
  async function delSauce(id){const {error}=await sb.from('sauces').delete().eq('id',id);if(error)setStatus('辣醬刪除失敗：'+error.message,'err');}
  function switchTab(t){
    activeTab=t;
    document.querySelectorAll('#apptabs button').forEach(x=>x.classList.toggle('on',x.dataset.tab===t));
    $('tab-buy').classList.toggle('hidden',t!=='buy');
    $('tab-sauce').classList.toggle('hidden',t!=='sauce');
    $('appTitle').textContent = t==='sauce' ? '辣醬庫' : '買物清單';
  }

  // ── 事件 ──
  $('bl-add').addEventListener('click',addItem);
  $('bl-export').addEventListener('click',exportMd);
  $('bl-bulk-add').addEventListener('click',bulkAdd);
  $('bl-import').addEventListener('click',importFromLink);
  $('bl-name').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.isComposing){e.preventDefault();addItem();}});
  $('seg-urg').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;addUrg=b.dataset.v;$('seg-urg').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));});
  $('seg-acc').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;addAcc=b.dataset.v;$('seg-acc').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));});
  $('bl-budget').addEventListener('change',e=>saveBudget(e.target.value));
  $('bl-budget').addEventListener('keydown',e=>{if(e.key==='Enter')e.target.blur();});
  $('whoSel').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;me=b.dataset.me;localStorage.setItem('buylist_me',me);renderWho();});
  // 篩選改變時兩個清單檢視都要重畫（使用者可能正看著分類檢視）
  function refreshLists(){renderList();renderCatGroups();}
  $('f-status').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;fStatus=b.dataset.v;$('f-status').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));refreshLists();});
  $('f-cat').addEventListener('change',e=>{fCat=e.target.value;refreshLists();});
  $('f-tag').addEventListener('change',e=>{fTag=e.target.value;refreshLists();});
  $('f-sort').addEventListener('change',e=>{fSort=e.target.value;refreshLists();});
  // 邊打邊篩。中文輸入法組字中不要觸發，否則注音還沒選字就先把清單清空
  $('bl-search').addEventListener('input',e=>{if(e.isComposing)return;fSearch=e.target.value;refreshLists();});
  $('bl-search').addEventListener('compositionend',e=>{fSearch=e.target.value;refreshLists();});
  $('viewtabs').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;view=b.dataset.view;
    document.querySelectorAll('#viewtabs button').forEach(x=>x.classList.toggle('on',x===b));
    $('view-list').classList.toggle('hidden',view!=='list');
    $('view-cat').classList.toggle('hidden',view!=='cat');
    $('view-matrix').classList.toggle('hidden',view!=='matrix');});
  $('bl-repeat').addEventListener('click',()=>toggleRepeat($('repeat-box').classList.contains('hidden')));
  $('rp-cancel').addEventListener('click',()=>toggleRepeat(false));
  $('rp-go').addEventListener('click',repeatAdd);
  // 辣醬庫事件
  $('apptabs').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;switchTab(b.dataset.tab);});
  $('sc-add').addEventListener('click',addSauce);
  $('sc-name').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.isComposing){e.preventDefault();addSauce();}});
  $('sc-search').addEventListener('input',e=>{scSearch=e.target.value;renderSauces();});
  $('sc-ratings').addEventListener('click',e=>{const st=e.target.closest('.st');if(!st)return;newSauce[st.dataset.dim]=+st.dataset.n;renderRatingPicker();});

  // ── 即時訂閱 ──
  sb.channel('buylist-all')
    .on('postgres_changes',{event:'*',schema:'public',table:'buylist_items'},loadAll)
    .on('postgres_changes',{event:'*',schema:'public',table:'buylist_budget'},loadAll)
    .on('postgres_changes',{event:'*',schema:'public',table:'sauces'},loadSauces)
    .subscribe(st=>{ if(st==='SUBSCRIBED')setStatus('即時同步已連線','live'); else if(st==='CHANNEL_ERROR'||st==='TIMED_OUT')setStatus('即時連線異常：'+st,'err'); });

  // 沒設 Gemini 金鑰（如公開部署不帶 config.js）→ 隱藏「貼連結帶入」，金鑰不外洩、按鈕也不留死路
  if(!GEMINI_KEY) $('bl-import').style.display='none';
  renderRatingPicker(); renderWho(); loadAll(); loadSauces();
})();