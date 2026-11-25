"""買酒網 MY9 (https://www.my9.com.tw/) — Shopify 商店。

Shopify 有公開的 /products.json，一次可拿 250 筆，含原價、售價、是否有貨、圖片，
不用解析 HTML，是六個網站裡最穩定的。
"""
from __future__ import annotations

import re

from ..common import Product, session, get, parse_volume, parse_abv, clean
from .. import brands

SITE = "my9"
BASE = "https://www.my9.com.tw"
MAX_PAGES = 20  # 250 x 20 = 最多 5000 筆


def _strip_html(html: str) -> str:
    return clean(re.sub(r"<[^>]+>", " ", html or ""))


def crawl(limit: int | None = None) -> list[Product]:
    s = session()
    out: list[Product] = []
    for page in range(1, MAX_PAGES + 1):
        r = get(s, f"{BASE}/products.json", params={"limit": 250, "page": page})
        items = r.json().get("products", [])
        if not items:
            break
        for p in items:
            out.append(parse_product(p))
            if limit and len(out) >= limit:
                return out
    return out


def parse_product(p: dict) -> Product:
    variants = p.get("variants") or [{}]
    v = variants[0]
    title = p.get("title", "")
    # 標題常是「中文 || English」，兩段都保留
    name = clean(title.replace("||", "/"))
    body = _strip_html(p.get("body_html", ""))
    opt_text = " ".join(str(v.get(k) or "") for k in ("option1", "option2", "option3", "title"))
    price = float(v["price"]) if v.get("price") else None
    compare = float(v["compare_at_price"]) if v.get("compare_at_price") else None
    if compare and price and compare > price:
        list_price, promo = compare, price
    else:
        list_price, promo = price, None
    available = any(x.get("available") for x in variants)
    imgs = p.get("images") or []
    tags = p.get("tags") or []
    if isinstance(tags, str):
        tags = tags.split(",")
    return Product(
        site=SITE,
        brand=brands.normalize(p.get("vendor"), title),
        name=name,
        volume_ml=parse_volume(opt_text) or parse_volume(title) or parse_volume(body),
        abv=parse_abv(title, strict=True) or parse_abv(body, strict=True),
        list_price=list_price,
        promo_price=promo,
        currency="TWD",
        stock="有貨" if available else "缺貨",
        image=imgs[0]["src"] if imgs else None,
        url=f"{BASE}/products/{p.get('handle')}",
        extra={"type": p.get("product_type") or None, "tags": [t.strip() for t in tags][:8]},
    )
