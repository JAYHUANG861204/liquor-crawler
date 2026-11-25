"""用真實瀏覽器（Playwright + Chromium）開網頁，給 JavaScript 才會載入商品的網站用。

做法是通用的：找出網頁上所有「網址符合商品頁格式」的連結，往外找到包住它的
商品卡（有圖片、有價格的那一塊），把卡片上的文字和圖片抓下來，
再交給各網站自己的程式解析成品名、價格、庫存。
"""
from __future__ import annotations

import logging
import re
from contextlib import contextmanager

from .common import UA, to_num

log = logging.getLogger("crawler")

JS_EXTRACT = r"""
(pattern) => {
  const re = new RegExp(pattern);
  const priceRe = /(\$|NT|S\$|HK\$|¥|￥|元|價|price)/i;
  const out = new Map();
  for (const a of document.querySelectorAll('a[href]')) {
    const href = a.href.split('#')[0];
    if (!re.test(href)) continue;
    let el = a, card = null;
    for (let i = 0; i < 8 && el; i++) {
      const hrefs = new Set([...el.querySelectorAll('a[href]')].map(x => x.href.split('#')[0]).filter(h => re.test(h)));
      if (hrefs.size > 1) break;               // 已經包到別的商品了，停
      const t = el.innerText || '';
      if (/\d/.test(t) && priceRe.test(t) && el.querySelector('img')) card = el;
      el = el.parentElement;
    }
    if (!card) continue;
    const text = (card.innerText || '').trim();
    if (!text || text.length > 1000) continue;
    // 卡片上可能有多張圖（禮物盒、愛心等小圖示），挑面積最大、不是 svg 圖示的那張
    let img = null, best = -1;
    for (const im of card.querySelectorAll('img')) {
      const s0 = im.currentSrc || im.src || im.getAttribute('data-src') || im.getAttribute('data-original') || '';
      if (/\.svg(\?|$)|icon|logo|badge|giftwrap|heart|flag/i.test(s0)) continue;
      const r = im.getBoundingClientRect();
      const area = Math.max(r.width * r.height, (im.naturalWidth || 0) * (im.naturalHeight || 0) / 4);
      if (area > best) { best = area; img = im; }
    }
    let src = '';
    if (img) src = img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || '';
    if (img && src.startsWith('data:')) src = img.getAttribute('data-src') || img.getAttribute('data-original') || '';
    const prev = out.get(href);
    if (!prev || text.length > prev.text.length)
      out.set(href, {url: href, text, img: src, title: a.getAttribute('title') || (img && img.alt) || ''});
  }
  return [...out.values()];
}
"""

MORE_TEXTS = ["LOAD MORE", "Load More", "Load more", "載入更多", "查看更多", "更多商品", "顯示更多"]


@contextmanager
def browser(headless: bool = True):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=headless, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, locale="zh-TW", viewport={"width": 1366, "height": 900})
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        try:
            yield ctx
        finally:
            b.close()


def open_page(ctx, url: str, wait_ms: int = 2500):
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(wait_ms)
    return page


def scroll_and_more(page, max_rounds: int = 10) -> None:
    """一直往下捲，有「載入更多」按鈕就按，直到沒有新東西或達到次數上限。"""
    last_h = 0
    for _ in range(max_rounds):
        page.mouse.wheel(0, 20000)
        page.wait_for_timeout(1200)
        clicked = False
        for t in MORE_TEXTS:
            btn = page.get_by_text(t, exact=False)
            try:
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=5000)
                    page.wait_for_timeout(2500)
                    clicked = True
                    break
            except Exception:  # noqa: BLE001
                continue
        h = page.evaluate("document.body.scrollHeight")
        if not clicked and h == last_h:
            break
        last_h = h


# 每個網站留幾張商品卡的原始文字，存到 docs/data/debug_samples.json，方便調整解析規則
SAMPLES: dict[str, list[dict]] = {}


def extract_cards(page, url_pattern: str) -> list[dict]:
    cards = page.evaluate(JS_EXTRACT, url_pattern)
    host = re.sub(r"^https?://(www\.)?", "", page.url).split("/")[0]
    bucket = SAMPLES.setdefault(host, [])
    for c in cards[: max(0, 5 - len(bucket))]:
        bucket.append(c)
    if not cards:
        SAMPLES.setdefault(host + " (no cards)", []).append(
            {"url": page.url, "title": page.title(), "text": page.inner_text("body")[:1500]})
    return cards


def fetch_html(ctx, url: str) -> str:
    """用瀏覽器拿網頁 HTML（給 requests 被擋時用）。"""
    page = open_page(ctx, url, wait_ms=1500)
    try:
        return page.content()
    finally:
        page.close()


# ---------- 解析卡片文字 ----------

PRICE_RE = re.compile(
    r"(?:NT\.?\s*\$?|S\$|HK\$|US\$|\$|¥|￥|RMB|(?:售價|特價|優惠價|會員價|建議售價|原價|價格|定價)\s*[:：]?\s*\$?)\s*([\d,]+(?:\.\d+)?)"
    r"|([\d,]+(?:\.\d+)?)\s*元")
STOCK_WORDS = [
    (re.compile(r"out of stock|sold out|notify me|售完|缺貨|已售罄|補貨中", re.I), "缺貨"),
    (re.compile(r"only few left|few left|僅剩|少量|即將售完", re.I), "少量"),
    (re.compile(r"selling fast|熱賣|熱銷", re.I), "熱賣中"),
    (re.compile(r"in stock|現貨|有貨", re.I), "有貨"),
]


def prices_in(text: str) -> list[float]:
    out = []
    for m in PRICE_RE.finditer(text):
        v = to_num(m.group(1) or m.group(2))
        if v and v >= 1:
            out.append(v)
    return out


def stock_in(text: str) -> str | None:
    for rx, label in STOCK_WORDS:
        if rx.search(text):
            return label
    return None


BADGE_RE = re.compile(
    r"^(gift ?wrap|exclusive|online exclusive|travel exclusive|changi first|changi exclusive|new|new arrival|limited|"
    r"best ?seller|hot|sale|bundle|deal|pre-?order|members? only|熱賣|新品|限定|獨家|預購)$"
    r"|buy \d|get \d+ ?%|\d+ ?% off|save |free gift|gwp|\bfor s?\$", re.I)


def text_lines(text: str) -> list[str]:
    """卡片文字切行，去掉價格行、庫存行、按鈕字。"""
    junk = re.compile(r"加入購物車|立即購買|add to (cart|bag)|buy now|收藏|wishlist|from$|^\W*$", re.I)
    lines = []
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or junk.search(ln) or BADGE_RE.search(ln):
            continue
        if PRICE_RE.fullmatch(ln.replace("From", "").replace("起", "").strip()):
            continue
        if stock_in(ln) and len(ln) < 25:
            continue
        if re.fullmatch(r"[-\d%\s.,]+(off)?", ln, re.I):
            continue
        lines.append(ln)
    return lines


def pick_name(title: str, lines: list[str]) -> str:
    """品名：連結的 title / 圖片 alt 夠長就用它，不然用卡片上最長的一行。"""
    title = (title or "").strip()
    longest = max(lines, key=len) if lines else ""
    return title if len(title) >= 6 and len(title) >= len(longest) // 2 else (longest or title)
