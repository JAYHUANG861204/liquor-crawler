"""在自己電腦執行：先從 GitHub 拿最新資料 → 爬蟲 → 把結果上傳回 GitHub（網頁就會更新）。

由 run_windows.bat 呼叫。參數同 crawler.run，沒給 --sites 時只跑「要在自己電腦跑」的網站。
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

from . import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _identity() -> list[str]:
    """這台電腦還沒設定 git 的名字 / email 時，用預設值，避免 commit 失敗。"""
    def has(key):
        r = subprocess.run(["git", "config", key], cwd=ROOT, capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip()
    extra = []
    if not has("user.name"):
        extra += ["-c", "user.name=liquor-crawler-local"]
    if not has("user.email"):
        extra += ["-c", "user.email=liquor-crawler-local@users.noreply.github.com"]
    return extra


def git(*args, check=True) -> int:
    print("> git", " ".join(args))
    r = subprocess.run(["git", *_identity(), *args], cwd=ROOT)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失敗")
    return r.returncode


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
        print("\n[1/3] 從 GitHub 取得最新資料…")
        try:
            git("pull", "--rebase", "--autostash")
        except RuntimeError as e:
            print("  ！", e, "— 先用電腦上現有的資料繼續")
    else:
        print("\n（這個資料夾不是用 git clone 下載的，跑完只會更新電腦上的 Excel，不會上傳到網頁。")
        print("  想自動上傳，請看 README「在自己電腦執行」。）")

    print("\n[2/3] 開始爬蟲…")
    run.main(argv)

    if upload:
        print("\n[3/3] 上傳結果到 GitHub…")
        git("add", "docs/data", "docs/products.xlsx")
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
            print("  資料沒有變動，不用上傳")
        else:
            git("commit", "-m", f"自己電腦更新資料 {datetime.now():%Y-%m-%d %H:%M}")
            try:
                git("pull", "--rebase", "--autostash")
                git("push")
                print("\n  上傳完成！大約 1～3 分鐘後網頁會更新：")
                print("  https://jayhuang861204.github.io/liquor-crawler/")
            except RuntimeError as e:
                print("  ！上傳失敗：", e)
                print("  可以稍後再執行一次 run_windows.bat，會一起補上傳。")

    xlsx = os.path.join(ROOT, "docs", "products.xlsx")
    if os.name == "nt" and os.path.exists(xlsx) and not os.environ.get("LIQUOR_NO_OPEN"):
        os.startfile(xlsx)  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
