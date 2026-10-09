@echo off
setlocal
title AI-KME - schedule daily auto update (18:00)
cd /d "%~dp0"
set "BAT=%~dp0UPDATE_CLOUD.bat"
if not exist "%BAT%" (
  echo [ERROR] UPDATE_CLOUD.bat not found next to this file.
  goto :end
)
echo This registers a Windows scheduled task that runs UPDATE_CLOUD.bat every day at 18:00
echo (commit + push to GitHub, so Streamlit Cloud redeploys with your latest data and code).
echo To change the time, edit /st 18:00 in this file. To remove: schtasks /delete /tn "AI-KME auto update" /f
echo.
schtasks /create /tn "AI-KME auto update" /tr "\"%BAT%\" auto" /sc daily /st 18:00 /f
if errorlevel 1 (
  echo [ERROR] Could not create the task. Try: right-click this file and "Run as administrator".
  goto :end
)
echo.
echo Registered. You can also run UPDATE_CLOUD.bat by hand any time.
:end
echo.
pause
