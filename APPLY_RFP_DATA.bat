@echo off
setlocal
title Apply RFP / PDM data
cd /d "%~dp0"
if exist "app\ui.py" goto :found
if exist "bucas-pmc-ai\app\ui.py" cd /d "%~dp0bucas-pmc-ai"
if exist "app\ui.py" goto :found
echo [ERROR] app\ui.py not found. Put this file next to AI_ME_v1.bat.
goto :end
:found
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Run AI_ME_v1 once first so that the environment is installed.
  goto :end
)
echo This replaces the example tables in the pmc folder with the RFP / PDM based data.
echo Your current files are copied to a backup folder inside pmc first. Chat logs, AI question answers and issue memos are kept.
echo Close the running app window before continuing.
pause
"%PY%" -m pip install -q pypdf
"%PY%" scripts\load_rfp_data.py
:end
echo.
pause
