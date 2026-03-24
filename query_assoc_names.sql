SELECT
  ea.default_id,
  ea.name,
  ea.home_code_id,
  ea.shift,
  ea.agency_id
FROM `wmt-drax-prod.DRAX_VM.EVENTS_ASSOCIATE` ea
WHERE ea.fc_id = 'TPA'
  AND (ea.release_date IS NULL OR ea.release_date > DATE_SUB(CURRENT_DATE(), INTERVAL 200 DAY))
ORDER BY ea.name
