"""把這次爬到的資料安全地上傳到 GitHub（自己電腦和 GitHub 排程共用）。

不會跟另一邊同時上傳的資料衝突：
1. 從 sites.json 找出「這次成功跑完」的網站（last_success 等於這次的時間）
2. 把這些網站的資料先存在記憶體
3. 拿 GitHub 上最新版當底，只把這些網站的資料換進去，其他網站保持最新版的內容
4. 存檔、commit、push；如果 push 前 GitHub 又更新了，重做 3～4（最多 3 次）

用法：python -m crawler.publish "commit 訊息"
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILES = ["docs/data", "docs/products.xlsx"]


def _identity() -> list[str]:
    """還沒設定 git 名字 / email 時用預設值，避免 commit 失敗。"""
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
        print("> git", " ".join(args), flush=True)
    r = subprocess.run(["git", *_identity(), *args], cwd=ROOT,
                       stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.DEVNULL if quiet else None)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失敗")
    return r.returncode


def wait_unlocked(path: str, timeout_s: int = 180) -> None:
    """Windows 上檔案被 Excel 打開時無法更新：提醒使用者關掉，等它釋放。"""
    full = os.path.join(ROOT, path)
    end, warned = time.time() + timeout_s, False
    while os.path.exists(full) and time.time() < end:
        try:
            os.rename(full, full)        # 被其他程式開著時，Windows 會拒絕
            return
        except OSError:
            if not warned:
                print(f"  ！{path} 正在被其他程式使用（通常是 Excel 開著），請先關閉它，程式會自動繼續…", flush=True)
                warned = True
            time.sleep(3)


def recover() -> None:
    """上次如果中途失敗（同步到一半），先清乾淨。只動資料檔，不動程式和 .venv。"""
    git("rebase", "--abort", check=False, quiet=True)
    git("merge", "--abort", check=False, quiet=True)
    git("checkout", "--", *DATA_FILES, check=False, quiet=True)


def sync_latest() -> None:
    """程式和資料都換成 GitHub 最新版（.venv、紀錄檔等本機檔案不受影響）。"""
    wait_unlocked("docs/products.xlsx")
    git("fetch", "origin", "main")
    git("reset", "--hard", "origin/main")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def ran_sites() -> tuple[list[str], list[dict], dict]:
    """這次成功跑完的網站，以及它們的資料和狀態。"""
    from . import run
    st = _load(run.SITES_JSON, {"sites": []})
    now = st.get("updated")
    ran = [x["id"] for x in st.get("sites", []) if x.get("status") == "ok" and x.get("last_success") == now]
    products = [p for p in _load(run.PRODUCTS_JSON, []) if p["site"] in ran]
    # 狀態：這次有嘗試跑的網站都更新（失敗的也要讓網頁顯示「抓取失敗」）
    status = {x["id"]: x for x in st.get("sites", []) if x.get("last_run") == now or x["id"] in ran}
    return ran, products, status


def merge_and_save(ran: list[str], mine_products: list[dict], mine_status: dict, excel_images: bool = True) -> None:
    """以 GitHub 最新版為底，把這次跑的網站換進去。"""
    from . import run, excel
    from .clean import clean_all
    from .sites import SITES
    latest = _load(run.PRODUCTS_JSON, [])
    merged = [p for p in latest if p["site"] not in ran] + mine_products
    order = {sid: i for i, sid in enumerate(SITES)}
    merged.sort(key=lambda p: order.get(p["site"], 99))
    merged, _ = clean_all(merged)
    st = _load(run.SITES_JSON, {"sites": []})
    by_id = {x["id"]: x for x in st.get("sites", [])}
    by_id.update(mine_status)
    counts = {}
    for p in merged:
        counts[p["site"]] = counts.get(p["site"], 0) + 1
    st["sites"] = [dict(by_id.get(sid, {"id": sid}), count=counts.get(sid, 0)) for sid in SITES]
    st["updated"] = datetime.now(run.TW).isoformat(timespec="seconds")
    os.makedirs(run.DATA_DIR, exist_ok=True)
    with open(run.PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=0)
    with open(run.SITES_JSON, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    print("  更新 Excel（含縮圖，需要一點時間）…", flush=True)
    try:
        excel.write(merged, {k: v[1] for k, v in SITES.items()}, run.XLSX, images=excel_images)
    except Exception as e:  # noqa: BLE001
        print("  ！Excel 縮圖失敗，改成不含縮圖：", e)
        excel.write(merged, {k: v[1] for k, v in SITES.items()}, run.XLSX, images=False)


def publish(message: str, extra_files: dict[str, bytes] | None = None) -> bool:
    """上傳這次跑完的網站資料。成功回傳 True。extra_files：要一起放回去的檔案（例如 run.log）。"""
    ran, mine_products, mine_status = ran_sites()
    if not mine_status:
        print("  這次沒有執行任何網站，不上傳。")
        return False
    if not ran:
        print("  這次沒有網站成功抓到新資料，只更新各網站的狀態。")
    for attempt in range(1, 4):
        try:
            sync_latest()
            merge_and_save(ran, mine_products, mine_status)
            for rel, data in (extra_files or {}).items():
                with open(os.path.join(ROOT, rel), "wb") as f:
                    f.write(data)
            git("add", *DATA_FILES)
            if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
                print("  資料沒有變動，不用上傳")
                return True
            git("commit", "-q", "-m", f"{message}（{', '.join(ran) or '只更新狀態'}）")
            git("push", "origin", "HEAD:main")
            print(f"  上傳完成：{', '.join(ran) or '狀態'}", flush=True)
            return bool(ran)
        except RuntimeError as e:
            print(f"  ！第 {attempt} 次上傳失敗：{e}", flush=True)
            time.sleep(5 * attempt)
    return False


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else f"更新商品資料 {datetime.now():%Y-%m-%d %H:%M}"
    log = {}
    p = os.path.join(ROOT, "crawl-output.log")
    if os.path.exists(p):
        with open(p, "rb") as f:
            log["docs/data/run.log"] = b"".join(f.readlines()[-400:])
    raise SystemExit(0 if publish(msg, log) else 1)
