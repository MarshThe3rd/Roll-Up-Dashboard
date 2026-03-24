SELECT DISTINCT
  dc.sc_code_id,
  dc.department,
  dc.super_department,
  dc.area,
  dc.unit_measure,
  dc.fixed,
  dg.GOAL,
  dg.GOAL_UOM,
  dg.ACTIVE_DATE,
  dg.INACTIVE_DATE
FROM `wmt-drax-prod.DRAX_VM.DEPARTMENT_COALESCE` dc
LEFT JOIN `wmt-drax-prod.DRAX_VM.INPUTS_DEPARTMENTGOAL` dg
  ON dc.sc_code_id = dg.SC_CODE_ID
  AND dg.FC_ID = 'TPA'
WHERE dc.fc_id = 'TPA'
  AND dc.dept_type = 'standard'
  AND dc.fixed = FALSE
ORDER BY dc.super_department, dc.department, dc.sc_code_id
