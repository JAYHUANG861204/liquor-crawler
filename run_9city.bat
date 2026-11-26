@echo off
rem Crawl 9city on this computer and upload the result to GitHub.
rem Double-click to run now. Task Scheduler calls it with --auto.
cd /d "%~dp0"
call run_windows.bat --sites 9city %*
