"""行程表的前端 JS——移植自參考產品 `trips/_reference/body2.part` 末尾的三段 IIFE。

三段各自獨立、互不相依：
    1. 勾選狀態存 localStorage（出發前待確認打勾之後，關掉再開還在）
    2. 手機版表格轉卡片時，把 thead 的欄位名寫進 td[data-l]
    3. 主 tab／子 tab 切換，狀態也存 localStorage
    4. 示意地圖（資料與繪製分離，資料由 Python 端算好塞進 MAPDATA）

與參考產品的差異只有兩處，都是刻意的：
  * **地圖只保留「每日路線」模式。** 參考產品的「排隊候補」模式可以點卡片跳到地圖位置，
    那段互動本次延後（規格的延後清單第四項），候補清單本身仍然在。
  * **資料全部來自 MAPDATA**，不再是手寫的 P{} / DAYS{}。換城市只要換 trip.json。

這裡不能出現 fetch / XMLHttpRequest / 外部 script——自含單檔、斷網可開是硬需求（A9）。
localStorage 的 key 用 page_slug 前綴，不同旅程不會互相蓋掉。
"""

JS = r"""
(function(){
  // ── 1. 勾選狀態 ──
  var KEY = MAPDATA.slug + '-checks';
  function load(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')||{};}catch(e){return {};}}
  function save(v){try{localStorage.setItem(KEY,JSON.stringify(v));}catch(e){}}
  var checks = load();
  document.querySelectorAll('.check input').forEach(function(box){
    if(checks[box.id]) box.checked = true;
    box.addEventListener('change',function(){checks[box.id]=box.checked;save(checks);});
  });
})();

(function(){
  // ── 2. 手機版表格轉卡片時要有欄位名 ──
  document.querySelectorAll('.tbl.stack table').forEach(function(tb){
    var hs = [].map.call(tb.querySelectorAll('thead th'),function(h){return h.textContent;});
    tb.querySelectorAll('tbody tr').forEach(function(tr){
      [].forEach.call(tr.children,function(c,i){ if(hs[i]) c.setAttribute('data-l',hs[i]); });
    });
  });
})();

(function(){
  // ── 4. 示意地圖 ──
  // 示意圖，不是真地圖磚：真地圖磚要連網，與「斷網可開」衝突（規格 Q5）。
  // 畫布固定 1000x640，不隨天數縮放——縮放過的圖在不同日期之間無法比對。
  var svg = document.getElementById('map-svg'); if(!svg || !MAPDATA.order.length) return;
  var box = svg.parentNode, sec = document.getElementById('mapsec');
  var NS = 'http://www.w3.org/2000/svg';
  var pj = MAPDATA.proj;
  function X(lon){ return (lon-pj.lon0)/(pj.lon1-pj.lon0)*1000; }
  function Y(lat){ return (pj.lat1-lat)/(pj.lat1-pj.lat0)*640; }
  function el(n,a,p){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e;}

  if(MAPDATA.river && MAPDATA.river.length>1){
    el('path',{d:'M'+MAPDATA.river.map(function(p){return X(p[1]).toFixed(1)+' '+Y(p[0]).toFixed(1);}).join(' L'),class:'river'});
  }

  var P = MAPDATA.P, DAYS = MAPDATA.DAYS, order = MAPDATA.order;
  var gLines = el('g',{}), gPts = el('g',{});
  order.forEach(function(d,i){
    // 每天的折線各偏移一點，不然共用路段會完全疊在一起看不出有幾條
    var off = (i-(order.length-1)/2)*3.2;
    var pts = DAYS[d].r.map(function(k){ return [X(P[k].lon)+off, Y(P[k].lat)+off]; });
    DAYS[d].line = el('polyline',{
      points: pts.map(function(p){return p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' '),
      class:'route-line', style:'stroke:'+DAYS[d].c}, gLines);
  });

  var LC = MAPDATA.lineColors || {};
  function tw(s){var w=0;for(var i=0;i<s.length;i++)w+=s.charCodeAt(i)>255?12.5:6.8;return w;}
  var gSeg = el('g',{});
  order.forEach(function(d,i){
    var off=(i-(order.length-1)/2)*3.2, g=el('g',{class:'seg'},gSeg);
    DAYS[d].seg_g = g; g.style.display='none';
    (DAYS[d].seg||[]).forEach(function(sg,j){
      if(!sg) return;
      var a=P[DAYS[d].r[j]], b=P[DAYS[d].r[j+1]];
      if(!a||!b) return;
      var tt = (sg.t==null?0.5:sg.t);
      var ax=X(a.lon)+(X(b.lon)-X(a.lon))*tt+off, ay=Y(a.lat)+(Y(b.lat)-Y(a.lat))*tt+off;
      var cx=ax+(sg.dx||0), cy=ay+(sg.dy||0);
      // 標籤被推得太遠就畫一條引線回去，不然看不出它在講哪一段
      if(Math.abs(cx-ax)+Math.abs(cy-ay)>18){
        el('line',{x1:ax,y1:ay,x2:cx,y2:cy,class:'leader',style:'stroke:'+DAYS[d].c},g);
        el('circle',{cx:ax,cy:ay,r:3,style:'fill:'+DAYS[d].c},g);
      }
      var lines = sg.l||[], H=22;
      var w = lines.length*19 + (lines.length?4:0) + tw(sg.m||'') + 14;
      var h = H+4, x0=cx-w/2, y0=cy-h/2;
      el('rect',{x:x0,y:y0,width:w,height:h,rx:8,class:'segbox',style:'stroke:'+DAYS[d].c},g);
      var x=x0+7, y=y0+2+H/2;
      lines.forEach(function(n){
        var c = LC[n] || ['#888','#fff'];
        el('circle',{cx:x+8,cy:y,r:8.5,fill:c[0]},g);
        var ct=el('text',{x:x+8,y:y+3.8,'text-anchor':'middle',class:'segchip',fill:c[1]},g);
        ct.textContent=n; x+=19;
      });
      if(lines.length) x+=4;
      var mt=el('text',{x:x,y:y+4.2,class:'segtxt'},g); mt.textContent=sg.m||'';
    });
  });

  Object.keys(P).forEach(function(k){
    var p=P[k], x=X(p.lon), y=Y(p.lat), pg=el('g',{class:'pg'},gPts); p.g=pg;
    el('circle',{cx:x,cy:y,r:p.home?9:6.5,class:p.home?'pt home':'pt'},pg);
    var t=el('text',{x:x+p.dx,y:y+p.dy,'text-anchor':p.a,class:'plabel'},pg); t.textContent=p.n;
    if(p.s){ var s=el('text',{x:x+p.dx,y:y+p.dy+15,'text-anchor':p.a,class:'plabel sub'},pg); s.textContent=p.s; }
  });
  svg.appendChild(gSeg);

  var day='all', sc=1, sized=false;
  function fit(){
    var cw=box.clientWidth; if(!cw) return;
    sc=Math.min(cw/1000,1); if(cw<620) sc=Math.max(sc,0.72);
    svg.setAttribute('viewBox','0 0 1000 640');
    svg.style.width=(1000*sc)+'px'; svg.style.height=(640*sc)+'px';
    if(!sized && MAPDATA.home){ sized=true; center(X(MAPDATA.home[1]),Y(MAPDATA.home[0])); }
  }
  function center(x,y,smooth){
    var l=x*sc-box.clientWidth/2, tp=y*sc-box.clientHeight/2;
    if(box.scrollTo) box.scrollTo({left:l,top:tp,behavior:smooth?'smooth':'auto'});
    else {box.scrollLeft=l;box.scrollTop=tp;}
  }
  // 選了某一天之後，把畫面移到那天的路線中心。
  // 沒有這一步的話，畫布固定 1000x640、手機只看得到一小塊，
  // 點了日期還得自己左右滑去找那條線——那等於這個篩選沒有用。
  function centerOnDay(d){
    if(d==='all'){ if(MAPDATA.home) center(X(MAPDATA.home[1]),Y(MAPDATA.home[0]),true); return; }
    var xs=[], ys=[];
    DAYS[d].r.forEach(function(k){ if(P[k]){ xs.push(X(P[k].lon)); ys.push(Y(P[k].lat)); } });
    if(!xs.length) return;
    center((Math.min.apply(null,xs)+Math.max.apply(null,xs))/2,
           (Math.min.apply(null,ys)+Math.max.apply(null,ys))/2, true);
  }
  var legsBox=document.getElementById('map-legs');
  function show(d){
    day=d;
    order.forEach(function(k){
      DAYS[k].line.style.opacity=(d==='all'||d===k)?'1':'0.08';
      DAYS[k].seg_g.style.display=(d===k)?'':'none';
    });
    Object.keys(P).forEach(function(k){
      P[k].g.style.opacity=(d==='all'||DAYS[d].r.indexOf(k)>=0)?'1':'0.22';
    });
    document.querySelectorAll('.dayfilter button').forEach(function(b){
      b.setAttribute('aria-pressed', b.dataset.day===d?'true':'false');
    });
    var list=(d==='all')?order:[d], html='';
    list.forEach(function(k){
      html += '<div class="leg"><h3><i style="background:'+DAYS[k].c+'"></i>'+esc(DAYS[k].label)+'</h3><ol>'
           + DAYS[k].legs.map(function(s){return '<li>'+esc(s)+'</li>';}).join('') + '</ol></div>';
    });
    legsBox.innerHTML=html;
    fit();
  }
  function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  document.querySelectorAll('.dayfilter button').forEach(function(b){
    // 只有「使用者自己點的」才移動畫面。初次載入不移動，
    // 不然一進地圖分頁就自己捲一下，會像壞掉。
    b.addEventListener('click',function(){show(b.dataset.day);centerOnDay(b.dataset.day);});
  });
  var rz; window.addEventListener('resize',function(){clearTimeout(rz);rz=setTimeout(function(){sized=false;fit();},150);});
  window.mapFit=fit;
  show('all');
})();

(function(){
  // ── 3. tab 切換（放最後，因為它要呼叫地圖的 mapFit）──
  var tabs=document.querySelectorAll('.tabs button');
  var panels={};
  tabs.forEach(function(b){ panels[b.dataset.tab]=document.getElementById('tab-'+b.dataset.tab); });
  var bar=document.querySelector('.tabs');
  function sticky(){document.documentElement.style.setProperty('--tabs-h',bar.offsetHeight+'px');}
  function go(k,scroll){
    Object.keys(panels).forEach(function(p){ if(panels[p]) panels[p].hidden=(p!==k); });
    tabs.forEach(function(b){b.setAttribute('aria-selected',b.dataset.tab===k?'true':'false');});
    try{localStorage.setItem(MAPDATA.slug+'-tab',k);}catch(e){}
    if(k==='map'&&window.mapFit) window.mapFit();
    if(scroll){var top=bar.getBoundingClientRect().top+window.scrollY; if(window.scrollY>top) window.scrollTo(0,top);}
  }
  tabs.forEach(function(b){b.addEventListener('click',function(){go(b.dataset.tab,true);});});

  var more=panels.more;
  if(more){
    var subs=more.querySelectorAll('.subtabs button');
    function sub(k){
      subs.forEach(function(b){b.setAttribute('aria-selected',b.dataset.sub===k?'true':'false');});
      more.querySelectorAll('section.block').forEach(function(s){s.hidden=(s.id!==k);});
      try{localStorage.setItem(MAPDATA.slug+'-more',k);}catch(e){}
    }
    subs.forEach(function(b){b.addEventListener('click',function(){sub(b.dataset.sub);});});
    var s0=subs.length?subs[0].dataset.sub:null;
    try{ var saved=localStorage.getItem(MAPDATA.slug+'-more'); if(saved&&more.querySelector('#'+CSS.escape(saved))) s0=saved; }catch(e){}
    if(s0) sub(s0);
  }

  var t0='plan'; try{t0=localStorage.getItem(MAPDATA.slug+'-tab')||'plan';}catch(e){}
  sticky(); window.addEventListener('resize',sticky);
  go(panels[t0]?t0:'plan',false);
})();
"""
