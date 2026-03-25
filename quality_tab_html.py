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
      <select id="qf-cat" onchange="onQFilter()">
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
    <button onclick="downloadQCSV()" class="px-4 py-2 rounded-lg text-sm font-semibold text-white flex items-center gap-2"
      style="background:var(--wm-blue)" onmouseover="this.style.background='#0047c4'" onmouseout="this.style.background='var(--wm-blue)'">
      &#128229; Export Errors CSV
    </button>
  </div>

  <!-- KPI cards (always visible) -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5" id="q-kpis"></div>

  <!-- Charts row (always visible) -->
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

  <!-- ============================================================ -->
  <!-- ASSOCIATE PROFILE (shown only when an associate is selected) -->
  <!-- ============================================================ -->
  <div id="q-assoc-profile" class="hidden">

    <!-- Banner: name + summary KPIs -->
    <div class="bg-white rounded-2xl shadow p-5 mb-4" id="q-assoc-banner"></div>

    <!-- Row 1: weekly trend (2/3) + category donut (1/3) -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-4">
      <div class="xl:col-span-2 bg-white rounded-2xl shadow p-5">
        <h2 class="font-bold text-sm text-gray-600 mb-2">&#128200; Weekly Errors vs Team Average</h2>
        <p class="text-xs text-gray-400 mb-2">Associate error qty per week (red) against the per-associate team average (dashed blue).</p>
        <div style="height:260px"><canvas id="q-chart-assoc-trend"></canvas></div>
      </div>
      <div class="bg-white rounded-2xl shadow p-5">
        <h2 class="font-bold text-sm text-gray-600 mb-2">&#127775; Error Category Mix</h2>
        <p class="text-xs text-gray-400 mb-2">Breakdown of this associate's errors by category.</p>
        <div style="height:260px"><canvas id="q-chart-assoc-donut"></canvas></div>
      </div>
    </div>

    <!-- Row 2: top error types bar (1/2) + week-by-week table (1/2) -->
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-4">
      <div class="bg-white rounded-2xl shadow p-5">
        <h2 class="font-bold text-sm text-gray-600 mb-2">&#9888;&#65039; Top Error Types</h2>
        <p class="text-xs text-gray-400 mb-2">Top 8 error types by total quantity.</p>
        <div style="height:260px"><canvas id="q-chart-assoc-bar"></canvas></div>
      </div>
      <div class="bg-white rounded-2xl shadow p-5">
        <h2 class="font-bold text-sm text-gray-600 mb-2">&#128197; Week-by-Week Breakdown</h2>
        <p class="text-xs text-gray-400 mb-2">Error quantities and rate per 1,000 units processed each week.</p>
        <div class="overflow-x-auto" id="q-assoc-week-table"></div>
      </div>
    </div>

  </div>
  <!-- END ASSOCIATE PROFILE -->

  <!-- Leaderboard (hidden when associate is selected) -->
  <div id="q-leaderboard-wrap" class="bg-white rounded-2xl shadow p-5 mb-5">
    <h2 class="font-bold text-sm text-gray-600 mb-3">Associate Error Leaderboard &#8212; Past 13 Weeks</h2>
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
