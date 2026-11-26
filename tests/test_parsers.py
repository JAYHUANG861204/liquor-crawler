"""離線測試：用假資料檢查各解析函式。執行：python -m pytest tests 或 python tests/test_parsers.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawler.common import parse_volume, parse_abv, to_num, split_prices
from crawler import brands
from crawler.sites import my9, ninecity, changi, s609
from crawler.browser import prices_in, stock_in, text_lines

def test_common():
    assert parse_volume("Blue Label 1000ML 40%") == 1000
    assert parse_volume("Gin 1L") == 1000
    assert parse_volume("70cl") == 700
    assert parse_volume("布坎南12年1000ml") == 1000
    assert parse_abv("Blue Label 1000ML 40%") == 40
    assert parse_abv("酒精濃度：56.3%") == 56.3
    assert parse_abv("15% off") is None or parse_abv("15% off") == 15
    assert to_num("$ 1,480") == 1480
    assert split_prices([276.6, 249.0]) == (276.6, 249.0)

def test_brands():
    assert brands.normalize("Kongsgaard 康士嘉酒莊") == "Kongsgaard"
    assert brands.normalize(None, "格蘭傑 Glenmorangie 13年 雪莉桶") == "Glenmorangie"
    assert brands.normalize(None, "布坎南DELUXE-12年調和威士忌1000ml") == "Buchanan's"
    assert brands.normalize("NIKKA 一甲") == "Nikka"
    # 之前出過錯的案例，避免再犯
    cases = {
        (None, "諾蒂絲琴酒700ml"): "諾蒂絲", (None, "南非圖卡納白稍南白葡萄酒750ml"): "圖卡納",
        (None, "布納哈本1998年蘋果白蘭地桶"): "Bunnahabhain", (None, "古董玩家Antiquary12年調和威士忌700ml"): "Antiquary",
        (None, "吉拉15年雪莉RESERVE單一純麥威士忌700ml"): "Jura", (None, "Nikka Frontier90週年紀念調和威士忌500"): "Nikka",
        (None, "AS WE GET IT高地雪莉桶單一純麥威士忌700ml"): "As We Get It", (None, "梅酒王720ml"): "梅酒王",
        (None, "國盛知多梅酒"): "Kunizakari", (None, "大山夢工房柑橘梅酒720ml"): "大山夢工房",
        ("23RD STREET DISTILLERY", ""): "23rd Street Distillery", ("WARWICK", ""): "Warwick", ("JD&S", ""): "JD&S",
        ("The Glen Grant", ""): "Glen Grant", ("Ch. Lafite Rothschild", ""): "Château Lafite Rothschild",
        ("中野BC", "中野BC 綠茶梅酒"): "Nakano BC", ("1792", ""): "1792", (None, "野格 迷你酒 / Jägermeister Mini Size"): "Jägermeister",
    }
    for (b, n), want in cases.items():
        assert brands.normalize(b, n) == want, (b, n, brands.normalize(b, n), want)

def test_my9():
    p = my9.parse_product({"title": "康士嘉酒莊 國王的農場 || Kongsgaard King's Farm 2024", "vendor": "Kongsgaard 康士嘉酒莊",
        "handle": "abc", "body_html": "<p>酒精濃度 14.5%</p>", "images": [{"src": "https://x/i.png"}],
        "variants": [{"price": "3800.00", "compare_at_price": "4300.00", "available": True, "option1": "750ml"}]})
    assert (p.brand, p.volume_ml, p.abv, p.list_price, p.promo_price, p.stock) == ("Kongsgaard", 750, 14.5, 4300, 3800, "有貨")

NINE = """<html><head><meta property="og:title" content="格蘭傑 Glenmorangie 13年 雪莉桶 台灣限定版｜洋酒城">
<meta property="og:image" content="//fs1.shop123.com.tw/a.jpg"><meta property="og:url" content="https://www.9city.com.tw/product/P260720011860"></head>
<body><h1>格蘭傑 Glenmorangie 13年 雪莉桶 台灣限定版</h1><h6>Glenmorangie 13YO Sherry Cask</h6>
<table><tr><th>產地</th><th>類別</th><th>酒精濃度</th><th>包裝</th></tr><tr><td>蘇格蘭</td><td>單一麥芽</td><td>40%</td><td>盒裝</td></tr></table>
<div>建議售價</div><div>$ 1,480</div><div>會員特價</div><div>$ 1,268 ( 700ml )</div><div>容量規格</div><div>700ml</div>
<button>加入購物車</button><a href="/product/P1?promotion_product_sn=363">x</a><a href="category.php?type=1&arem=67&arem1=660">c</a></body></html>"""

def test_9city():
    p = ninecity.parse_product(NINE, "https://www.9city.com.tw/product/P260720011860")
    assert (p.brand, p.volume_ml, p.abv, p.list_price, p.promo_price, p.stock) == ("Glenmorangie", 700, 40, 1480, 1268, "可訂購")
    assert p.image == "https://fs1.shop123.com.tw/a.jpg"
    prods, cats = ninecity._links(NINE, "https://www.9city.com.tw/")
    assert prods == {"https://www.9city.com.tw/product/P1"} and len(cats) == 1

def test_changi_card():
    c = {"url": "https://www.ishopchangi.com/en/product/johnnie-walker-blue-label-1000ml-40--mp00089136",
         "text": "Johnnie Walker\nBlue Label 1000ML 40%\nS$276.60\nS$249.00\nSelling Fast\nADD TO CART", "img": "https://x/j.jpg"}
    p = changi.parse_card(c)
    assert (p.brand, p.name, p.volume_ml, p.abv, p.list_price, p.promo_price, p.stock) == ("Johnnie Walker", "Blue Label 1000ML 40%", 1000, 40, 276.6, 249.0, "熱賣中")

def test_609_card():
    p = s609.parse_card({"url": "https://www.609.com.tw/Product/111999", "text": "布坎南DELUXE-12年調和威士忌1000ml\nNT$ 899", "img": "", "title": ""})
    assert (p.brand, p.volume_ml, p.list_price) == ("Buchanan's", 1000, 899)

def test_clean():
    from crawler.clean import clean_product as C
    base = dict(site="609", brand="ml", name="諾蒂絲琴酒700ml", volume_ml=700, abv=None, list_price=999,
                promo_price=None, currency="TWD", stock=None, image="x", url="u")
    assert C(base)["brand"] == "諾蒂絲"
    assert C(dict(base, name="img-product")) is None
    assert C(dict(base, name="Nikka Frontier90週年紀念調和威士忌500", volume_ml=None))["volume_ml"] == 500
    assert C(dict(base, site="changi", brand="+1", name="OYSTER ADRIATIC GIN 700ML"))["brand"] == "Oyster"
    r = C(dict(base, site="changi", brand="The Glen Grant", name="GLEN GRANT 18YO", list_price=188, promo_price=18))
    assert (r["brand"], r["list_price"], r["promo_price"]) == ("Glen Grant", 188, None)
    assert C(dict(base, site="hk", name="- 購買葡萄酒、香檳滿HK$2,999，即送香檳杯 1套。")) is None
    assert C(dict(base, site="my9", brand="Y", name="山崎", list_price=0.0))["list_price"] is None
    assert C(dict(base, site="my9", brand="G", name="Graham's Port", abv=77))["abv"] is None
    assert C(dict(base, site="my9", brand="MY9", name="買酒網品牌開瓶器", volume_ml=None)) is None
    assert C(dict(base, site="hk", brand="WARWICK", name="Warwick 白葡萄酒"))["brand"] == "Warwick"


if __name__ == "__main__":  # noqa
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
