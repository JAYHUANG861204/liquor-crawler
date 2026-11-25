"""iShopChangi 新加坡樟宜機場 (https://www.ishopchangi.com/) — 酒類分類頁。

分類頁一次顯示 48 件，下面有「LOAD MORE」按鈕，需要用瀏覽器一直按。
商品頁網址格式：/en/product/{slug}-mp{編號}
標題裡通常就有容量和濃度，例如「Blue Label 1000ML 40%」。
"""
from __future__ import annotations

import re

from ..common import Product, parse_volume, parse_abv, split_prices
from ..browser import browser, open_page, scroll_and_more, extract_cards, prices_in, stock_in, text_lines
from .. import brands

SITE = "changi"
URL = ("https://www.ishopchangi.com/en/category/wine-and-spirits"
       "?cagCollectionPoint=HOMEDELIVERYTRAVELLER,ARRIVAL,DEPARTURE")
PRODUCT_RE = r"ishopchangi\.com/.*/product/.+-mp\d+"
MAX_LOAD_MORE = 25  # 48 x 25 ≈ 1200 件


def crawl(limit: int | None = None) -> list[Product]:
    with browser() as ctx:
        page = open_page(ctx, URL, wait_ms=4000)
        rounds = MAX_LOAD_MORE if not limit else max(1, limit // 48 + 1)
        scroll_and_more(page, max_rounds=rounds)
        cards = extract_cards(page, PRODUCT_RE)
    out = [parse_card(c) for c in cards]
    out = [p for p in out if p.name]
    return out[:limit] if limit else out


def _name_from_slug(url: str) -> str:
    m = re.search(r"/product/(.+?)-mp\d+", url)
    return m.group(1).replace("-", " ").title() if m else ""


def parse_card(c: dict) -> Product:
    text = c.get("text", "")
    lines = text_lines(text)
    title = c.get("title") or ""
    # 卡片上通常第一行是品牌、第二行是品名
    if len(lines) >= 2 and len(lines[0]) <= 40:
        brand_line, name = lines[0], lines[1]
    else:
        brand_line, name = "", (lines[0] if lines else title or _name_from_slug(c["url"]))
    full = f"{brand_line} {name} {title} {_name_from_slug(c['url'])}"
    lp, pp = split_prices(prices_in(text))
    return Product(
        site=SITE,
        brand=brands.normalize(brand_line or None, name or full),
        name=name,
        volume_ml=parse_volume(full),
        abv=parse_abv(full),
        list_price=lp,
        promo_price=pp,
        currency="SGD",
        stock=stock_in(text),
        image=c.get("img") or None,
        url=c["url"],
    )
