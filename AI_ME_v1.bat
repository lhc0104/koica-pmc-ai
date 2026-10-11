@echo off
setlocal
title AI-KME (AI KOICA Monitoring ^& Evaluation)
cd /d "%~dp0"

rem --- find project folder (handles one extra nested folder from unzip)
if exist "app\ui.py" goto :found
if exist "bucas-pmc-ai\app\ui.py" cd /d "%~dp0bucas-pmc-ai"
if exist "app\ui.py" goto :found
echo [ERROR] app\ui.py not found. Put this file inside the bucas-pmc-ai folder.
goto :end

:found
rem --- Per-PC files live OUTSIDE the project folder, so the project can sit in Google Drive
rem     and sync between computers without syncing the virtual environment or the SQLite cache.
set "LOCAL=%LOCALAPPDATA%\AI-KME"
if not exist "%LOCAL%" mkdir "%LOCAL%"
set "PMC_DB_PATH=%LOCAL%\pmc.db"
set "PY=%LOCAL%\venv\Scripts\python.exe"

rem --- (re)create a desktop-style shortcut next to this file (points to this location)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut('%~dp0AI M&E_v1.lnk'); $s.TargetPath='%~f0'; $s.WorkingDirectory='%~dp0'; $s.Save()" >nul 2>nul

if exist "%PY%" goto :deps
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed or not on PATH. Install from python.org and check "Add to PATH".
  goto :end
)
echo [1/3] Creating virtual environment in %LOCAL%\venv ...
python -m venv "%LOCAL%\venv"
if errorlevel 1 goto :fail

:deps
"%PY%" -c "import streamlit, anthropic, pandas, yaml, dotenv, pypdf, docx, reportlab, openpyxl, PIL, googleapiclient, google_auth_oauthlib, openai" >nul 2>nul
if not errorlevel 1 goto :db
echo [2/3] Installing packages. This takes a few minutes the first time on each PC...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

:db
if exist "%PMC_DB_PATH%" goto :run
echo [3/3] Building the local database cache from the pmc folder...
"%PY%" scripts\init_db.py
if errorlevel 1 goto :fail

:run
echo.
echo Project folder : %CD%
echo Local cache    : %LOCAL%  (venv + pmc.db, not synced)
echo Starting... the browser opens at http://localhost:8501
echo To stop: press Ctrl+C in this window, or just close it.
echo.
"%PY%" -m streamlit run app\ui.py
goto :end

:fail
echo.
echo [ERROR] A step failed. Copy the messages above and send them to Claude.

:end
echo.
pause
