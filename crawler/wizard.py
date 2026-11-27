"""中文操作選單（由 setup.bat / menu.bat 開啟）。

讓不會寫程式的人也能：立即執行、選網站、設定每日排程、刪除排程、開報表、檢查資料品質。
排程使用 Windows 內建的「工作排程器」（schtasks），工作名稱都以 LiquorCrawler- 開頭。
"""
from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import sys

from .sites import SITES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK_PREFIX = "LiquorCrawler-"
RUN_BAT = os.path.join(ROOT, "run_windows.bat")
IS_WIN = os.name == "nt"


def line(ch="=", n=56):
    print(ch * n)


def ask(prompt: str, default: str = "") -> str:
    try:
        v = input(f"{prompt}" + (f" [{default}]" if default else "") + "：").strip()
    except EOFError:
        v = ""
    return v or default


def pause():
    ask("\n按 Enter 回到選單")


# ---------- 網站選擇 ----------

def choose_sites() -> str | None:
    """回傳 --sites 參數值（逗號分隔），None 表示取消。"""
    ids = list(SITES)
    print()
    for i, sid in enumerate(ids, 1):
        print(f"  {i}. {SITES[sid][1]}（{sid}）")
    print("  A. 全部網站")
    v = ask("輸入編號，多個用逗號分隔（例如 1,3,5），或 A", "A").upper()
    if v == "A":
        return "all"
    picked = []
    for x in re.split(r"[,\s，、]+", v):
        if x.isdigit() and 1 <= int(x) <= len(ids):
            picked.append(ids[int(x) - 1])
    if not picked:
        print("  沒有選到任何網站。")
        return None
    return ",".join(dict.fromkeys(picked))


def sites_label(val: str) -> str:
    if val == "all":
        return "全部網站"
    return "、".join(SITES[s][1] for s in val.split(",") if s in SITES)


# ---------- 執行 ----------

def run_now(sites: str):
    print(f"\n開始執行：{sites_label(sites)}（會開出瀏覽器視窗，請不要關掉它）\n")
    if IS_WIN:
        subprocess.call(f'"{RUN_BAT}" --sites {sites} --from-menu', shell=True, cwd=ROOT)
    else:
        subprocess.call([sys.executable, "-m", "crawler.local", "--sites", sites], cwd=ROOT)


# ---------- 排程 ----------

def list_tasks() -> list[dict]:
    """列出 LiquorCrawler- 開頭的排程。schtasks 的欄位名稱會隨 Windows 語言變，所以用位置取值。"""
    if not IS_WIN:
        return []
    r = subprocess.run(["schtasks", "/Query", "/FO", "CSV", "/V"], capture_output=True, text=True,
                       encoding="mbcs", errors="ignore")
    out, seen = [], set()
    for row in csv.reader(io.StringIO(r.stdout)):
        if len(row) < 3 or TASK_PREFIX not in row[1]:
            continue
        name = row[1].strip("\\")
        if name in seen:
            continue
        seen.add(name)
        m = re.search(r"--sites\s+(\S+)", " ".join(row))
        out.append({"_name": name, "_next": row[2], "_sites": m.group(1) if m else ""})
    return out


def show_tasks():
    tasks = list_tasks()
    print()
    if not tasks:
        print("  目前沒有設定任何排程。")
        return tasks
    for t in tasks:
        print(f"  ・{t['_name']}　下次執行：{t['_next']}　網站：{sites_label(t['_sites']) if t['_sites'] else '?'}")
    return tasks


def add_task():
    print("\n【新增每日排程】那個時間電腦要開著（可以鎖定螢幕，但不能關機或睡眠）。")
    t = ask("每天幾點執行？24 小時制 HH:MM", "08:30")
    if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", t):
        print("  時間格式不對，例如 08:30 或 21:00。")
        return
    t = f"{int(t.split(':')[0]):02d}:{t.split(':')[1]}"
    sites = choose_sites()
    if not sites:
        return
    name = TASK_PREFIX + ("all" if sites == "all" else sites.replace(",", "-")) + "-" + t.replace(":", "")
    tr = f'"{RUN_BAT}" --auto --sites {sites}'
    if len(tr) > 255:
        print("  路徑太長，請把資料夾放到較短的位置（例如 C:\\liquor-crawler）。")
        return
    if not IS_WIN:
        print(f"  （非 Windows，示範指令）schtasks /Create /F /SC DAILY /ST {t} /TN {name} /TR {tr}")
        return
    r = subprocess.run(["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", t, "/TN", name, "/TR", tr],
                       capture_output=True, text=True, encoding="mbcs", errors="ignore")
    if r.returncode == 0:
        print(f"\n  ✔ 已建立：每天 {t} 執行「{sites_label(sites)}」")
        print(f"    執行紀錄會寫在 {os.path.join(ROOT, 'local-run.log')}")
    else:
        print("\n  ✘ 建立失敗：", (r.stderr or r.stdout).strip())
        print("    請關掉視窗，對 setup.bat 或 menu.bat 按右鍵 →「以系統管理員身分執行」再試一次。")


