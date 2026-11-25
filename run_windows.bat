@echo off
chcp 65001 >nul
cd /d %~dp0
echo === 酒類爬蟲 ===
if not exist .venv (
  echo 第一次執行，安裝套件中（需要幾分鐘）...
  python -m venv .venv || (echo 找不到 Python，請先安裝 https://www.python.org/downloads/ 並勾選 Add to PATH & pause & exit /b 1)
  call .venv\Scripts\activate
  pip install -r requirements.txt
  python -m playwright install chromium
) else (
  call .venv\Scripts\activate
)
python -m crawler.run %*
echo.
echo 完成！結果在 docs\products.xlsx
start "" docs\products.xlsx
pause
