@echo off
rem ============================================================
rem  Liquor price crawler - one-time setup
rem  1) find or install Python  2) (no Git needed)  3) install packages
rem  3) download the browser     4) open the Chinese menu
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title Liquor crawler setup

echo.
echo [1/4] Checking Python...
set "PY="
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if defined PY goto havepython

echo     Python not found. Installing Python 3.12 with winget...
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PY goto havepython
echo.
echo     Could not install Python automatically.
echo     Please install it from https://www.python.org/downloads/
echo     (check "Add python.exe to PATH"), then run setup.bat again.
pause
exit /b 1

:havepython
echo     OK: %PY%

echo.
echo [2/4] Git is not required (uploading uses the key set in the menu).

echo.
echo [3/4] Installing packages (first time takes a few minutes)...
if not exist .venv\Scripts\python.exe "%PY%" -m venv .venv
if not exist .venv\Scripts\python.exe goto venvfail
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\python -m pip install -q -r requirements.txt
if errorlevel 1 goto pipfail

echo.
echo [4/4] Downloading the browser used by the crawler...
.venv\Scripts\python -m playwright install chromium
if errorlevel 1 goto pipfail

echo.
echo Setup finished. Opening the menu...
.venv\Scripts\python -m crawler.wizard
exit /b 0

:venvfail
echo Could not create the .venv folder. Check that this folder is writable.
pause
exit /b 1

:pipfail
echo Package installation failed. Check the internet connection and run setup.bat again.
pause
exit /b 1
