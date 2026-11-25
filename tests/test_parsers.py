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

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
