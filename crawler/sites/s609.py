"""酒條通 609 (https://www.609.com.tw/)

分類頁的商品是 JavaScript 載入的，用瀏覽器打開各分類頁，抓商品卡。
商品頁網址格式：/Product/{編號}
品名裡通常有容量（例如「…調和威士忌1000ml」），酒精濃度列表上沒有。
"""
from __future__ import annotations

from urllib.parse import quote

from ..common import Product, parse_volume, parse_abv, split_prices, log
from ..browser import pick_name as _pick_name, browser, open_page, scroll_and_more, extract_cards, prices_in, stock_in, text_lines
from .. import brands

SITE = "609"
BASE = "https://www.609.com.tw"
CATEGORIES = ["威士忌", "白蘭地", "葡萄酒", "香檳氣泡酒", "清酒", "調酒"]
PRODUCT_RE = r"609\.com\.tw/Product/\d+"


def urls() -> list[str]:
    return [BASE + "/"] + [f"{BASE}/Country/{quote(c)}" for c in CATEGORIES] + [f"{BASE}/ProductList/{quote('果實酒')}"]


# 分類頁上的品牌/國別連結（例如 /ProductList/麥卡倫），逐一打開才看得到商品
LIST_RE = r"609\.com\.tw/(ProductList|Country|Area|Brand|Product/List|Search)[/?]"
MAX_PAGES = 150

JS_LINKS = """(pat) => [...new Set([...document.querySelectorAll('a[href]')]
  .map(a => a.href.split('#')[0]).filter(h => new RegExp(pat).test(h)))]"""


def crawl(limit: int | None = None) -> list[Product]:
    cards: dict[str, dict] = {}
    queue, seen = urls(), set()
    with browser() as ctx:
        while queue and len(seen) < MAX_PAGES:
            u = queue.pop(0)
            if u in seen:
                continue
            seen.add(u)
            try:
                page = open_page(ctx, u, wait_ms=1500)
                scroll_and_more(page, max_rounds=6)
                for c in extract_cards(page, PRODUCT_RE):
                    cards.setdefault(c["url"], c)
                queue += [x for x in page.evaluate(JS_LINKS, LIST_RE) if x not in seen and x not in queue]
                page.close()
            except Exception as e:  # noqa: BLE001
                log.warning("609 頁面失敗 %s: %s", u, e)
            if limit and len(cards) >= limit:
                break
    log.info("609 開了 %d 頁，找到 %d 件", len(seen), len(cards))
    out = [parse_card(c) for c in cards.values()]
    out = [p for p in out if p.name]
    return out[:limit] if limit else out


def parse_card(c: dict) -> Product:
    text = c.get("text", "")
    lines = text_lines(text)
    name = _pick_name(c.get("title") or "", lines)
    lp, pp = split_prices(prices_in(text))
    return Product(
        site=SITE,
        brand=brands.normalize(None, name),
        name=name,
        volume_ml=parse_volume(name),
        abv=parse_abv(text),
        list_price=lp,
        promo_price=pp,
        currency="TWD",
        stock=stock_in(text),
        image=c.get("img") or None,
        url=c["url"],
    )
