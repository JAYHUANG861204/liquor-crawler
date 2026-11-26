"""在自己電腦執行：爬蟲 → 跟 GitHub 上最新的資料合併 → 上傳（網頁就會更新）。

由 run_windows.bat / run_9city.bat 呼叫。參數同 crawler.run，沒給 --sites 時只跑「要在自己電腦跑」的網站。

上傳流程刻意做成不會衝突：
1. 爬完先把結果（只有這次跑的網站）存在記憶體
2. 丟掉資料夾裡被改過的資料檔，從 GitHub 拿最新版
3. 把這次跑的網站資料換進最新版，其他網站（GitHub 排程更新的）保持不動
4. 存檔、上傳；如果上傳前 GitHub 又更新了，重複 2～4（最多 3 次）
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime

from . import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILES = ["docs/data", "docs/products.xlsx"]


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


def git(*args, check=True, quiet=False) -> int:
    if not quiet:
        print("> git", " ".join(args))
    r = subprocess.run(["git", *_identity(), *args], cwd=ROOT,
                       stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.DEVNULL if quiet else None)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失敗")
    return r.returncode


def has_git() -> bool:
    try:
        return subprocess.run(["git", "--version"], capture_output=True).returncode == 0 and \
            os.path.isdir(os.path.join(ROOT, ".git"))
    except FileNotFoundError:
        return False


def recover() -> None:
    """上次如果中途失敗（同步到一半），先清乾淨。只動資料檔，不動程式和 .venv。"""
    git("rebase", "--abort", check=False, quiet=True)
    git("merge", "--abort", check=False, quiet=True)
    git("checkout", "--", *DATA_FILES, check=False, quiet=True)


def wait_unlocked(path: str, timeout_s: int = 180) -> None:
    """Windows 上檔案被 Excel 打開時無法更新：提醒使用者關掉，等它釋放。"""
    import time
    full = os.path.join(ROOT, path)
    end, warned = time.time() + timeout_s, False
    while os.path.exists(full) and time.time() < end:
        try:
            os.rename(full, full)        # 被其他程式開著時，Windows 會拒絕
            return
        except OSError:
            if not warned:
                print(f"  ！{path} 正在被其他程式使用（通常是 Excel 開著），請先關閉它，程式會自動繼續…")
                warned = True
            time.sleep(3)


def sync_latest() -> None:
    wait_unlocked("docs/products.xlsx")
    git("fetch", "origin", "main")
    git("reset", "--hard", "origin/main")   # 程式和資料都換成 GitHub 最新版（.venv 等本機檔案不受影響）


def _load(path, default):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def merge_and_save(mine_products: list[dict], mine_status: dict, sites: list[str]) -> None:
    """把這次跑的網站資料，換進 GitHub 最新版的資料裡。"""
    from .clean import clean_all
    from .sites import SITES
    from . import excel
    latest = _load(run.PRODUCTS_JSON, [])
    merged = [p for p in latest if p["site"] not in sites] + [p for p in mine_products if p["site"] in sites]
    order = {sid: i for i, sid in enumerate(SITES)}
    merged.sort(key=lambda p: order.get(p["site"], 99))
    merged, _ = clean_all(merged)
    st = _load(run.SITES_JSON, {"sites": []})
    by_id = {x["id"]: x for x in st.get("sites", [])}
    for sid in sites:
        if sid in mine_status:
            by_id[sid] = mine_status[sid]
    counts = {}
    for p in merged:
        counts[p["site"]] = counts.get(p["site"], 0) + 1
    st["sites"] = [dict(by_id.get(sid, {"id": sid}), count=counts.get(sid, 0)) for sid in SITES]
    st["updated"] = datetime.now(run.TW).isoformat(timespec="seconds")
    with open(run.PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=0)
    with open(run.SITES_JSON, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    print("  更新 Excel（含縮圖，需要一點時間）…")
    excel.write(merged, {k: v[1] for k, v in SITES.items()}, run.XLSX, images=True)


def main() -> int:
    argv = [a for a in sys.argv[1:] if a.lower() != "--auto"]
    if not any(a.startswith("--sites") for a in argv):
        argv = ["--sites", "local"] + argv
    upload = has_git()

    if upload:
        print("\n[1/3] 從 GitHub 取得最新的程式和資料…")
        recover()
        try:
            sync_latest()
        except RuntimeError as e:
            print("  ！", e, "— 先用電腦上現有的資料繼續")
    else:
        print("\n（這個資料夾不是用 git clone 下載的，跑完只會更新電腦上的 Excel，不會上傳到網頁。")
        print("  想自動上傳，請看 README「在自己電腦執行」。）")

    print("\n[2/3] 開始爬蟲…")
    run.main(argv)
    logging.shutdown()            # 關閉紀錄檔，Windows 才能讓 git 更新它
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)

    if upload:
        print("\n[3/3] 上傳結果到 GitHub…")
        st = _load(run.SITES_JSON, {"sites": []})
        ran = [x["id"] for x in st.get("sites", []) if x["id"] in _wanted(argv) and x.get("status") == "ok"]
        if not ran:
            print("  這次沒有網站成功抓到資料，不上傳。請把上面的訊息截圖給 Claude。")
            return 1
        mine_products = [p for p in _load(run.PRODUCTS_JSON, []) if p["site"] in ran]
        mine_status = {x["id"]: x for x in st.get("sites", []) if x["id"] in ran}
        for attempt in range(1, 4):
            try:
                git("checkout", "--", *DATA_FILES, check=False, quiet=True)
                sync_latest()
                merge_and_save(mine_products, mine_status, ran)
                git("add", *DATA_FILES)
                if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
                    print("  資料沒有變動，不用上傳")
                    break
                git("commit", "-m", f"自己電腦更新 {','.join(ran)} {datetime.now():%Y-%m-%d %H:%M}")
                git("push", "origin", "HEAD:main")
                print(f"\n  上傳完成（{', '.join(ran)}）！大約 1～3 分鐘後網頁會更新：")
                print("  https://jayhuang861204.github.io/liquor-crawler/")
                break
            except RuntimeError as e:
                print(f"  ！第 {attempt} 次上傳失敗：{e}")
                if attempt == 3:
                    print("  請稍後再執行一次；如果一直失敗，把這個畫面截圖給 Claude。")
                    return 1

    xlsx = os.path.join(ROOT, "docs", "products.xlsx")
    if os.name == "nt" and os.path.exists(xlsx) and not os.environ.get("LIQUOR_NO_OPEN"):
        os.startfile(xlsx)  # type: ignore[attr-defined]
    return 0


def _wanted(argv: list[str]) -> list[str]:
    from .sites import SITES, LOCAL_DEFAULT
    val = ""
    for i, a in enumerate(argv):
        if a.startswith("--sites="):
            val = a.split("=", 1)[1]
        elif a == "--sites" and i + 1 < len(argv):
            val = argv[i + 1]
    if val in ("", "all"):
        return list(SITES)
    if val == "local":
        return sorted(LOCAL_DEFAULT)
    return [x.strip().lower() for x in val.replace("，", ",").split(",") if x.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
