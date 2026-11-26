"""主程式：依序爬每個網站，輸出 JSON（給網頁）和 Excel。

用法：
    python -m crawler.run                    # 全部網站
    python -m crawler.run --sites my9,9city  # 只跑指定網站
    python -m crawler.run --limit 30         # 每站最多 30 筆（測試用）
    python -m crawler.run --no-images        # Excel 不放縮圖（比較快）

某個網站失敗時，會保留它上一次成功的資料，網頁上會標示「沿用上次資料」。
"""
from __future__ import annotations

import argparse
import re
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta

from .sites import SITES, LOCAL_ONLY, LOCAL_DEFAULT
from . import excel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "docs", "data")
PRODUCTS_JSON = os.path.join(DATA_DIR, "products.json")
SITES_JSON = os.path.join(DATA_DIR, "sites.json")
XLSX = os.path.join(ROOT, "docs", "products.xlsx")
TW = timezone(timedelta(hours=8))

log = logging.getLogger("crawler")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="酒類商品爬蟲")
    ap.add_argument("--sites", help="逗號分隔的網站代號：" + ",".join(SITES) + "；all = 全部；local = 只跑要在自己電腦跑的網站")
    ap.add_argument("--limit", type=int, help="每站最多幾筆（測試用）")
    ap.add_argument("--no-images", action="store_true", help="Excel 不放縮圖")
    ap.add_argument("--no-excel", action="store_true", help="不輸出 Excel")
    a = ap.parse_args(argv)
    a.sites = (a.sites or "").strip()
    os.makedirs(DATA_DIR, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(os.path.join(DATA_DIR, "run.log"), "w", encoding="utf-8")])

    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    explicit = a.sites not in (None, "", "all", "local")
    if a.sites in (None, "", "all"):
        wanted = list(SITES)
    elif a.sites == "local":
        wanted = sorted(LOCAL_DEFAULT)
    else:
        alias = {k.lower(): k for k in SITES}
        alias.update({"dutyzero": "hk", "dz": "hk", "香港": "hk", "609": "609", "changi": "changi",
                      "樟宜": "changi", "9city": "9city", "洋酒城": "9city", "my9": "my9", "買酒網": "my9",
                      "cdf": "cdf", "中免": "cdf"})
        raw = [x.strip() for x in re.split(r"[,，、\s]+", a.sites) if x.strip()]
        wanted = [alias[x.lower()] for x in raw if x.lower() in alias]
        bad = [x for x in raw if x.lower() not in alias]
        if bad:
            log.error("看不懂的網站代號：%s（可用：%s）", ", ".join(bad), ", ".join(SITES))
        if not wanted:
            log.error("沒有任何要執行的網站，請檢查 --sites 參數")
            return 2
    old_products = _load(PRODUCTS_JSON, [])
    old_status = {s["id"]: s for s in _load(SITES_JSON, {}).get("sites", [])}
    by_site: dict[str, list[dict]] = {}
    for p in old_products:
        by_site.setdefault(p["site"], []).append(p)

    now = datetime.now(TW).isoformat(timespec="seconds")
    status = {}
    for sid, (mod, name, home, cur, how) in SITES.items():
        prev = old_status.get(sid, {})
        st = {"id": sid, "name": name, "home": home, "currency": cur, "how": how,
              "last_success": prev.get("last_success"), "count": len(by_site.get(sid, [])),
              "status": prev.get("status", "未執行"), "message": prev.get("message", "")}
        if sid in wanted and in_ci and sid in LOCAL_ONLY and not explicit:
            if not prev.get("last_success"):
                by_site.pop(sid, None)   # 從沒在自己電腦成功過 → 拿掉示範資料，避免誤會
            st.update(status="local" if by_site.get(sid) else "local-none",
                      message="只在自己電腦執行（run_windows.bat），GitHub 排程不跑這站" +
                              (f"；資料是 {prev.get('last_success')} 在自己電腦抓的" if prev.get("last_success") else "，還沒在自己電腦跑過"))
        elif sid in wanted:
            t0 = time.time()
            log.info("==== %s 開始 ====", name)
            try:
                items = [p.to_dict() for p in mod.crawl(limit=a.limit)]
                # 去除重複網址
                seen, uniq = set(), []
                for p in items:
                    k = p.get("url") or (p["brand"], p["name"])
                    if k not in seen:
                        seen.add(k)
                        uniq.append(p)
                if uniq:
                    by_site[sid] = uniq
                    st.update(status="ok", last_success=now, count=len(uniq), message=f"{len(uniq)} 筆，{time.time()-t0:.0f} 秒")
                else:
                    st.update(status="empty", message="這次沒抓到商品，沿用上次資料" if by_site.get(sid) else "沒抓到商品")
            except BaseException as e:  # noqa: BLE001  連瀏覽器當掉也接住
                if isinstance(e, KeyboardInterrupt):
                    raise
                log.exception("%s 失敗", name)
                st.update(status="error", message=f"{type(e).__name__}: {str(e)[:160]}" + ("（沿用上次資料）" if by_site.get(sid) else ""))
            log.info("==== %s 結束：%s %s ====", name, st["status"], st["message"])
        st["count"] = len(by_site.get(sid, []))
        status[sid] = st

    products = [p for sid in SITES for p in by_site.get(sid, [])]
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=0)
    with open(SITES_JSON, "w", encoding="utf-8") as f:
        json.dump({"updated": now, "sites": list(status.values())}, f, ensure_ascii=False, indent=1)
    log.info("共 %d 筆 → %s", len(products), PRODUCTS_JSON)
    try:
        from .browser import SAMPLES
        with open(os.path.join(DATA_DIR, "debug_samples.json"), "w", encoding="utf-8") as f:
            json.dump(SAMPLES, f, ensure_ascii=False, indent=1)
    except Exception:  # noqa: BLE001
        pass

    if not a.no_excel:
        try:
            excel.write(products, {k: v[1] for k, v in SITES.items()}, XLSX, images=not a.no_images)
            log.info("Excel → %s", XLSX)
        except Exception:  # noqa: BLE001
            log.exception("Excel 產生失敗（網頁資料已存好，不受影響）")
            try:
                excel.write(products, {k: v[1] for k, v in SITES.items()}, XLSX, images=False)
                log.info("改用不含縮圖的 Excel → %s", XLSX)
            except Exception:  # noqa: BLE001
                log.exception("Excel 仍失敗")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
