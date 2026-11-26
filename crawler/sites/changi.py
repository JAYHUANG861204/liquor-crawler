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
    return re.sub(r"\s+", " ", m.group(1).replace("-", " ")).strip().title() if m else ""


def parse_card(c: dict) -> Product:
    text = c.get("text", "")
    lines = text_lines(text)              # 已去掉 Giftwrap / Exclusive / Buy 2 Get… 這類標籤
    slug_name = _name_from_slug(c["url"])
    # 品名：卡片上最長的那行（通常是「品牌 + 品名 + 容量 + 濃度」全大寫）
    name = max(lines, key=len) if lines else slug_name
    if len(name) < 12 and len(slug_name) > len(name):
        name = slug_name
    # 品牌：品名開頭的那個短行，例如 PENFOLDS / PENFOLDS BIN 407…
    brand_line = next((ln for ln in lines if ln != name and len(ln) <= 30 and name.upper().startswith(ln.upper())), None)
    if not brand_line and lines and len(lines[0]) <= 30 and lines[0] != name:
        brand_line = lines[0]
    full = f"{name} {slug_name.replace(' ', ' ')}"
    # Changi 的價格一定是「S$123.45」兩位小數；其他數字（年份、省下的金額）不算
    ps = [float(x.replace(",", "")) for x in re.findall(r"S\$\s*([\d,]+\.\d{2})", text)]
    ps = [v for v, m in zip(ps, re.finditer(r"S\$\s*[\d,]+\.\d{2}", text))
          if not re.search(r"(save|off|less)\W{0,3}$", text[max(0, m.start() - 10):m.start()], re.I)]
    lp, pp = split_prices(ps or prices_in(text))
    brand = brands.normalize(brand_line, name)
    return Product(
        site=SITE,
        brand=brand.title() if brand.isupper() else brand,
        name=name,
        volume_ml=parse_volume(full),
        abv=parse_abv(name) or _abv_from_slug(c["url"]),
        list_price=lp,
        promo_price=pp,
        currency="SGD",
        stock=stock_in(text),
        image=c.get("img") or None,
        url=c["url"].split("#")[0],
    )


def _abv_from_slug(url: str):
    # 網址像 …-700ml-43--mp00888861 → 43%；…-12-5--750ml → 12.5%
    m = re.search(r"-(\d{1,2})(?:-(\d))?--", url)
    if not m:
        return None
    v = float(m.group(1) + ("." + m.group(2) if m.group(2) else ""))
    return v if 3 <= v <= 75 else None
