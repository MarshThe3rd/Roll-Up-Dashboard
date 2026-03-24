"""
HTML Dashboard Builder — TPA Associate Productivity
Generates a fully self-contained HTML file with embedded JSON data.
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
<style>
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f3f4f6; }
  /* ---------- Walmart brand tokens ---------- */
  :root {
    --wm-blue:  #0053e2;
    --wm-blue2: #0047c4;
    --wm-spark: #ffc220;
    --wm-green: #2a8703;
    --wm-red:   #ea1100;
  }
  /* ---------- Table ---------- */
  table { border-collapse: collapse; font-size: 0.8rem; }
  th, td { padding: 5px 11px; border: 1px solid #e5e7eb; white-space: nowrap; }
  thead th { background: var(--wm-blue); color: #fff; font-weight: 700; position: sticky; top: 0; z-index: 2; }
  tbody tr:hover td { background: #eff6ff !important; }
  .sticky-1 { position: sticky; left: 0;    background: #fff; z-index: 3; }
  .sticky-2 { position: sticky; left: 176px; background: #fff; z-index: 3; }
  thead .sticky-1, thead .sticky-2 { z-index: 10; }
  /* ---------- Performance cells ---------- */
  .c-green  { background:#dcfce7; color:#14532d; font-weight:700; }
  .c-amber  { background:#fef9c3; color:#713f12; font-weight:700; }
  .c-orange { background:#ffedd5; color:#7c2d12; font-weight:700; }
  .c-red    { background:#fee2e2; color:#7f1d1d; font-weight:700; }
  .c-gray   { background:#f9fafb; color:#9ca3af; }
  /* ---------- Badges ---------- */
  .badge-flag  { background:var(--wm-red);   color:#fff; border-radius:3px; padding:1px 5px; font-size:.68rem; font-weight:800; }
  .badge-train { background:var(--wm-spark); color:#1c1c1c; border-radius:3px; padding:1px 5px; font-size:.65rem; font-weight:700; }
  /* ---------- Tabs ---------- */
  .tab-btn { cursor:pointer; padding:8px 22px; border-radius:8px 8px 0 0; font-weight:700; font-size:.85rem; border:none; }
  .tab-btn.active { background:var(--wm-blue); color:#fff; }
  .tab-btn:not(.active) { background:#e5e7eb; color:#374151; }
  /* ---------- Controls ---------- */
  select, input[type=text] {
    border:1px solid #d1d5db; border-radius:6px;
    padding:6px 10px; font-size:.85rem; background:#fff;
    min-width:160px;
  }
  select:focus, input:focus { outline:2px solid var(--wm-blue); outline-offset:1px; }
  /* ---------- Cards ---------- */
  .kpi-card { border-radius:12px; padding:16px 20px; background:#fff;
    box-shadow:0 1px 4px rgba(0,0,0,.08); border-left:5px solid; }
  /* ---------- Charts ---------- */
  .chart-box { position:relative; }
  /* ---------- Pill ---------- */
  .sd-pill { border-radius:999px; padding:1px 9px; font-size:.72rem; font-weight:700; display:inline-block; }
  /* ---------- Scrollbars ---------- */
  ::-webkit-scrollbar { height:7px; width:5px; }
  ::-webkit-scrollbar-thumb { background:var(--wm-blue); border-radius:4px; }
</style>
</head>
<body>

<!-- ===== HEADER ===== -->
<header style="background:var(--wm-blue)" class="text-white shadow">
  <div class="max-w-screen-2xl mx-auto px-5 py-3 flex items-center gap-4">
    <div style="background:var(--wm-spark)" class="rounded-full w-10 h-10 flex items-center justify-center text-xl font-black text-gray-900 flex-shrink-0">W</div>
    <div>
      <h1 class="text-lg font-bold leading-tight">FC TPA — Associate Productivity Dashboard</h1>
      <p class="text-xs opacity-75">Previous 13 Walmart Fiscal Weeks &nbsp;·&nbsp; UPH Goals w/ Training Curve &nbsp;·&nbsp; FY2026-W48 through FY2027-W08</p>
    </div>
    <div class="ml-auto text-xs opacity-60" id="hdr-date"></div>
  </div>
</header>

<!-- ===== FILTERS ===== -->
<div class="max-w-screen-2xl mx-auto px-5 py-3 bg-white shadow-sm border-b">
  <div class="flex flex-wrap gap-3 items-end">
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">Super Department</label>
      <select id="f-sd"></select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">SC Code / Department</label>
      <select id="f-sc"></select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">Associate</label>
      <select id="f-assoc"></select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">Show</label>
      <select id="f-flag">
        <option value="">All Associates</option>
        <option value="1">❗ Flagged Only (&lt;100% x4+ wks)</option>
      </select>
    </div>
    <button onclick="resetFilters()" class="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold transition-colors">Reset</button>
  </div>
</div>

<!-- ===== MAIN ===== -->
<div class="max-w-screen-2xl mx-auto px-5 py-4">

  <!-- KPI Cards -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5" id="kpi-cards"></div>

  <!-- Chart section: switches between aggregate trend vs. associate deep-dive -->
  <div class="bg-white rounded-2xl shadow p-5 mb-5">
    <!-- Aggregate (no associate selected) -->
    <div id="chart-aggregate">
      <h2 class="font-bold text-sm text-gray-600 mb-3">Weekly Avg Adjusted % to Goal — All Filtered Associates (13 Weeks)</h2>
      <div class="chart-box" style="height:260px"><canvas id="chart-agg"></canvas></div>
    </div>
    <!-- Associate deep-dive (associate selected) -->
    <div id="chart-assoc" class="hidden">
      <div class="flex items-center justify-between mb-3">
        <div>
          <h2 class="font-bold text-base" id="chart-assoc-name"></h2>
          <p class="text-xs text-gray-500" id="chart-assoc-meta"></p>
        </div>
        <span id="chart-assoc-flag" class="text-sm"></span>
      </div>
      <!-- Per-SC trend chart -->
      <div class="chart-box mb-4" style="height:280px"><canvas id="chart-sc-trend"></canvas></div>
      <!-- Daily bar chart for selected associate -->
      <h3 class="font-semibold text-sm text-gray-600 mb-2">Daily Adjusted % to Goal (all SC codes combined)</h3>
      <div class="chart-box" style="height:200px"><canvas id="chart-daily-bar"></canvas></div>
    </div>
  </div>

  <!-- Tabs -->
  <div class="flex gap-1 mb-0">
    <button class="tab-btn active" id="tab-wk" onclick="switchTab('weekly')">Weekly View</button>
    <button class="tab-btn" id="tab-dy" onclick="switchTab('daily')">Daily View</button>
  </div>

  <div class="bg-white shadow rounded-b-2xl rounded-tr-2xl overflow-x-auto">
    <div id="tbl-content"></div>
  </div>

  <p class="text-xs text-gray-400 mt-2 leading-relaxed">
    Training multipliers: 0–40 hrs=25% &bull; 41–80 hrs=50% &bull; 81–120 hrs=75% &bull; 120+ hrs=100%.
    Pick super-dept: per-SC-code independent. All others: cross-SC carry-over, 90% cap when outside home super-dept.
    <span class="badge-flag">FLAG</span> = below 100% adj. goal in 4+ of 13 weeks AND in most recent week.
  </p>
</div>

<script>
// ===================================================================
// DATA
// ===================================================================
const DATA = __DATA_PLACEHOLDER__;

// ===================================================================
// STATE
// ===================================================================
let activeTab = 'weekly';
const charts = {};
const filters = { sd: '', sc: '', assoc: '', flag: '' };

// ===================================================================
// HELPERS
// ===================================================================
const SD_COLORS = {
  'Pick':'#0053e2','Pack':'#7c3aed','Ship Dock':'#0891b2','Receive':'#15803d',
  'Stock':'#92400e','Stocking':'#92400e','Inbound':'#65a30d',
  'Orderfilling':'#c026d3','Support (OB)':'#6b7280','Support':'#6b7280',
  'Shipping':'#0369a1','General Support':'#6b7280',
};
const SD_CHART_PALETTE = [
  '#0053e2','#ea1100','#2a8703','#ffc220','#7c3aed','#0891b2',
  '#c026d3','#f97316','#65a30d','#0369a1','#854d0e'
];

function sdColor(sd) { return SD_COLORS[sd] || '#374151'; }

function pctClass(p) {
  if (p == null) return 'c-gray';
  return p >= 100 ? 'c-green' : p >= 90 ? 'c-amber' : p >= 80 ? 'c-orange' : 'c-red';
}

function pctCell(p) {
  if (p == null) return `<td class="c-gray text-center">—</td>`;
  return `<td class="${pctClass(p)} text-right">${p.toFixed(1)}%</td>`;
}

function fmt(v, d=1) {
  return (v == null || isNaN(v)) ? '—' : Number(v).toFixed(d);
}

function wkLabel(w) {
  return `FY${w.year}-W${String(w.week).padStart(2,'0')}`;
}

function assocLabel(aid) {
  const a = DATA.associates[aid];
  if (!a) return aid;
  return a.name && a.name !== aid ? `${a.name} (${aid})` : aid;
}

// ===================================================================
// FLAGGING
// ===================================================================
function computeFlags(rows) {
  // Group (assoc, sc) -> week -> {sumPct, sumHrs}
  const g = {};
  for (const r of rows) {
    if (r.ADJUSTED_PCT_TO_GOAL == null || r.GOAL == null) continue;
    const key = `${r.default_id}|||${r.SC_CODE_ID}`;
    const wk  = `${r.year}-${r.week}`;
    if (!g[key]) g[key] = {};
    if (!g[key][wk]) g[key][wk] = { p: 0, h: 0 };
    g[key][wk].p += r.ADJUSTED_PCT_TO_GOAL * (r.HOURS || 0);
    g[key][wk].h += r.HOURS || 0;
  }
  const sortedWks = DATA.weeks.map(w => `${w.year}-${w.week}`);
  const mostRecent = sortedWks[sortedWks.length - 1];
  const flags = new Set();
  for (const [key, wkMap] of Object.entries(g)) {
    let below = 0, belowRecent = false;
    for (const wk of sortedWks) {
      if (!wkMap[wk] || wkMap[wk].h === 0) continue;
      const avg = wkMap[wk].p / wkMap[wk].h;
      if (avg < 100) { below++; if (wk === mostRecent) belowRecent = true; }
    }
    if (below >= 4 && belowRecent) flags.add(key);
  }
  return flags;
}

function isFlaggedAssoc(aid, rows) {
  const flags = computeFlags(rows);
  return [...flags].some(k => k.startsWith(aid + '|||'));
}

// ===================================================================
// FILTERING
// ===================================================================
function getRows(opts = {}) {
  return DATA.rows.filter(r => {
    if (filters.sd   && r.SUPER_DEPARTMENT !== filters.sd) return false;
    if (filters.sc   && r.SC_CODE_ID       !== filters.sc) return false;
    if (!opts.skipAssoc && filters.assoc   && r.default_id !== filters.assoc) return false;
    return true;
  });
}

// ===================================================================
// FILTER UI INIT
// ===================================================================
function initFilters() {
  // Super depts
  const sds = [...new Set(Object.values(DATA.sc_codes).map(s => s.super_department))]
    .filter(Boolean).sort();
  const sdSel = document.getElementById('f-sd');
  sdSel.innerHTML = '<option value="">All Super Depts</option>';
  sds.forEach(sd => { sdSel.innerHTML += `<option value="${sd}">${sd}</option>`; });

  refreshSCDropdown();
  refreshAssocDropdown();

  sdSel.addEventListener('change', e => { filters.sd = e.target.value; filters.sc = ''; refreshSCDropdown(); onFilter(); });
  document.getElementById('f-sc').addEventListener('change', e => { filters.sc = e.target.value; onFilter(); });
  document.getElementById('f-assoc').addEventListener('change', e => { filters.assoc = e.target.value; onFilter(); });
  document.getElementById('f-flag').addEventListener('change', e => { filters.flag = e.target.value; onFilter(); });
}

function refreshSCDropdown() {
  const codes = Object.entries(DATA.sc_codes)
    .filter(([, v]) => !filters.sd || v.super_department === filters.sd)
    .sort(([, a], [, b]) => a.department.localeCompare(b.department));
  const sel = document.getElementById('f-sc');
  sel.innerHTML = '<option value="">All SC Codes</option>';
  codes.forEach(([sc, v]) => {
    sel.innerHTML += `<option value="${sc}">${sc} — ${v.department}</option>`;
  });
  if (filters.sc) sel.value = filters.sc;
}

function refreshAssocDropdown() {
  const rows = getRows({ skipAssoc: true });
  let assocSet;
  if (filters.flag === '1') {
    const flags = computeFlags(rows);
    assocSet = new Set([...flags].map(k => k.split('|||')[0]));
  } else {
    assocSet = new Set(rows.map(r => r.default_id));
  }
  const sorted = [...assocSet].sort((a, b) => assocLabel(a).localeCompare(assocLabel(b)));
  const sel = document.getElementById('f-assoc');
  sel.innerHTML = '<option value="">All Associates</option>';
  sorted.forEach(aid => {
    sel.innerHTML += `<option value="${aid}">${assocLabel(aid)}</option>`;
  });
  if (filters.assoc && !assocSet.has(filters.assoc)) filters.assoc = '';
  if (filters.assoc) sel.value = filters.assoc;
}

function onFilter() {
  refreshAssocDropdown();
  render();
}

function resetFilters() {
  Object.assign(filters, { sd: '', sc: '', assoc: '', flag: '' });
  document.getElementById('f-sd').value = '';
  document.getElementById('f-sc').value = '';
  document.getElementById('f-assoc').value = '';
  document.getElementById('f-flag').value = '';
  refreshSCDropdown();
  refreshAssocDropdown();
  render();
}

// ===================================================================
// KPI CARDS
// ===================================================================
function renderKPIs(rows) {
  const withGoal = rows.filter(r => r.ADJUSTED_PCT_TO_GOAL != null);
  const totalH = withGoal.reduce((s, r) => s + (r.HOURS || 0), 0);
  const avgPct = totalH > 0
    ? withGoal.reduce((s, r) => s + r.ADJUSTED_PCT_TO_GOAL * (r.HOURS || 0), 0) / totalH
    : null;
  const flags = computeFlags(rows);
  const flaggedAssocs = new Set([...flags].map(k => k.split('|||')[0]));
  const assocSet = new Set(rows.map(r => r.default_id));
  const scSet    = new Set(rows.filter(r => r.GOAL != null).map(r => r.SC_CODE_ID));
  const color = avgPct == null ? '#6b7280' : avgPct >= 100 ? '#2a8703' : avgPct >= 90 ? '#f59e0b' : '#ea1100';
  const cards = [
    { label:'Associates',          val: assocSet.size,                    col:'#0053e2' },
    { label:'SC Codes w/ Goals',   val: scSet.size,                       col:'#7c3aed' },
    { label:'Avg Adj % to Goal',   val: avgPct != null ? avgPct.toFixed(1)+'%' : '—', col: color },
    { label:'Flagged Associates',  val: flaggedAssocs.size,               col:'#ea1100' },
  ];
  document.getElementById('kpi-cards').innerHTML = cards.map(c =>
    `<div class="kpi-card" style="border-color:${c.col}">
       <div class="text-3xl font-black" style="color:${c.col}">${typeof c.val === 'number' ? c.val.toLocaleString() : c.val}</div>
       <div class="text-xs text-gray-500 mt-1">${c.label}</div>
     </div>`
  ).join('');
}

// ===================================================================
// CHARTS — AGGREGATE TREND
// ===================================================================
function renderAggChart(rows) {
  const weekMap = {};
  for (const r of rows) {
    if (r.ADJUSTED_PCT_TO_GOAL == null || r.GOAL == null) continue;
    const wk = `${r.year}-${r.week}`;
    if (!weekMap[wk]) weekMap[wk] = { p: 0, h: 0 };
    weekMap[wk].p += r.ADJUSTED_PCT_TO_GOAL * (r.HOURS || 0);
    weekMap[wk].h += r.HOURS || 0;
  }
  const labels = DATA.weeks.map(wkLabel);
  const vals = DATA.weeks.map(w => {
    const e = weekMap[`${w.year}-${w.week}`];
    return e && e.h > 0 ? parseFloat((e.p / e.h).toFixed(2)) : null;
  });
  const ptColors = vals.map(v =>
    v == null ? '#9ca3af' : v >= 100 ? '#2a8703' : v >= 90 ? '#f59e0b' : v >= 80 ? '#f97316' : '#ea1100'
  );
  destroyChart('agg');
  charts['agg'] = new Chart(document.getElementById('chart-agg').getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label:'Avg Adj % to Goal', data: vals, borderColor:'#0053e2',
          backgroundColor:'rgba(0,83,226,.07)', fill:true, tension:.35,
          pointRadius:6, pointBackgroundColor: ptColors },
        { label:'100% Goal', data: labels.map(()=>100), borderColor:'#ffc220',
          borderWidth:2, borderDash:[7,4], pointRadius:0, fill:false },
      ]
    },
    options: chartOpts('Adj % to Goal', 0, 160)
  });
}

// ===================================================================
// CHARTS — ASSOCIATE DEEP-DIVE
// ===================================================================
function renderAssocCharts(aid, rows) {
  const a = DATA.associates[aid] || {};
  const name = a.name && a.name !== aid ? a.name : aid;
  document.getElementById('chart-assoc-name').textContent = name;
  document.getElementById('chart-assoc-meta').textContent =
    `ID: ${aid}  |  Home SC: ${a.home_code || '—'}  |  Home Dept: ${a.home_superdept || '—'}  |  Shift: ${a.shift || '—'}`;

  const flags = computeFlags(rows);
  const flagged = isFlaggedAssoc(aid, rows);
  document.getElementById('chart-assoc-flag').innerHTML = flagged
    ? '<span class="badge-flag">❗ FLAGGED</span>' : '<span class="text-green-600 font-bold text-xs">&#10003; On Track</span>';

  // ---- Per-SC weekly trend ----
  const assocRows = rows.filter(r => r.default_id === aid && r.GOAL != null);
  const scCodes = [...new Set(assocRows.map(r => r.SC_CODE_ID))];

  // (sc, week) -> weighted avg pct
  const scWeekPct = {};
  for (const r of assocRows) {
    const k = `${r.SC_CODE_ID}||${r.year}-${r.week}`;
    if (!scWeekPct[k]) scWeekPct[k] = { p:0, h:0 };
    scWeekPct[k].p += (r.ADJUSTED_PCT_TO_GOAL || 0) * (r.HOURS || 0);
    scWeekPct[k].h += r.HOURS || 0;
  }

  const labels = DATA.weeks.map(wkLabel);
  const scDatasets = scCodes.map((sc, i) => {
    const info = DATA.sc_codes[sc] || {};
    const data = DATA.weeks.map(w => {
      const k = `${sc}||${w.year}-${w.week}`;
      const e = scWeekPct[k];
      return e && e.h > 0 ? parseFloat((e.p / e.h).toFixed(2)) : null;
    });
    return {
      label: `${info.department || sc}`,
      data,
      borderColor: SD_CHART_PALETTE[i % SD_CHART_PALETTE.length],
      backgroundColor: 'transparent',
      tension: .3, pointRadius: 5,
      spanGaps: true,
    };
  });
  // Goal line
  scDatasets.push({ label:'100% Goal', data: labels.map(()=>100),
    borderColor:'#ffc220', borderWidth:2, borderDash:[7,4], pointRadius:0, fill:false });

  destroyChart('sc-trend');
  charts['sc-trend'] = new Chart(document.getElementById('chart-sc-trend').getContext('2d'), {
    type: 'line',
    data: { labels, datasets: scDatasets },
    options: chartOpts('Adj % to Goal by SC Code', 0, 200)
  });

  // ---- Daily bar chart ----
  // all SC codes combined, by date
  const dayMap = {};
  for (const r of assocRows) {
    if (!dayMap[r.date]) dayMap[r.date] = { p:0, h:0 };
    dayMap[r.date].p += (r.ADJUSTED_PCT_TO_GOAL || 0) * (r.HOURS || 0);
    dayMap[r.date].h += r.HOURS || 0;
  }
  const days = Object.keys(dayMap).sort();
  const dayVals = days.map(d => dayMap[d].h > 0 ? parseFloat((dayMap[d].p / dayMap[d].h).toFixed(2)) : null);
  const dayColors = dayVals.map(v =>
    v == null ? '#9ca3af' : v >= 100 ? '#2a8703' : v >= 90 ? '#f59e0b' : v >= 80 ? '#f97316' : '#ea1100'
  );

  destroyChart('daily-bar');
  charts['daily-bar'] = new Chart(document.getElementById('chart-daily-bar').getContext('2d'), {
    type: 'bar',
    data: {
      labels: days,
      datasets: [
        { label:'Daily Adj % to Goal', data: dayVals, backgroundColor: dayColors },
        { label:'100% Goal', data: days.map(()=>100), type:'line',
          borderColor:'#ffc220', borderWidth:2, borderDash:[6,4], pointRadius:0, fill:false },
      ]
    },
    options: chartOpts('Adj % to Goal', 0, 200)
  });
}

function chartOpts(yLabel, yMin, yMax) {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { position:'top', labels:{ boxWidth:12 } }, tooltip:{ mode:'index', intersect:false } },
    scales: {
      y: { min: yMin, suggestedMax: yMax,
           ticks: { callback: v => v+'%' },
           title: { display: true, text: yLabel } },
      x: { title: { display: true } }
    }
  };
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

// ===================================================================
// WEEKLY TABLE
// ===================================================================
function renderWeeklyTable(rows, flags) {
  // Build (assoc, sc) groups
  const g = {};
  for (const r of rows) {
    if (r.GOAL == null) continue;
    const key = `${r.default_id}|||${r.SC_CODE_ID}`;
    if (!g[key]) g[key] = { aid: r.default_id, sc: r.SC_CODE_ID, sd: r.SUPER_DEPARTMENT, dept: r.DEPARTMENT, wks: {} };
    const wk = `${r.year}-${r.week}`;
    if (!g[key].wks[wk]) g[key].wks[wk] = { p:0, h:0, mult:null };
    const e = g[key].wks[wk];
    if (r.ADJUSTED_PCT_TO_GOAL != null) { e.p += r.ADJUSTED_PCT_TO_GOAL*(r.HOURS||0); e.h += r.HOURS||0; }
    if (r.TRAINING_MULTIPLIER != null)  e.mult = r.TRAINING_MULTIPLIER;
  }

  let combos = Object.values(g);
  if (filters.flag === '1') combos = combos.filter(c => flags.has(`${c.aid}|||${c.sc}`));
  combos.sort((a,b) => a.sd.localeCompare(b.sd) || a.dept.localeCompare(b.dept) || assocLabel(a.aid).localeCompare(assocLabel(b.aid)));

  if (!combos.length) return '<p class="p-10 text-gray-400 text-center text-sm">No data for the current filters.</p>';

  let html = '<table class="w-full">';
  html += '<thead><tr>';
  html += `<th class="sticky-1 text-left" style="min-width:176px">Associate</th>`;
  html += `<th class="sticky-2 text-left" style="min-width:210px">SC Code / Department</th>`;
  html += '<th>Super Dept</th>';
  DATA.weeks.forEach(w => html += `<th>${wkLabel(w)}<br><span style="font-weight:400;font-size:.68rem">${w.week_start}</span></th>`);
  html += '<th>Wks &lt;100%</th></tr></thead><tbody>';

  for (const c of combos) {
    const flagged = flags.has(`${c.aid}|||${c.sc}`);
    const col = sdColor(c.sd);
    html += '<tr>';
    html += `<td class="sticky-1">${assocLabel(c.aid)} ${flagged ? '<span class="badge-flag">❗ FLAG</span>' : ''}</td>`;
    html += `<td class="sticky-2"><span class="font-mono text-xs text-gray-400">${c.sc}</span><br>${c.dept}</td>`;
    html += `<td><span class="sd-pill" style="background:${col}22;color:${col}">${c.sd}</span></td>`;

    let below = 0;
    for (const w of DATA.weeks) {
      const e = c.wks[`${w.year}-${w.week}`];
      if (!e || e.h === 0) { html += '<td class="c-gray text-center">—</td>'; continue; }
      const avg = e.p / e.h;
      if (avg < 100) below++;
      const multBadge = e.mult != null && e.mult < 1
        ? `<br><span class="badge-train">${(e.mult*100).toFixed(0)}%</span>` : '';
      html += `<td class="${pctClass(avg)} text-right">${avg.toFixed(1)}%${multBadge}</td>`;
    }
    html += `<td class="text-center font-bold ${below >= 4 ? 'text-red-600' : 'text-gray-600'}">${below}/13</td>`;
    html += '</tr>';
  }
  html += '</tbody></table>';
  html += `<p class="px-4 py-2 text-xs text-gray-400">${combos.length.toLocaleString()} associate × SC combinations shown.</p>`;
  return html;
}

// ===================================================================
// DAILY TABLE
// ===================================================================
function renderDailyTable(rows, flags) {
  let visible = rows.filter(r => r.GOAL != null);
  if (filters.flag === '1') {
    visible = visible.filter(r => flags.has(`${r.default_id}|||${r.SC_CODE_ID}`));
  }
  visible.sort((a,b) => b.date.localeCompare(a.date) || a.SUPER_DEPARTMENT.localeCompare(b.SUPER_DEPARTMENT) || assocLabel(a.default_id).localeCompare(assocLabel(b.default_id)));

  if (!visible.length) return '<p class="p-10 text-gray-400 text-center text-sm">No data for the current filters.</p>';

  const headers = ['Date','WM Week','Name','User ID','SC Code','Department','Super Dept',
    'Hours','Volume','Goal','Adj Goal','RPH','% Goal','Adj % Goal','Train Mult','Home Dept?','SC Hrs@Start'];
  let html = '<table class="w-full"><thead><tr>';
  headers.forEach(h => html += `<th>${h}</th>`);
  html += '</tr></thead><tbody>';

  for (const r of visible) {
    const col = sdColor(r.SUPER_DEPARTMENT);
    const wk  = `FY${r.year}-W${String(r.week).padStart(2,'0')}`;
    const a   = DATA.associates[r.default_id] || {};
    html += '<tr>';
    html += `<td>${r.date}</td>`;
    html += `<td>${wk}</td>`;
    html += `<td>${a.name && a.name !== r.default_id ? a.name : '—'}</td>`;
    html += `<td class="font-mono text-xs">${r.default_id}</td>`;
    html += `<td class="font-mono text-xs">${r.SC_CODE_ID}</td>`;
    html += `<td>${r.DEPARTMENT || ''}</td>`;
    html += `<td><span class="sd-pill" style="background:${col}22;color:${col}">${r.SUPER_DEPARTMENT||''}</span></td>`;
    html += `<td class="text-right">${fmt(r.HOURS)}</td>`;
    html += `<td class="text-right">${r.VOLUME != null ? fmt(r.VOLUME,0) : '—'}</td>`;
    html += `<td class="text-right">${r.GOAL != null ? r.GOAL : '—'} ${r.GOAL_UOM||''}</td>`;
    html += `<td class="text-right">${r.ADJUSTED_GOAL != null ? fmt(r.ADJUSTED_GOAL,2) : '—'}</td>`;
    html += `<td class="text-right">${r.RATE_PER_HOUR != null ? fmt(r.RATE_PER_HOUR,1) : '—'}</td>`;
    html += pctCell(r.PCT_TO_GOAL);
    html += pctCell(r.ADJUSTED_PCT_TO_GOAL);
    const m = r.TRAINING_MULTIPLIER;
    html += `<td class="text-center">${m != null ? `<span class="${m<1?'badge-train':'text-green-700 font-bold'}">${(m*100).toFixed(0)}%</span>` : '—'}</td>`;
    html += `<td class="text-center">${r.IS_HOME_SUPERDEPT==='Y' ? '✅' : r.IS_HOME_SUPERDEPT==='N' ? '🔄' : '—'}</td>`;
    html += `<td class="text-right">${r.LIFETIME_SC_HOURS != null ? fmt(r.LIFETIME_SC_HOURS,1) : '—'}</td>`;
    html += '</tr>';
  }
  html += '</tbody></table>';
  html += `<p class="px-4 py-2 text-xs text-gray-400">${visible.length.toLocaleString()} rows shown. Sorted by date desc.</p>`;
  return html;
}

// ===================================================================
// TABS
// ===================================================================
function switchTab(tab) {
  activeTab = tab;
  document.getElementById('tab-wk').className = 'tab-btn' + (tab==='weekly'?' active':'');
  document.getElementById('tab-dy').className  = 'tab-btn' + (tab==='daily' ?' active':'');
  render();
}

// ===================================================================
// MAIN RENDER
// ===================================================================
function render() {
  const rows  = getRows();
  const flags = computeFlags(rows);

  renderKPIs(rows);

  // Toggle between aggregate trend vs. associate deep-dive
  if (filters.assoc) {
    document.getElementById('chart-aggregate').classList.add('hidden');
    document.getElementById('chart-assoc').classList.remove('hidden');
    renderAssocCharts(filters.assoc, getRows({ skipAssoc: true }));
  } else {
    document.getElementById('chart-aggregate').classList.remove('hidden');
    document.getElementById('chart-assoc').classList.add('hidden');
    renderAggChart(rows);
  }

  document.getElementById('tbl-content').innerHTML =
    activeTab === 'weekly' ? renderWeeklyTable(rows, flags) : renderDailyTable(rows, flags);
}

// ===================================================================
// BOOT
// ===================================================================
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('hdr-date').textContent = 'Generated: ' +
    new Date().toLocaleString('en-US', { dateStyle:'medium', timeStyle:'short' });
  initFilters();
  render();
});
</script>
</body>
</html>
""".strip()
