-- Query 3 REVISED: Lifetime hours per associate per SC code for TPA
-- Uses DEFAULT_ID (not default_id - BigQuery is case-insensitive, but keeping uppercase)
SELECT
  DEFAULT_ID       AS default_id,
  SC_CODE_ID,
  SUM(HOURS)       AS total_lifetime_hours
FROM `wmt-drax-prod.DRAX_VM.VIEWS_ASSOCIATE_PERFORMANCE_DAY`
WHERE FC_ID = 'TPA'
  AND HOURS > 0
GROUP BY DEFAULT_ID, SC_CODE_ID
ORDER BY DEFAULT_ID, SC_CODE_ID
