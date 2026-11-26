"""香港 DUTY ZERO by cdf (https://www.dutyzero.com.hk/) — 香港機場免稅店的網上商店。

（原本的 hkairportshop.com 有阿里雲滑塊驗證，改抓這個網站。）
做法：從首頁找出各酒類分類頁（/showactivity/威士忌-11828 這種），
用瀏覽器逐頁打開、捲到底，抓商品卡。卡片上依序是：品牌 / 品名 / SALE / HK$ 價格 / 原價。
"""
from __future__ import annotations

import re
from urllib.parse import quote, unquote

from ..common import Product, parse_volume, parse_abv, split_prices, to_num, log
from ..browser import (browser, open_page, scroll_and_more, extract_cards, extract_cards_by_price,
                       slow_scroll, stock_in, text_lines)
from .. import brands

SITE = "hk"
BASE = "https://www.dutyzero.com.hk/"
# 已知的分類頁；首頁上找到的其他 showactivity 分類也會一起抓
SEEDS = [BASE + "showactivity/" + quote("威士忌") + "-11828"]
CATEGORY_RE = r"dutyzero\.com\.hk/showactivity/"
PRODUCT_RE = r"dutyzero\.com\.hk/(item|product|goods|detail)s?/"
PRICE_JS = r"HK\$\s*[\d,]+"   # 一張商品卡有 1～2 個 HK$ 價格
SKIP_CATEGORY = re.compile(r"food|食品|toy|玩具|cigar|雪茄|cigarette|香煙", re.I)
MAX_PAGES = 80

JS_LINKS = """(pat) => [...new Set([...document.querySelectorAll('a[href]')]
  .map(a => a.href.split('#')[0]).filter(h => new RegExp(pat).test(h)))]"""


def crawl(limit: int | None = None) -> list[Product]:
    cards: dict[str, dict] = {}
    with browser() as ctx:
        home = open_page(ctx, BASE, wait_ms=3000)
        queue = SEEDS + [u for u in home.evaluate(JS_LINKS, CATEGORY_RE) if not SKIP_CATEGORY.search(unquote(u))]
        for c in extract_cards(home, PRODUCT_RE):
            cards.setdefault(c["url"], c)
        home.close()
        seen = set()
        while queue and len(seen) < MAX_PAGES:
            u = queue.pop(0)
            if u in seen:
                continue
            seen.add(u)
            try:
                page = open_page(ctx, u, wait_ms=2500)
                slow_scroll(page)                       # 慢慢捲，讓圖片和後面的商品載入
                scroll_and_more(page, max_rounds=5)
                found = extract_cards(page, PRODUCT_RE) + extract_cards_by_price(page, PRICE_JS, BASE)
                for c in found:
                    key = c["url"] or _key(c["text"])
                    old = cards.get(key)
                    if not old or (c.get("img") and not old.get("img")):
                        cards[key] = c
                # 同一分類的分頁連結（?page=2 之類）
                for x in page.evaluate(JS_LINKS, CATEGORY_RE):
                    if x not in seen and x not in queue and x.split("?")[0] == u.split("?")[0]:
                        queue.append(x)
                log.info("hk %s：%d 件", unquote(u)[-40:], len(found))
                page.close()
            except Exception as e:  # noqa: BLE001
                log.warning("hk 頁面失敗 %s: %s", u, e)
            if limit and len(cards) >= limit:
                break
    log.info("hk 開了 %d 個分類頁，共 %d 件", len(seen), len(cards))
    out = [parse_card(c) for c in cards.values()]
    return [p for p in out if p.name][: limit or None]


def _key(text: str) -> str:
    """沒有商品網址時，用品名當作識別。"""
    lines = [ln for ln in text_lines(text) if not re.fullmatch(r"HK\$?|SALE|[\d,.]+", ln, re.I)]
    return "name:" + (max(lines, key=len) if lines else text[:80])


def prices(text: str) -> list[float]:
    """價格可能寫成「HK$\\n684」或「SALE\\n219\\nHK$338」：HK$ 後面的數字和單獨一行的數字都算。"""
    out = [to_num(m.group(1)) for m in re.finditer(r"HK\$\s*([\d,]+(?:\.\d+)?)", text)]
    for ln in text.splitlines():
        ln = ln.strip()
        if re.fullmatch(r"[\d,]+(?:\.\d+)?", ln):
            v = to_num(ln)
            if v and v >= 10:
                out.append(v)
    return [v for v in out if v]


def parse_card(c: dict) -> Product:
    text = c.get("text", "")
    lines = [ln for ln in text_lines(text) if not re.fullmatch(r"HK\$?|SALE|[\d,.]+", ln, re.I)]
    name = max(lines, key=len) if lines else (c.get("title") or "")
    # 品牌是品名前面那一行短的英文，例如 Masi / The Macallan
    idx = lines.index(name) if name in lines else len(lines)
    brand_line = next((ln for ln in reversed(lines[:idx]) if len(ln) <= 30), None)
    lp, pp = split_prices(prices(text))
    return Product(
        site=SITE,
        brand=brands.normalize(brand_line, name),
        name=name,
        volume_ml=parse_volume(name),
        abv=parse_abv(name),
        list_price=lp,
        promo_price=pp,
        currency="HKD",
        stock=stock_in(text),
        image=c.get("img") or None,
        url=c["url"] or None,
    )
