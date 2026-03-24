"""
TPA Associate Productivity Dashboard Generator
Reads BQ CSVs -> applies training curve -> generates self-contained HTML dashboard

Learning curve logic per QUERY_README.md:
  - Hours at week start determines training multiplier
  - Pick super dept: SC-code-independent training
  - Other super depts: cross-SC training carries over
"""
import csv
import json
import os
import sys
from collections import defaultdict

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
PERF_CSV = os.path.join(DATA_DIR, "tpa_associate_performance_13weeks.csv")
LIFETIME_CSV = os.path.join(DATA_DIR, "tpa_lifetime_hours.csv")
SC_GOALS_CSV = os.path.join(DATA_DIR, "tpa_sc_codes_goals.csv")
OUTPUT_HTML = os.path.join(DATA_DIR, "TPA_Productivity_Dashboard.html")

# Per README: Pick is SC-code-independent training
SC_INDEPENDENT_SUPERDEPTS = {"Pick"}

# ---- Hardcoded goal overrides (per README / known BQ data errors) ----
# Format: (sc_code_id, year_week_start_inclusive, year_week_end_inclusive): correct_goal
# year_week = (WM_FISCAL_YEAR_APPROX, WM_FISCAL_WEEK_APPROX)
GOAL_OVERRIDES = [
    # Pallet Putaway FY2026-W44 -> FY2027-W03: 38 -> 15
    {"sc_code": "018055008", "fy_week_start": (2026, 44), "fy_week_end": (2027, 3), "correct_goal": 15},
]


def _float(val):
    try:
        return float(val) if val not in (None, "") else None
    except (ValueError, TypeError):
        return None


def _int(val):
    try:
        return int(val) if val not in (None, "") else None
    except (ValueError, TypeError):
        return None


def load_performance(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "default_id": row["default_id"],
                "FC_ID": row["FC_ID"],
                "date": row["date"],
                "year": _int(row["WM_FISCAL_YEAR_APPROX"]),
                "week": _int(row["WM_FISCAL_WEEK_APPROX"]),
                "week_start": row["week_start"],
                "SC_CODE_ID": row["SC_CODE_ID"],
                "HOME_CODE_ID": row["HOME_CODE_ID"],
                "AREA": row["AREA"],
                "SUPER_DEPARTMENT": row["SUPER_DEPARTMENT"],
                "DEPARTMENT": row["DEPARTMENT"],
                "HOURS": _float(row["HOURS"]) or 0.0,
                "IDLE_HOURS": _float(row["IDLE_HOURS"]) or 0.0,
                "VOLUME": _float(row["VOLUME"]) or 0.0,
                "GOAL": _float(row["GOAL"]),
                "GOAL_UOM": row.get("GOAL_UOM", ""),
                "RATE_PER_HOUR": _float(row["RATE_PER_HOUR"]),
                "PCT_TO_GOAL": _float(row["PCT_TO_GOAL"]),
            })
    print(f"  Loaded {len(rows):,} performance rows")
    return rows


def load_lifetime(path):
    data = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["default_id"], row["SC_CODE_ID"])
            data[key] = _float(row["total_lifetime_hours"]) or 0.0
    print(f"  Loaded {len(data):,} lifetime hour records")
    return data


def load_sc_goals(path):
    """Returns dict: sc_code_id -> {department, super_department, area, goal_history[]}."""
    sc_info = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sc = row["sc_code_id"]
            if sc not in sc_info:
                sc_info[sc] = {
                    "department": row["department"],
                    "super_department": row["super_department"],
                    "area": row["area"],
                    "unit_measure": row["unit_measure"],
                    "goal_history": [],
                }
            if row["GOAL"] not in (None, ""):
                sc_info[sc]["goal_history"].append({
                    "goal": _float(row["GOAL"]),
                    "goal_uom": row["GOAL_UOM"],
                    "active_date": row["ACTIVE_DATE"],
                    "inactive_date": row["INACTIVE_DATE"],
                })
    print(f"  Loaded {len(sc_info):,} SC code definitions")
    return sc_info


# ---------------------------------------------------------------------------
# Step 1: Normalize goals within each (SC_CODE_ID, year, week)
# Use the goal from the earliest date in that week
# ---------------------------------------------------------------------------
def normalize_weekly_goals(rows):
    """Pin each (SC_CODE_ID, year, week) to the goal on the earliest date in that week."""
    # Build: (sc, year, week) -> {date -> goal}
    key_date_goal = defaultdict(dict)
    for r in rows:
        if r["GOAL"] is not None:
            key = (r["SC_CODE_ID"], r["year"], r["week"])
            key_date_goal[key][r["date"]] = r["GOAL"]

    # For each key, pick goal from earliest date
    canonical_goal = {}
    for key, date_goal in key_date_goal.items():
        earliest_date = min(date_goal.keys())
        canonical_goal[key] = date_goal[earliest_date]

    # Apply back to rows
    changed = 0
    for r in rows:
        if r["GOAL"] is None:
            continue
        key = (r["SC_CODE_ID"], r["year"], r["week"])
        new_goal = canonical_goal.get(key)
        if new_goal is not None and new_goal != r["GOAL"]:
            r["GOAL"] = new_goal
            # Recompute PCT_TO_GOAL
            if r["RATE_PER_HOUR"] is not None and new_goal > 0:
                r["PCT_TO_GOAL"] = (r["RATE_PER_HOUR"] / new_goal) * 100
            changed += 1
    print(f"  Normalized goals: {changed} rows updated")
    return rows


