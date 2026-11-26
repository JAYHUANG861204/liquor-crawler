"""存檔前的統一清理：不管哪個網站、哪次抓的資料，都過這一關。

會做的事：
- 品牌：是單位（ml）、數字、促銷字（+1、滿6件…）時重新從品名判斷；統一大小寫
- 品名：無效（img-product）的整筆剔除；促銷公告、非酒類商品（開瓶器、酒杯…）剔除
- 容量：品名結尾是 500 / 700 / 750 這類常見容量但沒寫 ml 時補上
- 濃度：超過 72% 或低於 0.5% 視為抓錯，清空
- 價格：0 元當作沒有價格；促銷價 ≥ 訂價時只留一個；促銷價不到訂價 25% 視為抓錯，清空促銷價
- 庫存：統一成 有貨 / 缺貨 / 少量 / 熱賣中 / 可訂購
"""
from __future__ import annotations

import re

from . import brands
from .common import parse_volume

UNIT_OR_NUM = re.compile(r"^(\d+\s*)?(ml|cl|l|lt|ltr|abv|vol|yo|yrs?|years?|x|毫升|公升)$|^[\d\W_]+$", re.I)
PROMO = re.compile(r"^[+\-–•]|折|滿\s*\d|贈|送|活動|優惠|特價|限時|指定產品|gift ?wrap|exclusive|buy \d|get \d|% off", re.I)
GENERIC_NAME = re.compile(r"^(img|image|pic|photo|picture|product|thumb|商品|圖片|商品圖)[-_ ]?[\w-]*$", re.I)
PROMO_NAME = re.compile(r"^[\-–•*]|滿\s*(HK\$|NT\$|\$)?\s*[\d,]+.{0,12}(送|贈|折)|即送|即贈|購買.{0,20}滿", re.I)
NOT_LIQUOR = re.compile(r"開瓶器|酒杯|杯組|醒酒器|冰桶|酒架|禮袋|提袋|購物袋|紅櫻桃|糖漿|小菜|零食|雪茄剪|"
                        r"opener|decanter|corkscrew|wine glass|tumbler|ice bucket", re.I)
# 飲料（不管有沒有容量都剔除）
DRINK_NOT_ALCOHOL = re.compile(r"礦泉水|氣泡水|蘇打水|汽水|通寧水|碳酸水|可爾必思|無酒精|non-?alcoholic|0% alcohol|"
                               r"mineral water|soda water|tonic water|sparkling water|ginger ale|\bwater$", re.I)
COMMON_ML = (50, 100, 180, 187, 200, 300, 330, 350, 375, 500, 700, 720, 750, 1000, 1500, 1750, 1800, 3000)
NAME_ONLY_BRAND = {"609", "9city", "cdf"}   # 這些網站沒有品牌欄位，品牌一律從品名判斷
STOCK_MAP = [
    (re.compile(r"缺貨|售完|售罄|sold out|out of stock", re.I), "缺貨"),
    (re.compile(r"少量|few left|僅剩", re.I), "少量"),
    (re.compile(r"熱賣|selling fast", re.I), "熱賣中"),
    (re.compile(r"可訂購|預購|pre-?order", re.I), "可訂購"),
    (re.compile(r"有貨|現貨|in stock", re.I), "有貨"),
]


def bad_brand(b: str | None) -> bool:
    b = (b or "").strip()
    return (not b) or bool(UNIT_OR_NUM.match(b) and b not in ("1792",)) or (
        bool(PROMO.search(b)) and not re.search(r"[A-Za-z]{4,}", b)) or len(b) > 30


PRICE_NAME = re.compile(r"^(建議價|建議售價|會員價|售價|特價|優惠價|價格|定價|原價|NT\$|S\$|HK\$|\$)\s*[:：]?\s*(NT\$|\$)?\s*[\d,]", re.I)


