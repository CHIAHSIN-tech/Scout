"""行程表的 CSS——原封不動移植自參考產品 `trips/_reference/head3.part`。

**刻意不重寫。** 那份 CSS 是上一趟首爾行程手改 45 版改出來的，
包含手機版表格轉卡片、時間軸 grid、地鐵線號徽章、深淺色主題這些已經在真手機上
survive 過的細節。重寫等於把那 45 版的經驗丟掉。

移植時只改了一件事：**拿掉 Google Fonts**。外部字體檔要連網，
會破壞「斷網也能開」（A9），所以字體改成系統既有的字堆。
檔案末尾另外加了本模組才有的幾個類別（有註解標出來）。
"""

CSS = r""":root{
  --ground:#F3F4F7; --surface:#FFFFFF; --ink:#18202E; --muted:#5A6376; --faint:#8A92A3;
  --line:#DCE0E8; --accent:#2F4A8A; --accent-soft:#E6EBF6;
  --moon:#9A6F12; --moon-disc:#D9A93A; --moon-soft:#F6EDD5;
  --warn:#9B3B1E; --warn-soft:#F8E6DF; --ok:#2E6B45; --ok-soft:#E3F0E7;
  /* 字體只用系統既有的：外部字體檔＝要連網，會破壞「斷網可開」（A9）。
     每一族都從最可能存在的排到最後的通用 fallback，三個平台都吃得到。 */
  --serif:"Noto Serif TC","Songti TC","PMingLiU","Source Han Serif TC",serif;
  --sans:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,-apple-system,sans-serif;
  --mono:ui-monospace,"SFMono-Regular",Menlo,Consolas,"Courier New",monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#0F121A; --surface:#171B25; --ink:#E7E9EF; --muted:#A0A8B8; --faint:#6F7788;
    --line:#2A303D; --accent:#98ACE8; --accent-soft:#1D2438;
    --moon:#E6C063; --moon-disc:#E6C063; --moon-soft:#2A2415;
    --warn:#F0A58A; --warn-soft:#2E1C16; --ok:#8FD1A6; --ok-soft:#18291F;
  }
}
:root[data-theme="dark"]{
  --ground:#0F121A; --surface:#171B25; --ink:#E7E9EF; --muted:#A0A8B8; --faint:#6F7788;
  --line:#2A303D; --accent:#98ACE8; --accent-soft:#1D2438;
  --moon:#E6C063; --moon-disc:#E6C063; --moon-soft:#2A2415;
  --warn:#F0A58A; --warn-soft:#2E1C16; --ok:#8FD1A6; --ok-soft:#18291F;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:4.5rem}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.7;padding-inline:16px;padding-block:0 4rem}
.wrap{max-width:780px;margin-inline:auto}
a{color:var(--accent);text-underline-offset:3px}
a:focus-visible,input:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
h1,h2,h3{text-wrap:balance;margin:0}
p{margin:0}

/* header */
header{padding-block:2.5rem 1.5rem;display:grid;gap:1.25rem}
.eyebrow{font-size:.78rem;letter-spacing:.12em;color:var(--muted);display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}
.eyebrow b{font-weight:500;color:var(--moon)}
h1{font-family:var(--serif);font-weight:900;font-size:clamp(2.2rem,7vw,3.4rem);line-height:1.1;letter-spacing:.02em}
h1 .moon{display:inline-block;width:.62em;height:.62em;border-radius:50%;background:var(--moon-disc);vertical-align:.08em;margin-left:.2em;box-shadow:0 0 0 .12em var(--moon-soft)}
.lede{color:var(--muted);max-width:40em}
.flights{display:grid;gap:0;background:var(--surface);border:1px solid var(--line);border-radius:10px}
.flight{display:grid;grid-template-columns:4.5rem 1fr auto;gap:.75rem;align-items:center;padding:.8rem 1rem}
.flight+.flight{border-top:1px dashed var(--line)}
.flight .d{font-family:var(--mono);font-size:.8rem;color:var(--muted);line-height:1.3}
.flight .d strong{display:block;color:var(--ink);font-size:1rem}
.flight .r{font-family:var(--mono);font-weight:600;font-size:1.05rem;letter-spacing:.04em;display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
.flight .r i{font-style:normal;color:var(--faint);font-weight:500}
.flight .t{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right;font-size:.95rem}
.flight .t sup{color:var(--warn);font-size:.65em}
.flight .note{grid-column:2/-1;font-size:.8rem;color:var(--muted);margin-top:-.4rem}

/* day nav */
nav.days{position:sticky;top:var(--tabs-h,0px);z-index:5;background:var(--ground);margin-inline:-16px;padding:.6rem 16px;border-bottom:1px solid var(--line);overflow-x:auto}
nav.days ul{list-style:none;margin:0 auto;padding:0;display:flex;gap:.4rem;max-width:780px}
nav.days a{display:flex;align-items:center;gap:.35rem;white-space:nowrap;text-decoration:none;color:var(--ink);font-size:.85rem;padding:.3rem .7rem;border:1px solid var(--line);border-radius:999px;background:var(--surface)}
nav.days a span{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:600}
nav.days a .mdot{width:.55rem;height:.55rem;border-radius:50%;background:var(--moon-disc)}

/* briefing */
.brief{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-block:1.75rem 0}
@media (max-width:640px){.brief{grid-template-columns:1fr}}
.panel{border-radius:10px;padding:1rem 1.1rem;display:grid;gap:.55rem;align-content:start}
.panel h2{font-family:var(--serif);font-weight:600;font-size:1.1rem;display:flex;align-items:center;gap:.5rem}
.panel ul{margin:0;padding-left:1.1rem;display:grid;gap:.3rem;font-size:.9rem}
.panel.moon{background:var(--moon-soft)}
.panel.moon h2 .mdot{width:.8rem;height:.8rem;border-radius:50%;background:var(--moon-disc)}
.panel.stay{background:var(--surface);border:1px solid var(--line)}
.panel .sub{font-size:.8rem;color:var(--muted)}

/* day */
section.day{margin-top:3rem}
.dayhead{display:grid;grid-template-columns:auto 1fr;gap:.2rem 1rem;align-items:end;padding-bottom:.8rem;border-bottom:2px solid var(--ink)}
.date{font-family:var(--mono);font-weight:600;font-size:2.4rem;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.date small{display:block;font-size:.72rem;font-weight:500;letter-spacing:.1em;color:var(--muted);margin-bottom:.35rem}
.dayhead h2{font-family:var(--serif);font-weight:900;font-size:clamp(1.3rem,4.2vw,1.7rem);line-height:1.25}
.dayhead .tags{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}
.chip{font-size:.75rem;padding:.1rem .55rem;border-radius:999px;border:1px solid var(--line);color:var(--muted);background:var(--surface);white-space:nowrap}
.chip.moon{border-color:transparent;background:var(--moon-soft);color:var(--moon);font-weight:500}
.chip.sun{border-color:transparent;background:var(--warn-soft);color:var(--warn);font-weight:500}

ol.tl{list-style:none;margin:0;padding:0}
ol.tl>li{display:grid;grid-template-columns:3.6rem 1fr;gap:0 .9rem}
ol.tl time{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:.85rem;font-weight:600;padding-top:1rem;text-align:right;color:var(--ink)}
ol.tl .b{border-left:1px solid var(--line);padding:1rem 0 .9rem 1.1rem;position:relative;display:grid;gap:.3rem;min-width:0}
ol.tl .b::before{content:"";position:absolute;left:-5px;top:1.35rem;width:9px;height:9px;border-radius:50%;background:var(--surface);border:2px solid var(--accent)}
ol.tl li.mv time{color:var(--faint);font-weight:500}
ol.tl li.mv .b{padding-block:.55rem}
ol.tl .b.route{display:flex;flex-wrap:wrap;align-items:center;gap:.3rem .4rem}
ol.tl li.mv .b::before{width:5px;height:5px;left:-3px;top:1rem;border:0;background:var(--faint)}
ol.tl li.hi .b::before{background:var(--accent)}
ol.tl li.sunset .b::before{background:var(--moon-disc);border-color:var(--moon-disc)}
ol.tl h3{font-size:1rem;font-weight:700;line-height:1.45;display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem .5rem}
ol.tl h3 .ko{font-weight:400;font-size:.8rem;color:var(--muted)}
.b p{color:var(--muted);font-size:.9rem;max-width:36em}
.b .links{display:flex;flex-wrap:wrap;gap:.3rem .9rem;font-size:.8rem}
.pick{font-size:.68rem;font-weight:500;letter-spacing:.06em;padding:0 .4rem;border-radius:4px;background:var(--accent-soft);color:var(--accent);align-self:center}
.pick.rec{background:transparent;border:1px solid var(--line);color:var(--muted)}
.route{font-size:.85rem;color:var(--muted);display:flex;flex-wrap:wrap;align-items:center;gap:.3rem .35rem}
.ln{display:inline-grid;place-items:center;min-width:1.35rem;height:1.35rem;padding:0 .3rem;border-radius:999px;background:var(--c);color:#fff;font-family:var(--mono);font-size:.7rem;font-weight:600;line-height:1}
.ln.dk{color:#1a1a1a}
.alt{margin-top:.2rem;font-size:.85rem;border:1px dashed var(--line);border-radius:8px;padding:.6rem .8rem;color:var(--muted);display:grid;gap:.25rem}
.alt strong{color:var(--ink);font-weight:500}
.warnbox{background:var(--warn-soft);color:var(--ink);border-radius:8px;padding:.6rem .8rem;font-size:.85rem}
.warnbox b{color:var(--warn)}

/* checklist + more */
section.block{margin-top:3.5rem;display:grid;gap:1rem}
section.block>h2{font-family:var(--serif);font-weight:900;font-size:1.5rem;padding-bottom:.6rem;border-bottom:2px solid var(--ink)}
.check{list-style:none;margin:0;padding:0;display:grid;gap:0;background:var(--surface);border:1px solid var(--line);border-radius:10px}
.check li+li{border-top:1px solid var(--line)}
.check label{display:grid;grid-template-columns:1.2rem 1fr;gap:.7rem;padding:.7rem 1rem;cursor:pointer;align-items:start}
.check input{width:1.05rem;height:1.05rem;margin-top:.3rem;accent-color:var(--accent)}
.check span{font-size:.92rem}
.check small{display:block;color:var(--muted);font-size:.8rem}
.check input:checked+span{color:var(--faint);text-decoration:line-through}
.more{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.75rem}
.more div{padding:.8rem .9rem;border:1px solid var(--line);border-radius:10px;background:var(--surface);display:grid;gap:.2rem;align-content:start}
.more h3{font-size:.95rem;font-weight:700}
.more p{font-size:.84rem;color:var(--muted)}
.more .fit{font-size:.75rem;color:var(--accent)}
footer{margin-top:3rem;font-size:.78rem;color:var(--faint);display:grid;gap:.4rem}
footer ul{margin:0;padding-left:1rem}

/* dining */
.dining{margin-top:2rem;display:grid;gap:.8rem}
.dining h2{font-family:var(--serif);font-weight:900;font-size:1.5rem;padding-bottom:.6rem;border-bottom:2px solid var(--ink)}
.dining .lede2{color:var(--muted);font-size:.9rem;max-width:42em}
.legend{display:flex;flex-wrap:wrap;gap:.4rem .9rem;font-size:.8rem;color:var(--muted);align-items:center}
.summary{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:0 1.25rem;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.4rem 1rem}
.summary li{display:flex;justify-content:space-between;gap:.75rem;padding:.45rem 0;border-bottom:1px dashed var(--line);font-size:.88rem}
.summary a{font-family:var(--mono);font-size:.8rem;font-weight:600;color:var(--ink);text-decoration:none;white-space:nowrap}
.summary .chosen{color:var(--faint);text-align:right;min-width:0}
.summary .chosen.on{color:var(--accent);font-weight:500}
.reset{justify-self:start;font:inherit;font-size:.8rem;color:var(--muted);background:none;border:1px solid var(--line);border-radius:999px;padding:.2rem .8rem;cursor:pointer}
.rs{font-size:.7rem;font-weight:500;padding:.05rem .45rem;border-radius:4px;white-space:nowrap}
.rs.walkin{background:var(--ok-soft);color:var(--ok)}
.rs.advance{background:var(--accent-soft);color:var(--accent)}
.rs.hard{background:var(--warn-soft);color:var(--warn)}
.rs.unknown{background:transparent;border:1px solid var(--line);color:var(--muted)}
ol.tl li.meal .b::before{background:var(--ok);border-color:var(--ok)}
ol.tl li.meal time{color:var(--ok)}
.opts{display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:.6rem;margin-top:.4rem}
.opt{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.7rem .8rem;display:grid;gap:.2rem;align-content:start}
.opt:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.oh{display:flex;justify-content:space-between;align-items:baseline;gap:.5rem}
.oh strong{font-size:.95rem;line-height:1.35}
.opt .meta{font-size:.78rem;color:var(--muted);line-height:1.5}
.opt .fit{font-size:.84rem;color:var(--ink);margin-top:.2rem;line-height:1.6}
.of{display:flex;justify-content:space-between;align-items:center;gap:.5rem;margin-top:.35rem;padding-top:.45rem;border-top:1px dashed var(--line);flex-wrap:wrap}
.of .links{display:flex;gap:.8rem;font-size:.8rem}
.choose{display:inline-flex;align-items:center;gap:.3rem;font-size:.8rem;cursor:pointer;color:var(--muted)}
.choose input{accent-color:var(--accent);margin:0}
.opt:has(input:checked) .choose{color:var(--accent);font-weight:500}
.skip{font-size:.85rem;color:var(--muted);display:grid;gap:.3rem;margin:0;padding-left:1.1rem}
.skip b{color:var(--ink);font-weight:500}

.bd{font-family:var(--sans);font-size:.68rem;letter-spacing:.08em;color:var(--ink);border:1px solid var(--line);border-radius:4px;padding:0 .35rem;white-space:nowrap}
.tags2{display:inline-flex;gap:.3rem;flex-wrap:wrap;justify-content:flex-end}
.recmark{font-size:.68rem;font-weight:600;color:var(--surface);background:var(--accent);border-radius:4px;padding:.05rem .4rem;white-space:nowrap}
.opt.rec{border-color:var(--accent)}
.opt.fixed{background:var(--accent-soft);border-color:transparent}
.opt.fixed.try{background:var(--surface);border:1px dashed var(--accent)}
.st{color:var(--accent);font-weight:700}
.tbl{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}
.tbl table{border-collapse:collapse;width:100%;font-size:.86rem}
.tbl th,.tbl td{padding:.5rem .75rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.tbl tr:last-child th,.tbl tr:last-child td{border-bottom:0}
.tbl thead th{font-size:.72rem;letter-spacing:.08em;color:var(--muted);font-weight:500;white-space:nowrap}
.tbl th[scope=row]{font-family:var(--mono);font-size:.8rem;white-space:nowrap}
.tbl th[scope=row] a{color:var(--accent)}
.tbl small{display:block;color:var(--faint);font-size:.75rem}
.tbl .num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.tbl .bdc{font-family:var(--sans);letter-spacing:.06em;white-space:nowrap}
.tbl .need{color:var(--warn);font-weight:600}
.tbl td.chosen{color:var(--faint)}
.tbl td.chosen.on{color:var(--accent);font-weight:500}
.h2sub{font-family:var(--serif);font-weight:600;font-size:1.05rem;margin-top:.6rem}
.hotel{font-size:.7rem;font-weight:600;padding:0 .35rem;border-radius:4px;background:var(--moon-soft);color:var(--moon);white-space:nowrap}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.7rem}
.cards .opt .fit{font-size:.83rem}
.qa{display:grid;gap:.8rem;max-width:44em}
.qa h3{font-size:1rem;font-weight:700}
.qa p,.qa li{font-size:.9rem;color:var(--ink)}
.qa ul{margin:0;padding-left:1.1rem;display:grid;gap:.3rem}
.qa .src{font-size:.78rem;color:var(--faint)}
.route .hv{flex-basis:100%;display:flex;flex-wrap:wrap;align-items:center;gap:.3rem .35rem}
.crab{font-size:.68rem;font-weight:600;color:var(--warn);background:var(--warn-soft);border-radius:4px;padding:.05rem .4rem;white-space:nowrap}

:root{--d1:#2F6FBA;--d2:#C2452D;--d3:#2E8B57;--d4:#8A55C4;--d5:#B07A0E;--river:#BFD4EA}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--d1:#7FB0F0;--d2:#F08A73;--d3:#6FCF97;--d4:#C4A1F0;--d5:#E6C063;--river:#23364D}}
:root[data-theme="dark"]{--d1:#7FB0F0;--d2:#F08A73;--d3:#6FCF97;--d4:#C4A1F0;--d5:#E6C063;--river:#23364D}
.tabs{display:flex;gap:.4rem;position:sticky;top:0;z-index:6;background:var(--ground);margin-inline:-16px;padding:.55rem 16px}
.tabs button{font:inherit;font-size:.95rem;font-weight:700;padding:.45rem 1.1rem;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--muted);cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--ink);color:var(--ground);border-color:var(--ink)}
.dayfilter{display:flex;flex-wrap:wrap;gap:.4rem}
.dayfilter button{font:inherit;font-size:.82rem;display:inline-flex;align-items:center;gap:.35rem;padding:.25rem .7rem;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.dayfilter button[aria-pressed="true"]{border-color:var(--ink);box-shadow:0 0 0 1px var(--ink)}
.dayfilter i,.leg h3 i{display:inline-block;width:.7rem;height:.25rem;border-radius:2px}
.mapbox{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}
#map-svg{display:block;margin-inline:auto;max-width:none}
#map-svg .river{fill:none;stroke:var(--river);stroke-width:26;stroke-linecap:round;stroke-linejoin:round}
#map-svg .rlabel{fill:var(--muted);font-size:14px;font-style:italic}
#map-svg .route-line{fill:none;stroke-width:3.5;stroke-linejoin:round;stroke-linecap:round;transition:opacity .2s}
#map-svg .air{stroke:var(--faint);stroke-width:2;stroke-dasharray:6 5}
#map-svg .pt{fill:var(--surface);stroke:var(--ink);stroke-width:2.5}
#map-svg .pt.home{fill:var(--ink)}
#map-svg .plabel{fill:var(--ink);font-size:14px;font-weight:700;paint-order:stroke;stroke:var(--surface);stroke-width:4px}
#map-svg .pg{transition:opacity .2s}
#map-svg .leader{stroke-width:1.5;stroke-dasharray:3 3}
#map-svg .segbox{fill:var(--surface);stroke-width:2}
#map-svg .segchip{font-size:10.5px;font-weight:700;font-family:var(--mono)}
#map-svg .segtxt{fill:var(--ink);font-size:12px;font-weight:700}
#map-svg .plabel.sub{fill:var(--muted);font-size:11.5px;font-weight:500}
.legs{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:.8rem}
.leg{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.7rem .9rem}
.leg h3{font-family:var(--mono);font-size:.9rem;display:flex;align-items:center;gap:.4rem}
.leg ol{margin:.4rem 0 0;padding-left:1.1rem;display:grid;gap:.25rem;font-size:.84rem;color:var(--ink)}
td.lines{white-space:nowrap}
td.lines .ln{margin-right:.2rem}
@media (prefers-reduced-motion:reduce){#map-svg .route-line{transition:none}}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.subtabs{display:flex;gap:0;margin:.2rem 0 1rem;border:1px solid var(--line);border-radius:10px;padding:3px;background:var(--surface);width:max-content;max-width:100%}
.subtabs button{font:inherit;font-size:.9rem;font-weight:600;padding:.4rem 1rem;border:0;border-radius:7px;background:transparent;color:var(--muted);cursor:pointer;white-space:nowrap}
.subtabs button[aria-selected="true"]{background:var(--ink);color:var(--ground)}
#tab-more .subtabs{margin-top:1.2rem}
#map-svg .wdot{fill:var(--surface);stroke:var(--d2);stroke-width:2.5}
#map-svg .wnum{font-size:12px;font-weight:700;fill:var(--ink);font-family:var(--mono);pointer-events:none}
#map-svg .wm{cursor:pointer}
#map-svg .wm .wlab{display:none}
#map-svg .wm.sel .wlab{display:inline}
#map-svg .wm.sel .wdot{fill:var(--d2)}
#map-svg .wm.sel .wnum{fill:#fff}
#map-svg .wm:focus{outline:none}
#map-svg .wm:focus-visible .wdot{stroke:var(--ink);stroke-width:3}
.wn{display:inline-grid;place-items:center;width:1.4rem;height:1.4rem;border-radius:50%;border:2px solid var(--d2);font-family:var(--mono);font-size:.75rem;margin-right:.4rem;vertical-align:.1em}
.wlist .opt{transition:box-shadow .2s}
.wlist .opt.sel{box-shadow:0 0 0 2px var(--d2)}
.wlist .opt.sel .wn{background:var(--d2);color:#fff}
.wbtn{font:inherit;font-size:.8rem;font-weight:600;padding:.3rem .75rem;border-radius:999px;border:1px solid var(--d2);background:transparent;color:var(--ink);cursor:pointer;margin-right:.6rem}
.wsec .lede2{margin-top:1rem}
@media (max-width:700px){
  .mapsec.walk .mapbox{position:sticky;top:var(--tabs-h,0px);z-index:4;max-height:46vh;overflow:auto}
}

#tab-map .mapsec.walk .pg:not(:first-child){opacity:.3}
#tab-map .mapsec.walk .pg:not(:first-child) text{display:none}
@media (max-width:640px){
  .dayhead{grid-template-columns:1fr;align-items:start}
  .dayhead h2{word-break:keep-all;overflow-wrap:anywhere}
  .tabs button{flex:1;padding-inline:.6rem}
  .subtabs{width:100%}
  .subtabs button{flex:1;padding-inline:.4rem}
  #map-svg .wnum{font-size:15px}
  #map-svg .wm .wlab .plabel{font-size:17px}
  #map-svg .wm .wlab .plabel.sub{font-size:13px}
  .tbl.stack{overflow:visible}
  .tbl.stack thead{display:none}
  .tbl.stack table,.tbl.stack tbody{display:block}
  .tbl.stack tr{display:grid;grid-template-columns:1fr auto;gap:.2rem .8rem;padding:.65rem .85rem;border-bottom:1px solid var(--line)}
  .tbl.stack tr:last-child{border-bottom:0}
  .tbl.stack th,.tbl.stack td{display:block;padding:0;border:0;grid-column:1/-1;white-space:normal;text-align:left}
  .tbl.stack th[scope=row]{font-size:.88rem;font-weight:700}
  .t-book th,.t-meal th,.t-med th{grid-column:1;grid-row:1}
  .t-book td:last-child,.t-meal td.bdc,.t-med td.num{grid-column:2;grid-row:1;text-align:right}
  .t-meal td:last-child small,.t-book td:last-child small{color:var(--muted)}
  .t-food td[data-l]::before,.t-med td:last-child[data-l]::before{content:attr(data-l) "："; color:var(--muted);font-size:.78rem}
  .t-med td:last-child{color:var(--ink)}
  .t-stn tr{display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem .7rem}
  .t-stn th[scope=row]{flex:1 1 calc(100% - 6rem)}
  .t-stn td.lines{flex:0 0 5.2rem;text-align:right}
  .t-stn td:nth-child(3){color:var(--muted)}
  .t-stn td:nth-child(2),.t-stn td:nth-child(3){flex:0 0 auto}
  .t-stn td:nth-child(5){margin-left:auto;text-align:right}
}
#tab-map section.mapsec{margin-top:1rem}
#tab-more section.block{margin-top:.5rem}
#tab-more .subtabs{margin-top:1rem}
.wrap [hidden]{display:none!important}
.panhint{display:none;margin:.3rem 0 0;font-size:.78rem;color:var(--muted)}
@media (max-width:640px){.panhint{display:block}.mapsec.walk .panhint{display:none}}
ol.tl ul.mini{margin:.1rem 0 .2rem;padding-left:1.1rem;display:grid;gap:.35rem;font-size:.88rem;color:var(--muted)}
ol.tl ul.mini b{color:var(--ink)}
.check li.cg{padding:.45rem 1rem;font-family:var(--mono);font-size:.78rem;font-weight:600;color:var(--muted);background:var(--ground)}
#prep h3{font-size:1.05rem;margin-top:.6rem}

/* ── 本模組新增（參考產品沒有的部分）────────────────────────────── */

/* 每日標題下的自動摘要。它是由當天的 events 算出來的，不是人寫的標題——
   改一個行程，這行就會跟著變（A7 的五個連動點之一）。 */
.daysum{grid-column:1/-1;font-size:.85rem;color:var(--muted);margin-top:.35rem}

/* 地點名。每一個從 places 渲染出來的名字都包在這裡，
   驗收腳本靠它確認「頁面上沒有 trip.json 以外的店」（A8）。 */
.pn{font-weight:inherit}

/* 來源打架時兩個值都印，並且標出來——不挑一個當正確答案。 */
.conflict{display:grid;gap:.2rem;font-size:.85rem}
.conflict .cmark{font-size:.7rem;font-weight:600;color:var(--warn);background:var(--warn-soft);border-radius:4px;padding:.05rem .4rem;justify-self:start}
.conflict .cv{color:var(--ink)}
.conflict .cv+.cv{border-top:1px dashed var(--line);padding-top:.2rem}

/* 未查證：印出「查不到」而不是留白，留白會被讀成「沒有營業時間限制」。 */
.unverified{font-size:.82rem;color:var(--faint);font-style:italic}

/* 排隊候補清單（這一版沒有地圖定位互動，見 KNOWN_ISSUES）。 */
.qlist{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.7rem}

/* 待確認清單的每一條。auto 的那幾筆標出來，人才知道哪些是程式推的。 */
.autotag{font-size:.68rem;font-weight:600;color:var(--accent);background:var(--accent-soft);border-radius:4px;padding:.05rem .4rem;margin-left:.4rem;white-space:nowrap}

"""
