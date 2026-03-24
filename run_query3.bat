@echo off
set CLOUDSDK_PYTHON=C:\Users\m0m0ag5\.code-puppy-venv\Scripts\python.exe
bq query --use_legacy_sql=false --project_id=wmt-sc-ops-sandbox --format=csv --max_rows=10000 < C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\query3.sql > C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\tpa_lifetime_hours.csv 2> C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\query3_error.txt
exit /b %ERRORLEVEL%
