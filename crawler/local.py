"""在自己電腦執行：從 GitHub 拿最新版 → 爬蟲 → 合併後上傳（網頁就會更新）。

由 run_windows.bat / run_9city.bat 呼叫。參數同 crawler.run，沒給 --sites 時只跑「要在自己電腦跑」的網站。
上傳的細節（不會跟 GitHub 排程衝突）見 crawler/publish.py。
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime

from . import run
from .publish import recover, sync_latest, publish

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def has_git() -> bool:
    try:
        return subprocess.run(["git", "--version"], capture_output=True).returncode == 0 and \
            os.path.isdir(os.path.join(ROOT, ".git"))
    except FileNotFoundError:
        return False


def main() -> int:
    argv = [a for a in sys.argv[1:] if a.lower() != "--auto"]
    if not any(a.startswith("--sites") for a in argv):
        argv = ["--sites", "local"] + argv
    upload = has_git()

    if upload:
        print("\n[1/3] 從 GitHub 取得最新的程式和資料…", flush=True)
        recover()
        try:
            sync_latest()
        except RuntimeError as e:
            print("  ！", e, "— 先用電腦上現有的資料繼續")
    else:
        print("\n（這個資料夾不是用 git clone 下載的，跑完只會更新電腦上的 Excel，不會上傳到網頁。")
        print("  想自動上傳，請看 README「在自己電腦執行」。）")

    print("\n[2/3] 開始爬蟲…", flush=True)
    run.main(argv)
    logging.shutdown()            # 關閉紀錄檔，Windows 才能讓 git 更新它
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)

    if upload:
        print("\n[3/3] 上傳結果到 GitHub…", flush=True)
        if publish(f"自己電腦更新 {datetime.now():%Y-%m-%d %H:%M}"):
            print("\n  大約 1～3 分鐘後網頁會更新：https://jayhuang861204.github.io/liquor-crawler/")
        else:
            print("\n  沒有上傳。請把上面的訊息截圖給 Claude。")
            return 1

    xlsx = os.path.join(ROOT, "docs", "products.xlsx")
    if os.name == "nt" and os.path.exists(xlsx) and not os.environ.get("LIQUOR_NO_OPEN"):
        os.startfile(xlsx)  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
