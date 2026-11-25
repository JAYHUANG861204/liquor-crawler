"""洋酒城 9city (https://www.9city.com.tw/)

列表頁只有會員價，所以做法是：
1. 從首頁和各酒類分類頁收集商品頁連結（/product/P… 或 product.php?pid_for_show=…）
2. 一頁一頁打開商品頁，抓 建議售價、會員特價、容量規格、酒精濃度、og:image
商品頁是一般 HTML，不需要瀏覽器。
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..common import Product, session, get, parse_volume, parse_abv, to_num, clean, abs_url, log
from .. import brands

SITE = "9city"
BASE = "https://www.9city.com.tw/"
START = [
    BASE,
    BASE + "index.php?type=1&arem=67",   # 威士忌
    BASE + "index.php?type=1&arem=97",   # 白蘭地
    BASE + "index.php?type=1&arem=98",   # 葡萄酒
    BASE + "index.php?type=1&arem=100",  # 調烈酒
]
PRODUCT_RE = re.compile(r"(/product/P\d+|product\.php\?pid_for_show=\d+)")
CATEGORY_RE = re.compile(r"category\.php\?[^\"'#]*arem=\d+[^\"'#]*")
MAX_CATEGORY_PAGES = 60
MAX_PRODUCTS = 400


def _links(html: str, base: str) -> tuple[set[str], set[str]]:
    soup = BeautifulSoup(html, "html.parser")
    prods, cats = set(), set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if PRODUCT_RE.search(href):
            u = urljoin(base, href)
            u = re.sub(r"([?&])(promotion_product_sn|category_sn)=\d+&?", r"\1", u).rstrip("?&")
            prods.add(u)
        elif CATEGORY_RE.search(href):
            cats.add(urljoin(base, href))
    return prods, cats


def collect_links(s) -> list[str]:
    prods: set[str] = set()
    queue, seen = list(START), set()
    while queue and len(seen) < MAX_CATEGORY_PAGES:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            html = get(s, url).text
        except Exception as e:  # noqa: BLE001
            log.warning("9city 分類頁失敗 %s: %s", url, e)
            continue
        p, c = _links(html, url)
        prods |= p
        queue += [x for x in sorted(c) if x not in seen]
    return sorted(prods)


def crawl(limit: int | None = None) -> list[Product]:
    s = session()
    links = collect_links(s)
    log.info("9city 找到 %d 個商品連結", len(links))
    out, seen = [], set()
    for url in links[: (limit or MAX_PRODUCTS)]:
        try:
            p = parse_product(get(s, url).text, url)
        except Exception as e:  # noqa: BLE001
            log.warning("9city 商品頁失敗 %s: %s", url, e)
            continue
        if p and p.url not in seen:
            seen.add(p.url)
            out.append(p)
    return out


def _meta(soup, prop):
    t = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return t.get("content") if t else None


def parse_product(html: str, url: str) -> Product | None:
    soup = BeautifulSoup(html, "html.parser")
    title = _meta(soup, "og:title") or (soup.title.string if soup.title else "") or ""
    title = clean(re.split(r"[｜|]", title)[0])
    h1 = soup.find("h1")
    name = clean(h1.get_text()) if h1 else title
    if not name:
        return None
    text = soup.get_text("\n")
    flat = clean(text)

    def after(label_re):
        m = re.search(label_re + r"\s*[:：]?\s*(?:NT)?\$?\s*([\d,]+)", flat)
        return to_num(m.group(1)) if m else None

    list_price = after(r"建議售價")
    member = after(r"會員(?:特)?價")
    sale = after(r"(?:優惠|特惠|促銷)價")
    promo = member or sale
    if list_price is None and promo is not None:
        # 沒有建議售價時，唯一的價格當訂價
        list_price, promo = promo, None
    vol = None
    m = re.search(r"容量規格\s*[:：]?\s*([\d.,]+\s*(?:ml|ML|l|L|cl))", flat)
    if m:
        vol = parse_volume(m.group(1))
    m = re.search(r"酒精濃度[\s\S]{0,120}?(\d{1,2}(?:\.\d+)?)\s*%", flat)
    abv = float(m.group(1)) if m else parse_abv(flat)
    if re.search(r"已售完|售完|缺貨|補貨中", flat):
        stock = "缺貨"
    elif re.search(r"加入購物車|立即購買", flat):
        stock = "可訂購"
    else:
        stock = None
    canon = _meta(soup, "og:url") or url
    en = soup.find("h6")
    return Product(
        site=SITE,
        brand=brands.normalize(None, f"{name} {clean(en.get_text()) if en else ''}"),
        name=name,
        volume_ml=vol or parse_volume(name),
        abv=abv,
        list_price=list_price,
        promo_price=promo if promo != list_price else None,
        currency="TWD",
        stock=stock,
        image=abs_url(url, _meta(soup, "og:image")),
        url=canon,
    )
