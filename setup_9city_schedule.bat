@echo off
chcp 65001 >nul
cd /d "%~dp0"
set TASK=LiquorCrawler-9city

echo ============================================================
echo  Create a daily Windows scheduled task for 9city
echo  (the computer must be on at that time)
echo ============================================================
echo.
set /p RUNAT=Run time every day, 24h HH:MM [default 12:00]: 
if "%RUNAT%"=="" set RUNAT=12:00

schtasks /Create /F /SC DAILY /ST %RUNAT% /TN "%TASK%" /TR "\"%~dp0run_9city.bat\" --auto"
if errorlevel 1 goto fail

echo.
echo OK. Task "%TASK%" will run every day at %RUNAT%.
echo Log file: %~dp0local-run.log
echo To remove it later:  schtasks /Delete /TN "%TASK%" /F
echo To run it now:       schtasks /Run /TN "%TASK%"
pause
exit /b 0

:fail
echo.
echo Failed to create the task. Try right-click this file and "Run as administrator".
pause
exit /b 1
