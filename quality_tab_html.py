"""
Quality Tab — HTML markup injected into the main dashboard template.
Kept separate to prevent html_builder.py exceeding 600 lines.
"""

QUALITY_HTML = r"""
<!-- ================================================================ -->
<!-- QUALITY TAB SECTION                                               -->
<!-- ================================================================ -->
<div id="quality-section" class="hidden">

  <!-- Quality-specific filter bar -->
  <div class="bg-white rounded-2xl shadow p-4 mb-5 flex flex-wrap gap-3 items-end">
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1" for="qf-cat">Category</label>
      <select id="qf-cat" class="" onchange="onQFilter()">
        <option value="">All Categories</option>
        <option value="Picking">Picking</option>
        <option value="Packing">Packing</option>
        <option value="RSR">RSR (Pallet)</option>
        <option value="Receiving">Receiving</option>
      </select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1" for="qf-code">Error Type</label>
      <select id="qf-code" onchange="onQFilter()"></select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-gray-500 mb-1" for="qf-shift">Shift</label>
      <select id="qf-shift" onchange="onQFilter()">
        <option value="">All Shifts</option>
      </select>
    </div>
    <div class="flex items-center gap-2 pt-4">
      <input type="checkbox" id="qf-np" onchange="onQFilter()" class="w-4 h-4 accent-blue-700">
      <label for="qf-np" class="text-sm font-semibold text-gray-600">Include Non-Punitive</label>
    </div>
    <button onclick="resetQFilters()" class="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm font-semibold">Reset</button>
    <button onclick="downloadQCSV()" class="px-4 py-2 rounded-lg text-sm font-semibold text-white flex items-center gap-2" style="background:var(--wm-blue)" onmouseover="this.style.background='#0047c4'" onmouseout="this.style.background='var(--wm-blue)'">
      &#128229; Export Errors CSV
    </button>
  </div>

  <!-- KPI cards -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5" id="q-kpis"></div>

  <!-- Charts row -->
  <div class="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">
    <div class="xl:col-span-2 bg-white rounded-2xl shadow p-5">
      <h2 class="font-bold text-sm text-gray-600 mb-3">Weekly Error Count by Category (13 Weeks)</h2>
      <div style="height:270px"><canvas id="q-chart-trend"></canvas></div>
    </div>
    <div class="bg-white rounded-2xl shadow p-5">
      <h2 class="font-bold text-sm text-gray-600 mb-3">Errors by Type</h2>
      <div style="height:270px"><canvas id="q-chart-donut"></canvas></div>
    </div>
  </div>

  <!-- Associate leaderboard -->
  <div class="bg-white rounded-2xl shadow p-5 mb-5">
    <h2 class="font-bold text-sm text-gray-600 mb-3">Associate Error Leaderboard — Past 13 Weeks</h2>
    <div class="overflow-x-auto"><div id="q-leaderboard"></div></div>
  </div>

  <!-- Detail log -->
  <div class="bg-white rounded-2xl shadow p-5">
    <h2 class="font-bold text-sm text-gray-600 mb-1">Error Event Log</h2>
    <p class="text-xs text-gray-400 mb-3">Most recent first. Filtered by all active selections above and on the main filter bar.</p>
    <div class="overflow-x-auto"><div id="q-detail"></div></div>
  </div>

</div>
<!-- END QUALITY TAB SECTION -->
"""
