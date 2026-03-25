@echo off
echo ============================================================
echo  TPA Productivity + Quality Dashboard Generator
echo ============================================================
echo.

:: Use the project venv which has pyodbc for Access DB access
set PYTHON=%~dp0.venv\Scripts\python.exe

if not exist "%PYTHON%" (
    echo ERROR: .venv not found. Run:  uv venv  then  uv pip install pyodbc
    exit /b 1
)

echo Running process_data.py...
"%PYTHON%" "%~dp0process_data.py"

echo.
echo Done! Dashboard opened in your browser.
exit /b %ERRORLEVEL%
