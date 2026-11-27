@echo off
rem Core runner. Used by run_all.bat, run_9city.bat, the menu and scheduled tasks.
rem   --auto       unattended (scheduled): no pause, no windows, output to local-run.log
rem   --from-menu  started from the menu: no pause, do not pop up the report
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1

set AUTO=
set FROMMENU=
echo %* | find /i "--auto" >nul && set AUTO=1
echo %* | find /i "--from-menu" >nul && set FROMMENU=1
if defined AUTO set LIQUOR_NO_OPEN=1
if defined AUTO set SHOW_BROWSER=0
if defined FROMMENU set LIQUOR_NO_OPEN=1

if exist .venv\Scripts\python.exe goto ready
if defined AUTO goto notready
echo First run: setting up...
call setup.bat
if not exist .venv\Scripts\python.exe exit /b 1

:ready
if defined AUTO goto auto
.venv\Scripts\python -m crawler.local %*
if defined FROMMENU exit /b 0
echo.
pause
exit /b 0

:auto
echo ===== %date% %time% ===== >> local-run.log
.venv\Scripts\python -m crawler.local %* >> local-run.log 2>&1
exit /b %errorlevel%

:notready
echo ===== %date% %time% ===== not set up, please run setup.bat >> local-run.log
exit /b 1