# ---------------------------------------------------------------------------
# Step 2: Apply hardcoded goal overrides
# ---------------------------------------------------------------------------
def _week_key_in_range(year, week, start_yw, end_yw):
    yw = (year, week)
    return start_yw <= yw <= end_yw


def apply_goal_overrides(rows):
    changed = 0
    for r in rows:
        for ov in GOAL_OVERRIDES:
            if (
                r["SC_CODE_ID"] == ov["sc_code"]
                and r["year"] is not None
                and r["week"] is not None
                and _week_key_in_range(r["year"], r["week"], ov["fy_week_start"], ov["fy_week_end"])
            ):
                if r["GOAL"] != ov["correct_goal"]:
                    r["GOAL"] = ov["correct_goal"]
                    if r["RATE_PER_HOUR"] is not None and ov["correct_goal"] > 0:
                        r["PCT_TO_GOAL"] = (r["RATE_PER_HOUR"] / ov["correct_goal"]) * 100
                    changed += 1
    print(f"  Goal overrides applied: {changed} rows")
    return rows


# ---------------------------------------------------------------------------
# Step 3: Apply training curve
# ---------------------------------------------------------------------------
def get_training_tier(hours):
    if hours <= 40:
        return 0.25
    elif hours <= 80:
        return 0.50
    elif hours <= 120:
        return 0.75
    else:
        return 1.00


def apply_training_curve(rows, lifetime_hours):
    # Sort all unique (year, week) pairs to get ranks
    all_weeks = sorted(set(
        (r["year"], r["week"]) for r in rows if r["year"] and r["week"]
    ))
    week_rank = {w: i for i, w in enumerate(all_weeks)}

    # Accumulate hours per (assoc, sc, week)
    assoc_sc_week_hours = defaultdict(lambda: defaultdict(float))
    for r in rows:
        key = (r["default_id"], r["SC_CODE_ID"])
        wk = (r["year"], r["week"])
        assoc_sc_week_hours[key][wk] += r["HOURS"]

    # Compute hours before the 13-week window (per README formula)
    assoc_sc_before = {}
    for (assoc, sc), week_hrs in assoc_sc_week_hours.items():
        total_in_window = sum(week_hrs.values())
        total_lifetime = lifetime_hours.get((assoc, sc), total_in_window)
        assoc_sc_before[(assoc, sc)] = max(0.0, total_lifetime - total_in_window)

    def hrs_at_week_start(assoc, sc, wk):
        key = (assoc, sc)
        before = assoc_sc_before.get(key, 0.0)
        cur_rank = week_rank.get(wk, 0)
        prior = sum(
            h for w, h in assoc_sc_week_hours[key].items()
            if week_rank.get(w, 0) < cur_rank
        )
        return before + prior

    # Map each SC_CODE_ID -> SUPER_DEPARTMENT from the dataset
    sc_to_superdept = {}
    for r in rows:
        if r["SUPER_DEPARTMENT"]:
            sc_to_superdept[r["SC_CODE_ID"]] = r["SUPER_DEPARTMENT"]

    # Determine each associate's home super department
    assoc_home_superdept = {}
    for r in rows:
        aid = r["default_id"]
        if aid not in assoc_home_superdept:
            home_sd = sc_to_superdept.get(r["HOME_CODE_ID"])
            if home_sd:
                assoc_home_superdept[aid] = home_sd

    # (assoc, super_dept) -> set of SC codes worked
    assoc_sd_scs = defaultdict(lambda: defaultdict(set))
    for r in rows:
        if r["SUPER_DEPARTMENT"]:
            assoc_sd_scs[r["default_id"]][r["SUPER_DEPARTMENT"]].add(r["SC_CODE_ID"])

    def fully_trained_in_sd(assoc, super_dept, wk):
        """True if associate has >120 hours at week start in any SC code in this super dept."""
        for sc in assoc_sd_scs[assoc][super_dept]:
            if hrs_at_week_start(assoc, sc, wk) > 120:
                return True
        return False

    # Apply to each row
    mult_dist = defaultdict(int)
    for r in rows:
        if not r["GOAL"]:
            r["TRAINING_MULTIPLIER"] = None
            r["ADJUSTED_GOAL"] = None
            r["ADJUSTED_PCT_TO_GOAL"] = None
            r["IS_HOME_SUPERDEPT"] = None
            r["LIFETIME_SC_HOURS"] = None
            continue

        assoc = r["default_id"]
        sc = r["SC_CODE_ID"]
        sd = r["SUPER_DEPARTMENT"]
        wk = (r["year"], r["week"])

        hrs = hrs_at_week_start(assoc, sc, wk)
        r["LIFETIME_SC_HOURS"] = round(hrs, 2)
        base_tier = get_training_tier(hrs)

        home_sd = assoc_home_superdept.get(assoc)
        is_home = (home_sd == sd) if home_sd else True
        r["IS_HOME_SUPERDEPT"] = "Y" if is_home else "N"

        if sd in SC_INDEPENDENT_SUPERDEPTS:
            # Pick: per-SC-code independent training
            mult = base_tier
            if not is_home and mult == 1.00:
                mult = 0.90
        else:
            fully = fully_trained_in_sd(assoc, sd, wk)
            if fully and is_home:
                mult = 1.00
            elif fully and not is_home:
                mult = 0.90
            elif not is_home and base_tier > 0.90:
                mult = 0.90
            else:
                mult = base_tier

        r["TRAINING_MULTIPLIER"] = mult
        r["ADJUSTED_GOAL"] = round(r["GOAL"] * mult, 4)
        mult_dist[mult] += 1

        rph = r["RATE_PER_HOUR"]
        adj_goal = r["ADJUSTED_GOAL"]
        if rph is not None and adj_goal and adj_goal > 0:
            r["ADJUSTED_PCT_TO_GOAL"] = round((rph / adj_goal) * 100, 2)
        else:
            r["ADJUSTED_PCT_TO_GOAL"] = None

    print(f"  Training curve applied. Multiplier distribution: {dict(mult_dist)}")
    return rows