def delete_task():
    tasks = show_tasks()
    if not tasks:
        return
    names = [t["_name"] for t in tasks]
    for i, n in enumerate(names, 1):
        print(f"  {i}. {n}")
    v = ask("要刪除哪一個？輸入編號，A = 全部刪除，Enter = 取消", "")
    targets = names if v.upper() == "A" else ([names[int(v) - 1]] if v.isdigit() and 1 <= int(v) <= len(names) else [])
    for n in targets:
        r = subprocess.run(["schtasks", "/Delete", "/F", "/TN", n], capture_output=True, text=True,
                           encoding="mbcs", errors="ignore")
        print(("  ✔ 已刪除 " if r.returncode == 0 else "  ✘ 刪除失敗 ") + n)


def run_task_now():
    tasks = show_tasks()
    names = [t["_name"] for t in tasks]
    if not names:
        return
    for i, n in enumerate(names, 1):
        print(f"  {i}. {n}")
    v = ask("要立刻試跑哪一個排程？輸入編號", "1")
    if v.isdigit() and 1 <= int(v) <= len(names):
        subprocess.run(["schtasks", "/Run", "/TN", names[int(v) - 1]])
        print("  已在背景開始執行，完成後可用「開啟報表」查看；過程記錄在 local-run.log。")


# ---------- 報表 / 檢查 ----------

def open_file(path: str):
    if not os.path.exists(path):
        print("  還沒有這個檔案，請先執行一次爬蟲。")
        return
    if IS_WIN:
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        print("  檔案位置：", path)


def open_report():
    from .report import build
    try:
        path = build()
    except Exception as e:  # noqa: BLE001
        print("  報表產生失敗：", e)
        return
    open_file(path)


def show_log():
    p = os.path.join(ROOT, "local-run.log")
    if not os.path.exists(p):
        print("  還沒有排程執行紀錄。")
        return
    with open(p, encoding="utf-8", errors="ignore") as f:
        tail = f.readlines()[-60:]
    print("".join(tail))


def audit():
    from .audit import main as audit_main
    audit_main(["--samples", "2"])


def status():
    import json
    p = os.path.join(ROOT, "docs", "data", "sites.json")
    if not os.path.exists(p):
        print("  還沒有資料。")
        return
    s = json.load(open(p, encoding="utf-8"))
    print(f"\n  最後更新：{s.get('updated', '')}")
    for x in s.get("sites", []):
        print(f"  ・{x.get('name', x['id'])}：{x.get('count', 0)} 筆，狀態 {x.get('status', '')}，"
              f"上次成功 {x.get('last_success') or '—'}")


def setup_upload():
    from .ghapi import load_config, save_config, GitHub, DEFAULT_REPO
    cur = load_config()
    print("\n【設定自動上傳到網頁】")
    if cur:
        print(f"  目前已設定：上傳到 {cur['repo']}（金鑰 …{cur['token'][-4:]}）")
        try:
            print("  檢查結果：" + GitHub(cur).check())
        except Exception as e:  # noqa: BLE001
            print("  檢查結果：✘", e)
    print("  金鑰請向網站管理者索取（以 github_pat_ 開頭的一長串字）。直接按 Enter = 不變更。")
    tok = ask("請貼上金鑰（在這個視窗按滑鼠右鍵就能貼上）", "")
    if not tok:
        return
    repo = ask("repo 名稱", (cur or {}).get("repo", DEFAULT_REPO))
    cfg = {"token": tok.strip(), "repo": repo.strip(), "branch": "main"}
    try:
        msg = GitHub(cfg).check()
    except Exception as e:  # noqa: BLE001
        print("  ✘ 金鑰不能用：", e)
        print("    沒有儲存。請確認金鑰有沒有貼完整、權限是不是 Contents: Read and write。")
        return
    save_config(cfg["token"], cfg["repo"])
    print("  ✔ 已儲存，" + msg + "。之後每次執行（包含排程）都會自動上傳。")


def remove_upload():
    from .ghapi import CONFIG
    if os.path.exists(CONFIG) and ask("確定要刪除上傳金鑰？(y/N)", "N").lower() == "y":
        os.remove(CONFIG)
        print("  已刪除，之後只會更新這台電腦上的報表。")


MENU = [
    ("立即執行（選擇網站）", lambda: (lambda s: s and run_now(s))(choose_sites())),
    ("開啟報表（網頁）", open_report),
    ("開啟 Excel", lambda: open_file(os.path.join(ROOT, "docs", "products.xlsx"))),
    ("查看各網站資料狀態", status),
    ("新增每日排程", add_task),
    ("查看目前的排程", show_tasks),
    ("刪除排程", delete_task),
    ("立刻試跑某個排程", run_task_now),
    ("查看排程執行紀錄", show_log),
    ("檢查資料品質", audit),
    ("設定自動上傳到網頁（貼上金鑰）", setup_upload),
    ("刪除上傳金鑰", remove_upload),
]


def main():
    while True:
        print()
        line()
        print("  酒類比價爬蟲　操作選單")
        line()
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i:>2}. {label}")
        print("   0. 離開")
        line("-")
        v = ask("請輸入編號", "")
        if v in ("0", "q", "Q"):
            return 0
        if v.isdigit() and 1 <= int(v) <= len(MENU):
            try:
                MENU[int(v) - 1][1]()
            except KeyboardInterrupt:
                print("\n  已取消。")
            except Exception as e:  # noqa: BLE001
                print("\n  發生錯誤：", e)
            pause()


if __name__ == "__main__":
    raise SystemExit(main())
