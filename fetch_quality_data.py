"""
Fetch quality / error data from 6253ErrorDB.accdb for the past 13
WM fiscal weeks and return a payload dict ready for dashboard embedding.
"""
import pyodbc
from datetime import date, timedelta
from collections import defaultdict

DB_PATH = r"\\US06253w8000d2a.s06253.US.wal-mart.com\Shipping\6253ErrorDB.accdb"
DB_PWD  = "6253"
DRIVER  = "Microsoft Access Driver (*.mdb, *.accdb)"

# WM Fiscal year start dates (Saturday nearest end of Jan)
FY_STARTS = [
    (2025, date(2024, 2,  3)),
    (2026, date(2025, 2,  1)),
    (2027, date(2026, 1, 31)),
]

ERROR_CATEGORIES = {
    "Picking":   [1, 2, 20],
    "Packing":   [3, 4, 5],
    "RSR":       [6, 7, 8, 9, 10, 11, 12],
    "Receiving": [13, 14, 15, 16, 17, 18, 19],
}

WINDOW_WEEKS = 13


# ---------------------------------------------------------------------------
# Fiscal calendar helpers
# ---------------------------------------------------------------------------

def _fy_start(fy: int) -> date | None:
    for f, s in FY_STARTS:
        if f == fy:
            return s
    return None


def get_fy_week(dt) -> tuple[int, int]:
    """Return (fiscal_year, fiscal_week_1_indexed) for a date."""
    if hasattr(dt, "date"):
        dt = dt.date()
    elif isinstance(dt, str):
        dt = date.fromisoformat(dt[:10])
    for fy, start in reversed(FY_STARTS):
        if dt >= start:
            return fy, (dt - start).days // 7 + 1
    fy, start = FY_STARTS[0]
    return fy, 1


def week_start_date(fy: int, week: int) -> date | None:
    """Return the Monday ... actually Saturday start of a WM fiscal week."""
    start = _fy_start(fy)
    return start + timedelta(weeks=week - 1) if start else None


def get_13_weeks(today: date | None = None) -> list[tuple[int, int]]:
    """Return the 13 most-recent completed WM fiscal (year, week) tuples."""
    today = today or date.today()
    fy, wk = get_fy_week(today)

    result = []
    for i in range(WINDOW_WEEKS):
        w = wk - i
        f = fy
        while w <= 0:
            f -= 1
            s_prev = _fy_start(f)
            s_next = _fy_start(f + 1)
            if s_prev and s_next:
                weeks_in_fy = (s_next - s_prev).days // 7
                w += weeks_in_fy
            else:
                w = 1
                break
        result.insert(0, (f, w))
    return result


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _conn():
    return pyodbc.connect(
        f"DRIVER={{{DRIVER}}};DBQ={DB_PATH};PWD={DB_PWD};ReadOnly=1;",
        timeout=15,
    )


def _row_to_date(val) -> date | None:
    if val is None:
        return None
    if hasattr(val, "date"):
        return val.date()
    return None


def _clean(s) -> str:
    return (s or "").strip()


def _resolve_name(uid: str, assoc_names: dict, first: str, last: str) -> str:
    if uid in assoc_names:
        return assoc_names[uid]
    full = f"{_clean(first)} {_clean(last)}".strip()
    return full or uid


# ---------------------------------------------------------------------------
# Main fetch
# ---------------------------------------------------------------------------