# ---------------------------------------------------------------------------
# Build dashboard JSON payload
# ---------------------------------------------------------------------------
def build_json_payload(rows, sc_info):
    """Package processed data as JSON for the dashboard."""
    # Sort weeks
    weeks_set = sorted(set(
        (r["year"], r["week"], r["week_start"])
        for r in rows if r["year"] and r["week"]
    ))
    weeks = [{"year": y, "week": w, "week_start": ws} for y, w, ws in weeks_set]

    # SC code lookup (only those with goals in actual data)
    sc_lookup = {}
    for r in rows:
        sc = r["SC_CODE_ID"]
        if sc not in sc_lookup:
            info = sc_info.get(sc, {})
            sc_lookup[sc] = {
                "department": r["DEPARTMENT"] or info.get("department", sc),
                "super_department": r["SUPER_DEPARTMENT"] or info.get("super_department", ""),
                "area": r["AREA"] or info.get("area", ""),
                "goal": r["GOAL"],
                "goal_uom": r["GOAL_UOM"] or info.get("unit_measure", ""),
            }

    # Associate lookup
    assoc_lookup = {}
    for r in rows:
        aid = r["default_id"]
        if aid not in assoc_lookup:
            assoc_lookup[aid] = {
                "home_code": r["HOME_CODE_ID"],
                "home_superdept": sc_lookup.get(r["HOME_CODE_ID"], {}).get("super_department", ""),
            }

    # Keep only the columns the dashboard needs
    keep_cols = [
        "default_id", "date", "year", "week", "week_start",
        "SC_CODE_ID", "HOME_CODE_ID", "AREA", "SUPER_DEPARTMENT", "DEPARTMENT",
        "HOURS", "IDLE_HOURS", "VOLUME", "GOAL", "GOAL_UOM",
        "RATE_PER_HOUR", "PCT_TO_GOAL",
        "LIFETIME_SC_HOURS", "TRAINING_MULTIPLIER", "ADJUSTED_GOAL",
        "ADJUSTED_PCT_TO_GOAL", "IS_HOME_SUPERDEPT",
    ]
    slim_rows = [{k: r.get(k) for k in keep_cols} for r in rows]

    return {
        "weeks": weeks,
        "sc_codes": sc_lookup,
        "associates": assoc_lookup,
        "rows": slim_rows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("TPA Productivity Dashboard — Data Processor")
    print("=" * 60)

    print("\n[1/5] Loading CSVs...")
    perf = load_performance(PERF_CSV)
    lifetime = load_lifetime(LIFETIME_CSV)
    sc_info = load_sc_goals(SC_GOALS_CSV)

    print("\n[2/5] Normalizing weekly goals...")
    perf = normalize_weekly_goals(perf)

    print("\n[3/5] Applying goal overrides...")
    perf = apply_goal_overrides(perf)

    print("\n[4/5] Applying training curve...")
    perf = apply_training_curve(perf, lifetime)

    print("\n[5/5] Building HTML dashboard...")
    payload = build_json_payload(perf, sc_info)
    from html_builder import build_html
    html = build_html(payload)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Written: {OUTPUT_HTML}")
    print(f"  Rows in payload: {len(payload['rows']):,}")
    print(f"  Weeks: {len(payload['weeks'])}")
    print(f"  SC Codes: {len(payload['sc_codes'])}")
    print(f"  Associates: {len(payload['associates'])}")

    print("\n[DONE] Opening dashboard...")
    import subprocess
    subprocess.Popen(["cmd", "/c", "start", "", OUTPUT_HTML])


if __name__ == "__main__":
    main()
