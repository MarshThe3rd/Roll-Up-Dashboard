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
from collections import defaultdict

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
PERF_CSV = os.path.join(DATA_DIR, "tpa_associate_performance_13weeks.csv")
LIFETIME_CSV = os.path.join(DATA_DIR, "tpa_lifetime_hours.csv")
SC_GOALS_CSV = os.path.join(DATA_DIR, "tpa_sc_codes_goals.csv")
ASSOCIATES_CSV = os.path.join(DATA_DIR, "tpa_associates.csv")
OUTPUT_HTML = os.path.join(DATA_DIR, "TPA_Productivity_Dashboard.html")

# Per README: Pick is SC-code-independent training
SC_INDEPENDENT_SUPERDEPTS = {"Pick"}

# Hardcoded goal overrides per README (known BQ data errors)
# year_week tuples use (WM_FISCAL_YEAR, WM_FISCAL_WEEK)
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


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_associates(path):
    """Returns dict: default_id -> {name, home_code_id, shift, agency_id}."""
    assocs = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            aid = row["default_id"]
            name = (row.get("name") or "").strip()
            if aid and aid not in ("nouser",):
                assocs[aid] = {
                    "name": name if name else aid,
                    "home_code_id": row.get("home_code_id", ""),
                    "shift": row.get("shift", ""),
                    "agency_id": row.get("agency_id", ""),
                }
    print(f"  Loaded {len(assocs):,} associates")
    return assocs


