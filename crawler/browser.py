"""用真實瀏覽器（Playwright + Chromium）開網頁，給 JavaScript 才會載入商品的網站用。

做法是通用的：找出網頁上所有「網址符合商品頁格式」的連結，往外找到包住它的
商品卡（有圖片、有價格的那一塊），把卡片上的文字和圖片抓下來，
再交給各網站自己的程式解析成品名、價格、庫存。
"""
from __future__ import annotations

import logging
import os
import re
import time
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
      const s0 = im.getAttribute('data-src') || im.getAttribute('data-original') || im.currentSrc || (im.getAttribute('src') ? im.src : '') || '';
      if (/\.svg(\?|$)|icon|logo|badge|giftwrap|heart|flag/i.test(s0)) continue;
      const r = im.getBoundingClientRect();
      const area = Math.max(r.width * r.height, (im.naturalWidth || 0) * (im.naturalHeight || 0) / 4);
      if (area > best) { best = area; img = im; }
    }
    let src = '';
    if (img) src = img.getAttribute('data-src') || img.getAttribute('data-original') || img.currentSrc || (img.getAttribute('src') ? img.src : '') || '';
    if (img && src.startsWith('data:')) src = img.getAttribute('data-src') || img.getAttribute('data-original') || '';
    const prev = out.get(href);
    if (!prev || text.length > prev.text.length)
      out.set(href, {url: href, text, img: src, title: a.getAttribute('title') || (img && img.alt) || ''});
  }
  return [...out.values()];
}
"""

MORE_TEXTS = ["LOAD MORE", "Load More", "Load more", "載入更多", "查看更多", "更多商品", "顯示更多"]


IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(ROOT, ".browser-profile")


def headless_default() -> bool:
    """GitHub 上沒有螢幕，一定用無頭模式；自己電腦上預設開出看得到的視窗（遇到驗證可以手動處理）。"""
    if IN_CI:
        return True
    return os.environ.get("HEADLESS", "0") == "1"


@contextmanager
def browser(headless: bool | None = None):
    from playwright.sync_api import sync_playwright
    if headless is None:
        headless = headless_default()
    args = ["--disable-blink-features=AutomationControlled"]
    with sync_playwright() as p:
        if IN_CI:
            b = p.chromium.launch(headless=True, args=args)
            ctx = b.new_context(user_agent=UA, locale="zh-TW", viewport={"width": 1366, "height": 900})
            closer = b.close
        else:
            # 自己電腦：優先用已安裝的 Google Chrome，並保留登入/驗證過的 cookie（存在 .browser-profile）
            kw = dict(user_data_dir=PROFILE_DIR, headless=headless, args=args, locale="zh-TW",
                      viewport={"width": 1366, "height": 900})
            try:
                ctx = p.chromium.launch_persistent_context(channel="chrome", **kw)
            except Exception:  # noqa: BLE001  沒裝 Chrome 就用內建的 Chromium
                ctx = p.chromium.launch_persistent_context(user_agent=UA, **kw)
            closer = ctx.close
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        try:
            yield ctx
        finally:
            closer()


CAPTCHA_RE = re.compile(r"验证您是真人|驗證您是真人|滑动验证|滑動驗證|拖动到最右边|拖動到最右邊|verify you are human|"
                        r"are you a robot|captcha|人機驗證|安全驗證|security check", re.I)


def is_captcha(page) -> bool:
    try:
        return bool(CAPTCHA_RE.search(page.title() + " " + page.inner_text("body")[:2000]))
    except Exception:  # noqa: BLE001
        return False


def wait_for_human(page, timeout_s: int = 300) -> bool:
    """遇到真人驗證：自己電腦上就停下來等使用者在視窗裡完成；GitHub 上直接放棄。"""
    if not is_captcha(page):
        return True
    if IN_CI or headless_default():
        log.warning("遇到真人驗證頁（%s），無頭模式無法處理", page.url)
        return False
    print("\n" + "=" * 60)
    print("  網站要求真人驗證！請到跳出來的瀏覽器視窗，")
    print("  完成驗證（例如把滑塊拖到最右邊），程式會自動繼續。")
    print(f"  最多等 {timeout_s // 60} 分鐘。")
    print("=" * 60 + "\n")
    try:
        page.bring_to_front()
    except Exception:  # noqa: BLE001
        pass
    end = time.time() + timeout_s
    while time.time() < end:
        page.wait_for_timeout(2000)
        if not is_captcha(page):
            log.info("驗證完成，繼續抓取")
            page.wait_for_timeout(2500)
            return True
    log.warning("等待驗證逾時")
    return False


def open_page(ctx, url: str, wait_ms: int = 2500):
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(wait_ms)
    if is_captcha(page) and wait_for_human(page):
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
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
    r"(?:NT\.?\s*\$?|S\$|HK\$|US\$|\$|¥|￥|RMB|(?:售價|特價|優惠價|會員價|建議售價|原價|價格|定價)\s*[:：]?\s*\$?)\s*[:：]?\s*([\d,]+(?:\.\d+)?)"
    r"|([\d,]+(?:\.\d+)?)\s*元")
STOCK_WORDS = [
    (re.compile(r"out of stock|sold out|notify me|售完|缺貨|售罄|補貨中", re.I), "缺貨"),
    (re.compile(r"only few left|few left|僅剩|少量|即將售完", re.I), "少量"),
    (re.compile(r"selling fast|熱賣|熱銷", re.I), "熱賣中"),
    (re.compile(r"in stock|現貨|有貨", re.I), "有貨"),
]


SAVE_RE = re.compile(r"(save|off|less|discount|省|減|折抵|現折|回饋|贈)\W{0,3}$", re.I)


def prices_in(text: str) -> list[float]:
    """找卡片上的價格；「Save S$18」「現折 100」這類省下的金額不算。"""
    out = []
    for m in PRICE_RE.finditer(text):
        if SAVE_RE.search(text[max(0, m.start() - 12):m.start()]):
            continue
        if re.match(r"\s*(off|折)", text[m.end():m.end() + 5], re.I):
            continue
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
    r"best ?seller|hot|sale|bundle|deal|pre-?order|members? only|熱賣|新品|限定|獨家|預購|"
    r"活動價|滿贈活動|贈品活動|買一送一|機場預購|瀏覽更多|[\d.]+\s*折|售罄|sold out)$"
    r"|^滿\s*\d+\s*(件|元|港幣|HK\$)|^\d+件\d*折|^\+\s*\d+$|^[-–]\s|指定產品|額外\s*\d*\s*折"
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
    # 圖片替代文字常是 img-product、image、商品圖 這種沒意義的字，不能當品名
    if re.fullmatch(r"(img|image|pic|photo|picture|product|thumb|商品圖|圖片|商品)[-_ ]?[\w-]*", title, re.I):
        title = ""
    longest = max(lines, key=len) if lines else ""
    return title if len(title) >= 6 and len(title) >= len(longest) // 2 else (longest or title)


# ---------- 沒有商品連結的網站：靠「價格」找商品卡 ----------

JS_EXTRACT_BY_PRICE = r"""
(args) => {
  const [priceSrc, base] = args;
  const priceRe = new RegExp(priceSrc, 'g');
  const count = el => ((el.innerText || '').match(priceRe) || []).length;
  const imgOf = card => {
    let best = '', area = -1;
    for (const im of card.querySelectorAll('img')) {
      const s = im.getAttribute('data-src') || im.getAttribute('data-original') || im.getAttribute('lazy-src') ||
                im.currentSrc || (im.getAttribute('src') ? im.src : '') || (im.getAttribute('srcset') || '').split(' ')[0] || '';
      if (!s || s.startsWith('data:') || /\.svg(\?|$)|icon|logo|badge|tag|label|flag/i.test(s)) continue;
      const r = im.getBoundingClientRect(), a = r.width * r.height || 1;
      if (a > area) { area = a; best = s; }
    }
    if (!best) for (const el of [card, ...card.querySelectorAll('*')]) {
      const bg = getComputedStyle(el).backgroundImage;
      const m = bg && bg.match(/url\(["']?(.*?)["']?\)/);
      if (m && !/icon|logo/i.test(m[1])) { best = m[1]; break; }
    }
    return best ? new URL(best, location.href).href : '';
  };
  const urlOf = card => {
    const a = card.closest('a[href]') || card.querySelector('a[href]');
    if (a && !/javascript:|#$/.test(a.getAttribute('href'))) return a.href.split('#')[0];
    const html = card.outerHTML;
    const m = html.match(/item\/(p?\d{5,})/) || html.match(/(?:goods|item|sku|product|spu)[_-]?(?:id|no|code)["'\s:=]+["']?(p?\d{5,})/i)
           || html.match(/\bp(\d{7,})\b/);
    if (m) return base + 'item/' + (m[1].startsWith('p') ? m[1] : 'p' + m[1]);
    return '';
  };
  const out = [], seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    const n = count(el);
    if (n < 1 || n > 2 || !el.querySelector('img')) continue;
    const p = el.parentElement;
    if (p && count(p) <= n && p.querySelector('img')) continue;   // 父層還是同一張卡 → 繼續往上
    const text = (el.innerText || '').trim();
    if (!text || text.length > 600 || seen.has(text)) continue;
    seen.add(text);
    out.push({url: urlOf(el), text, img: imgOf(el), title: ''});
  }
  return out;
}
"""


def extract_cards_by_price(page, price_regex: str, base: str) -> list[dict]:
    cards = page.evaluate(JS_EXTRACT_BY_PRICE, [price_regex, base])
    host = re.sub(r"^https?://(www\.)?", "", page.url).split("/")[0] + " (by price)"
    bucket = SAMPLES.setdefault(host, [])
    for c in cards[: max(0, 5 - len(bucket))]:
        bucket.append(c)
    return cards


def slow_scroll(page, step: int = 700, pause_ms: int = 250, max_steps: int = 400) -> None:
    """慢慢往下捲，讓「捲到才載入」的圖片和商品都出來。"""
    last_h, same = 0, 0
    for _ in range(max_steps):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(pause_ms)
        y, h = page.evaluate("[window.scrollY + window.innerHeight, document.body.scrollHeight]")
        if y >= h - 5:
            page.wait_for_timeout(1500)       # 到底了，等一下看會不會再載入更多
            h2 = page.evaluate("document.body.scrollHeight")
            if h2 == h:
                same += 1
                if same >= 2:
                    break
            else:
                same = 0