def name_from_image(url: str | None) -> str:
    """圖片檔名常就是品名，例如 …/藏元梅酒500.jpg → 藏元梅酒500。"""
    from urllib.parse import unquote
    if not url:
        return ""
    base = unquote(url.split("?")[0].rstrip("/").split("/")[-1])
    base = re.sub(r"\.(jpe?g|png|webp|gif)$", "", base, flags=re.I)
    base = re.sub(r"[（(]?主推圖[)）]?|[-_ ]?\d{0,2}$(?<=[-_ ]\d)|^\d+[-_]", "", base).strip(" -_")
    # 檔名要像品名：有中文或英文字，而且不是一串亂碼編號
    if len(base) < 3 or not re.search(r"[\u3400-\u9fffA-Za-z]{2,}", base) or re.fullmatch(r"[\w-]{16,}", base):
        return ""
    return base


def clean_product(p: dict) -> dict | None:
    """回傳清理後的商品；不該出現在比價表的回傳 None。"""
    p = dict(p)
    name = re.sub(r"\s+", " ", (p.get("name") or "")).strip()
    if not name or GENERIC_NAME.match(name) or PRICE_NAME.match(name):
        name = name_from_image(p.get("image"))      # 卡片上沒品名時，改用圖片檔名
    # 沒有商品網址又沒有容量的，通常是活動橫幅（例如「9週年精選香檳」），不是商品
    if not p.get("url") and not p.get("volume_ml") and not re.search(r"\d+\s*(ml|毫升|cl|l)\b", name, re.I):
        return None
    if not name or GENERIC_NAME.match(name) or PROMO_NAME.search(name):
        return None
    if NOT_LIQUOR.search(name) and not p.get("volume_ml"):
        return None
    if DRINK_NOT_ALCOHOL.search(name) or (p.get("extra") or {}).get("type") == "無酒精":
        return None
    p["name"] = name

    # 品牌
    if p["site"] in NAME_ONLY_BRAND or bad_brand(p.get("brand")):
        p["brand"] = brands.normalize(None, name)
    else:
        p["brand"] = brands.normalize(p.get("brand"), name)
    if bad_brand(p["brand"]):
        p["brand"] = brands.normalize(None, re.sub(r"^[^\w㐀-鿿]+", "", name))

    # 容量
    v = p.get("volume_ml")
    if v is None:
        v = p["volume_ml"] = parse_volume(name)
    if v is None:
        m = re.search(r"(?<![\d.])(\d{2,4})\s*$", name)
        if m and int(m.group(1)) in COMMON_ML:
            p["volume_ml"] = float(m.group(1))
    elif not (5 <= v <= 20000):
        p["volume_ml"] = None

    # 濃度
    a = p.get("abv")
    if a is not None and not (0.5 <= a <= 72):
        p["abv"] = None

    # 價格
    lp, pp = p.get("list_price") or None, p.get("promo_price") or None
    if lp and pp:
        if pp >= lp:
            lp, pp = max(lp, pp), None if pp == lp else min(lp, pp)
            if pp is not None:          # 兩個價格順序反了：大的當訂價
                lp, pp = max(lp, pp), min(lp, pp)
        elif pp < lp * 0.25:
            pp = None                   # 打 2.5 折以下幾乎不可能，是抓到別的數字
    if lp is None and pp is not None:
        lp, pp = pp, None
    p["list_price"], p["promo_price"] = lp, pp

    # 庫存
    s = p.get("stock")
    if s:
        p["stock"] = next((lab for rx, lab in STOCK_MAP if rx.search(s)), None)
    return p


def clean_all(products: list[dict]) -> tuple[list[dict], int]:
    out, dropped, seen = [], 0, set()
    for p in products:
        c = clean_product(p)
        key = (c["site"], c.get("url") or c["name"]) if c else None
        if c is None or key in seen:
            dropped += 1
            continue
        seen.add(key)
        out.append(c)
    return out, dropped