def fetch_quality(assoc_names: dict | None = None) -> dict:
    """
    Pull 13-week error + production data from Access DB.

    assoc_names: optional dict of {user_id: display_name} from BQ CSV.
    Returns a dict suitable for embedding as DATA.quality in the dashboard.
    """
    assoc_names = assoc_names or {}
    weeks = get_13_weeks()

    ws_start = week_start_date(*weeks[0])
    ws_end   = week_start_date(*weeks[-1]) + timedelta(weeks=1)

    code_to_cat = {
        c: cat
        for cat, codes in ERROR_CATEGORIES.items()
        for c in codes
    }

    conn = _conn()
    cur  = conn.cursor()

    # Error code lookup
    cur.execute("SELECT error_code, [desc] FROM ErrorCodes ORDER BY error_code")
    error_codes = {r.error_code: r.desc for r in cur.fetchall()}

    errors: list[dict] = []

    # -- Picking errors -------------------------------------------------------
    cur.execute(
        "SELECT picker_user_id, ts, shift, error_code, error_qty,"
        " non_punitive, notes, picker_first_name, picker_last_name"
        " FROM PickingErrors WHERE ts >= ? AND ts < ?",
        ws_start, ws_end,
    )
    for r in cur.fetchall():
        uid = _clean(r.picker_user_id)
        dt  = _row_to_date(r.ts)
        if not uid or not dt:
            continue
        fy, wk = get_fy_week(dt)
        errors.append(dict(
            user_id     = uid,
            name        = _resolve_name(uid, assoc_names, r.picker_first_name, r.picker_last_name),
            category    = "Picking",
            error_code  = r.error_code,
            error_desc  = error_codes.get(r.error_code, f"Code {r.error_code}"),
            error_qty   = abs(r.error_qty or 1),
            date        = dt.isoformat(),
            year        = fy,
            week        = wk,
            shift       = _clean(r.shift),
            non_punitive= bool(r.non_punitive),
            notes       = _clean(r.notes),
        ))

    # -- Packing errors -------------------------------------------------------
    cur.execute(
        "SELECT user_id, ts, shift, error_code, error_qty,"
        " notes, first_name, last_name"
        " FROM PackingErrors WHERE ts >= ? AND ts < ?",
        ws_start, ws_end,
    )
    for r in cur.fetchall():
        uid = _clean(r.user_id)
        dt  = _row_to_date(r.ts)
        if not uid or not dt:
            continue
        fy, wk = get_fy_week(dt)
        errors.append(dict(
            user_id     = uid,
            name        = _resolve_name(uid, assoc_names, r.first_name, r.last_name),
            category    = "Packing",
            error_code  = r.error_code,
            error_desc  = error_codes.get(r.error_code, f"Code {r.error_code}"),
            error_qty   = abs(r.error_qty or 1),
            date        = dt.isoformat(),
            year        = fy,
            week        = wk,
            shift       = _clean(r.shift),
            non_punitive= False,
            notes       = _clean(r.notes),
        ))

    # -- RSR / Pallet movement errors -----------------------------------------
    cur.execute(
        "SELECT user_id, ts, shift, error_code, notes, first_name, last_name"
        " FROM PalletMovementErrors WHERE ts >= ? AND ts < ?",
        ws_start, ws_end,
    )
    for r in cur.fetchall():
        uid = _clean(r.user_id)
        dt  = _row_to_date(r.ts)
        if not uid or not dt:
            continue
        fy, wk = get_fy_week(dt)
        errors.append(dict(
            user_id     = uid,
            name        = _resolve_name(uid, assoc_names, r.first_name, r.last_name),
            category    = "RSR",
            error_code  = r.error_code,
            error_desc  = error_codes.get(r.error_code, f"Code {r.error_code}"),
            error_qty   = 1,
            date        = dt.isoformat(),
            year        = fy,
            week        = wk,
            shift       = _clean(r.shift),
            non_punitive= False,
            notes       = _clean(r.notes),
        ))

    # -- Receiving errors -----------------------------------------------------
    cur.execute(
        "SELECT user_id, ts, shift, error_code, error_qty,"
        " notes, first_name, last_name"
        " FROM ReceivingErrors WHERE ts >= ? AND ts < ?",
        ws_start, ws_end,
    )
    for r in cur.fetchall():
        uid = _clean(r.user_id)
        dt  = _row_to_date(r.ts)
        if not uid or not dt:
            continue
        fy, wk = get_fy_week(dt)
        errors.append(dict(
            user_id     = uid,
            name        = _resolve_name(uid, assoc_names, r.first_name, r.last_name),
            category    = "Receiving",
            error_code  = r.error_code,
            error_desc  = error_codes.get(r.error_code, f"Code {r.error_code}"),
            error_qty   = abs(r.error_qty or 1),
            date        = dt.isoformat(),
            year        = fy,
            week        = wk,
            shift       = _clean(r.shift),
            non_punitive= False,
            notes       = _clean(r.notes),
        ))

    # -- Production (for error-rate calculation) ------------------------------
    def _load_prod(table, unit_col):
        # Both PickingProduction and PackingProduction use 'user_id'
        cur.execute(
            f"SELECT user_id, prod_date, [{unit_col}] FROM [{table}]"
            f" WHERE prod_date >= ? AND prod_date < ? AND [{unit_col}] > 0",
            ws_start, ws_end,
        )
        prod: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for r in cur.fetchall():
            uid = _clean(r.user_id)
            dt  = _row_to_date(r.prod_date)
            if not uid or not dt:
                continue
            fy, wk = get_fy_week(dt)
            prod[uid][f"{fy}-{wk}"] += int(getattr(r, unit_col) or 0)
        return {k: dict(v) for k, v in prod.items()}

    picking_prod = _load_prod("PickingProduction", "units_picked")
    packing_prod = _load_prod("PackingProduction", "units_packed")

    conn.close()

    # Build weeks list (mirroring the productivity payload format)
    week_list = [
        {
            "year": fy,
            "week": wk,
            "key":  f"{fy}-{wk}",
            "week_start": (week_start_date(fy, wk) or date.today()).isoformat(),
            "label": f"FY{fy}-W{wk:02d}",
        }
        for fy, wk in weeks
    ]

    print(f"  Quality: {len(errors):,} errors across {len(weeks)} weeks")
    return {
        "weeks":      week_list,
        "error_codes": error_codes,
        "categories": ERROR_CATEGORIES,
        "errors":     errors,
        "production": {
            "picking": picking_prod,
            "packing": packing_prod,
        },
    }
