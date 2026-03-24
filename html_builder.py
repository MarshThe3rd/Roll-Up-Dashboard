"""
HTML Dashboard Builder for TPA Productivity Dashboard
Generates a fully self-contained HTML file with embedded JSON data.
"""
import json


def _pct_color(pct):
    """Return Tailwind-ish inline style color for a pct_to_goal value."""
    if pct is None:
        return "#9ca3af"  # gray
    if pct >= 100:
        return "#2a8703"  # Walmart green
    if pct >= 90:
        return "#f59e0b"  # amber
    if pct >= 80:
        return "#f97316"  # orange
    return "#ea1100"  # Walmart red


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TPA FC — Associate Productivity Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #f9fafb; }
  .wm-blue { color: #0053e2; }
  .bg-wm-blue { background-color: #0053e2; }
  .wm-spark { color: #ffc220; }
  .bg-wm-spark { background-color: #ffc220; }
  .cell-green  { background-color: #dcfce7; color: #166534; font-weight: 600; }
  .cell-amber  { background-color: #fef9c3; color: #854d0e; font-weight: 600; }
  .cell-orange { background-color: #ffedd5; color: #9a3412; font-weight: 600; }
  .cell-red    { background-color: #fee2e2; color: #991b1b; font-weight: 600; }
  .cell-gray   { background-color: #f3f4f6; color: #6b7280; }
  .flag-badge  { background:#ea1100; color:#fff; border-radius:4px; padding:1px 6px; font-size:0.68rem; font-weight:700; }
  .train-badge { background:#ffc220; color:#1c1c1c; border-radius:4px; padding:1px 6px; font-size:0.68rem; font-weight:700; }
  .sticky-col  { position: sticky; left: 0; background: #fff; z-index: 5; }
  .sticky-col2 { position: sticky; left: 120px; background: #fff; z-index: 5; }
  table { border-collapse: collapse; }
  th, td { white-space: nowrap; padding: 4px 10px; border: 1px solid #e5e7eb; font-size: 0.82rem; }
  thead th { background: #0053e2; color: #fff; }
  tr:hover td { background-color: #eff6ff !important; }
  .tab-btn { cursor: pointer; padding: 8px 20px; border-radius: 6px 6px 0 0; font-weight: 600; }
  .tab-btn.active { background: #0053e2; color: #fff; }
  .tab-btn:not(.active) { background: #e5e7eb; color: #374151; }
  select, input { border: 1px solid #d1d5db; border-radius: 6px; padding: 5px 10px; font-size: 0.85rem; }
  .chart-wrap { position:relative; height:280px; }
  ::-webkit-scrollbar { height: 8px; width: 6px; }
  ::-webkit-scrollbar-thumb { background: #0053e2; border-radius: 4px; }
  .superdept-pill { border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; font-weight: 700; }
</style>
</head>
<body class="text-gray-800">

<!-- HEADER -->
<header class="bg-wm-blue text-white shadow-lg">
  <div class="max-w-screen-2xl mx-auto px-4 py-3 flex items-center gap-4">
    <div class="bg-wm-spark rounded-full w-9 h-9 flex items-center justify-center text-xl font-black text-gray-900">W</div>
    <div>
      <h1 class="text-lg font-bold leading-tight">FC TPA — Associate Productivity Dashboard</h1>
      <p class="text-xs opacity-80">13-Week Rolling Performance | UPH Goals with Training Curve Adjustment</p>
    </div>
    <div class="ml-auto text-xs opacity-70" id="last-updated"></div>
  </div>
</header>

<!-- FILTERS -->
<div class="max-w-screen-2xl mx-auto px-4 py-3 bg-white shadow-sm border-b">
  <div class="flex flex-wrap gap-3 items-end">
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">Super Department</label>
      <select id="filter-superdept" class="min-w-[160px]">
        <option value="">All Super Depts</option>
      </select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">SC Code / Department</label>
      <select id="filter-sc" class="min-w-[220px]">
        <option value="">All SC Codes</option>
      </select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">Associate ID</label>
      <select id="filter-assoc" class="min-w-[160px]">
        <option value="">All Associates</option>
      </select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1">Flagged Only</label>
      <select id="filter-flagged" class="min-w-[130px]">
        <option value="">All</option>
        <option value="1">❗ Flagged (&lt;100% x4+)</option>
      </select>
    </div>
    <button onclick="resetFilters()" class="ml-auto px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold">Reset Filters</button>
  </div>
</div>

<!-- SUMMARY CARDS -->
<div class="max-w-screen-2xl mx-auto px-4 py-4">
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4" id="summary-cards"></div>

  <!-- TREND CHART -->
  <div class="bg-white rounded-xl shadow p-4 mb-4" id="chart-section">
    <h2 class="font-bold text-sm text-gray-600 mb-2">Weekly Avg % to Adjusted Goal — Trend (13 Weeks)</h2>
    <div class="chart-wrap"><canvas id="trend-chart"></canvas></div>
  </div>

  <!-- TABS -->
  <div class="flex gap-1 mb-0">
    <button class="tab-btn active" id="tab-weekly" onclick="switchTab('weekly')">Weekly View</button>
    <button class="tab-btn" id="tab-daily" onclick="switchTab('daily')">Daily View</button>
  </div>

  <div class="bg-white shadow rounded-b-xl rounded-tr-xl overflow-x-auto" id="table-container">
    <div id="table-content"></div>
  </div>

  <p class="text-xs text-gray-400 mt-2">
    ❗ Flagged: below 100% adjusted goal in 4+ of 13 weeks AND in most recent week.
    Training multipliers: 0–40 hrs=25% • 41–80 hrs=50% • 81–120 hrs=75% • 120+ hrs=100%.
    Pick super-dept uses per-SC-code independent training. Cross-dept cap=90%.
  </p>
</div>

<script>
// ============================================================
// EMBEDDED DATA
// ============================================================
const DATA = __DATA_PLACEHOLDER__;

// ============================================================
// STATE
// ============================================================
let activeTab = 'weekly';
let trendChart = null;

const filters = { superdept: '', sc: '', assoc: '', flagged: '' };

// ============================================================
// HELPERS
// ============================================================
function pctCell(pct) {
  if (pct == null) return '<td class="cell-gray text-center">—</td>';
  let cls = pct >= 100 ? 'cell-green' : pct >= 90 ? 'cell-amber' : pct >= 80 ? 'cell-orange' : 'cell-red';
  return `<td class="${cls} text-right">${pct.toFixed(1)}%</td>`;
}

function fmtNum(v, dec=1) {
  if (v == null || isNaN(v)) return '—';
  return Number(v).toFixed(dec);
}

function weekLabel(w) {
  return `FY${w.year}-W${String(w.week).padStart(2,'0')}`;
}

function getSuperdeptColor(sd) {
  const colors = {
    'Pick': '#0053e2', 'Pack': '#7c3aed', 'Ship Dock': '#0891b2',
    'Receive': '#15803d', 'Stock': '#b45309', 'Stocking': '#b45309',
    'Inbound': '#65a30d', 'Orderfilling': '#c026d3', 'Support (OB)': '#6b7280',
    'Support': '#6b7280', 'Shipping': '#0891b2', 'General Support': '#6b7280',
  };
  return colors[sd] || '#374151';
}

// ============================================================
// INIT: Populate filter dropdowns
// ============================================================
function initFilters() {
  // Super depts
  const sds = [...new Set(Object.values(DATA.sc_codes).map(s => s.super_department))].sort();
  const sdSel = document.getElementById('filter-superdept');
  sds.forEach(sd => { if (sd) sdSel.innerHTML += `<option value="${sd}">${sd}</option>`; });

  populateSCFilter();
  populateAssocFilter();

  sdSel.addEventListener('change', e => { filters.superdept = e.target.value; onFilterChange(); });
  document.getElementById('filter-sc').addEventListener('change', e => { filters.sc = e.target.value; onFilterChange(); });
  document.getElementById('filter-assoc').addEventListener('change', e => { filters.assoc = e.target.value; onFilterChange(); });
  document.getElementById('filter-flagged').addEventListener('change', e => { filters.flagged = e.target.value; onFilterChange(); });
}

function populateSCFilter() {
  const scSel = document.getElementById('filter-sc');
  const sd = filters.superdept;
  const scCodes = Object.entries(DATA.sc_codes)
    .filter(([, v]) => !sd || v.super_department === sd)
    .sort(([, a], [, b]) => a.department.localeCompare(b.department));
  scSel.innerHTML = '<option value="">All SC Codes</option>';
  scCodes.forEach(([sc, v]) => {
    scSel.innerHTML += `<option value="${sc}">${sc} — ${v.department}</option>`;
  });
}

function populateAssocFilter() {
  const assocSel = document.getElementById('filter-assoc');
  const filtered = getFilteredRows({ ignoreAssoc: true });
  const assocs = [...new Set(filtered.map(r => r.default_id))].sort();
  assocSel.innerHTML = '<option value="">All Associates</option>';
  assocs.forEach(a => { assocSel.innerHTML += `<option value="${a}">${a}</option>`; });
}

function resetFilters() {
  filters.superdept = ''; filters.sc = ''; filters.assoc = ''; filters.flagged = '';
  document.getElementById('filter-superdept').value = '';
  document.getElementById('filter-sc').value = '';
  document.getElementById('filter-assoc').value = '';
  document.getElementById('filter-flagged').value = '';
  populateSCFilter();
  populateAssocFilter();
  render();
}

function onFilterChange() {
  if (!filters.sc) populateSCFilter();
  populateAssocFilter();
  render();
}

// ============================================================
// FILTERING
// ============================================================
function getFilteredRows(opts = {}) {
  return DATA.rows.filter(r => {
    if (filters.superdept && r.SUPER_DEPARTMENT !== filters.superdept) return false;
    if (filters.sc && r.SC_CODE_ID !== filters.sc) return false;
    if (!opts.ignoreAssoc && filters.assoc && r.default_id !== filters.assoc) return false;
    return true;
  });
}

// ============================================================
// FLAGGING LOGIC
// Per README: flagged if below 100% adj goal in 4+ of 13 weeks
// AND below goal in the most recent week
// ============================================================
function computeFlags(rows) {
  // Group by (assoc, sc) -> week -> [{ADJUSTED_PCT_TO_GOAL, HOURS}]
  const groups = {};
  for (const r of rows) {
    if (r.ADJUSTED_PCT_TO_GOAL == null || r.GOAL == null) continue;
    const key = `${r.default_id}|||${r.SC_CODE_ID}`;
    if (!groups[key]) groups[key] = {};
    const wk = `${r.year}-${r.week}`;
    if (!groups[key][wk]) groups[key][wk] = [];
    groups[key][wk].push(r);
  }

  const sortedWeeks = DATA.weeks.map(w => `${w.year}-${w.week}`);
  const mostRecentWk = sortedWeeks[sortedWeeks.length - 1];

  const flags = new Set();
  for (const [key, weekMap] of Object.entries(groups)) {
    let belowCount = 0;
    let belowRecent = false;
    for (const wk of sortedWeeks) {
      if (!weekMap[wk]) continue;
      // Weighted avg pct for this week
      const hrs = weekMap[wk].reduce((s, r) => s + (r.HOURS || 0), 0);
      const wavg = weekMap[wk].reduce((s, r) => s + (r.ADJUSTED_PCT_TO_GOAL || 0) * (r.HOURS || 0), 0) / (hrs || 1);
      if (wavg < 100) {
        belowCount++;
        if (wk === mostRecentWk) belowRecent = true;
      }
    }
    if (belowCount >= 4 && belowRecent) flags.add(key);
  }
  return flags;
}

// ============================================================
// WEEKLY VIEW
// ============================================================
function renderWeeklyTable(rows, flags) {
  const weeks = DATA.weeks;

  // Group: (assoc, sc) -> week -> weighted avg pct
  const grouped = {};
  for (const r of rows) {
    if (r.GOAL == null) continue;
    const key = `${r.default_id}|||${r.SC_CODE_ID}`;
    if (!grouped[key]) grouped[key] = { assoc: r.default_id, sc: r.SC_CODE_ID, sd: r.SUPER_DEPARTMENT, dept: r.DEPARTMENT, wks: {} };
    const wk = `${r.year}-${r.week}`;
    if (!grouped[key].wks[wk]) grouped[key].wks[wk] = { sumPct: 0, sumHrs: 0, adjGoal: null, mult: null };
    const entry = grouped[key].wks[wk];
    if (r.ADJUSTED_PCT_TO_GOAL != null) {
      entry.sumPct += r.ADJUSTED_PCT_TO_GOAL * (r.HOURS || 0);
      entry.sumHrs += (r.HOURS || 0);
    }
    if (r.ADJUSTED_GOAL != null) entry.adjGoal = r.ADJUSTED_GOAL;
    if (r.TRAINING_MULTIPLIER != null) entry.mult = r.TRAINING_MULTIPLIER;
  }

  let combos = Object.values(grouped);

  // Filter flagged if needed
  if (filters.flagged === '1') {
    combos = combos.filter(c => flags.has(`${c.assoc}|||${c.sc}`));
  }

  combos.sort((a, b) => a.sd.localeCompare(b.sd) || a.dept.localeCompare(b.dept) || a.assoc.localeCompare(b.assoc));

  if (!combos.length) return '<p class="p-8 text-gray-400 text-center">No data for selected filters.</p>';

  let html = '<div class="overflow-x-auto"><table class="w-full">';
  // Header row
  html += '<thead><tr>';
  html += '<th class="sticky-col text-left">Associate</th>';
  html += '<th class="sticky-col2 text-left">SC Code / Dept</th>';
  html += '<th>Super Dept</th>';
  weeks.forEach(w => { html += `<th>${weekLabel(w)}<br><span class="text-xs opacity-70">${w.week_start}</span></th>`; });
  html += '<th>Weeks &lt;100%</th>';
  html += '</tr></thead><tbody>';

  for (const c of combos) {
    const flagged = flags.has(`${c.assoc}|||${c.sc}`);
    const sdColor = getSuperdeptColor(c.sd);
    html += '<tr>';
    html += `<td class="sticky-col">${c.assoc} ${flagged ? '<span class="flag-badge">❗ FLAG</span>' : ''}</td>`;
    html += `<td class="sticky-col2"><span class="font-mono text-xs text-gray-500">${c.sc}</span><br>${c.dept}</td>`;
    html += `<td><span class="superdept-pill" style="background:${sdColor}22;color:${sdColor}">${c.sd}</span></td>`;

    let belowCount = 0;
    for (const w of weeks) {
      const wk = `${w.year}-${w.week}`;
      const entry = c.wks[wk];
      if (!entry || entry.sumHrs === 0) {
        html += '<td class="cell-gray text-center">—</td>';
        continue;
      }
      const avg = entry.sumPct / entry.sumHrs;
      if (avg < 100) belowCount++;
      const multLabel = entry.mult != null && entry.mult < 1.0 ? `<br><span class="train-badge">${(entry.mult*100).toFixed(0)}%</span>` : '';
      let cls = avg >= 100 ? 'cell-green' : avg >= 90 ? 'cell-amber' : avg >= 80 ? 'cell-orange' : 'cell-red';
      html += `<td class="${cls} text-right">${avg.toFixed(1)}%${multLabel}</td>`;
    }
    html += `<td class="text-center font-bold ${belowCount >= 4 ? 'text-red-600' : 'text-gray-700'}">${belowCount}/13</td>`;
    html += '</tr>';
  }

  html += '</tbody></table></div>';
  html += `<p class="px-4 py-2 text-xs text-gray-400">Showing ${combos.length.toLocaleString()} associate × SC combinations. Cells show weighted avg adjusted % to goal. Training multiplier badge shown when &lt;100%.</p>`;
  return html;
}

// ============================================================
// DAILY VIEW
// ============================================================
function renderDailyTable(rows) {
  const filtered = filters.flagged === '1'
    ? rows.filter(r => {
        const flags = computeFlags(rows);
        return flags.has(`${r.default_id}|||${r.SC_CODE_ID}`);
      })
    : rows;

  const visible = filtered.filter(r => r.GOAL != null).sort(
    (a, b) => b.date.localeCompare(a.date) || a.SUPER_DEPARTMENT.localeCompare(b.SUPER_DEPARTMENT)
      || a.default_id.localeCompare(b.default_id)
  );

  if (!visible.length) return '<p class="p-8 text-gray-400 text-center">No data for selected filters.</p>';

  let html = '<div class="overflow-x-auto"><table class="w-full">';
  html += '<thead><tr>';
  [
    'Date','Week','Associate','SC Code','Department','Super Dept',
    'Hours','Volume','Goal (UOM)','Adj Goal','RPH',
    '% to Goal','Adj % Goal','Training Mult','Home Dept?','SC Hrs@WkStart'
  ].forEach(h => { html += `<th>${h}</th>`; });
  html += '</tr></thead><tbody>';

  for (const r of visible) {
    const sdColor = getSuperdeptColor(r.SUPER_DEPARTMENT);
    const wk = `FY${r.year}-W${String(r.week).padStart(2,'0')}`;
    html += '<tr>';
    html += `<td>${r.date}</td>`;
    html += `<td>${wk}</td>`;
    html += `<td>${r.default_id}</td>`;
    html += `<td class="font-mono text-xs">${r.SC_CODE_ID}</td>`;
    html += `<td>${r.DEPARTMENT || ''}</td>`;
    html += `<td><span class="superdept-pill" style="background:${sdColor}22;color:${sdColor}">${r.SUPER_DEPARTMENT || ''}</span></td>`;
    html += `<td class="text-right">${fmtNum(r.HOURS)}</td>`;
    html += `<td class="text-right">${r.VOLUME != null ? fmtNum(r.VOLUME, 0) : '—'}</td>`;
    html += `<td class="text-right">${r.GOAL != null ? r.GOAL : '—'} ${r.GOAL_UOM || ''}</td>`;
    html += `<td class="text-right">${r.ADJUSTED_GOAL != null ? fmtNum(r.ADJUSTED_GOAL, 2) : '—'}</td>`;
    html += `<td class="text-right">${r.RATE_PER_HOUR != null ? fmtNum(r.RATE_PER_HOUR, 1) : '—'}</td>`;
    html += pctCell(r.PCT_TO_GOAL);
    html += pctCell(r.ADJUSTED_PCT_TO_GOAL);
    const mult = r.TRAINING_MULTIPLIER;
    html += `<td class="text-center">${mult != null ? `<span class="${mult < 1 ? 'train-badge' : 'text-green-700 font-bold'}">${(mult*100).toFixed(0)}%</span>` : '—'}</td>`;
    html += `<td class="text-center">${r.IS_HOME_SUPERDEPT === 'Y' ? '✅' : r.IS_HOME_SUPERDEPT === 'N' ? '🔄' : '—'}</td>`;
    html += `<td class="text-right">${r.LIFETIME_SC_HOURS != null ? fmtNum(r.LIFETIME_SC_HOURS, 1) : '—'}</td>`;
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  html += `<p class="px-4 py-2 text-xs text-gray-400">Showing ${visible.length.toLocaleString()} rows. Sorted by date desc.</p>`;
  return html;
}

// ============================================================
// TREND CHART
// ============================================================
function renderTrendChart(rows) {
  const weeks = DATA.weeks;
  const weekMap = {};
  for (const r of rows) {
    if (r.ADJUSTED_PCT_TO_GOAL == null || r.GOAL == null) continue;
    const wk = `${r.year}-${r.week}`;
    if (!weekMap[wk]) weekMap[wk] = { sum: 0, hrs: 0 };
    weekMap[wk].sum += r.ADJUSTED_PCT_TO_GOAL * (r.HOURS || 0);
    weekMap[wk].hrs += r.HOURS || 0;
  }
  const labels = weeks.map(w => weekLabel(w));
  const data = weeks.map(w => {
    const wk = `${w.year}-${w.week}`;
    const e = weekMap[wk];
    return e && e.hrs > 0 ? parseFloat((e.sum / e.hrs).toFixed(2)) : null;
  });

  const ctx = document.getElementById('trend-chart').getContext('2d');
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Avg Adj % to Goal',
        data,
        borderColor: '#0053e2',
        backgroundColor: 'rgba(0,83,226,0.08)',
        tension: 0.35,
        fill: true,
        pointRadius: 5,
        pointBackgroundColor: data.map(v => v == null ? '#9ca3af' : v >= 100 ? '#2a8703' : v >= 90 ? '#f59e0b' : v >= 80 ? '#f97316' : '#ea1100'),
      }, {
        label: 'Goal (100%)',
        data: labels.map(() => 100),
        borderColor: '#ffc220',
        borderWidth: 2,
        borderDash: [6, 4],
        pointRadius: 0,
        fill: false,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top' }, tooltip: { mode: 'index' } },
      scales: {
        y: { min: 0, max: 160, ticks: { callback: v => v + '%' }, title: { display: true, text: 'Adj % to Goal' } },
        x: { title: { display: true, text: 'Fiscal Week' } }
      }
    }
  });
}

// ============================================================
// SUMMARY CARDS
// ============================================================
function renderSummaryCards(rows) {
  const withGoal = rows.filter(r => r.ADJUSTED_PCT_TO_GOAL != null);
  const totalHrs = withGoal.reduce((s, r) => s + (r.HOURS || 0), 0);
  const avgPct = totalHrs > 0
    ? withGoal.reduce((s, r) => s + (r.ADJUSTED_PCT_TO_GOAL || 0) * (r.HOURS || 0), 0) / totalHrs
    : null;
  const assocSet = new Set(rows.map(r => r.default_id));
  const scSet = new Set(rows.filter(r => r.GOAL != null).map(r => r.SC_CODE_ID));

  // Flagged count
  const flags = computeFlags(rows);
  const flaggedAssocs = new Set([...flags].map(k => k.split('|||')[0]));

  const cards = [
    { label: 'Associates', value: assocSet.size.toLocaleString(), color: '#0053e2' },
    { label: 'SC Codes w/ Goals', value: scSet.size.toLocaleString(), color: '#7c3aed' },
    { label: 'Avg Adj % to Goal', value: avgPct != null ? avgPct.toFixed(1) + '%' : '—',
      color: avgPct == null ? '#6b7280' : avgPct >= 100 ? '#2a8703' : avgPct >= 90 ? '#f59e0b' : '#ea1100' },
    { label: 'Flagged Associates', value: flaggedAssocs.size.toLocaleString(), color: '#ea1100' },
  ];

  document.getElementById('summary-cards').innerHTML = cards.map(c => `
    <div class="bg-white rounded-xl shadow p-4 border-l-4" style="border-color:${c.color}">
      <div class="text-2xl font-black" style="color:${c.color}">${c.value}</div>
      <div class="text-xs text-gray-500 mt-1">${c.label}</div>
    </div>`).join('');
}

// ============================================================
// TABS
// ============================================================
function switchTab(tab) {
  activeTab = tab;
  document.getElementById('tab-weekly').className = 'tab-btn' + (tab === 'weekly' ? ' active' : '');
  document.getElementById('tab-daily').className = 'tab-btn' + (tab === 'daily' ? ' active' : '');
  render();
}

// ============================================================
// MAIN RENDER
// ============================================================
function render() {
  const rows = getFilteredRows();
  renderSummaryCards(rows);
  renderTrendChart(rows);
  const flags = computeFlags(rows);
  if (activeTab === 'weekly') {
    document.getElementById('table-content').innerHTML = renderWeeklyTable(rows, flags);
  } else {
    document.getElementById('table-content').innerHTML = renderDailyTable(rows);
  }
}

// ============================================================
// BOOT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('last-updated').textContent =
    'Generated: ' + new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
  initFilters();
  render();
});
</script>
</body>
</html>
""".strip()


def build_html(payload):
    json_data = json.dumps(payload, separators=(',', ':'))
    return HTML_TEMPLATE.replace('__DATA_PLACEHOLDER__', json_data)
