"""網站清單。新增網站：在 sites/ 下加一個檔案（要有 SITE 和 crawl()），再加進 SITES。"""
from . import s609, changi, hkairport, ninecity, my9, cdf

# 代號: (模組, 顯示名稱, 首頁, 幣別, 說明)
SITES = {
    "609":    (s609,      "酒條通 609",       "https://www.609.com.tw/",              "TWD", "瀏覽器抓分類頁"),
    "changi": (changi,    "iShopChangi",      "https://www.ishopchangi.com/",         "SGD", "瀏覽器抓分類頁，按 LOAD MORE"),
    "hk":     (hkairport, "DUTY ZERO 香港",   "https://www.dutyzero.com.hk/",         "HKD", "瀏覽器抓分類頁（香港機場免稅店網店）"),
    "9city":  (ninecity,  "洋酒城 9city",     "https://www.9city.com.tw/",            "TWD", "在自己電腦執行（網站擋 GitHub）"),
    "my9":    (my9,       "買酒網 MY9",       "https://www.my9.com.tw/",              "TWD", "Shopify JSON"),
    "cdf":    (cdf,       "中免日上 CDF",     "https://www.cdfsunrise.com/",          "CNY", "在自己電腦執行（實驗中，App 型網站）"),
}

# 這些網站會擋 GitHub 的主機，只在自己電腦上跑（run_windows.bat）；
# GitHub 每日排程會跳過它們，保留上次在自己電腦抓到的資料。
LOCAL_ONLY = {"9city", "cdf"}
# 在自己電腦跑 run_windows.bat 時預設會跑的網站（GitHub 被擋的話也能在這裡補）
LOCAL_DEFAULT = {"hk", "9city", "cdf"}
