"""
Quality Tab — JavaScript logic injected into the dashboard <script> block.
Kept separate to keep html_builder.py under the 600-line limit.
"""

QUALITY_JS = r"""
// ============================================================
// QUALITY TAB
// ============================================================
const Q = DATA.quality;
const Q_CAT_CLR = {
  Picking:'#0053e2', Packing:'#7c3aed', RSR:'#f97316', Receiving:'#2a8703'
};
const Q_CAT_LIGHT = {
  Picking:'#dbeafe', Packing:'#ede9fe', RSR:'#ffedd5', Receiving:'#dcfce7'
};
const qCharts = {};
const qFilters = {category:'', errorCode:'', shift:'', inclNonPunitive:false};

// --- helpers ---
function qWkKey(w){ return `${w.year}-${w.week}`; }
function getQWeeks(){
  const all = Q.weeks;
  const from = filters.weekFrom, to = filters.weekTo;
  if(!from && !to) return all;
  return all.filter(w=>{
    const k = `${w.year}-${String(w.week).padStart(2,'0')}`;
    if(from && k<from) return false;
    if(to   && k>to  ) return false;
    return true;
  });
}
function destroyQ(id){ if(qCharts[id]){qCharts[id].destroy();delete qCharts[id];} }

function getQErrors(){
  const aw = new Set(getQWeeks().map(w=>`${w.year}-${w.week}`));
  return Q.errors.filter(e=>{
    if(!aw.has(`${e.year}-${e.week}`)) return false;
    if(!qFilters.inclNonPunitive && e.non_punitive) return false;
    if(qFilters.category && e.category !== qFilters.category) return false;
    if(qFilters.errorCode && e.error_code !== +qFilters.errorCode) return false;
    if(qFilters.shift && e.shift !== qFilters.shift) return false;
    if(filters.assoc && e.user_id !== filters.assoc) return false;
    return true;
  });
}

function initQFilters(){
  // Shifts from error data
  const shifts=[...new Set(Q.errors.map(e=>e.shift).filter(Boolean))].sort();
  const shEl=document.getElementById('qf-shift');
  shifts.forEach(s=>{ shEl.innerHTML+=`<option value="${s}">${s}</option>`; });
  rebuildQCodeDrop();
}
function rebuildQCodeDrop(){
  const cat = qFilters.category;
  const codes = Q.errors
    .filter(e=>!cat||e.category===cat)
    .map(e=>({code:e.error_code, desc:e.error_desc}));
  const seen={};
  codes.forEach(c=>{ seen[c.code]=c.desc; });
  const el = document.getElementById('qf-code');
  el.innerHTML='<option value="">All Error Types</option>';
  Object.entries(seen).sort((a,b)=>+a[0]-+b[0]).forEach(([c,d])=>{
    el.innerHTML+=`<option value="${c}">${c} — ${d}</option>`;
  });
  if(qFilters.errorCode)el.value=qFilters.errorCode;
}
function onQFilter(){
  qFilters.category = document.getElementById('qf-cat').value;
  qFilters.errorCode= document.getElementById('qf-code').value;
  qFilters.shift    = document.getElementById('qf-shift').value;
  qFilters.inclNonPunitive = document.getElementById('qf-np').checked;
  rebuildQCodeDrop();
  renderQ();
}
function resetQFilters(){
  Object.assign(qFilters,{category:'',errorCode:'',shift:'',inclNonPunitive:false});
  ['qf-cat','qf-code','qf-shift'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('qf-np').checked=false;
  rebuildQCodeDrop();
  renderQ();
}

// --- KPIs ---
function renderQKPIs(errs){
  const totalEvt = errs.length;
  const totalQty = errs.reduce((s,e)=>s+e.error_qty,0);
  // Most common error type by qty
  const byDesc={};
  errs.forEach(e=>{ byDesc[e.error_desc]=(byDesc[e.error_desc]||0)+e.error_qty; });
  const topDesc = Object.entries(byDesc).sort((a,b)=>b[1]-a[1])[0];
  // Most errors by associate
  const byAssoc={};
  errs.forEach(e=>{ byAssoc[e.user_id]=(byAssoc[e.user_id]||0)+e.error_qty; });
  const topAssoc = Object.entries(byAssoc).sort((a,b)=>b[1]-a[1])[0];
  const topAssocName = topAssoc ? assocLbl(topAssoc[0]) : '—';
  const cards = [
    {l:'Error Events',   v:totalEvt.toLocaleString(),           c:'#0053e2'},
    {l:'Total Error Qty',v:totalQty.toLocaleString(),           c:'#ea1100'},
    {l:'Top Error Type', v:topDesc  ?topDesc[0].replace(/^\w+ - /,''):'—', c:'#f97316'},
    {l:'Most Errors',    v:topAssocName.split('(')[0].trim()||'—',     c:'#7c3aed'},
  ];
  document.getElementById('q-kpis').innerHTML = cards.map(c=>
    `<div class="kpi" style="border-color:${c.c}">
      <div class="text-2xl font-black" style="color:${c.c}">${c.v}</div>
      <div class="text-xs text-gray-500 mt-1">${c.l}</div>
    </div>`
  ).join('');
}

// --- Trend chart (stacked bar by category per week) ---
function renderQTrend(errs){
  const qw = getQWeeks();
  const cats = ['Picking','Packing','RSR','Receiving'];
  const wkData = {};
  qw.forEach(w=>{ wkData[qWkKey(w)]={Picking:0,Packing:0,RSR:0,Receiving:0}; });
  errs.forEach(e=>{
    const k=`${e.year}-${e.week}`;
    if(wkData[k]) wkData[k][e.category]=(wkData[k][e.category]||0)+e.error_qty;
  });
  const labels = qw.map(w=>w.label);
  destroyQ('trend');
  qCharts['trend'] = new Chart(
    document.getElementById('q-chart-trend').getContext('2d'),{
      type:'bar',
      data:{
        labels,
        datasets: cats.map(cat=>({
          label: cat,
          data: qw.map(w=>wkData[qWkKey(w)][cat]||0),
          backgroundColor: Q_CAT_CLR[cat]+'cc',
          borderColor: Q_CAT_CLR[cat],
          borderWidth:1,
        }))
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{legend:{position:'top',labels:{boxWidth:12}},tooltip:{mode:'index',intersect:false}},
        scales:{
          x:{stacked:true},
          y:{stacked:true,beginAtZero:true,title:{display:true,text:'Error Qty'}}
        }
      }
    }
  );
}

// --- Donut chart (by error desc) ---
function renderQDonut(errs){
  const byDesc={};
  errs.forEach(e=>{ byDesc[e.error_desc]=(byDesc[e.error_desc]||0)+e.error_qty; });
  const entries=Object.entries(byDesc).sort((a,b)=>b[1]-a[1]).slice(0,12);
  const palette=[
    '#0053e2','#ea1100','#7c3aed','#2a8703','#f97316','#0891b2',
    '#c026d3','#65a30d','#854d0e','#0369a1','#d97706','#6b7280'
  ];
  destroyQ('donut');
  qCharts['donut'] = new Chart(
    document.getElementById('q-chart-donut').getContext('2d'),{
      type:'doughnut',
      data:{
        labels: entries.map(([d])=>d.replace(/^\w+ - /,'')),
        datasets:[{
          data: entries.map(([,v])=>v),
          backgroundColor: palette.slice(0,entries.length),
          borderWidth:2, borderColor:'#fff'
        }]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{
          legend:{position:'right',labels:{boxWidth:12,font:{size:10}}},
          tooltip:{callbacks:{label:ctx=>`${ctx.label}: ${ctx.parsed.toLocaleString()} errors`}}
        }
      }
    }
  );
}

// --- Leaderboard ---
function renderQLeaderboard(errs){
  const qw = getQWeeks();
  const assocMap = {};
  errs.forEach(e=>{
    if(!assocMap[e.user_id]) assocMap[e.user_id]={
      name:e.name, Picking:0,Packing:0,RSR:0,Receiving:0,
      total:0, wks:{}
    };
    const a=assocMap[e.user_id];
    a.total += e.error_qty;
    a[e.category] += e.error_qty;
    const k=`${e.year}-${e.week}`;
    a.wks[k]=(a.wks[k]||0)+e.error_qty;
  });
  const sorted=Object.entries(assocMap).sort((a,b)=>b[1].total-a[1].total);
  if(!sorted.length){
    document.getElementById('q-leaderboard').innerHTML=
      '<p class="p-8 text-center text-gray-400">No errors for current filters.</p>';
    return;
  }
  const cats=['Picking','Packing','RSR','Receiving'];
  let h='<table class="w-full"><thead><tr>';
  h+='<th class="text-center">Rank</th><th class="text-left" style="min-width:160px">Associate</th>';
  h+='<th class="text-right">Total Qty</th>';
  cats.forEach(cat=>{
    h+=`<th class="text-right" style="color:${Q_CAT_CLR[cat]}">${cat}</th>`;
  });
  h+='<th>Error Rate<br><span style="font-weight:400;font-size:.65rem">per 1k units</span></th>';
  qw.forEach(w=>h+=`<th>${w.label}<br><span style="font-weight:400;font-size:.62rem">${w.week_start}</span></th>`);
  h+='</tr></thead><tbody>';
  sorted.forEach(([uid,a],i)=>{
    const pickProd = Object.entries(Q.production.picking[uid]||{}).reduce((s,[k,v])=>{
      const [fy,wk]=k.split('-').map(Number);
      return getQWeeks().some(w=>w.year===fy&&w.week===wk)?s+v:s;
    },0);
    const packProd = Object.entries(Q.production.packing[uid]||{}).reduce((s,[k,v])=>{
      const [fy,wk]=k.split('-').map(Number);
      return getQWeeks().some(w=>w.year===fy&&w.week===wk)?s+v:s;
    },0);
    const denom = pickProd + packProd;
    const rate  = denom>0 ? ((a.total/denom)*1000).toFixed(2) : '—';
    const rateClr= denom>0&&(a.total/denom)*1000>5 ? '#ea1100' : '#2a8703';
    const bg = i===0?'background:#fff8e1':i===1?'background:#f9fafb':i===2?'background:#fff7ed':'';
    h+=`<tr style="${bg}">`;
    h+=`<td class="text-center font-black text-lg" style="color:${i<3?'#f59e0b':'#9ca3af'}">${i+1}</td>`;
    h+=`<td class="font-semibold">${assocLbl(uid)}</td>`;
    h+=`<td class="text-right font-bold text-red-700">${a.total.toLocaleString()}</td>`;
    cats.forEach(cat=>{
      const v=a[cat]||0;
      h+=`<td class="text-right">${v>0?`<span class="pill" style="background:${Q_CAT_LIGHT[cat]};color:${Q_CAT_CLR[cat]}">${v}</span>`:'<span class="text-gray-300">0</span>'}</td>`;
    });
    h+=`<td class="text-center font-bold" style="color:${rateClr}">${rate}</td>`;
    qw.forEach(w=>{
      const v=a.wks[qWkKey(w)]||0;
      const bg=v===0?'#f9fafb':v<=2?'#fef9c3':v<=5?'#ffedd5':'#fee2e2';
      const fg=v===0?'#d1d5db':v<=2?'#92400e':v<=5?'#9a3412':'#7f1d1d';
      h+=`<td class="text-center" style="background:${bg};color:${fg};font-weight:${v>0?700:400}">${v||'—'}</td>`;
    });
    h+='</tr>';
  });
  h+=`</tbody></table>`;
  h+=`<p class="px-3 pt-2 text-xs text-gray-400">${sorted.length} associate${sorted.length!==1?'s':''} with errors. Error rate = total errors / (units picked + units packed) × 1,000.</p>`;
  document.getElementById('q-leaderboard').innerHTML=h;
}

// --- Detail log ---
function renderQDetail(errs){
  const sorted=[...errs].sort((a,b)=>b.date.localeCompare(a.date));
  if(!sorted.length){
    document.getElementById('q-detail').innerHTML=
      '<p class="p-8 text-center text-gray-400">No errors for current filters.</p>';
    return;
  }
  const hdrs=['Date','WM Week','Associate','Category','Error Type','Qty','Shift','Non-Punitive','Notes'];
  let h='<table class="w-full"><thead><tr>'+hdrs.map(x=>`<th>${x}</th>`).join('')+'</tr></thead><tbody>';
  sorted.forEach(e=>{
    const wk=`FY${e.year}-W${String(e.week).padStart(2,'0')}`;
    const catClr=Q_CAT_CLR[e.category]||'#374151';
    h+=`<tr>
      <td>${e.date}</td>
      <td class="font-mono text-xs">${wk}</td>
      <td>${assocLbl(e.user_id)}</td>
      <td><span class="pill" style="background:${Q_CAT_LIGHT[e.category]||'#f3f4f6'};color:${catClr}">${e.category}</span></td>
      <td>${e.error_desc}</td>
      <td class="text-right font-bold">${e.error_qty}</td>
      <td>${e.shift||'—'}</td>
      <td class="text-center">${e.non_punitive?'<span style="color:#f97316;font-weight:700">NP</span>':''}</td>
      <td class="text-gray-500 text-xs">${e.notes||''}</td>
    </tr>`;
  });
  h+=`</tbody></table>`;
  h+=`<p class="px-3 pt-2 text-xs text-gray-400">${sorted.length.toLocaleString()} error events shown.</p>`;
  document.getElementById('q-detail').innerHTML=h;
}

// --- CSV export ---
function downloadQCSV(){
  const errs=getQErrors().sort((a,b)=>b.date.localeCompare(a.date));
  const esc=s=>{s=String(s);return s.includes(',')||s.includes('"')||s.includes('\n')?`"${s.replace(/"/g,'""')}"`:s;};
  const cols=[
    {h:'DATE',          fn:e=>e.date},
    {h:'WM_WEEK',       fn:e=>`FY${e.year}-W${String(e.week).padStart(2,'0')}`},
    {h:'USER_ID',       fn:e=>e.user_id},
    {h:'NAME',          fn:e=>e.name},
    {h:'SHIFT',         fn:e=>e.shift},
    {h:'CATEGORY',      fn:e=>e.category},
    {h:'ERROR_CODE',    fn:e=>e.error_code},
    {h:'ERROR_DESC',    fn:e=>e.error_desc},
    {h:'ERROR_QTY',     fn:e=>e.error_qty},
    {h:'NON_PUNITIVE',  fn:e=>e.non_punitive?'Y':'N'},
    {h:'NOTES',         fn:e=>e.notes},
  ];
  const csv='\uFEFF'+cols.map(c=>c.h).join(',')+'\n'
    +errs.map(e=>cols.map(c=>esc(c.fn(e))).join(',')).join('\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8;'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download='TPA_Quality_Errors.csv';a.style.display='none';
  document.body.appendChild(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(url);document.body.removeChild(a);},500);
}

// --- Main quality render ---
function renderQ(){
  const errs=getQErrors();
  renderQKPIs(errs);
  renderQTrend(errs);
  renderQDonut(errs);
  renderQLeaderboard(errs);
  renderQDetail(errs);
}
"""
