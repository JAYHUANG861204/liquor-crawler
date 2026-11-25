"""HK Airport Shop 香港機場 (https://hkairportshop.com/) — 【實驗中】

一般請求會被網站防火牆（WAF）擋下，只拿到安全驗證頁。
這裡改用真實瀏覽器開，並慢慢翻頁。若在 GitHub 上仍被擋，
可改在自己電腦上跑（見 README「在自己電腦執行」）。
"""
from __future__ import annotations

from ..common import Product, parse_volume, parse_abv, split_prices, log
from ..browser import pick_name as _pick_name, browser, open_page, scroll_and_more, extract_cards, prices_in, stock_in, text_lines
from .. import brands

SITE = "hk"
URL = "https://hkairportshop.com/eshop_en/wines-spirits-liquors.html"
# 商品頁：/eshop_en/xxxx.html，排除分類頁本身
PRODUCT_RE = r"hkairportshop\.com/eshop_en/(?!wines-spirits-liquors)[\w\-]+\.html"
MAX_PAGES = 15


def crawl(limit: int | None = None) -> list[Product]:
    cards: dict[str, dict] = {}
    with browser() as ctx:
        for p in range(1, MAX_PAGES + 1):
            url = URL if p == 1 else f"{URL}?p={p}"
            page = open_page(ctx, url, wait_ms=4000)
            scroll_and_more(page, max_rounds=3)
            found = extract_cards(page, PRODUCT_RE)
            page.close()
            new = [c for c in found if c["url"] not in cards]
            log.info("hk 第 %d 頁：%d 件（新 %d）", p, len(found), len(new))
            if not new:
                break
            for c in new:
                cards[c["url"]] = c
            if limit and len(cards) >= limit:
                break
    out = [parse_card(c) for c in cards.values()]
    return [p for p in out if p.name][: limit or None]


def parse_card(c: dict) -> Product:
    text = c.get("text", "")
    lines = text_lines(text)
    name = _pick_name(c.get("title") or "", lines)
    lp, pp = split_prices(prices_in(text))
    return Product(
        site=SITE, brand=brands.normalize(None, name), name=name,
        volume_ml=parse_volume(text), abv=parse_abv(text),
        list_price=lp, promo_price=pp, currency="HKD",
        stock=stock_in(text), image=c.get("img") or None, url=c["url"],
    )
