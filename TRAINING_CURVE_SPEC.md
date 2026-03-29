# Training Curve & Lifetime Hours — Complete Implementation Specification

> **Audience:** A developer or AI agent implementing this logic in a new project.
> This document is fully self-contained. Read it top-to-bottom before writing any code.
>
> **Source of truth:** `refresh_data.py` → `apply_training_curve()` (and supporting
> functions). This document reflects the logic as of **2026-03-09**.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Walmart Fiscal Calendar](#2-walmart-fiscal-calendar)
3. [Data Sources & Schema](#3-data-sources--schema)
4. [Full Pipeline Order](#4-full-pipeline-order)
5. [Step A — Goal Normalization](#5-step-a--goal-normalization)
6. [Step B — Hardcoded Goal Overrides](#6-step-b--hardcoded-goal-overrides)
7. [Step C — Training Curve (Core Logic)](#7-step-c--training-curve-core-logic)
   - [7.1 Lifetime Hours Lookup](#71-lifetime-hours-lookup)
   - [7.2 Hours-at-Week-Start Calculation](#72-hours-at-week-start-calculation)
   - [7.3 Training Tiers (Base Multiplier)](#73-training-tiers-base-multiplier)
   - [7.4 Super-Department Rules](#74-super-department-rules)
   - [7.5 SC-Independent Departments (e.g. Pick)](#75-sc-independent-departments-eg-pick)
   - [7.6 Cross-SC Departments (all others)](#76-cross-sc-departments-all-others)
   - [7.7 Adjusted Goal & % to Goal](#77-adjusted-goal--to-goal)
8. [Output Columns Reference](#8-output-columns-reference)
9. [Dashboard Aggregation Logic](#9-dashboard-aggregation-logic)
10. [Flagging Criteria](#10-flagging-criteria)
11. [Edge Cases & Gotchas](#11-edge-cases--gotchas)
12. [Constants Cheat Sheet](#12-constants-cheat-sheet)
13. [Pseudocode — Full apply_training_curve()](#13-pseudocode--full-apply_training_curve)

---

## 1. System Overview

This system tracks fulfillment-center associate production performance over a rolling
**13 Walmart fiscal weeks**. The core problem it solves: new associates take time to ramp
up, so holding them to 100% of the same goal as a veteran on day one would be unfair and
misleading. The **training curve** reduces the effective goal proportionally based on how
many hours the associate has accumulated in each SC code (department).

**Key principle:** goals are adjusted *downward for new associates*, NOT upward. A 25%
multiplier means the associate only needs to hit 25% of the normal goal to be considered
"at goal."

**Why Python, not SQL?** The training curve requires knowing lifetime hours *at the start
of each fiscal week*, which means looking back further than the 13-week query window.
This cross-window calculation cannot be done cleanly in a single SQL query, so all
training curve logic lives in Python post-processing.

---

## 2. Walmart Fiscal Calendar

### Key Rules

- **Week:** Saturday → Friday (7 days)
- **Fiscal year start:** The Saturday on or before February 1 of the starting calendar year
- **FY naming:** Named for the calendar year the FY *ends* in
  - e.g. FY2027 starts **Jan 31, 2026** and ends **Jan 29, 2027**
- **Week 53:** Some fiscal years have 53 weeks. In this project, W53 is merged into W01
  of the next FY for display purposes (Python + dashboard JS both do this).

### Reference FY Start Dates

| Fiscal Year | FY Start (Saturday) | FY End (Friday) |
|-------------|---------------------|-----------------|
| FY2026      | 2025-02-01          | 2026-01-30      |
| FY2027      | 2026-01-31          | 2027-01-29      |
| FY2028      | 2027-01-30          | 2028-01-28      |

### Python Implementation

```python
from datetime import date, timedelta

def wm_fiscal_year_start(cal_year: int) -> date:
    """
    Return the Saturday on or before Feb 1 of cal_year.
    This is the start of the WM FY that ENDS in cal_year + 1.
    """
    feb1 = date(cal_year, 2, 1)
    days_since_saturday = (feb1.weekday() - 5) % 7  # Monday=0, Saturday=5
    return feb1 - timedelta(days=days_since_saturday)


def get_wm_fiscal_week(d: date) -> tuple[int, int]:
    """Return (WM_FISCAL_YEAR, WM_FISCAL_WEEK) for a given date."""
    fy_start = wm_fiscal_year_start(d.year)
    if d < fy_start:
        fy_start = wm_fiscal_year_start(d.year - 1)
    days_diff = (d - fy_start).days
    week_num = (days_diff // 7) + 1
    fiscal_year = fy_start.year + 1  # FY named for the year it ENDS
    return fiscal_year, week_num
```

### BigQuery SQL Equivalent

```sql
-- Fiscal Year
EXTRACT(YEAR FROM LAST_DAY(DATE_SUB(date_col, INTERVAL 1 MONTH))) + 1 AS WM_FISCAL_YEAR,

-- Fiscal Week
DIV(
  DATE_DIFF(
    date_col,
    DATE_TRUNC(
      DATE(EXTRACT(YEAR FROM LAST_DAY(DATE_SUB(date_col, INTERVAL 1 MONTH))), 2, 1),
      WEEK(SATURDAY)
    ),
    DAY
  ), 7
) + 1 AS WM_FISCAL_WEEK
```

### W53 Merge Rule

> Any row where `WM_FISCAL_WEEK == 53` is treated as `WM_FISCAL_YEAR + 1, WM_FISCAL_WEEK = 1`.

Apply this in Python before processing, and again in the dashboard JavaScript:

```python
# Python
if int(row['WM_FISCAL_WEEK']) == 53:
    row['WM_FISCAL_YEAR'] = int(row['WM_FISCAL_YEAR']) + 1
    row['WM_FISCAL_WEEK'] = 1
```

```javascript
// JavaScript (dashboard)
if (Number(r.WM_FISCAL_WEEK) === 53) {
  r.WM_FISCAL_YEAR = Number(r.WM_FISCAL_YEAR) + 1;
  r.WM_FISCAL_WEEK = 1;
}
```

---

## 3. Data Sources & Schema

### 3.1 Performance Data (BigQuery)

**Table:** `wmt-drax-prod.DRAX_VM.VIEWS_ASSOCIATE_PERFORMANCE_DAY`  
Joined with: `EVENTS_ASSOCIATE` (hire date, name, home SC code), `INPUTS_DEPARTMENTGOAL` (rate goals)

One row = one associate × one SC code × one calendar date.

| Column | Type | Description |
|--------|------|-------------|
| `NETWORK_NAME` | str | Associate's network login |
| `FC_ID` | str | Fulfillment center ID (e.g. `TPA`) |
| `date` | date | Calendar date of work |
| `WM_FISCAL_YEAR` | int | WM fiscal year |
| `WM_FISCAL_WEEK` | int | WM fiscal week (1–53) |
| `name` | str | Associate display name |
| `default_id` | str | Associate unique ID (join key) |
| `SC_CODE_ID` | str | SC code worked in that row |
| `HOME_CODE_ID` | str | Associate's home SC code (from EVENTS_ASSOCIATE) |
| `AREA` | str | Work area |
| `SUPER_DEPARTMENT` | str | Super department grouping |
| `DEPARTMENT` | str | Department |
| `HOURS` | float | Hours worked (this associate, dept, day) |
| `IDLE_HOURS` | float | Total idle hours |
| `VOLUME` | float | Units processed |
| `GOAL` | float | Base rate goal (units/hr); NULL for support roles |
| `GOAL_UOM` | str | Unit of measure for the goal |
| `RATE_PER_HOUR` | float | `VOLUME / HOURS` (computed in SQL) |
| `PCT_TO_GOAL` | float | `(RATE_PER_HOUR / GOAL) × 100` (unadjusted) |
| `tenure_weeks` | int | `DATE_DIFF(date, HIRED_DATE, WEEK)` |

### 3.2 Lifetime Hours Lookup (BigQuery)

**Table:** `wmt-drax-prod.DRAX_VM.VIEWS_ASSOCIATE_PERFORMANCE_DAY`  
(Same table, but with **no date filter** — pulls all-time totals)

**Query:**
```sql
SELECT
  DEFAULT_ID,
  SC_CODE_ID,
  ROUND(SUM(HOURS), 2) AS LIFETIME_SC_HOURS
FROM `wmt-drax-prod.DRAX_VM.VIEWS_ASSOCIATE_PERFORMANCE_DAY`
WHERE FC_ID = 'TPA'
GROUP BY DEFAULT_ID, SC_CODE_ID
```

**Result:** One row per `(DEFAULT_ID, SC_CODE_ID)` with `LIFETIME_SC_HOURS` = all-time
hours worked by that associate in that SC code.

**Stored in:** `tpa-lifetime-sc-hours.csv`  
**Columns:** `DEFAULT_ID`, `SC_CODE_ID`, `LIFETIME_SC_HOURS`

> ⚠️ **Critical:** The lifetime query must use the same `FC_ID` filter as the
> performance query. Using all FCs would inflate hours for associates who work multiple FCs.

---

## 4. Full Pipeline Order

The post-processing pipeline **must run in this exact order**. Each step reads and
overwrites `tpa-13wk-combined.csv` in place.

```
[BigQuery]
  LIFETIME_HOURS_QUERY   → tpa-lifetime-sc-hours.csv   (all-time hours, no date filter)
  QUERY_TEMPLATE Part 1  → tpa-13wk-part1-tenure.csv   (first ~60% of date range)
  QUERY_TEMPLATE Part 2  → tpa-13wk-part2-tenure.csv   (remaining ~40% of date range)

[Python: combine_csvs()]
  part1 + part2          → tpa-13wk-combined.csv        (raw, no training columns)

[Python: normalize_weekly_goals()]    ← Step A
  Pins each (SC_CODE_ID, fiscal week) to the goal active on the FIRST day of that week.
  Overwrites tpa-13wk-combined.csv.

[Python: apply_goal_overrides()]      ← Step B
  Applies hardcoded corrections for known BQ data errors.
  Overwrites tpa-13wk-combined.csv.

[Python: apply_training_curve()]      ← Step C  ← THIS IS THE MAIN FOCUS
  Reads tpa-lifetime-sc-hours.csv + tpa-13wk-combined.csv.
  Adds LIFETIME_SC_HOURS, TOTAL_LIFETIME_SC_HOURS, IS_HOME_SUPERDEPT,
       TRAINING_MULTIPLIER, ADJUSTED_GOAL, ADJUSTED_PCT_TO_GOAL.
  Overwrites tpa-13wk-combined.csv.

[Python: build_dashboard()]
  Embeds tpa-13wk-combined.csv into a self-contained HTML file.
```

---

## 5. Step A — Goal Normalization

### Problem

`INPUTS_DEPARTMENTGOAL` is date-ranged — a goal can change mid-fiscal-week. When BigQuery
joins on `p.DATE BETWEEN g.ACTIVE_DATE AND g.INACTIVE_DATE`, a single
`(SC_CODE_ID, fiscal week)` can have rows with two different `GOAL` values.
This breaks weighted averages in the dashboard.

### Solution

For each `(SC_CODE_ID, WM_FISCAL_YEAR, WM_FISCAL_WEEK)` group:
1. Find the **earliest calendar date** in that group.
2. Use the `GOAL` from that earliest date as the **canonical goal** for the entire week.
3. Update all rows in that group that have a different `GOAL`.
4. Recompute `PCT_TO_GOAL = RATE_PER_HOUR / canonical_goal × 100` for changed rows.
5. If `TRAINING_MULTIPLIER` already exists (re-patching), also recompute
   `ADJUSTED_GOAL` and `ADJUSTED_PCT_TO_GOAL`.

### Rationale

> "Start-of-week goal" = what was the goal on Saturday when the week began?
> A goal change mid-week takes effect at the START of the *next* fiscal week.
> This preserves the historical intent of each week.

### Alternative Strategies (if you need to change this)

| Strategy | Implementation |
|----------|---------------|
| Start-of-week (current) | `canonical = goal_on_min(date)` |
| End-of-week | `canonical = goal_on_max(date)` |
| Per-day (no normalization) | Remove `normalize_weekly_goals()` call |
| Majority-vote by hours | Weight by `HOURS` column |

---

## 6. Step B — Hardcoded Goal Overrides

When `INPUTS_DEPARTMENTGOAL` contains a **known data error** for specific
`(SC_CODE_ID, fiscal year, fiscal week)` combinations, add an entry to `GOAL_OVERRIDES`.

Overrides run **after** normalization and take precedence over both the BQ value and
the normalized value.

### Override Format

```python
GOAL_OVERRIDES = [
    {
        "description": "Human-readable reason (appears in logs)",
        "added_by": "Name, YYYY-MM-DD",
        "sc_code": "018055008",          # SC_CODE_ID string to match
        "fy_weeks": [                    # List of (fiscal_year_int, week_int) tuples
            (2026, 44), (2026, 45), ...  # Every week that needs correcting
        ],
        "goal": 15,                      # Correct goal value (int or float)
    },
]
```

### What Gets Recomputed

For every row matching an override's `(sc_code, fy, wk)`:
- `GOAL` → override value
- `PCT_TO_GOAL` → `RATE_PER_HOUR / new_goal × 100`
- `ADJUSTED_GOAL` → `new_goal × TRAINING_MULTIPLIER` (only if `TRAINING_MULTIPLIER` exists)
- `ADJUSTED_PCT_TO_GOAL` → `RATE_PER_HOUR / ADJUSTED_GOAL × 100` (only if above exists)

### Current Active Override (as of 2026-03-09)

| SC Code | Department | Weeks | Wrong → Correct | Added By |
|---------|-----------|-------|-----------------|----------|
| `018055008` | Pallet Putaway | FY2026-W44 → FY2027-W03 | 38 → **15** | B. Humpton, 2026-03-04 |

---

## 7. Step C — Training Curve (Core Logic)

This is the heart of the system. Read this section very carefully.

### 7.1 Lifetime Hours Lookup

Load `tpa-lifetime-sc-hours.csv` into a dictionary:

```python
lifetime_hours: dict  # key: (DEFAULT_ID: str, SC_CODE_ID: str) -> total_hours: float
```

This represents the **all-time cumulative hours** an associate has ever worked in each
SC code at this FC (no date ceiling — as of the moment the query ran).

> ⚠️ **Key insight:** Because the query runs at the time of the refresh, and the
> 13-week window ends on the most recent Friday, `lifetime_hours` effectively includes
> all hours up through the end of the 13-week window (plus any hours after it, but those
> are negligible since the query runs shortly after the window closes).

### 7.2 Hours-at-Week-Start Calculation

This is the most important concept in the whole system. We need to know how many hours
an associate had accumulated in a given SC code **at the start of each fiscal week** —
not at the end of the window.

**Algorithm:**

```
For each unique (associate, SC_CODE_ID) pair:

  1. hours_in_window = sum of HOURS for this (associate, SC) across ALL rows in the 13wk CSV

  2. hours_before_window = lifetime_total - hours_in_window
     (these are all the hours the associate worked before the 13-week window started)

  3. sorted_weeks = all fiscal weeks in the window, sorted chronologically
     (format: "YYYY-WWW", e.g. "2026-W44", "2026-W45", ...)

  4. cumulative = hours_before_window
     For each week in sorted_weeks (in order):
         hours_at_week_start[(associate, SC, week)] = cumulative
         cumulative += hours_in_window_for_this_week
```

**Why this works:**
- Week 1's start hours = everything before the 13-week window
- Week 2's start hours = Week 1's start hours + Week 1's actual hours
- Week N's start hours = everything before the window + sum of weeks 1..N-1

**Result:**
```python
hours_at_week_start: dict
# key: (default_id: str, SC_CODE_ID: str, week_key: str) -> hours: float
# week_key format: "YYYY-WWW" e.g. "2026-W44"
```

**Week key construction:**
```python
week_key = f"{WM_FISCAL_YEAR}-W{int(WM_FISCAL_WEEK):02d}"
# Examples: "2026-W44", "2027-W01", "2026-W09"
```

**Sorting weeks chronologically:**
```python
sorted_weeks = sorted(
    all_weeks,
    key=lambda w: (int(w.split('-W')[0]), int(w.split('-W')[1]))
)
```

### 7.3 Training Tiers (Base Multiplier)

Given `hours_at_week_start` for a specific `(associate, SC_CODE, week)`, the base
multiplier is:

| Hours at Week Start | Multiplier | Interpretation |
|---------------------|------------|----------------|
| 0 – 40 hours        | **0.25**   | ~Week 1: only need 25% of goal |
| 41 – 80 hours       | **0.50**   | ~Week 2: need 50% of goal |
| 81 – 120 hours      | **0.75**   | ~Week 3: need 75% of goal |
| > 120 hours         | **1.00**   | Week 4+: full goal |

> **Boundary rule:** The check is `<= threshold`, so exactly 40 hours = 0.25,
> exactly 80 hours = 0.50, exactly 120 hours = 0.75, and 120.01+ hours = 1.00.

```python
TRAINING_TIERS = [
    (40,  0.25),
    (80,  0.50),
    (120, 0.75),
]
TRAINING_DEFAULT = 1.0

def get_training_multiplier(cumulative_hours: float) -> float:
    for threshold, multiplier in TRAINING_TIERS:
        if cumulative_hours <= threshold:
            return multiplier
    return TRAINING_DEFAULT
```

### 7.4 Super-Department Rules

There are two fundamentally different training models depending on the
`SUPER_DEPARTMENT` of the row being processed.

#### Determining Home Super Department

The associate's **home super department** is derived from their `HOME_CODE_ID`
(the SC code listed as their home code in `EVENTS_ASSOCIATE`), mapped through a
lookup built from the performance rows:

```python
# Step 1: Build SC_CODE_ID -> SUPER_DEPARTMENT lookup
sc_to_superdept = {}  # SC_CODE_ID -> SUPER_DEPARTMENT string
for row in rows:
    if row['SC_CODE_ID'] and row['SUPER_DEPARTMENT']:
        sc_to_superdept[row['SC_CODE_ID']] = row['SUPER_DEPARTMENT']

# Step 2: Map each associate's HOME_CODE_ID to a super department
assoc_home_superdept = {}  # default_id -> home SUPER_DEPARTMENT string
for row in rows:
    assoc = row['default_id']
    home_sc = row['HOME_CODE_ID']
    if assoc and home_sc and assoc not in assoc_home_superdept:
        home_sd = sc_to_superdept.get(home_sc, '')
        if home_sd:
            assoc_home_superdept[assoc] = home_sd
```

#### Is the Associate Outside Their Home Super Department?

```python
home_superdept = assoc_home_superdept.get(assoc, '')
is_outside_home_superdept = bool(
    home_superdept and sd and sd != home_superdept
)
```

Where `sd` = the `SUPER_DEPARTMENT` of the **current row** (i.e., the SC code being
worked *this row*).

### 7.5 SC-Independent Departments (e.g. Pick)

Some super departments track training **per SC code independently**. Being fully trained
in SC-A does NOT promote an associate to a higher tier when working SC-B, even if both
are in the same super department.

```python
SC_INDEPENDENT_SUPERDEPTS = {"Pick"}  # add more strings here as needed
```

**Rules for SC-independent departments (in priority order):**

1. **Base tier from current SC's hours** — `get_training_multiplier(hours_at_week_start
   for this associate + this specific SC_CODE + this week)`. No cross-SC promotion.
2. **Outside home super department + tier > 0.90** → cap at **0.90**.
   (Even fully-trained Pick associates get capped at 90% when working outside their
   home super department.)

```python
if sd in SC_INDEPENDENT_SUPERDEPTS:
    multiplier = get_training_multiplier(week_hours)  # already per-SC
    if is_outside_home_superdept and multiplier > 0.90:
        multiplier = 0.90
```

> **Note:** If `multiplier <= 0.90` and they're outside their home superdept, the
> lower base tier applies as-is (e.g. 0.25, 0.50, 0.75 stay unchanged).

### 7.6 Cross-SC Departments (all others)

For all super departments **not** in `SC_INDEPENDENT_SUPERDEPTS`:
training carries across SC codes within the same super department.

#### Pre-computation: fully_trained_in_superdept()

Before applying the rule, build a lookup of which `(associate, superdept)` pairs
have worked which SC codes across the **entire 13-week window**:

```python
# (associate, superdept) -> set of SC_CODE_IDs worked anywhere in the window
assoc_superdept_scs = defaultdict(set)
for row in rows:
    assoc = row['default_id']
    sc = row['SC_CODE_ID']
    sd = row['SUPER_DEPARTMENT']
    if assoc and sc and sd:
        assoc_superdept_scs[(assoc, sd)].add(sc)
```

Then define:

```python
def is_fully_trained_in_superdept(assoc: str, superdept: str, week_key: str) -> bool:
    """
    Returns True if the associate has >120 hours (at the start of week_key)
    in ANY SC code they have worked under this super department
    across the entire 13-week window.

    Fully trained in one SC = fully trained across the whole super department
    (for non-SC-independent departments only).
    """
    sc_codes = assoc_superdept_scs.get((assoc, superdept), set())
    for sc_code in sc_codes:
        hrs = hours_at_week_start.get((assoc, sc_code, week_key), 0)
        if hrs > 120:
            return True
    return False
```

> **Important nuance:** The check is `hrs > 120` (strictly greater), whereas the
> base tier boundary is `hrs <= 120` → 0.75 and `hrs > 120` → 1.00. They are
> consistent: 120 hours exactly = tier 0.75, NOT fully trained.

#### Rules for cross-SC departments (in priority order):

| Priority | Condition | Multiplier |
|----------|-----------|------------|
| 1 | Fully trained in ANY SC under current superdept **AND** working in home superdept | **1.00** |
| 2 | Fully trained in ANY SC under current superdept **AND** working OUTSIDE home superdept | **0.90** |
| 3 | NOT fully trained **AND** outside home superdept **AND** base tier > 0.90 | **0.90** |
| 4 | Everything else | base tier (0.25 / 0.50 / 0.75 / 1.00) |

```python
else:  # Cross-SC department
    if is_fully_trained_in_superdept(assoc, sd, week_key):
        if is_outside_home_superdept:
            multiplier = 0.90  # Rule 2: fully trained but outside home
        else:
            multiplier = 1.0   # Rule 1: fully trained AND at home
    elif is_outside_home_superdept and multiplier > 0.90:
        multiplier = 0.90      # Rule 3: not fully trained, outside home, cap it
    # else: Rule 4 — leave multiplier as the base tier from get_training_multiplier()
```

#### Why the 0.90 cap exists

The 0.90 cap represents a policy decision: associates working **outside their home
super department** are not expected to perform at full speed even if they are
technically trained, because unfamiliar environments carry inherent overhead.

> **Bugfix note (2026-03-09):** Before this fix, the `is_fully_trained_in_superdept`
> check was applied without checking `is_outside_home_superdept`. This incorrectly
> gave 1.00 to fully-trained associates working outside their home superdept.
> Always check `is_outside_home_superdept` BEFORE assigning 1.00.

### 7.7 Adjusted Goal & % to Goal

Once the final `multiplier` is determined:

```python
ADJUSTED_GOAL = GOAL * TRAINING_MULTIPLIER
ADJUSTED_PCT_TO_GOAL = (RATE_PER_HOUR / ADJUSTED_GOAL) * 100
```

**Edge cases:**
- If `GOAL` is empty/NULL (support roles, utility, etc.) → `ADJUSTED_GOAL` and
  `ADJUSTED_PCT_TO_GOAL` are both left as empty string (`""`).
- If `ADJUSTED_GOAL == 0` (e.g. `GOAL=0` and any multiplier) → `ADJUSTED_PCT_TO_GOAL`
  is left as empty string to avoid division by zero.
- If `RATE_PER_HOUR` is empty → both adjusted columns are empty.

**Precision:** Round to 2 decimal places:
```python
adj_goal = round(float(goal) * multiplier, 2)
adj_pct  = round((float(rate) / adj_goal) * 100, 2)
```

---

## 8. Output Columns Reference

### Added by Python Post-Processing

| Column | Type | Description |
|--------|------|-------------|
| `LIFETIME_SC_HOURS` | float | Hours in **this SC code** at the **start** of this fiscal week. This is the value used to determine the training tier. NOT the all-time total. |
| `TOTAL_LIFETIME_SC_HOURS` | float | All-time cumulative hours in this SC code (for human reference only; not used in calculations). |
| `IS_HOME_SUPERDEPT` | str | `"Y"` if the associate is working in their home super department; `"N"` if outside. Derived from `HOME_CODE_ID` → `sc_to_superdept` → compared to `SUPER_DEPARTMENT` of this row. |
| `TRAINING_MULTIPLIER` | float | Final applied multiplier: one of `0.25`, `0.50`, `0.75`, `0.90`, `1.00`. |
| `ADJUSTED_GOAL` | float | `GOAL × TRAINING_MULTIPLIER`. Empty if `GOAL` is missing. |
| `ADJUSTED_PCT_TO_GOAL` | float | `(RATE_PER_HOUR / ADJUSTED_GOAL) × 100`. Empty if goal or rate missing. |

---

## 9. Dashboard Aggregation Logic

The dashboard does NOT use per-row `ADJUSTED_PCT_TO_GOAL` directly for display.
It computes a **hours-weighted average** per associate per fiscal week:

```
Weekly % to Goal =
    Σ(ADJUSTED_PCT_TO_GOAL × HOURS) for all rows in that (associate, week)
    ÷ Σ(HOURS) for goal-eligible rows in that (associate, week)
```

**Goal-eligible rows only:** rows where `ADJUSTED_PCT_TO_GOAL` is non-null AND `HOURS > 0`.

Rows without a `GOAL` (support, utility roles) are **excluded from the weighted average**
but still appear in the raw data export.

```javascript
// JavaScript aggregation (from app.js)
if (row.ADJUSTED_PCT_TO_GOAL != null && hrs > 0) {
    w.weightedPct += row.ADJUSTED_PCT_TO_GOAL * hrs;  // numerator accumulator
    w.goalHours += hrs;                                // denominator accumulator
}
// Final:
w.avgPctToGoal = w.weightedPct / w.goalHours;  // hours-weighted average
```

---

## 10. Flagging Criteria

An associate is flagged for review if **both** conditions are met:

1. They were **below 100% of adjusted goal** in **4 or more** of the past 13 fiscal weeks.
2. They were **below adjusted goal** in the **most recent** fiscal week.

```python
isFlagged = (belowGoalWeeks >= 4) AND (recentWeekBelow == True)
```

**"Below goal"** = `avgPctToGoal < 100` for a given week.  
**Only weeks with goal-eligible data count** (weeks where `goalHours > 0`).

Associates with **no goal-eligible data** in any week are not flagged.

---

## 11. Edge Cases & Gotchas

### A. Associate has no lifetime hours entry

If `(default_id, SC_CODE_ID)` is not in the lifetime hours lookup, treat as `0`.
This means the associate is treated as brand-new in that SC code.

```python
lt_total = lifetime_hours.get((assoc, sc), 0)
```

### B. hours_before_window is negative

This should not happen in practice, but if `lifetime_total < hours_in_window`
(data inconsistency), `hours_before_window` will be negative. This would produce
negative `hours_at_week_start`, which would then fall in the 0–40 tier (0.25).
This is a reasonable safe fallback — treat negative as zero if you want to be explicit:

```python
hours_before_window = max(0.0, lt_total - total_in_window)
```

### C. Associate's HOME_CODE_ID not found in sc_to_superdept

If the associate's home SC code doesn't appear in any performance row's `SC_CODE_ID`
(e.g. their home code is inactive), `assoc_home_superdept.get(assoc, '')` returns `''`.
In this case `is_outside_home_superdept` will be `False` (because `home_superdept` is
falssy), so the associate is treated as if they ARE in their home superdept.
This is the safe default — we don't penalize associates for data gaps.

### D. Week key format consistency

Always zero-pad the week number to 2 digits:
```python
week_key = f"{WM_FISCAL_YEAR}-W{int(WM_FISCAL_WEEK):02d}"
# "2026-W04" NOT "2026-W4"
```
This ensures chronological sorting works correctly with standard string sort.

### E. TRAINING_MULTIPLIER column already exists (re-patching)

When `patch_normalize_goals.py` re-runs post-processing on an already-enriched CSV,
goal normalization and override functions check for the existence of `TRAINING_MULTIPLIER`
in the row and re-derive `ADJUSTED_GOAL` and `ADJUSTED_PCT_TO_GOAL` if it's present.
This avoids stale derived values after a goal correction.

### F. W53 must be handled BEFORE sorted_weeks is built

If you apply the W53 merge rule (53 → next FY W01) in Python, do it when reading rows,
before building `weekly_hours`, `hours_at_week_start`, or `sorted_weeks`. Otherwise
you'll have two different week keys for the same logical week.

### G. CSV type casting

`HOURS`, `RATE_PER_HOUR`, `GOAL`, `TRAINING_MULTIPLIER`, etc. are all stored as strings
in CSV. Always cast to `float` before arithmetic. Always handle empty string as missing:
```python
val = row.get('GOAL', '')
if val != '':
    goal_float = float(val)
```

### H. The 0.90 cap only applies if the base tier would exceed 0.90

For associates in tiers 0.25, 0.50, or 0.75 who are outside their home superdept,
the lower tier wins — they are NOT bumped UP to 0.90:
```python
elif is_outside_home_superdept and multiplier > 0.90:
    multiplier = 0.90
# ^^^ if multiplier == 0.75 and outside home, stays at 0.75 (0.75 < 0.90)
```

---

## 12. Constants Cheat Sheet

```python
# Training tier thresholds and multipliers
TRAINING_TIERS = [
    (40,  0.25),   # 0–40 hrs at week start  → 25% of goal
    (80,  0.50),   # 41–80 hrs at week start → 50% of goal
    (120, 0.75),   # 81–120 hrs at week start → 75% of goal
]
TRAINING_DEFAULT = 1.0  # >120 hrs at week start → 100% of goal

# Super departments that train per-SC-code (no cross-SC promotion)
SC_INDEPENDENT_SUPERDEPTS = {"Pick"}

# Cross-department cap — applied when working outside home super department
# and would otherwise get a higher multiplier
CROSS_DEPT_CAP = 0.90

# Fully-trained threshold (must be STRICTLY > this many hours)
FULLY_TRAINED_HOURS = 120
```

---

## 13. Pseudocode — Full apply_training_curve()

This pseudocode exactly mirrors the real Python implementation.

```
FUNCTION apply_training_curve(performance_rows, lifetime_hours_lookup):

    # ── Build weekly hours per (associate, SC) ────────────────────────────
    weekly_hours = {}  # (assoc, sc) -> {week_key -> float}
    all_weeks = set()

    FOR each row IN performance_rows:
        key = (row.default_id, row.SC_CODE_ID)
        week_key = "{row.WM_FISCAL_YEAR}-W{row.WM_FISCAL_WEEK:02d}"
        all_weeks.add(week_key)
        weekly_hours[key][week_key] += float(row.HOURS or 0)

    sorted_weeks = sort(all_weeks) by (fiscal_year ASC, fiscal_week ASC)

    # ── Calculate hours at start of each week ─────────────────────────────
    hours_at_week_start = {}  # (assoc, sc, week_key) -> float

    FOR each (assoc, sc), weeks_data IN weekly_hours:
        lt_total = lifetime_hours_lookup.get((assoc, sc), 0.0)
        total_in_window = sum(weeks_data.values())
        hours_before_window = lt_total - total_in_window

        cumulative = hours_before_window
        FOR each week IN sorted_weeks:
            hours_at_week_start[(assoc, sc, week)] = round(cumulative, 2)
            cumulative += weeks_data.get(week, 0.0)

    # ── Build SC -> super department lookup ──────────────────────────────
    sc_to_superdept = {}
    FOR each row IN performance_rows:
        IF row.SC_CODE_ID AND row.SUPER_DEPARTMENT:
            sc_to_superdept[row.SC_CODE_ID] = row.SUPER_DEPARTMENT

    # ── Build associate -> home super department ─────────────────────────
    assoc_home_superdept = {}
    FOR each row IN performance_rows:
        IF row.default_id NOT IN assoc_home_superdept:
            home_sd = sc_to_superdept.get(row.HOME_CODE_ID, '')
            IF home_sd:
                assoc_home_superdept[row.default_id] = home_sd

    # ── Build (associate, superdept) -> set of SC codes worked ───────────
    assoc_superdept_scs = {}  # (assoc, superdept) -> set of SC_CODE_IDs
    FOR each row IN performance_rows:
        key = (row.default_id, row.SUPER_DEPARTMENT)
        assoc_superdept_scs[key].add(row.SC_CODE_ID)

    # ── Helper: is associate fully trained in a superdept? ───────────────
    FUNCTION is_fully_trained(assoc, superdept, week_key):
        FOR each sc IN assoc_superdept_scs.get((assoc, superdept), []):
            IF hours_at_week_start.get((assoc, sc, week_key), 0) > 120:
                RETURN True
        RETURN False

    # ── Apply training curve to each row ─────────────────────────────────
    FOR each row IN performance_rows:
        assoc    = row.default_id
        sc       = row.SC_CODE_ID
        sd       = row.SUPER_DEPARTMENT   # superdept of THIS row's work
        week_key = "{WM_FISCAL_YEAR}-W{WM_FISCAL_WEEK:02d}"

        week_hours    = hours_at_week_start.get((assoc, sc, week_key), 0)
        total_lt_hrs  = lifetime_hours_lookup.get((assoc, sc), 0)
        multiplier    = get_training_multiplier(week_hours)  # base tier

        home_sd            = assoc_home_superdept.get(assoc, '')
        is_outside_home    = bool(home_sd AND sd AND sd != home_sd)

        # ── Apply super-department rules ──────────────────────────────
        IF sd IN SC_INDEPENDENT_SUPERDEPTS:          # e.g. Pick
            # Per-SC training; base multiplier already correct
            IF is_outside_home AND multiplier > 0.90:
                multiplier = 0.90

        ELSE:                                        # Cross-SC training
            IF is_fully_trained(assoc, sd, week_key):
                IF is_outside_home:
                    multiplier = 0.90                # Fully trained but outside home
                ELSE:
                    multiplier = 1.00                # Fully trained AND at home
            ELIF is_outside_home AND multiplier > 0.90:
                multiplier = 0.90                    # Not fully trained, outside home
            # else: leave base tier as-is

        # ── Write training curve columns ──────────────────────────────
        row.LIFETIME_SC_HOURS       = week_hours
        row.TOTAL_LIFETIME_SC_HOURS = round(total_lt_hrs, 2)
        row.IS_HOME_SUPERDEPT       = "N" IF is_outside_home ELSE "Y"
        row.TRAINING_MULTIPLIER     = multiplier

        IF row.GOAL != '' AND row.RATE_PER_HOUR != '':
            adj_goal = round(float(row.GOAL) * multiplier, 2)
            row.ADJUSTED_GOAL = adj_goal
            IF adj_goal > 0:
                row.ADJUSTED_PCT_TO_GOAL = round(float(row.RATE_PER_HOUR) / adj_goal * 100, 2)
            ELSE:
                row.ADJUSTED_PCT_TO_GOAL = ''
        ELSE:
            row.ADJUSTED_GOAL        = ''
            row.ADJUSTED_PCT_TO_GOAL = ''

    RETURN performance_rows  # mutated in place
```

---

## Quick Reference: All Possible Multiplier Values

| Multiplier | When Applied |
|------------|-------------|
| **0.25** | 0–40 hrs at week start in the evaluated SC code |
| **0.50** | 41–80 hrs at week start in the evaluated SC code |
| **0.75** | 81–120 hrs at week start in the evaluated SC code |
| **0.90** | Working outside home super department AND base tier ≥ 0.90, OR fully trained but outside home superdept |
| **1.00** | >120 hrs (fully trained) AND working in home super department |

> There are exactly 5 possible multiplier values. No other values are ever assigned.

---

*Document generated from source: `refresh_data.py` as of 2026-03-09.*  
*Maintained by: Benjamin Humpton / Code Puppy (code-puppy-9e9e5a)*
