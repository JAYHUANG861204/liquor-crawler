@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1

rem --auto = unattended mode (used by Task Scheduler): no pause, no Excel popup, output saved to local-run.log
set AUTO=
echo %* | find /i "--auto" >nul && set AUTO=1
if defined AUTO set LIQUOR_NO_OPEN=1

where python >nul 2>nul
if errorlevel 1 goto nopython

if exist .venv\Scripts\python.exe goto ready
echo First run: installing packages, please wait a few minutes...
python -m venv .venv
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\python -m pip install -q -r requirements.txt
.venv\Scripts\python -m playwright install chromium

:ready
.venv\Scripts\python -m pip install -q -r requirements.txt
if defined AUTO goto auto
.venv\Scripts\python -m crawler.local %*
echo.
pause
exit /b 0

:auto
echo ===== %date% %time% ===== >> local-run.log
.venv\Scripts\python -m crawler.local %* >> local-run.log 2>&1
exit /b %errorlevel%

:nopython
echo Python not found. Install from https://www.python.org/downloads/
echo and check "Add python.exe to PATH" during install.
if not defined AUTO pause
exit /b 1
