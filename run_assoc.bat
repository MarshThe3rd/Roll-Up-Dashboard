@echo off
set CLOUDSDK_PYTHON=C:\Users\m0m0ag5\.code-puppy-venv\Scripts\python.exe
bq query --use_legacy_sql=false --project_id=wmt-sc-ops-sandbox --format=csv --max_rows=5000 < C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\query_assoc_names.sql > C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\tpa_associates.csv 2> C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\q_assoc_err.txt
exit /b %ERRORLEVEL%
