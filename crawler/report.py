"""產生本機報表 docs/report.html：把資料直接放進網頁，雙擊就能用瀏覽器打開（不需要網路伺服器）。"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
REPORT = os.path.join(DOCS, "report.html")


def _js(data) -> str:
    # 放進 <script> 裡要避免 </script> 提早結束
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def build() -> str:
    with open(os.path.join(DOCS, "index.html"), encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(DOCS, "data", "products.json"), encoding="utf-8") as f:
        products = json.load(f)
    with open(os.path.join(DOCS, "data", "sites.json"), encoding="utf-8") as f:
        sites = json.load(f)
    inject = f"<script>window.__PRODUCTS__={_js(products)};window.__SITES__={_js(sites)};</script>\n"
    marker = "</head>"
    assert marker in html
    html = html.replace(marker, inject + marker, 1)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(html)
    return REPORT


if __name__ == "__main__":
    print(build())
