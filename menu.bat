@echo off
rem Open the Chinese menu (run now / schedule / report). Runs setup first if needed.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title Liquor crawler
if not exist .venv\Scripts\python.exe goto setup
.venv\Scripts\python -m crawler.wizard
exit /b 0
:setup
call setup.bat
