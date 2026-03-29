-- Lifetime hours at the START of each fiscal week, per (associate, SC code).
-- Uses a window function over all-time TPA history so the cumulative total
-- at week N includes every prior week, not just the 13-week window.
--
-- Output columns:
--   hours_at_week_start  -- hours accumulated BEFORE this week (used for training tier)
--   total_lifetime_hours -- hours accumulated THROUGH this week (display only)
--
-- Output is filtered to the 13 most recent fiscal weeks so the CSV stays small.

WITH weekly_perf AS (
  -- Collapse daily rows to one total per (associate, SC, fiscal week).
  -- The fiscal year/week formula covers any calendar year without CASE statements.
  SELECT
    DEFAULT_ID                                                                  AS default_id,
    SC_CODE_ID,
    EXTRACT(YEAR FROM LAST_DAY(DATE_SUB(p.DATE, INTERVAL 1 MONTH))) + 1        AS WM_FISCAL_YEAR,
    DIV(
      DATE_DIFF(
        p.DATE,
        DATE_TRUNC(
          DATE(EXTRACT(YEAR FROM LAST_DAY(DATE_SUB(p.DATE, INTERVAL 1 MONTH))), 2, 1),
          WEEK(SATURDAY)
        ),
        DAY
      ), 7
    ) + 1                                                                       AS WM_FISCAL_WEEK,
    SUM(HOURS)                                                                  AS hours_in_week
  FROM `wmt-drax-prod.DRAX_VM.VIEWS_ASSOCIATE_PERFORMANCE_DAY` p
  WHERE p.FC_ID = 'TPA'
  GROUP BY default_id, SC_CODE_ID, WM_FISCAL_YEAR, WM_FISCAL_WEEK
),

recent_wm_weeks AS (
  -- Identify the 13 most recent fiscal weeks present in the data.
  SELECT DISTINCT WM_FISCAL_YEAR, WM_FISCAL_WEEK
  FROM weekly_perf
  ORDER BY WM_FISCAL_YEAR DESC, WM_FISCAL_WEEK DESC
  LIMIT 13
),

cumulative AS (
  -- Compute two running totals per (associate, SC):
  --   hours_at_week_start : SUM of all weeks BEFORE the current row  (1 PRECEDING)
  --   total_lifetime_hours: SUM of all weeks THROUGH the current row  (CURRENT ROW)
  -- COALESCE handles the very first week (no preceding rows -> NULL -> 0).
  SELECT
    default_id,
    SC_CODE_ID,
    WM_FISCAL_YEAR,
    WM_FISCAL_WEEK,
    COALESCE(
      SUM(hours_in_week) OVER (
        PARTITION BY default_id, SC_CODE_ID
        ORDER BY WM_FISCAL_YEAR, WM_FISCAL_WEEK
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
      ), 0
    )                                                                           AS hours_at_week_start,
    SUM(hours_in_week) OVER (
      PARTITION BY default_id, SC_CODE_ID
      ORDER BY WM_FISCAL_YEAR, WM_FISCAL_WEEK
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                                           AS total_lifetime_hours
  FROM weekly_perf
)

SELECT
  c.default_id,
  c.SC_CODE_ID,
  c.WM_FISCAL_YEAR,
  c.WM_FISCAL_WEEK,
  c.hours_at_week_start,
  c.total_lifetime_hours
FROM cumulative c
INNER JOIN recent_wm_weeks rww
  ON  c.WM_FISCAL_YEAR = rww.WM_FISCAL_YEAR
  AND c.WM_FISCAL_WEEK = rww.WM_FISCAL_WEEK
ORDER BY c.default_id, c.SC_CODE_ID, c.WM_FISCAL_YEAR, c.WM_FISCAL_WEEK