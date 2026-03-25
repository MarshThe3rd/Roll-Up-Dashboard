# FC TPA — Associate Productivity & Quality Dashboard

A self-contained, single-file HTML dashboard that tracks associate UPH
performance and quality/error data across all SC codes for a Walmart FC
Fulfillment Center TPA operation.

> **This repository is the canonical template.** Copy it to adapt for a
> different FC or to rebuild after a data-schema change.

---

## What It Produces

| Tab | Description |
|---|---|
| **Weekly View** | 13-week UPH table per associate, colour-coded vs adjusted goal. Flags associates below goal in 4+ weeks. |
| **Daily View** | Same data exploded to individual work days. |
| **Quality & Errors** | 13-week error event breakdown from the Access DB. Team trend chart, leaderboard, event log, and CSV export. Associate profile panel when an associate is selected. |

Filters (top bar): Super Department → SC Code → Associate + Week range.

---

## Architecture

```
BigQuery (DRAX_VM)
  ├─ query_perf_13wk.sql    → tpa_associate_performance_13weeks.csv
  ├─ query_assoc_names.sql  → tpa_associates.csv
  ├─ query_lifetime.sql     → tpa_lifetime_hours.csv
  └─ query3.sql             → tpa_sc_codes_goals.csv

Access DB (\\{server}\Shipping\6253ErrorDB.accdb)
  └─ fetch_quality_data.py  → quality payload (embedded JSON)

process_data.py
  reads CSVs + queries Access DB
  applies training curve
  → html_builder.py  +  quality_tab_html.py  +  quality_tab_js.py
  → TPA_Productivity_Dashboard.html   (single self-contained file)
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Via `.venv` (created by `uv`) |
| `uv` | `pip install uv` or via Artifactory |
| `pyodbc` | Installed in `.venv`; needed for Access DB |
| BigQuery access | Requires `gcloud auth login` and access to `wmt-drax-prod.DRAX_VM` |
| `bq` CLI | Part of Google Cloud SDK |
| Microsoft Access Driver | 64-bit ODBC driver on Windows |
| Corporate network (VPN/Eagle) | Required for BQ, Access DB, and all Walmart services |

### One-time venv setup

```cmd
uv venv
.venv\Scripts\activate
uv pip install pyodbc --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple --allow-insecure-host pypi.ci.artifacts.walmart.com
```

---

## Running the Dashboard

### Step 1 — Pull data from BigQuery

Run the PowerShell batch files in order:

```cmd
run_assoc.bat       # associate roster  -> tpa_associates.csv
run_perf.bat        # 13-week perf data -> tpa_associate_performance_13weeks.csv
run_lifetime.bat    # all-time hours    -> tpa_lifetime_hours.csv
```

Or use the combined runner:
```cmd
fetch_13weeks.ps1
```

### Step 2 — Generate the dashboard

```cmd
run_dashboard.bat
```

This calls `.venv\Scripts\python.exe process_data.py`, which:
1. Loads the four CSVs
2. Applies goal normalisation + training curve
3. Connects to the Access error DB (step skipped gracefully if unreachable)
4. Writes `TPA_Productivity_Dashboard.html`
5. Opens the file in your default browser

> The HTML is gitignored (contains PII). Regenerate it from source files any time.

---

## Adapting for a Different FC or Site

### 1. Change the FC identifier

In every `.sql` file and in `process_data.py`, replace `'TPA'` with your FC ID:
```sql
WHERE p.FC_ID = 'YOUR_FC'
```
```python
# process_data.py — top of file
PERF_CSV  = os.path.join(DATA_DIR, "YOUR_FC_associate_performance_13weeks.csv")
# etc.
```

### 2. Update BQ table references (if needed)

The queries reference `wmt-drax-prod.DRAX_VM.*`. If your site uses a
different project or dataset, update the FROM / JOIN clauses.

### 3. Update the Access DB path

In `fetch_quality_data.py`:
```python
DB_PATH = r"\\your-server\your-share\YourErrorDB.accdb"
DB_PWD  = "your_password"
```

### 4. Map error codes to categories

In `fetch_quality_data.py`, update the `ERROR_CATEGORIES` dict:
```python
ERROR_CATEGORIES = {
    "Picking":   [1, 2, 20],   # error_code values
    "Packing":   [3, 4, 5],
    "RSR":       [6, 7, 8, 9, 10, 11, 12],
    "Receiving": [13, 14, 15, 16, 17, 18, 19],
}
```
Also update the column names in `_load_errors()` if your DB schema differs.

### 5. Goal overrides

Known BQ data errors can be patched in `process_data.py`:
```python
GOAL_OVERRIDES = [
    {
        "sc_code":       "018055008",
        "fy_week_start": (2026, 44),
        "fy_week_end":   (2027, 3),
        "correct_goal":  15,
    },
]
```

---

## Training Curve Logic

Adjusted UPH goal is multiplied by a ramp factor based on the associate’s
total lifetime hours worked in that SC code **before the performance week**.

| Lifetime Hours | Goal Multiplier |
|---|---|
| 0 – 40 h | 25% |
| 41 – 80 h | 50% |
| 81 – 120 h | 75% |
| 121 – 160 h | 90% |
| 160+ h | 100% |

**Pick super-department**: training is tracked per-SC independently (no
cross-SC carry-over).

**All other super-departments**: hours carry over across SC codes within
the same super-department, capped at 90% goal outside the associate’s
home super-department.

---

## Flagging Logic

An associate is flagged (🚩) in the weekly table when:
- They are **below 100% of their adjusted goal** in **4 or more** of the
  13 weeks, AND
- Their **most recent week is also below goal**.

---

## File Reference

| File | Purpose |
|---|---|
| `process_data.py` | Main pipeline — loads CSVs, applies curve, builds payload |
| `html_builder.py` | HTML template + injects embedded JSON + quality modules |
| `quality_tab_html.py` | Quality tab HTML markup (injected at build time) |
| `quality_tab_js.py` | Quality tab JavaScript (injected at build time) |
| `fetch_quality_data.py` | Access DB connector + fiscal-week calculations |
| `run_dashboard.bat` | One-click dashboard generator (uses `.venv` Python) |
| `query_perf_13wk.sql` | BQ: 13-week performance by day, fiscal week, goals |
| `query_assoc_names.sql` | BQ: active associate roster with home SC and shift |
| `query_lifetime.sql` | BQ: all-time hours per associate per SC code |
| `query3.sql` | BQ: SC code definitions (area, super dept, goal, UOM) |
| `run_perf.bat` | Runs `query_perf_13wk.sql` via `bq` CLI → CSV |
| `run_assoc.bat` | Runs `query_assoc_names.sql` via `bq` CLI → CSV |
| `run_lifetime.bat` | Runs `query_lifetime.sql` via `bq` CLI → CSV |
| `fetch_13weeks.ps1` | PowerShell wrapper to run all BQ queries in sequence |
| `sample_data/COLUMN_FORMATS.md` | CSV schema reference with example rows |

---

## Fiscal Calendar

Walmart FY starts are hardcoded in both `query_perf_13wk.sql` and
`fetch_quality_data.py`. Update `FY_STARTS` in `fetch_quality_data.py`
and the `wm_fiscal_cal` CTE in the SQL when a new fiscal year begins:

```python
# fetch_quality_data.py
FY_STARTS = [
    (2025, date(2024, 2,  3)),
    (2026, date(2025, 2,  1)),
    (2027, date(2026, 1, 31)),
    # Add (2028, date(2027, 2, 1)) etc.
]
```

---

## Data Security

- Generated HTML (`TPA_Productivity_Dashboard.html`) is **gitignored** — it
  contains associate names and performance data (PII).
- Raw CSV exports are **gitignored** (`*.csv`).
- All computation happens locally; no data leaves your machine or Walmart’s
  network.
- This dashboard is approved for use on Eagle/VPN. Do **not** share the
  generated HTML outside the corporate network.

---

## Contributing / Updating

1. Make changes to the relevant `.py` files.
2. Run `run_dashboard.bat` to verify the build is clean.
3. Commit with a descriptive message and push to `master`.
4. **Never force-push to master.**

```cmd
git add -A
git commit -m "feat|fix|style|chore: short description"
git push origin master
```

---

*Generated by Code Puppy 🐶 — questions? Ping #element-genai-support on Slack.*
