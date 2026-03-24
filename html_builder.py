"""
HTML Dashboard Builder — TPA Associate Productivity
Generates a self-contained HTML dashboard with embedded JSON data.
"""
import json


def build_html(payload):
    json_data = json.dumps(payload, separators=(',', ':'))
    return HTML_TEMPLATE.replace('__DATA_PLACEHOLDER__', json_data)


HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FC TPA — Associate Productivity Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
  :root{--wm-blue:#0053e2;--wm-spark:#ffc220;--wm-green:#2a8703;--wm-red:#ea1100;}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#f3f4f6;}
  table{border-collapse:collapse;font-size:.8rem;}
  th,td{padding:5px 10px;border:1px solid #e5e7eb;white-space:nowrap;}
  thead th{background:var(--wm-blue);color:#fff;font-weight:700;position:sticky;top:0;z-index:2;}
  tbody tr:hover td{background:#eff6ff!important;}
  .s1{position:sticky;left:0;background:#fff;z-index:3;}
  .s2{position:sticky;left:180px;background:#fff;z-index:3;}
  thead .s1,thead .s2{z-index:10;background:var(--wm-blue);}
  .cg{background:#dcfce7;color:#14532d;font-weight:700;}
  .ca{background:#fef9c3;color:#713f12;font-weight:700;}
  .co{background:#ffedd5;color:#7c2d12;font-weight:700;}
  .cr{background:#fee2e2;color:#7f1d1d;font-weight:700;}
  .cn{background:#f9fafb;color:#9ca3af;}
  .ci{background:#eff6ff;color:#1e40af;font-weight:600;}
  .badge-flag{background:var(--wm-red);color:#fff;border-radius:3px;padding:1px 5px;font-size:.65rem;font-weight:800;}
  .badge-t{background:var(--wm-spark);color:#1c1c1c;border-radius:3px;padding:1px 5px;font-size:.65rem;font-weight:700;}
  .tab-btn{cursor:pointer;padding:8px 22px;border-radius:8px 8px 0 0;font-weight:700;font-size:.85rem;border:none;}
  .tab-btn.active{background:var(--wm-blue);color:#fff;}
  .tab-btn:not(.active){background:#e5e7eb;color:#374151;}
  select{border:1px solid #d1d5db;border-radius:6px;padding:6px 10px;font-size:.85rem;background:#fff;min-width:160px;}
  select:focus{outline:2px solid var(--wm-blue);outline-offset:1px;}
  .kpi{border-radius:12px;padding:16px 20px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:5px solid;}
  .pill{border-radius:999px;padding:1px 9px;font-size:.72rem;font-weight:700;display:inline-block;}
  .chart-wrap{position:relative;}
  .sc-card{background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:14px;}
  ::-webkit-scrollbar{height:7px;width:5px;}
  ::-webkit-scrollbar-thumb{background:var(--wm-blue);border-radius:4px;}
</style>
</head>
<body>

<header style="background:var(--wm-blue)" class="text-white shadow">
  <div class="max-w-screen-2xl mx-auto px-5 py-3 flex items-center gap-4">
    <div style="background:var(--wm-spark)" class="rounded-full w-10 h-10 flex items-center justify-center text-xl font-black text-gray-900 flex-shrink-0">W</div>
    <div>
      <h1 class="text-lg font-bold leading-tight">FC TPA — Associate Productivity Dashboard</h1>
      <p class="text-xs opacity-75">13 WM Fiscal Weeks &nbsp;·&nbsp; UPH Goals + Training Curve &nbsp;·&nbsp; FY2026-W48 → FY2027-W08</p>
    </div>
    <div class="ml-auto text-xs opacity-60" id="hdr-date"></div>
  </div>
</header>

<!-- FILTERS -->
<div class="max-w-screen-2xl mx-auto px-5 py-3 bg-white shadow-sm border-b">
  <div class="flex flex-wrap gap-3 items-end">
    <div><label class="block text-xs font-semibold text-gray-500 mb-1">Super Department</label><select id="f-sd"></select></div>
    <div><label class="block text-xs font-semibold text-gray-500 mb-1">SC Code / Department</label><select id="f-sc"></select></div>
    <div><label class="block text-xs font-semibold text-gray-500 mb-1">Shift</label><select id="f-shift"></select></div>
    <div><label class="block text-xs font-semibold text-gray-500 mb-1">Associate</label><select id="f-assoc"></select></div>
    <div><label class="block text-xs font-semibold text-gray-500 mb-1">From Week</label><select id="f-wk-from"></select></div>
    <div><label class="block text-xs font-semibold text-gray-500 mb-1">To Week</label><select id="f-wk-to"></select></div>
    <div id="flag-wrap"><label class="block text-xs font-semibold text-gray-500 mb-1">Show</label>
      <select id="f-flag"><option value="">All Associates</option><option value="1">❗ Flagged Only</option></select></div>
    <button onclick="resetFilters()" class="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm font-semibold">Reset</button>
  </div>
</div>

<!-- MAIN -->
<div class="max-w-screen-2xl mx-auto px-5 py-4">

  <!-- Associate banner (shown only when associate selected) -->
  <div id="assoc-banner" class="hidden mb-5 rounded-2xl shadow p-5 text-white" style="background:var(--wm-blue)">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div class="text-2xl font-black" id="banner-name"></div>
        <div class="text-sm opacity-80 mt-1" id="banner-meta"></div>
      </div>
      <div id="banner-flag" class="text-lg font-bold"></div>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4" id="assoc-kpis"></div>
  </div>

  <!-- Team KPI cards (shown when no associate selected) -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5" id="team-kpis"></div>

  <!-- Aggregate trend chart -->
  <div class="bg-white rounded-2xl shadow p-5 mb-5" id="agg-chart-section">
    <h2 class="font-bold text-sm text-gray-600 mb-3">Weekly Avg Adjusted % to Goal — All Filtered Associates (13 Weeks)</h2>
    <div class="chart-wrap" style="height:260px"><canvas id="chart-agg"></canvas></div>
  </div>

  <!-- Associate chart section (overall + per-SC grid) -->
  <div id="assoc-chart-section" class="hidden mb-5">
    <div class="bg-white rounded-2xl shadow p-5 mb-4">
      <h2 class="font-bold text-sm text-gray-600 mb-1">Overall Weekly Performance (All SC Codes Combined)</h2>
      <p class="text-xs text-gray-400 mb-3">Weighted avg adjusted % to goal + idle % overlay</p>
      <div class="chart-wrap" style="height:320px"><canvas id="chart-overall"></canvas></div>
    </div>
    <h2 class="font-bold text-sm text-gray-600 mb-3">Performance by SC Code</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" id="per-sc-grid"></div>
  </div>

  <!-- Tabs + Table -->
  <div class="flex gap-1"><button class="tab-btn active" id="tab-wk" onclick="switchTab('weekly')">Weekly View</button><button class="tab-btn" id="tab-dy" onclick="switchTab('daily')">Daily View</button></div>
  <div class="bg-white shadow rounded-b-2xl rounded-tr-2xl overflow-x-auto"><div id="tbl-content"></div></div>
  <p class="text-xs text-gray-400 mt-2">
    Training: 0–40h=25% &bull; 41–80h=50% &bull; 81–120h=75% &bull; 120+h=100%. Pick: per-SC independent. Others: cross-SC carry-over, 90% cap outside home super-dept.
    <span class="badge-flag">FLAG</span> = &lt;100% adj. goal in 4+ of 13 weeks AND most recent week.
  </p>
</div>

<script>
const DATA = __DATA_PLACEHOLDER__;
let activeTab = 'weekly';
const charts = {};
const filters = { sd:'', sc:'', assoc:'', flag:'', shift:'', weekFrom:'', weekTo:'' };

const SD_CLR = {'Pick':'#0053e2','Pack':'#7c3aed','Ship Dock':'#0891b2','Receive':'#15803d',
  'Stock':'#92400e','Stocking':'#92400e','Inbound':'#65a30d','Orderfilling':'#c026d3',
  'Support (OB)':'#6b7280','Support':'#6b7280','Shipping':'#0369a1','General Support':'#6b7280'};
const PALETTE = ['#0053e2','#ea1100','#2a8703','#7c3aed','#0891b2','#c026d3','#f97316','#65a30d','#0369a1','#854d0e'];

function sdClr(sd){return SD_CLR[sd]||'#374151';}
function pCls(p){if(p==null)return'cn';return p>=100?'cg':p>=90?'ca':p>=80?'co':'cr';}
function pCell(p){if(p==null)return'<td class="cn text-center">—</td>';return`<td class="${pCls(p)} text-right">${p.toFixed(1)}%</td>`;}
function iCell(pct){if(pct==null)return'<td class="cn text-center">—</td>';return`<td class="ci text-right">${pct.toFixed(1)}%</td>`;}
function fmt(v,d=1){return(v==null||isNaN(v))?'—':Number(v).toFixed(d);}
function wkLbl(w){return`FY${w.year}-W${String(w.week).padStart(2,'0')}`;}
function assocLbl(aid){const a=DATA.associates[aid];if(!a)return aid;return a.name&&a.name!==aid?`${a.name} (${aid})`:aid;}
function destroy(id){if(charts[id]){charts[id].destroy();delete charts[id];}}
function cOpts(yLbl,yMin,ySugMax){return{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'top',labels:{boxWidth:12}},tooltip:{mode:'index',intersect:false}},scales:{y:{min:yMin,suggestedMax:ySugMax,ticks:{callback:v=>v+'%'},title:{display:true,text:yLbl}},x:{}}};}

// ---- Flagging ----
function computeFlags(rows){
  const g={};
  for(const r of rows){
    if(r.ADJUSTED_PCT_TO_GOAL==null||r.GOAL==null)continue;
    const k=`${r.default_id}|||${r.SC_CODE_ID}`,wk=`${r.year}-${r.week}`;
    if(!g[k])g[k]={};
    if(!g[k][wk])g[k][wk]={p:0,h:0};
    g[k][wk].p+=r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0);g[k][wk].h+=r.HOURS||0;
  }
  const aw=getActiveWeeks();
  const wks=aw.map(w=>`${w.year}-${w.week}`),last=wks[wks.length-1];
  const flags=new Set();
  for(const[k,wm]of Object.entries(g)){
    let b=0,br=false;
    for(const wk of wks){if(!wm[wk]||!wm[wk].h)continue;const avg=wm[wk].p/wm[wk].h;if(avg<100){b++;if(wk===last)br=true;}}
    if(b>=4&&br)flags.add(k);
  }
  return flags;
}
function assocFlagged(aid,flags){return[...flags].some(k=>k.startsWith(aid+'|||'));}

// ---- Week helpers ----
function wkKey(w){return`${w.year}-${String(w.week).padStart(2,'0')}`;}
function getActiveWeeks(){
  const all=DATA.weeks;
  const from=filters.weekFrom,to=filters.weekTo;
  if(!from&&!to)return all;
  return all.filter(w=>{
    const k=wkKey(w);
    if(from&&k<from)return false;
    if(to&&k>to)return false;
    return true;
  });
}

// ---- Filtering ----
function getRows(){
  const activeKeys=new Set(getActiveWeeks().map(wkKey));
  return DATA.rows.filter(r=>{
    if(filters.sd&&r.SUPER_DEPARTMENT!==filters.sd)return false;
    if(filters.sc&&r.SC_CODE_ID!==filters.sc)return false;
    if(filters.assoc&&r.default_id!==filters.assoc)return false;
    if(filters.shift){
      const a=DATA.associates[r.default_id];
      if(!a||a.shift!==filters.shift)return false;
    }
    const k=`${r.year}-${String(r.week).padStart(2,'0')}`;
    if(!activeKeys.has(k))return false;
    return true;
  });
}

// ---- Filter UI ----
function initFilters(){
  const sds=[...new Set(Object.values(DATA.sc_codes).map(s=>s.super_department))].filter(Boolean).sort();
  const sdEl=document.getElementById('f-sd');
  sdEl.innerHTML='<option value="">All Super Depts</option>';
  sds.forEach(sd=>{sdEl.innerHTML+=`<option value="${sd}">${sd}</option>`;});

  // Shift dropdown — built from associates metadata
  const shifts=[...new Set(Object.values(DATA.associates).map(a=>a.shift).filter(Boolean))].sort();
  const shiftEl=document.getElementById('f-shift');
  shiftEl.innerHTML='<option value="">All Shifts</option>';
  shifts.forEach(s=>{shiftEl.innerHTML+=`<option value="${s}">${s}</option>`;});

  // Week range dropdowns
  const wkFromEl=document.getElementById('f-wk-from');
  const wkToEl=document.getElementById('f-wk-to');
  wkFromEl.innerHTML='<option value="">Earliest</option>';
  wkToEl.innerHTML='<option value="">Latest</option>';
  DATA.weeks.forEach(w=>{
    const k=wkKey(w),lbl=wkLbl(w)+` (${w.week_start})`;
    wkFromEl.innerHTML+=`<option value="${k}">${lbl}</option>`;
    wkToEl.innerHTML+=`<option value="${k}">${lbl}</option>`;
  });

  rebuildSC();rebuildAssoc();
  sdEl.addEventListener('change',e=>{filters.sd=e.target.value;filters.sc='';rebuildSC();onFilter();});
  document.getElementById('f-sc').addEventListener('change',e=>{filters.sc=e.target.value;onFilter();});
  document.getElementById('f-shift').addEventListener('change',e=>{filters.shift=e.target.value;rebuildAssoc();onFilter();});
  document.getElementById('f-assoc').addEventListener('change',e=>{filters.assoc=e.target.value;onFilter();});
  document.getElementById('f-flag').addEventListener('change',e=>{filters.flag=e.target.value;onFilter();});
  document.getElementById('f-wk-from').addEventListener('change',e=>{
    filters.weekFrom=e.target.value;
    // auto-advance To if it's now before From
    if(filters.weekFrom&&filters.weekTo&&filters.weekTo<filters.weekFrom){
      filters.weekTo=filters.weekFrom;
      document.getElementById('f-wk-to').value=filters.weekTo;
    }
    onFilter();
  });
  document.getElementById('f-wk-to').addEventListener('change',e=>{
    filters.weekTo=e.target.value;
    if(filters.weekFrom&&filters.weekTo&&filters.weekTo<filters.weekFrom){
      filters.weekFrom=filters.weekTo;
      document.getElementById('f-wk-from').value=filters.weekFrom;
    }
    onFilter();
  });
}
function rebuildSC(){
  const codes=Object.entries(DATA.sc_codes).filter(([,v])=>!filters.sd||v.super_department===filters.sd).sort(([,a],[,b])=>a.department.localeCompare(b.department));
  const el=document.getElementById('f-sc');
  el.innerHTML='<option value="">All SC Codes</option>';
  codes.forEach(([sc,v])=>{el.innerHTML+=`<option value="${sc}">${sc} — ${v.department}</option>`;});
  if(filters.sc)el.value=filters.sc;
}
function rebuildAssoc(){
  const base=DATA.rows.filter(r=>{
    if(filters.sd&&r.SUPER_DEPARTMENT!==filters.sd)return false;
    if(filters.sc&&r.SC_CODE_ID!==filters.sc)return false;
    if(filters.shift){
      const a=DATA.associates[r.default_id];
      if(!a||a.shift!==filters.shift)return false;
    }
    return true;
  });
  let aids;
  if(filters.flag==='1'){const fl=computeFlags(base);aids=new Set([...fl].map(k=>k.split('|||')[0]));}
  else aids=new Set(base.map(r=>r.default_id));
  const sorted=[...aids].sort((a,b)=>assocLbl(a).localeCompare(assocLbl(b)));
  const el=document.getElementById('f-assoc');
  el.innerHTML='<option value="">All Associates</option>';
  sorted.forEach(aid=>{el.innerHTML+=`<option value="${aid}">${assocLbl(aid)}</option>`;});
  if(filters.assoc&&!aids.has(filters.assoc))filters.assoc='';
  if(filters.assoc)el.value=filters.assoc;
}
function onFilter(){rebuildAssoc();render();}
function resetFilters(){
  Object.assign(filters,{sd:'',sc:'',assoc:'',flag:'',shift:'',weekFrom:'',weekTo:''});
  ['f-sd','f-sc','f-assoc','f-flag','f-shift','f-wk-from','f-wk-to'].forEach(id=>document.getElementById(id).value='');
  rebuildSC();rebuildAssoc();render();
}

// ---- Team KPIs ----
function renderTeamKPIs(rows){
  const wg=rows.filter(r=>r.ADJUSTED_PCT_TO_GOAL!=null);
  const tH=wg.reduce((s,r)=>s+(r.HOURS||0),0);
  const avg=tH>0?wg.reduce((s,r)=>s+r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0),0)/tH:null;
  const flags=computeFlags(rows);
  const fla=new Set([...flags].map(k=>k.split('|||')[0]));
  const col=avg==null?'#6b7280':avg>=100?'#2a8703':avg>=90?'#f59e0b':'#ea1100';
  const cards=[
    {l:'Associates',v:new Set(rows.map(r=>r.default_id)).size,c:'#0053e2'},
    {l:'SC Codes w/ Goals',v:new Set(rows.filter(r=>r.GOAL!=null).map(r=>r.SC_CODE_ID)).size,c:'#7c3aed'},
    {l:'Avg Adj % to Goal',v:avg!=null?avg.toFixed(1)+'%':'—',c:col},
    {l:'Flagged Associates',v:fla.size,c:'#ea1100'},
  ];
  document.getElementById('team-kpis').innerHTML=cards.map(c=>`<div class="kpi" style="border-color:${c.c}"><div class="text-3xl font-black" style="color:${c.c}">${typeof c.v==='number'?c.v.toLocaleString():c.v}</div><div class="text-xs text-gray-500 mt-1">${c.l}</div></div>`).join('');
}

// ---- Associate Banner + KPIs ----
function renderAssocBanner(aid,rows,flags){
  const a=DATA.associates[aid]||{};
  const name=a.name&&a.name!==aid?a.name:aid;
  document.getElementById('banner-name').textContent=name;
  document.getElementById('banner-meta').textContent=`ID: ${aid}  |  Home SC: ${a.home_code||'—'}  |  Super Dept: ${a.home_superdept||'—'}  |  Shift: ${a.shift||'—'}`;
  const flagged=assocFlagged(aid,flags);
  document.getElementById('banner-flag').innerHTML=flagged?'<span class="badge-flag">❗ PERFORMANCE FLAG</span>':'<span style="color:#ffc220">✓ On Track</span>';
  // Associate KPIs
  const wg=rows.filter(r=>r.ADJUSTED_PCT_TO_GOAL!=null);
  const tH=rows.reduce((s,r)=>s+(r.HOURS||0),0);
  const tI=rows.reduce((s,r)=>s+(r.IDLE_HOURS||0),0);
  const avg=tH>0?wg.reduce((s,r)=>s+r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0),0)/wg.reduce((s,r)=>s+(r.HOURS||0),0):null;
  const idlePct=tH>0?(tI/tH)*100:null;
  const wksBelow=computeWeeksBelow(aid,rows);
  const nWks=getActiveWeeks().length;
  const kpis=[
    {l:'Total Hours (filtered)',v:tH.toFixed(1)+'h',c:'#0053e2'},
    {l:'Avg Adj % to Goal',v:avg!=null?avg.toFixed(1)+'%':'—',c:avg==null?'#6b7280':avg>=100?'#2a8703':avg>=90?'#f59e0b':'#ea1100'},
    {l:'Avg Idle %',v:idlePct!=null?idlePct.toFixed(1)+'%':'—',c:idlePct!=null&&idlePct>15?'#ea1100':'#0053e2'},
    {l:`Weeks Below 100% (of ${nWks})`,v:wksBelow+'/'+nWks,c:wksBelow>=4?'#ea1100':'#2a8703'},
  ];
  document.getElementById('assoc-kpis').innerHTML=kpis.map(k=>`<div class="rounded-xl p-3" style="background:rgba(255,255,255,.15)"><div class="text-xl font-black" style="color:${k.c===('#ea1100')||k.c==='#2a8703'?k.c:'#ffc220'}">${k.v}</div><div class="text-xs opacity-75 mt-1">${k.l}</div></div>`).join('');
}
function computeWeeksBelow(aid,rows){
  const wkPct={};
  for(const r of rows){
    if(r.default_id!==aid||r.ADJUSTED_PCT_TO_GOAL==null||r.GOAL==null)continue;
    const wk=`${r.year}-${r.week}`;
    if(!wkPct[wk])wkPct[wk]={p:0,h:0};
    wkPct[wk].p+=r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0);wkPct[wk].h+=r.HOURS||0;
  }
  return Object.values(wkPct).filter(e=>e.h>0&&(e.p/e.h)<100).length;
}

// ---- Overall associate chart ----
function renderOverallChart(rows){
  const wkMap={};
  for(const r of rows){
    const wk=`${r.year}-${r.week}`;
    if(!wkMap[wk])wkMap[wk]={p:0,h:0,ih:0};
    wkMap[wk].ih+=r.IDLE_HOURS||0;
    wkMap[wk].h+=r.HOURS||0;
    if(r.ADJUSTED_PCT_TO_GOAL!=null&&r.GOAL!=null){wkMap[wk].p+=r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0);}
  }
  const aw=getActiveWeeks(),labels=aw.map(wkLbl);
  const pctVals=aw.map(w=>{const e=wkMap[`${w.year}-${w.week}`];return e&&e.h>0?parseFloat((e.p/e.h).toFixed(2)):null;});
  const idleVals=aw.map(w=>{const e=wkMap[`${w.year}-${w.week}`];return e&&e.h>0?parseFloat(((e.ih/e.h)*100).toFixed(2)):null;});
  const ptClr=pctVals.map(v=>v==null?'#9ca3af':v>=100?'#2a8703':v>=90?'#f59e0b':v>=80?'#f97316':'#ea1100');
  destroy('overall');
  charts['overall']=new Chart(document.getElementById('chart-overall').getContext('2d'),{
    plugins:[ChartDataLabels],
    data:{labels,datasets:[
      {type:'line',label:'Adj % to Goal',data:pctVals,borderColor:'#0053e2',backgroundColor:'rgba(0,83,226,.08)',fill:true,tension:.35,pointRadius:6,pointBackgroundColor:ptClr,yAxisID:'y'},
      {type:'line',label:'Idle %',data:idleVals,borderColor:'#f97316',backgroundColor:'transparent',tension:.35,pointRadius:4,borderDash:[5,4],yAxisID:'y'},
      {type:'line',label:'100% Goal',data:labels.map(()=>100),borderColor:'#ffc220',borderWidth:2,borderDash:[7,4],pointRadius:0,fill:false,yAxisID:'y'},
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{
        legend:{position:'top',labels:{boxWidth:12}},
        tooltip:{mode:'index',intersect:false},
        datalabels:{
          display:ctx=>ctx.datasetIndex<2&&ctx.dataset.data[ctx.dataIndex]!=null,
          formatter:(v,ctx)=>v!=null?v.toFixed(1)+'%':null,
          font:{weight:'bold',size:10},
          color:ctx=>{
            const v=ctx.dataset.data[ctx.dataIndex];
            if(ctx.datasetIndex===1)return'#c2410c';
            return v>=100?'#15803d':v>=90?'#92400e':v>=80?'#9a3412':'#7f1d1d';
          },
          backgroundColor:ctx=>{
            if(ctx.datasetIndex===1)return'rgba(255,237,213,.85)';
            const v=ctx.dataset.data[ctx.dataIndex];
            return v>=100?'rgba(220,252,231,.85)':v>=90?'rgba(254,249,195,.85)':v>=80?'rgba(255,237,213,.85)':'rgba(254,226,226,.85)';
          },
          borderRadius:4,
          padding:{top:3,bottom:3,left:5,right:5},
          anchor:ctx=>ctx.datasetIndex===1?'start':'end',
          align:ctx=>ctx.datasetIndex===1?'bottom':'top',
          offset:4,
          clamp:true,
        }
      },
      scales:{y:{min:0,suggestedMax:160,ticks:{callback:v=>v+'%'},title:{display:true,text:'% (Goal & Idle)'}},x:{}}}
  });
}

// ---- Per-SC chart grid ----
function renderPerSCCharts(rows){
  const scCodes=[...new Set(rows.filter(r=>r.GOAL!=null).map(r=>r.SC_CODE_ID))];
  const grid=document.getElementById('per-sc-grid');
  // destroy old charts
  Object.keys(charts).filter(k=>k.startsWith('sc-')).forEach(k=>destroy(k));
  grid.innerHTML='';
  const aw=getActiveWeeks(),labels=aw.map(wkLbl);
  scCodes.forEach((sc,i)=>{
    const info=DATA.sc_codes[sc]||{};
    const scRows=rows.filter(r=>r.SC_CODE_ID===sc&&r.GOAL!=null);
    const wkMap={};
    for(const r of scRows){
      const wk=`${r.year}-${r.week}`;
      if(!wkMap[wk])wkMap[wk]={p:0,h:0,ih:0};
      wkMap[wk].p+=r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0);wkMap[wk].h+=r.HOURS||0;wkMap[wk].ih+=r.IDLE_HOURS||0;
    }
    const pctVals=aw.map(w=>{const e=wkMap[`${w.year}-${w.week}`];return e&&e.h>0?parseFloat((e.p/e.h).toFixed(2)):null;});
    const idleVals=aw.map(w=>{const e=wkMap[`${w.year}-${w.week}`];return e&&e.h>0?parseFloat(((e.ih/e.h)*100).toFixed(2)):null;});
    const ptClr=pctVals.map(v=>v==null?'#9ca3af':v>=100?'#2a8703':v>=90?'#f59e0b':v>=80?'#f97316':'#ea1100');
    const canvasId=`sc-canvas-${i}`;
    const card=document.createElement('div');
    card.className='sc-card';
    card.innerHTML=`<div class="font-bold text-sm mb-0">${info.department||sc}</div><div class="text-xs text-gray-400 font-mono mb-2">${sc} &nbsp;·&nbsp; Goal: ${scRows[0]?.GOAL??'—'} ${info.goal_uom||''}</div><div class="chart-wrap" style="height:200px"><canvas id="${canvasId}"></canvas></div>`;
    grid.appendChild(card);
    charts[`sc-${i}`]=new Chart(document.getElementById(canvasId).getContext('2d'),{
      data:{labels,datasets:[
        {type:'line',label:'Adj % to Goal',data:pctVals,borderColor:PALETTE[i%PALETTE.length],backgroundColor:`${PALETTE[i%PALETTE.length]}15`,fill:true,tension:.3,pointRadius:5,pointBackgroundColor:ptClr,yAxisID:'y'},
        {type:'line',label:'Idle %',data:idleVals,borderColor:'#f97316',backgroundColor:'transparent',tension:.3,pointRadius:3,borderDash:[5,3],yAxisID:'y'},
        {type:'line',label:'Goal',data:labels.map(()=>100),borderColor:'#ffc220',borderWidth:1.5,borderDash:[6,4],pointRadius:0,fill:false,yAxisID:'y'},
      ]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'top',labels:{boxWidth:10,font:{size:10}}},tooltip:{mode:'index',intersect:false}},
        scales:{y:{min:0,suggestedMax:150,ticks:{callback:v=>v+'%',font:{size:10}},title:{display:false}},x:{ticks:{font:{size:9}}}}}
    });
  });
}

// ---- Aggregate chart ----
function renderAggChart(rows){
  const wkMap={};
  for(const r of rows){
    if(r.ADJUSTED_PCT_TO_GOAL==null||r.GOAL==null)continue;
    const wk=`${r.year}-${r.week}`;
    if(!wkMap[wk])wkMap[wk]={p:0,h:0};
    wkMap[wk].p+=r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0);wkMap[wk].h+=r.HOURS||0;
  }
  const aw=getActiveWeeks(),labels=aw.map(wkLbl);
  const vals=aw.map(w=>{const e=wkMap[`${w.year}-${w.week}`];return e&&e.h>0?parseFloat((e.p/e.h).toFixed(2)):null;});
  const ptClr=vals.map(v=>v==null?'#9ca3af':v>=100?'#2a8703':v>=90?'#f59e0b':v>=80?'#f97316':'#ea1100');
  destroy('agg');
  charts['agg']=new Chart(document.getElementById('chart-agg').getContext('2d'),{
    type:'line',
    data:{labels,datasets:[
      {label:'Avg Adj % to Goal',data:vals,borderColor:'#0053e2',backgroundColor:'rgba(0,83,226,.07)',fill:true,tension:.35,pointRadius:6,pointBackgroundColor:ptClr},
      {label:'100% Goal',data:labels.map(()=>100),borderColor:'#ffc220',borderWidth:2,borderDash:[7,4],pointRadius:0,fill:false},
    ]},
    options:cOpts('Adj % to Goal',0,160)
  });
}

// ---- Weekly Table ----
function renderWeeklyTable(rows,flags){
  const g={};
  for(const r of rows){
    if(r.GOAL==null)continue;
    const k=`${r.default_id}|||${r.SC_CODE_ID}`,wk=`${r.year}-${r.week}`;
    if(!g[k])g[k]={aid:r.default_id,sc:r.SC_CODE_ID,sd:r.SUPER_DEPARTMENT,dept:r.DEPARTMENT,wks:{}};
    if(!g[k].wks[wk])g[k].wks[wk]={p:0,h:0,ih:0,mult:null};
    const e=g[k].wks[wk];
    if(r.ADJUSTED_PCT_TO_GOAL!=null){e.p+=r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0);e.h+=r.HOURS||0;}
    e.ih+=r.IDLE_HOURS||0;
    if(r.TRAINING_MULTIPLIER!=null)e.mult=r.TRAINING_MULTIPLIER;
  }
  let combos=Object.values(g);
  if(filters.flag==='1')combos=combos.filter(c=>flags.has(`${c.aid}|||${c.sc}`));
  combos.sort((a,b)=>a.sd.localeCompare(b.sd)||a.dept.localeCompare(b.dept)||assocLbl(a.aid).localeCompare(assocLbl(b.aid)));
  if(!combos.length)return'<p class="p-10 text-gray-400 text-center">No data for current filters.</p>';
  const aw=getActiveWeeks();
  const showAssocCol=!filters.assoc;
  let h='<table class="w-full"><thead><tr>';
  if(showAssocCol)h+=`<th class="s1 text-left" style="min-width:180px">Associate</th>`;
  h+=`<th class="${showAssocCol?'s2':'s1'} text-left" style="min-width:210px">SC Code / Department</th>`;
  h+='<th>Super Dept</th>';
  aw.forEach(w=>h+=`<th>${wkLbl(w)}<br><span style="font-weight:400;font-size:.65rem">${w.week_start}</span><br><span style="font-weight:400;font-size:.6rem;opacity:.7">Adj% / Idle%</span></th>`);
  h+=`<th>Wks&lt;100%</th></tr></thead><tbody>`;
  for(const c of combos){
    const fl=flags.has(`${c.aid}|||${c.sc}`),col=sdClr(c.sd);
    h+='<tr>';
    if(showAssocCol)h+=`<td class="s1">${assocLbl(c.aid)} ${fl?'<span class="badge-flag">❗</span>':''}</td>`;
    h+=`<td class="${showAssocCol?'s2':'s1'}"><span class="font-mono text-xs text-gray-400">${c.sc}</span><br>${c.dept}</td>`;
    h+=`<td><span class="pill" style="background:${col}22;color:${col}">${c.sd}</span></td>`;
    let below=0;
    for(const w of aw){
      const e=c.wks[`${w.year}-${w.week}`];
      if(!e||e.h===0){h+='<td class="cn text-center">—</td>';continue;}
      const avg=e.p/e.h;if(avg<100)below++;
      const idle=e.h>0?(e.ih/e.h)*100:null;
      const mb=e.mult!=null&&e.mult<1?`<span class="badge-t">${(e.mult*100).toFixed(0)}%</span> `:"";
      h+=`<td class="${pCls(avg)} text-right">${mb}${avg.toFixed(1)}%<br><span style="font-size:.7rem;color:#6b7280">${idle!=null?idle.toFixed(1)+'% idle':''}</span></td>`;
    }
    h+=`<td class="text-center font-bold ${below>=4?'text-red-600':'text-gray-600'}">${below}/${aw.length}</td></tr>`;
  }
  h+=`</tbody></table><p class="px-4 py-2 text-xs text-gray-400">${combos.length.toLocaleString()} assoc × SC combinations. Each cell: Adj % to goal / Idle %.</p>`;
  return h;
}

// ---- Daily Table ----
function renderDailyTable(rows,flags){
  let vis=rows.filter(r=>r.GOAL!=null);
  if(filters.flag==='1')vis=vis.filter(r=>flags.has(`${r.default_id}|||${r.SC_CODE_ID}`));
  vis.sort((a,b)=>b.date.localeCompare(a.date)||a.SUPER_DEPARTMENT.localeCompare(b.SUPER_DEPARTMENT)||assocLbl(a.default_id).localeCompare(assocLbl(b.default_id)));
  if(!vis.length)return'<p class="p-10 text-gray-400 text-center">No data for current filters.</p>';
  const showA=!filters.assoc;
  const hdrs=['Date','WM Week',...(showA?['Name','User ID']:['Name']),'SC Code','Department','Super Dept',
    'Hours','Idle Hrs','Idle %','Volume','Goal','Adj Goal','RPH','% Goal','Adj % Goal','Train Mult','Home Dept?','SC Hrs@Start'];
  let h='<table class="w-full"><thead><tr>'+hdrs.map(x=>`<th>${x}</th>`).join('')+'</tr></thead><tbody>';
  for(const r of vis){
    const col=sdClr(r.SUPER_DEPARTMENT),wk=`FY${r.year}-W${String(r.week).padStart(2,'0')}`,a=DATA.associates[r.default_id]||{};
    const idlePct=r.HOURS>0?((r.IDLE_HOURS||0)/r.HOURS)*100:null;
    h+='<tr>';
    h+=`<td>${r.date}</td><td>${wk}</td>`;
    if(showA)h+=`<td>${a.name&&a.name!==r.default_id?a.name:'—'}</td><td class="font-mono text-xs">${r.default_id}</td>`;
    else h+=`<td>${a.name&&a.name!==r.default_id?a.name:r.default_id}</td>`;
    h+=`<td class="font-mono text-xs">${r.SC_CODE_ID}</td>`;
    h+=`<td>${r.DEPARTMENT||''}</td>`;
    h+=`<td><span class="pill" style="background:${col}22;color:${col}">${r.SUPER_DEPARTMENT||''}</span></td>`;
    h+=`<td class="text-right">${fmt(r.HOURS)}</td>`;
    h+=`<td class="ci text-right">${fmt(r.IDLE_HOURS)}</td>`;
    h+=iCell(idlePct);
    h+=`<td class="text-right">${r.VOLUME!=null?fmt(r.VOLUME,0):'—'}</td>`;
    h+=`<td class="text-right">${r.GOAL??'—'} ${r.GOAL_UOM||''}</td>`;
    h+=`<td class="text-right">${r.ADJUSTED_GOAL!=null?fmt(r.ADJUSTED_GOAL,2):'—'}</td>`;
    h+=`<td class="text-right">${r.RATE_PER_HOUR!=null?fmt(r.RATE_PER_HOUR,1):'—'}</td>`;
    h+=pCell(r.PCT_TO_GOAL)+pCell(r.ADJUSTED_PCT_TO_GOAL);
    const m=r.TRAINING_MULTIPLIER;
    h+=`<td class="text-center">${m!=null?`<span class="${m<1?'badge-t':'text-green-700 font-bold'}">${(m*100).toFixed(0)}%</span>`:'—'}</td>`;
    h+=`<td class="text-center">${r.IS_HOME_SUPERDEPT==='Y'?'✅':r.IS_HOME_SUPERDEPT==='N'?'🔄':'—'}</td>`;
    h+=`<td class="text-right">${r.LIFETIME_SC_HOURS!=null?fmt(r.LIFETIME_SC_HOURS,1):'—'}</td></tr>`;
  }
  h+=`</tbody></table><p class="px-4 py-2 text-xs text-gray-400">${vis.length.toLocaleString()} rows. Sorted date desc.</p>`;
  return h;
}

// ---- Tabs ----
function switchTab(t){
  activeTab=t;
  document.getElementById('tab-wk').className='tab-btn'+(t==='weekly'?' active':'');
  document.getElementById('tab-dy').className='tab-btn'+(t==='daily'?' active':'');
  render();
}

// ---- Main render ----
function render(){
  const rows=getRows();
  const flags=computeFlags(rows);
  const hasAssoc=!!filters.assoc;

  // Show/hide sections
  document.getElementById('assoc-banner').classList.toggle('hidden',!hasAssoc);
  document.getElementById('team-kpis').classList.toggle('hidden',hasAssoc);
  document.getElementById('agg-chart-section').classList.toggle('hidden',hasAssoc);
  document.getElementById('assoc-chart-section').classList.toggle('hidden',!hasAssoc);
  document.getElementById('flag-wrap').classList.toggle('hidden',hasAssoc);

  if(hasAssoc){
    renderAssocBanner(filters.assoc,rows,flags);
    renderOverallChart(rows);
    renderPerSCCharts(rows);
  } else {
    renderTeamKPIs(rows);
    const nw=getActiveWeeks().length;
    document.querySelector('#agg-chart-section h2').textContent=
      `Weekly Avg Adjusted % to Goal — All Filtered Associates (${nw} Week${nw===1?'':'s'})`;
    renderAggChart(rows);
  }

  document.getElementById('tbl-content').innerHTML=
    activeTab==='weekly'?renderWeeklyTable(rows,flags):renderDailyTable(rows,flags);
}

document.addEventListener('DOMContentLoaded',()=>{
  document.getElementById('hdr-date').textContent='Generated: '+new Date().toLocaleString('en-US',{dateStyle:'medium',timeStyle:'short'});
  initFilters();render();
});
</script>
</body></html>
""".strip()