def load_performance(path, associates):
    """Reads perf CSV with real WM fiscal week columns."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            aid = row.get("default_id") or row.get("\ufeffdefault_id", "")
            assoc_info = associates.get(aid, {})
            rows.append({
                "default_id": aid,
                "name": assoc_info.get("name", aid),
                "FC_ID": row["FC_ID"],
                "date": row["date"],
                "year": _int(row["WM_FISCAL_YEAR"]),
                "week": _int(row["WM_FISCAL_WEEK"]),
                "week_start": row["WM_FISCAL_WEEK_START"],
                "SC_CODE_ID": row["SC_CODE_ID"],
                "HOME_CODE_ID": row.get("HOME_CODE_ID", ""),
                "AREA": row.get("AREA", ""),
                "SUPER_DEPARTMENT": row.get("SUPER_DEPARTMENT", ""),
                "DEPARTMENT": row.get("DEPARTMENT", ""),
                "HOURS": _float(row["HOURS"]) or 0.0,
                "IDLE_HOURS": _float(row["IDLE_HOURS"]) or 0.0,
                "VOLUME": _float(row.get("VOLUME")) or 0.0,
                "GOAL": _float(row.get("GOAL")),
                "GOAL_UOM": row.get("GOAL_UOM", ""),
                "RATE_PER_HOUR": _float(row.get("RATE_PER_HOUR")),
                "PCT_TO_GOAL": _float(row.get("PCT_TO_GOAL")),
            })
    print(f"  Loaded {len(rows):,} performance rows")
    return rows


def load_lifetime(path):
    """Loads all-time hours per (default_id, SC_CODE_ID).

    Three defensive fixes vs. the original:
    1. utf-8-sig — handles BOM that BigQuery CSV exports include;
       without it the first record's key gets a \ufeff prefix and
       silently misses the lifetime lookup, zeroing that associate's
       pre-window hours.
    2. .strip() on both key fields — guards against trailing whitespace
       that causes key mismatches on lookup.
    3. Accumulate with += instead of overwrite — in case the query
       returns more than one row per (assoc, sc) pair.
    """
    data = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (row["default_id"].strip(), row["SC_CODE_ID"].strip())
            hours = _float(row["total_lifetime_hours"]) or 0.0
            data[key] = data.get(key, 0.0) + hours
    print(f"  Loaded {len(data):,} lifetime hour records")
    return data


def load_sc_goals(path):
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
                }
    print(f"  Loaded {len(sc_info):,} SC code definitions")
    return sc_info


# ---------------------------------------------------------------------------
# Step 1: Normalize goals (earliest date in each week wins)
# ---------------------------------------------------------------------------

def normalize_weekly_goals(rows):
    key_date_goal = defaultdict(dict)
    for r in rows:
        if r["GOAL"] is not None:
            key = (r["SC_CODE_ID"], r["year"], r["week"])
            key_date_goal[key][r["date"]] = r["GOAL"]

    canonical_goal = {
        key: dg[min(dg.keys())]
        for key, dg in key_date_goal.items()
    }

    changed = 0
    for r in rows:
        if r["GOAL"] is None:
            continue
        key = (r["SC_CODE_ID"], r["year"], r["week"])
        new_goal = canonical_goal.get(key)
        if new_goal is not None and new_goal != r["GOAL"]:
            r["GOAL"] = new_goal
            if r["RATE_PER_HOUR"] is not None and new_goal > 0:
                r["PCT_TO_GOAL"] = (r["RATE_PER_HOUR"] / new_goal) * 100
            changed += 1

    print(f"  Normalized goals: {changed} rows updated")
    return rows


# ---------------------------------------------------------------------------
# Step 2: Goal overrides
# ---------------------------------------------------------------------------

def apply_goal_overrides(rows):
    changed = 0
    for r in rows:
        if r["year"] is None or r["week"] is None:
            continue
        yw = (r["year"], r["week"])
        for ov in GOAL_OVERRIDES:
            if r["SC_CODE_ID"] == ov["sc_code"] and ov["fy_week_start"] <= yw <= ov["fy_week_end"]:
                if r["GOAL"] != ov["correct_goal"]:
                    r["GOAL"] = ov["correct_goal"]
                    if r["RATE_PER_HOUR"] is not None and ov["correct_goal"] > 0:
                        r["PCT_TO_GOAL"] = (r["RATE_PER_HOUR"] / ov["correct_goal"]) * 100
                    changed += 1
    print(f"  Goal overrides applied: {changed} rows")
    return rows


# ---------------------------------------------------------------------------
# Step 3: Training curve
# ---------------------------------------------------------------------------

def get_training_tier(hours):
    if hours <= 40:
        return 0.25
    elif hours <= 80:
        return 0.50
    elif hours <= 120:
        return 0.75
    return 1.00


def apply_training_curve(rows, lifetime_hours):
    all_weeks = sorted(set(
        (r["year"], r["week"]) for r in rows if r["year"] and r["week"]
    ))
    week_rank = {w: i for i, w in enumerate(all_weeks)}

    # Accumulate hours per (assoc, sc) per week within window
    assoc_sc_week_hours = defaultdict(lambda: defaultdict(float))
    for r in rows:
        assoc_sc_week_hours[(r["default_id"], r["SC_CODE_ID"])][(r["year"], r["week"])] += r["HOURS"]

    # Hours before the 13-week window
    assoc_sc_before = {}
    for (assoc, sc), week_hrs in assoc_sc_week_hours.items():
        in_window = sum(week_hrs.values())
        lifetime = lifetime_hours.get((assoc, sc), in_window)
        assoc_sc_before[(assoc, sc)] = max(0.0, lifetime - in_window)

    def hrs_at_week_start(assoc, sc, wk):
        before = assoc_sc_before.get((assoc, sc), 0.0)
        cur_rank = week_rank.get(wk, 0)
        prior = sum(
            h for w, h in assoc_sc_week_hours[(assoc, sc)].items()
            if week_rank.get(w, 0) < cur_rank
        )
        return before + prior

    sc_to_superdept = {r["SC_CODE_ID"]: r["SUPER_DEPARTMENT"] for r in rows if r["SUPER_DEPARTMENT"]}

    assoc_home_superdept = {}
    for r in rows:
        aid = r["default_id"]
        if aid not in assoc_home_superdept:
            home_sd = sc_to_superdept.get(r["HOME_CODE_ID"])
            if home_sd:
                assoc_home_superdept[aid] = home_sd

    assoc_sd_scs = defaultdict(lambda: defaultdict(set))
    for r in rows:
        if r["SUPER_DEPARTMENT"]:
            assoc_sd_scs[r["default_id"]][r["SUPER_DEPARTMENT"]].add(r["SC_CODE_ID"])

    def fully_trained_in_sd(assoc, sd, wk):
        return any(
            hrs_at_week_start(assoc, sc, wk) > 120
            for sc in assoc_sd_scs[assoc][sd]
        )

    mult_dist = defaultdict(int)
    for r in rows:
        if not r["GOAL"]:
            r.update({"TRAINING_MULTIPLIER": None, "ADJUSTED_GOAL": None,
                      "ADJUSTED_PCT_TO_GOAL": None, "IS_HOME_SUPERDEPT": None,
                      "LIFETIME_SC_HOURS": None})
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
        adj = r["ADJUSTED_GOAL"]
        r["ADJUSTED_PCT_TO_GOAL"] = round((rph / adj) * 100, 2) if (rph is not None and adj and adj > 0) else None

    print(f"  Training curve applied. Distribution: {dict(mult_dist)}")
    return rows


# ---------------------------------------------------------------------------
# Build JSON payload
# ---------------------------------------------------------------------------

KEEP_COLS = [
    "default_id", "name", "date", "year", "week", "week_start",
    "SC_CODE_ID", "HOME_CODE_ID", "AREA", "SUPER_DEPARTMENT", "DEPARTMENT",
    "HOURS", "IDLE_HOURS", "VOLUME", "GOAL", "GOAL_UOM",
    "RATE_PER_HOUR", "PCT_TO_GOAL",
    "LIFETIME_SC_HOURS", "TRAINING_MULTIPLIER", "ADJUSTED_GOAL",
    "ADJUSTED_PCT_TO_GOAL", "IS_HOME_SUPERDEPT",
]


def build_json_payload(rows, sc_info, associates):
    weeks_set = sorted(set(
        (r["year"], r["week"], r["week_start"])
        for r in rows if r["year"] and r["week"]
    ))
    weeks = [{"year": y, "week": w, "week_start": ws} for y, w, ws in weeks_set]

    # SC code lookup — only codes seen in performance data
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

    # Associate lookup — merge BQ roster names with perf data
    assoc_lookup = {}
    for r in rows:
        aid = r["default_id"]
        if aid not in assoc_lookup:
            roster = associates.get(aid, {})
            assoc_lookup[aid] = {
                "name": roster.get("name") or r["name"] or aid,
                "home_code": r["HOME_CODE_ID"],
                "home_superdept": sc_lookup.get(r["HOME_CODE_ID"], {}).get("super_department", ""),
                "shift": roster.get("shift", ""),
            }

    slim_rows = [{k: r.get(k) for k in KEEP_COLS} for r in rows]

    return {"weeks": weeks, "sc_codes": sc_lookup, "associates": assoc_lookup, "rows": slim_rows}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("TPA Productivity Dashboard - Data Processor")
    print("=" * 60)

    print("\n[1/5] Loading CSVs...")
    associates = load_associates(ASSOCIATES_CSV)
    perf = load_performance(PERF_CSV, associates)
    lifetime = load_lifetime(LIFETIME_CSV)
    sc_info = load_sc_goals(SC_GOALS_CSV)

    print("\n[2/5] Normalizing weekly goals...")
    perf = normalize_weekly_goals(perf)

    print("\n[3/5] Applying goal overrides...")
    perf = apply_goal_overrides(perf)

    print("\n[4/5] Applying training curve...")
    perf = apply_training_curve(perf, lifetime)

    print("\n[5/5] Building HTML dashboard...")
    payload = build_json_payload(perf, sc_info, associates)
    from html_builder import build_html
    html = build_html(payload)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Written  : {OUTPUT_HTML}")
    print(f"  Rows     : {len(payload['rows']):,}")
    print(f"  Weeks    : {len(payload['weeks'])}")
    print(f"  SC Codes : {len(payload['sc_codes'])}")
    print(f"  Associates: {len(payload['associates'])}")

    print("\n[DONE] Opening dashboard...")
    import subprocess
    subprocess.Popen(["cmd", "/c", "start", "", OUTPUT_HTML])


if __name__ == "__main__":
    main()
