@echo off
setlocal
title AI M^&E v1 - BUCAS PMC AI
cd /d "%~dp0"

rem --- find project folder (handles one extra nested folder from unzip)
if exist "app\ui.py" goto :found
if exist "bucas-pmc-ai\app\ui.py" cd /d "%~dp0bucas-pmc-ai"
if exist "app\ui.py" goto :found
echo [ERROR] app\ui.py not found. Put this file inside the bucas-pmc-ai_v0.1 folder.
goto :end

:found
rem --- create a shortcut named "AI M&E_v1" next to this file (first run only)
if exist "%~dp0AI M&E_v1.lnk" goto :venv
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut('%~dp0AI M&E_v1.lnk'); $s.TargetPath='%~f0'; $s.WorkingDirectory='%~dp0'; $s.Save()" >nul 2>nul

:venv
set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto :deps
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed or not on PATH. Install from python.org and check "Add to PATH".
  goto :end
)
echo [1/3] Creating virtual environment...
python -m venv .venv
if errorlevel 1 goto :fail

:deps
"%PY%" -c "import streamlit, anthropic, pandas, yaml, dotenv, pypdf, docx, reportlab, openpyxl" >nul 2>nul
if not errorlevel 1 goto :db
echo [2/3] Installing packages. This takes a few minutes the first time...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

:db
if exist "data\pmc.db" goto :run
echo [3/3] Initializing database...
"%PY%" scripts\init_db.py
if errorlevel 1 goto :fail

:run
echo.
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
