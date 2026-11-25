"""網站清單。新增網站：在 sites/ 下加一個檔案（要有 SITE 和 crawl()），再加進 SITES。"""
from . import s609, changi, hkairport, ninecity, my9, cdf

# 代號: (模組, 顯示名稱, 首頁, 幣別, 說明)
SITES = {
    "609":    (s609,      "酒條通 609",       "https://www.609.com.tw/",              "TWD", "瀏覽器抓分類頁"),
    "changi": (changi,    "iShopChangi",      "https://www.ishopchangi.com/",         "SGD", "瀏覽器抓分類頁，按 LOAD MORE"),
    "hk":     (hkairport, "HK Airport Shop",  "https://hkairportshop.com/",           "HKD", "實驗中：網站有防火牆"),
    "9city":  (ninecity,  "洋酒城 9city",     "https://www.9city.com.tw/",            "TWD", "逐一抓商品頁"),
    "my9":    (my9,       "買酒網 MY9",       "https://www.my9.com.tw/",              "TWD", "Shopify JSON"),
    "cdf":    (cdf,       "中免日上 CDF",     "https://www.cdfsunrise.com/",          "CNY", "實驗中：App 型網站"),
}
