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
    argv = [a for a in sys.argv[1:] if a.lower() not in ("--auto", "--from-menu")]
    if not any(a.startswith("--sites") for a in argv):
        argv = ["--sites", "local"] + argv
    from .ghapi import load_config, publish_via_api
    api_cfg = load_config()                 # 有上傳金鑰 → 用 GitHub API 上傳（不需要 Git）
    upload = has_git() and not api_cfg      # 沒金鑰但有 Git → 用 Git 上傳

    if api_cfg:
        print("\n[1/3] 已設定上傳金鑰，跑完會自動上傳到網頁。", flush=True)
    elif upload:
        print("\n[1/3] 從 GitHub 取得最新的程式和資料…", flush=True)
        recover()
        try:
            sync_latest()
        except RuntimeError as e:
            print("  ！", e, "— 先用電腦上現有的資料繼續")
    else:
        print("\n（還沒設定上傳金鑰：跑完只會更新這台電腦上的報表和 Excel，網頁不會更新。")
        print("  要讓網頁也更新，請在 menu.bat 選「設定自動上傳到網頁」。）")

    print("\n[2/3] 開始爬蟲…", flush=True)
    run.main(argv)
    logging.shutdown()            # 關閉紀錄檔，Windows 才能讓 git 更新它
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)

    if api_cfg:
        print("\n[3/3] 上傳結果到網頁…", flush=True)
        if publish_via_api(f"自己電腦更新 {datetime.now():%Y-%m-%d %H:%M}", api_cfg):
            print("\n  大約 1～3 分鐘後網頁會更新。")
        else:
            print("\n  沒有上傳成功（資料還是有存在這台電腦的報表和 Excel）。")
            print("  如果顯示金鑰無效或過期，請在 menu.bat 選「設定自動上傳到網頁」重新貼上金鑰。")
    elif upload:
        print("\n[3/3] 上傳結果到 GitHub…", flush=True)
        if publish(f"自己電腦更新 {datetime.now():%Y-%m-%d %H:%M}"):
            print("\n  大約 1～3 分鐘後網頁會更新：https://jayhuang861204.github.io/liquor-crawler/")
        else:
            print("\n  沒有上傳。請把上面的訊息截圖給 Claude。")
            return 1

    xlsx = os.path.join(ROOT, "docs", "products.xlsx")
    report = os.path.join(ROOT, "docs", "report.html")
    print(f"\n  本機報表：{report}")
    print(f"  Excel：{xlsx}")
    if os.name == "nt" and os.path.exists(report) and not os.environ.get("LIQUOR_NO_OPEN"):
        os.startfile(report)  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
