"""不用安裝 Git，直接用 GitHub API 上傳資料（給沒有 Git 的使用者）。

需要一組 GitHub「fine-grained personal access token」，權限只要：
  Repository access：Only select repositories → 這個 repo
  Repository permissions：Contents → Read and write
金鑰存在本機的 upload.json（不會上傳到 GitHub）。

流程（不會跟 GitHub 排程互相覆蓋）：
1. 從 sites.json 找出這次成功跑完的網站，資料先存在記憶體
2. 從 GitHub 下載最新的 products.json / sites.json
3. 只把這次跑的網站換進去，重做 Excel
4. 用 Git Data API 一次提交三個檔案；如果期間 GitHub 又有新提交，重做 2～4（最多 3 次）
"""
from __future__ import annotations

import base64
import json
import os
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "upload.json")
DEFAULT_REPO = "JAYHUANG861204/liquor-crawler"
API = "https://api.github.com"
FILES = ["docs/data/products.json", "docs/data/sites.json", "docs/products.xlsx"]


def load_config() -> dict | None:
    try:
        with open(CONFIG, encoding="utf-8") as f:
            c = json.load(f)
        if c.get("token"):
            c.setdefault("repo", DEFAULT_REPO)
            c.setdefault("branch", "main")
            return c
    except Exception:  # noqa: BLE001
        pass
    return None


def save_config(token: str, repo: str = DEFAULT_REPO, branch: str = "main") -> None:
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump({"token": token.strip(), "repo": repo.strip(), "branch": branch.strip()}, f, indent=1)


class GitHub:
    def __init__(self, cfg: dict):
        self.repo, self.branch = cfg["repo"], cfg["branch"]
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {cfg['token']}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "liquor-crawler"})

    def _req(self, method: str, path: str, **kw):
        r = self.s.request(method, f"{API}/repos/{self.repo}{path}", timeout=120, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"GitHub API {method} {path} → {r.status_code} {r.text[:200]}")
        return r

    def check(self) -> str:
        """確認金鑰可用、有寫入權限。回傳說明文字；有問題就丟錯誤。"""
        r = self.s.get(f"{API}/repos/{self.repo}", timeout=30)
        if r.status_code == 401:
            raise RuntimeError("金鑰無效或已過期")
        if r.status_code == 404:
            raise RuntimeError(f"找不到 repo {self.repo}，或金鑰沒有這個 repo 的權限")
        r.raise_for_status()
        perm = r.json().get("permissions")
        if not perm:
            raise RuntimeError("金鑰沒有被 GitHub 接受（請確認有貼完整）")
        if not perm.get("push"):
            raise RuntimeError("金鑰沒有寫入權限（Contents 要設成 Read and write）")
        return f"可以上傳到 {self.repo}（{self.branch}）"

    def head(self) -> str:
        return self._req("GET", f"/git/ref/heads/{self.branch}").json()["object"]["sha"]

    def download(self, path: str, ref: str) -> bytes | None:
        r = self.s.get(f"{API}/repos/{self.repo}/contents/{path}", params={"ref": ref}, timeout=120,
                       headers={"Accept": "application/vnd.github.raw+json"})
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise RuntimeError(f"下載 {path} 失敗：{r.status_code}")
        return r.content

    def commit_files(self, parent: str, files: dict[str, bytes], message: str) -> str:
        base_tree = self._req("GET", f"/git/commits/{parent}").json()["tree"]["sha"]
        tree = []
        for path, data in files.items():
            blob = self._req("POST", "/git/blobs", json={"content": base64.b64encode(data).decode(),
                                                          "encoding": "base64"}).json()["sha"]
            tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob})
        new_tree = self._req("POST", "/git/trees", json={"base_tree": base_tree, "tree": tree}).json()["sha"]
        if new_tree == base_tree:
            return ""
        commit = self._req("POST", "/git/commits", json={"message": message, "tree": new_tree,
                                                          "parents": [parent]}).json()["sha"]
        # force=False：如果期間 GitHub 有新提交，這裡會失敗，外面會重來
        self._req("PATCH", f"/git/refs/heads/{self.branch}", json={"sha": commit, "force": False})
        return commit


def publish_via_api(message: str, cfg: dict | None = None) -> bool:
    from . import run
    from .publish import ran_sites, merge_and_save
    cfg = cfg or load_config()
    if not cfg:
        return False
    gh = GitHub(cfg)
    ran, mine_products, mine_status = ran_sites()
    if not mine_status:
        print("  這次沒有執行任何網站，不上傳。")
        return False
    for attempt in range(1, 4):
        try:
            parent = gh.head()
            # 下載網站上最新的資料當底
            for rel, local in (("docs/data/products.json", run.PRODUCTS_JSON), ("docs/data/sites.json", run.SITES_JSON)):
                data = gh.download(rel, parent)
                if data is not None:
                    with open(local, "wb") as f:
                        f.write(data)
            merge_and_save(ran, mine_products, mine_status)
            payload = {}
            for rel in FILES:
                p = os.path.join(ROOT, rel)
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        payload[rel] = f.read()
            sha = gh.commit_files(parent, payload, f"{message}（{', '.join(ran) or '只更新狀態'}）")
            print("  資料沒有變動，不用上傳" if not sha else f"  上傳完成：{', '.join(ran) or '狀態'}", flush=True)
            # 報表也用合併後的資料重做
            try:
                from .report import build
                build()
            except Exception:  # noqa: BLE001
                pass
            return bool(ran)
        except Exception as e:  # noqa: BLE001
            print(f"  ！第 {attempt} 次上傳失敗：{e}", flush=True)
            time.sleep(5 * attempt)
    return False


if __name__ == "__main__":
    c = load_config()
    print(GitHub(c).check() if c else "沒有設定 upload.json")
