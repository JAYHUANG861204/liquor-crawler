@echo off
rem Crawl ALL sites on this computer, update the local report / Excel, and upload if Git is set up.
cd /d "%~dp0"
call run_windows.bat --sites all %*
