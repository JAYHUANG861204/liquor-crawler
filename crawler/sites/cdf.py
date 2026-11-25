"""中免日上 CDF Sunrise (https://www.cdfsunrise.com/) — 【實驗中】

整個網站是 JavaScript 單頁應用（App 風格），靜態網頁是空的。
這裡用瀏覽器打開，搜尋酒類關鍵字，抓有 ¥ 價格的商品卡。

若抓不到：用 Chrome 開網站 → F12 → Network → 篩 Fetch/XHR，
找到回傳商品清單的 API 網址，改寫成直接呼叫 API 會最穩。
"""
from __future__ import annotations

from urllib.parse import quote

from ..common import Product, parse_volume, parse_abv, split_prices, log
from ..browser import pick_name as _pick_name, browser, open_page, scroll_and_more, extract_cards, prices_in, stock_in, text_lines
from .. import brands

SITE = "cdf"
BASE = "https://www.cdfsunrise.com/"
KEYWORDS = ["威士忌", "白兰地", "葡萄酒", "香槟", "洋酒"]
PRODUCT_RE = r"cdfsunrise\.com/.*(goods|product|detail|item)"


def crawl(limit: int | None = None) -> list[Product]:
    cards: dict[str, dict] = {}
    with browser() as ctx:
        for kw in KEYWORDS:
            for url in (f"{BASE}#/search?keyword={quote(kw)}", f"{BASE}#/searchResult?keyword={quote(kw)}"):
                try:
                    page = open_page(ctx, url, wait_ms=5000)
                    scroll_and_more(page, max_rounds=5)
                    for c in extract_cards(page, PRODUCT_RE):
                        cards.setdefault(c["url"], c)
                    page.close()
                except Exception as e:  # noqa: BLE001
                    log.warning("cdf 失敗 %s: %s", url, e)
            if limit and len(cards) >= limit:
                break
    out = []
    for c in cards.values():
        text = c.get("text", "")
        lines = text_lines(text)
        name = _pick_name(c.get("title") or "", lines)
        if not name:
            continue
        lp, pp = split_prices(prices_in(text))
        out.append(Product(
            site=SITE, brand=brands.normalize(None, name), name=name,
            volume_ml=parse_volume(text), abv=parse_abv(text),
            list_price=lp, promo_price=pp, currency="CNY",
            stock=stock_in(text), image=c.get("img") or None, url=c["url"],
        ))
    return out[: limit or None]
