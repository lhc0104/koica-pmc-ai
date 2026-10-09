@echo off
setlocal
title AI-KME - push to GitHub (Streamlit Cloud auto-redeploys)
cd /d "%~dp0"
if exist "bucas-pmc-ai\app\ui.py" cd /d "%~dp0bucas-pmc-ai"
if not exist "app\ui.py" (
  echo [ERROR] app\ui.py not found. Put this file in the bucas-pmc-ai folder.
  goto :end
)
where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] git is not installed. Install from https://git-scm.com and run again.
  goto :end
)
echo [1/3] Staging changes (code + pmc data; .env and data\pmc.db are ignored)...
git add -A
git diff --cached --quiet
if not errorlevel 1 (
  echo        Nothing new to commit. Pushing anyway in case earlier commits are pending.
  goto :push
)
echo [2/3] Committing...
git commit -m "update %date% %time%"
if errorlevel 1 goto :fail
:push
echo [3/3] Pushing to GitHub (origin/master)...
git push origin master
if errorlevel 1 (
  echo [ERROR] Push failed. Check your GitHub sign-in (Git Credential Manager) or network.
  goto :fail
)
echo.
echo Done. Streamlit Cloud redeploys automatically in about 1-3 minutes:
echo https://koica-pmc-ai-cn8uqsszjxdfnuuyjsbg4w.streamlit.app/
goto :end
:fail
echo.
echo [ERROR] A step failed. Copy the messages above and send them to Claude.
:end
if /i "%~1"=="auto" exit /b 0
echo.
pause
