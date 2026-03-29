@echo off

set CLOUDSDK_PYTHON=C:\Users\m0m0ag5\.code-puppy-venv\Scripts\python.exe

bq query --use_legacy_sql=false --project_id=wmt-sc-ops-sandbox --format=csv --max_rows=50000 < C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\query_perf_13wk.sql > C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\tpa_associate_performance_13weeks.csv 2> C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard\q_perf_err.txt

exit /b %ERRORLEVEL%

