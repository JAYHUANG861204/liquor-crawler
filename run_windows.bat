@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1

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
.venv\Scripts\python -m crawler.local %*
echo.
pause
exit /b 0

:nopython
echo Python not found. Install from https://www.python.org/downloads/
echo and check "Add python.exe to PATH" during install.
pause
exit /b 1
