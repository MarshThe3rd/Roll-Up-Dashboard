# CSV Column Format Reference

All four CSV files are produced by the BigQuery batch runners (`run_*.bat`).
They are **gitignored** (contain PII). This document shows the expected
column structure with anonymised example rows so you can reproduce or
validate the format.

---

## `tpa_associates.csv`

Source query: `query_assoc_names.sql`  
Runner: `run_assoc.bat`

| Column | Type | Notes |
|---|---|---|
| `default_id` | string | Walmart associate ID (e.g. `a0b1cd2`) |
| `name` | string | Full display name |
| `home_code_id` | string | Home SC code (e.g. `018055001`) |
| `shift` | string | `A`, `B`, `C`, or blank |
| `agency_id` | string | Agency/vendor code or blank for direct |

**Example rows:**
```
default_id,name,home_code_id,shift,agency_id
a0b1cd2,Jane Smith,018055001,A,
b2c3de4,John Doe,018055003,B,AGENCY1
c4d5ef6,Alex Johnson,018055007,A,
```

---

## `tpa_associate_performance_13weeks.csv`

Source query: `query_perf_13wk.sql`  
Runner: `run_perf.bat`

| Column | Type | Notes |
|---|---|---|
| `default_id` | string | Associate ID |
| `NETWORK_NAME` | string | Network login name (fallback display) |
| `FC_ID` | string | Facility code, e.g. `TPA` |
| `date` | YYYY-MM-DD | Calendar date of work |
| `WM_FISCAL_YEAR` | int | Walmart fiscal year (e.g. `2027`) |
| `WM_FISCAL_WEEK` | int | Week within fiscal year, 1-indexed |
| `WM_FISCAL_WEEK_START` | YYYY-MM-DD | Monday of the fiscal week |
| `SC_CODE_ID` | string | 9-digit SC code worked |
| `HOME_CODE_ID` | string | Associate’s home SC code |
| `AREA` | string | Physical area within FC |
| `SUPER_DEPARTMENT` | string | e.g. `Pick`, `Pack`, `Receive` |
| `DEPARTMENT` | string | More specific department label |
| `HOURS` | float | Hours worked this row |
| `IDLE_HOURS` | float | Idle/non-productive hours |
| `VOLUME` | float | Units produced |
| `GOAL` | float | UPH goal for this SC code (from BQ goal table) |
| `GOAL_UOM` | string | Unit of measure, e.g. `UPH` |
| `RATE_PER_HOUR` | float | `VOLUME / HOURS` (computed by query) |
| `PCT_TO_GOAL` | float | `RATE_PER_HOUR / GOAL` as decimal (1.0 = 100%) |

**Example rows:**
```
default_id,NETWORK_NAME,FC_ID,date,WM_FISCAL_YEAR,WM_FISCAL_WEEK,WM_FISCAL_WEEK_START,SC_CODE_ID,HOME_CODE_ID,AREA,SUPER_DEPARTMENT,DEPARTMENT,HOURS,IDLE_HOURS,VOLUME,GOAL,GOAL_UOM,RATE_PER_HOUR,PCT_TO_GOAL
a0b1cd2,jsmith,TPA,2026-02-02,2027,1,2026-01-31,018055001,018055001,Mod A,Pick,Singles Pick,8.0,0.5,1240,160,UPH,155.0,0.96875
b2c3de4,jdoe,TPA,2026-02-02,2027,1,2026-01-31,018055003,018055003,Mod B,Pack,Packing,7.5,0.0,600,85,UPH,80.0,0.94118
```

---

## `tpa_lifetime_hours.csv`

Source query: `query_lifetime.sql`  
Runner: `run_lifetime.bat`

| Column | Type | Notes |
|---|---|---|
| `default_id` | string | Associate ID |
| `SC_CODE_ID` | string | SC code |
| `total_lifetime_hours` | float | All-time hours worked in this SC code |

> **Important:** This is the **all-time** total, not just the 13-week
> window. It is used to calculate training-curve multipliers.
> The query aggregates `SUM(HOURS)` with no date filter.

**Example rows:**
```
default_id,SC_CODE_ID,total_lifetime_hours
a0b1cd2,018055001,342.5
a0b1cd2,018055003,47.0
b2c3de4,018055003,890.25
```

---

## `tpa_sc_codes_goals.csv`

Source query: `query3.sql`  
*(No dedicated runner — run manually or via `run_query3.bat` if present)*

| Column | Type | Notes |
|---|---|---|
| `sc_code_id` | string | 9-digit SC code |
| `department` | string | Department label |
| `super_department` | string | Super-department group |
| `area` | string | Physical area |
| `unit_measure` | string | UOM label (e.g. `UPH`) |

> This is used as a **fallback/supplement** when BQ performance rows
> are missing department metadata. The primary source of goals is the
> `GOAL` column in the performance CSV.

**Example rows:**
```
sc_code_id,department,super_department,area,unit_measure
018055001,Singles Pick,Pick,Mod A,UPH
018055003,Packing,Pack,Mod B,UPH
018055007,Pallet Putaway,RSR,Dock,UPH
018055010,Receiving,Receive,Dock,UPH
```

---

## Quality / Error Data (Access DB)

This data is **not** sourced from a CSV. `fetch_quality_data.py`
connects directly to an MS Access database over a UNC share.

### Tables queried

| Table | Key columns |
|---|---|
| `PickingErrors` | `picker_user_id`, `prod_date`, `error_code`, `error_qty`, `shift`, `non_punitive`, `notes` |
| `PackingErrors` | `user_id`, `prod_date`, `error_code`, `error_qty`, `shift`, `non_punitive`, `notes` |
| `PalletMovementErrors` | `user_id`, `prod_date`, `error_code`, `error_qty`, `shift`, `non_punitive`, `notes` |
| `ReceivingErrors` | `user_id`, `prod_date`, `error_code`, `error_qty`, `shift`, `non_punitive`, `notes` |
| `PickingProduction` | `user_id`, `prod_date`, `units_picked` |
| `PackingProduction` | `user_id`, `prod_date`, `units_packed` |
| `ErrorCodes` | `error_code`, `description` |

### Error code category mapping

Edit `ERROR_CATEGORIES` in `fetch_quality_data.py` if your error DB
uses different code numbers:

```python
ERROR_CATEGORIES = {
    "Picking":   [1, 2, 20],
    "Packing":   [3, 4, 5],
    "RSR":       [6, 7, 8, 9, 10, 11, 12],
    "Receiving": [13, 14, 15, 16, 17, 18, 19],
}
```

---

## Notes on BigQuery Export Format

- All BQ CLI exports include a **UTF-8 BOM** (`\ufeff`). The loaders
  use `encoding="utf-8-sig"` to strip it automatically.
- Numeric columns exported as empty strings for `NULL` are handled
  via `_float()` / `_int()` helpers in `process_data.py`.
- Column names are **case-sensitive** as shown above.
