"""共用工具：商品資料格式、HTTP 連線、文字解析。"""
from __future__ import annotations

import re
import time
import random
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional

import requests

log = logging.getLogger("crawler")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class Product:
    site: str                      # 網站代號，例如 my9
    brand: str                     # 品牌（英文為主）
    name: str                      # 品名
    volume_ml: Optional[float] = None
    abv: Optional[float] = None    # 酒精濃度 %
    list_price: Optional[float] = None   # 訂價 / 原價 / 建議售價
    promo_price: Optional[float] = None  # 促銷價 / 會員價 / 特價
    currency: str = "TWD"
    stock: Optional[str] = None    # 庫存文字，例如 有貨 / Selling Fast / 缺貨
    image: Optional[str] = None    # 圖片網址
    url: Optional[str] = None      # 商品頁網址
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d["extra"]:
            d.pop("extra")
        return d


# ---------- HTTP ----------

def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    })
    return s


def get(s: requests.Session, url: str, *, retries: int = 3, **kw) -> requests.Response:
    """GET，失敗自動重試，每次請求之間隨機停一下，避免對網站造成負擔。"""
    last = None
    for i in range(retries):
        try:
            time.sleep(random.uniform(0.8, 1.8))
            r = s.get(url, timeout=30, **kw)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            log.warning("GET 失敗 (%s/%s) %s: %s", i + 1, retries, url, e)
            time.sleep(2 * (i + 1))
    raise last  # type: ignore[misc]


# ---------- 文字解析 ----------

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?"


def to_num(text) -> Optional[float]:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(_NUM, str(text))
    if not m:
        return None
    v = m.group(1).replace(",", "")
    if m.group(2):
        v += "." + m.group(2)
    try:
        return float(v)
    except ValueError:
        return None


def parse_volume(text: str) -> Optional[float]:
    """從文字找容量，回傳 ml。支援 700ml、1L、1.75 L、70cl、2 x 1000ml。"""
    if not text:
        return None
    t = text.replace("ＭＬ", "ml").replace("ｍｌ", "ml")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|毫升)\b", t, re.I) or re.search(r"(\d+(?:\.\d+)?)\s*(ml|毫升)", t, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*cl\b", t, re.I)
    if m:
        return float(m.group(1)) * 10
    m = re.search(r"(\d+(?:\.\d+)?)\s*(l|lt|ltr|公升)\b", t, re.I) or re.search(r"(\d+(?:\.\d+)?)\s*公升", t)
    if m:
        return float(m.group(1)) * 1000
    return None


def parse_abv(text: str, strict: bool = False) -> Optional[float]:
    """從文字找酒精濃度 %。strict=True 時只認「酒精濃度 / ABV / %vol」這類明確寫法（給長篇商品描述用）。"""
    if not text:
        return None
    m = re.search(r"(?:酒精濃度|酒精度|ABV|alc\.?)\s*[:：]?\s*(\d{1,2}(?:\.\d+)?)\s*%", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:vol|abv|alc)", text, re.I)
    if m:
        return float(m.group(1))
    if strict:
        return None
    # 寬鬆：任何 xx%，但排除折扣、精米步合等
    for m in re.finditer(r"(?<![\d.])(\d{1,2}(?:\.\d+)?)\s*%", text):
        before = text[max(0, m.start() - 8):m.start()]
        after = text[m.end():m.end() + 6]
        if re.search(r"精米|步合|折|減|save|get|buy|up to", before, re.I) or re.search(r"off|折|回饋|現折", after, re.I):
            continue
        v = float(m.group(1))
        if 3 <= v <= 75:
            return v
    return None


def clean(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def abs_url(base: str, u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http"):
        return u
    from urllib.parse import urljoin
    return urljoin(base, u)


def split_prices(prices: list[float]) -> tuple[Optional[float], Optional[float]]:
    """一張商品卡上找到多個價格時：最高當訂價，最低當促銷價。"""
    ps = sorted({p for p in prices if p and p > 0})
    if not ps:
        return None, None
    if len(ps) == 1:
        return ps[0], None
    return ps[-1], ps[0]
