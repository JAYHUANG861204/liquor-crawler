"""資料品質檢查：找出不合理的品牌、品名、容量、濃度、價格、庫存、圖片、網址。

用法：python -m crawler.audit            （印出各站問題數量與範例）
      python -m crawler.audit --strict   （有嚴重問題時回傳錯誤碼，給 GitHub 排程用）
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS = os.path.join(ROOT, "docs", "data", "products.json")

CJK = re.compile(r"[㐀-鿿]")
UNIT_WORD = re.compile(r"^(\d+\s*)?(ml|cl|l|lt|ltr|abv|vol|yo|yrs?|years?|x|毫升|公升)$", re.I)
PROMO_WORD = re.compile(r"折|滿|贈|送|活動|優惠|特價|限時|sale|off|gift ?wrap|exclusive|new|buy \d|get \d|\+\d|price|hk\$|s\$|nt\$|\$", re.I)
GENERIC_NAME = re.compile(r"^(img|image|pic|photo|product|商品|圖片)[-_ ]?\w*$", re.I)
# 每瓶合理的價格範圍（換成台幣）；超出就列出來人工看
TWD = {"TWD": 1, "SGD": 24, "HKD": 4.1, "CNY": 4.4}


def problems(p: dict) -> list[tuple[str, str]]:
    """回傳 [(嚴重度, 問題代碼)]；嚴重度：error = 一定錯，warn = 可疑。"""
    out = []
    b, n = (p.get("brand") or "").strip(), (p.get("name") or "").strip()
    # 品牌
    if not b:
        out.append(("error", "品牌空白"))
    else:
        if UNIT_WORD.match(b) or (re.fullmatch(r"[\d\W_]+", b) and b != "1792"):
            out.append(("error", "品牌是單位或數字"))
        if PROMO_WORD.search(b) and len(b) < 25 and not re.search(r"[A-Za-z]{4,}", b):
            out.append(("error", "品牌是促銷文字"))
        if len(b) == 1 or len(b) > 30:
            out.append(("warn", "品牌長度異常"))
        if re.search(r"\d{2,}", b) and b not in ("1792", "Monkey 47", "Vat 69", "Código 1530"):
            out.append(("warn", "品牌含數字"))
        if CJK.search(b):
            out.append(("warn", "品牌未轉成英文"))
        if b.isupper() and len(b) > 3:
            out.append(("warn", "品牌全大寫"))
    # 品名
    if not n or GENERIC_NAME.match(n) or re.match(r"^(建議價|建議售價|會員價|售價|特價|優惠價|價格|NT\$|S\$|HK\$)\s*[:：]?\s*(NT\$|\$)?\s*[\d,]", n):
        out.append(("error", "品名無效"))
    elif re.search(r"(NT|S|HK)\$\s*[\d,]+\s*/\s*瓶", n):
        out.append(("error", "品名含價格"))
    elif len(n) < 4:
        out.append(("warn", "品名太短"))
    elif b and n.strip().lower() == b.lower():
        out.append(("warn", "品名只有品牌"))
    # 容量
    v = p.get("volume_ml")
    if v is None:
        out.append(("warn", "沒有容量"))
    elif not (5 <= v <= 20000):
        out.append(("error", "容量不合理"))
    # 濃度
    a = p.get("abv")
    if a is not None and not (0.5 <= a <= 72):
        out.append(("error", "濃度不合理"))
    # 價格
    lp, pp, cur = p.get("list_price"), p.get("promo_price"), p.get("currency")
    if cur not in TWD:
        out.append(("error", "幣別異常"))
    if lp is None and pp is None:
        out.append(("warn", "沒有價格"))
    for x in (lp, pp):
        if x is not None and x <= 0:
            out.append(("error", "價格 ≤ 0"))
    if lp and pp and pp >= lp:
        out.append(("error", "促銷價 ≥ 訂價"))
    if lp and pp and pp < lp * 0.25:
        out.append(("error", "促銷價不到訂價 25%"))
    price = (pp or lp or 0) * TWD.get(cur, 1)
    if price and price < 30:
        out.append(("warn", "價格過低（< NT$30）"))
    # 圖片 / 網址
    img = p.get("image") or ""
    if not img:
        out.append(("warn", "沒有圖片"))
    elif re.search(r"\.svg(\?|$)|icon|logo|giftwrap|placeholder|no[-_]?image", img, re.I):
        out.append(("error", "圖片是圖示"))
    elif not img.startswith("http"):
        out.append(("error", "圖片網址錯誤"))
    if not p.get("url"):
        out.append(("warn", "沒有商品網址"))
        if not v:
            out.append(("error", "沒網址也沒容量（可能是橫幅）"))
    # 庫存
    s = p.get("stock")
    if s and s not in ("有貨", "缺貨", "少量", "熱賣中", "可訂購"):
        out.append(("warn", "庫存文字未統一"))
    return out


def audit(products: list[dict], samples: int = 3) -> dict:
    by_site = collections.defaultdict(list)
    for p in products:
        by_site[p["site"]].append(p)
    report = {}
    for site, ps in by_site.items():
        cnt = collections.Counter()
        ex = collections.defaultdict(list)
        for p in ps:
            for sev, code in problems(p):
                cnt[(sev, code)] += 1
                if len(ex[code]) < samples:
                    ex[code].append(f'{p.get("brand")!s:.25} | {p.get("name")!s:.55} | {p.get("volume_ml")} | '
                                    f'{p.get("abv")} | {p.get("list_price")}/{p.get("promo_price")}')
        # 同站重複網址
        urls = collections.Counter(p.get("url") for p in ps if p.get("url"))
        dup = sum(c - 1 for c in urls.values() if c > 1)
        if dup:
            cnt[("error", "同站重複網址")] = dup
        report[site] = {"total": len(ps), "issues": cnt, "examples": ex}
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=PRODUCTS)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--samples", type=int, default=3)
    a = ap.parse_args(argv)
    products = json.load(open(a.file, encoding="utf-8"))
    rep = audit(products, a.samples)
    errors = 0
    for site, r in rep.items():
        print(f"\n=== {site}（{r['total']} 筆）===")
        for (sev, code), c in sorted(r["issues"].items(), key=lambda x: (x[0][0] != "error", -x[1])):
            pct = c / r["total"] * 100
            print(f"  [{'錯誤' if sev == 'error' else '可疑'}] {code}: {c} 筆（{pct:.0f}%）")
            for e in r["examples"].get(code, []):
                print("        ", e)
            if sev == "error":
                errors += c
    print(f"\n嚴重問題合計：{errors} 筆")
    return 1 if (a.strict and errors) else 0


if __name__ == "__main__":
    sys.exit(main())
