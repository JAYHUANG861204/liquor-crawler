# 酒類比價爬蟲 liquor-crawler

每天自動抓 6 個酒類電商的商品資料，整理成一張比價表：

| 商品圖片 | 品牌 | 品名 | 容量 | 酒精濃度 | 訂價 | 促銷價 | 庫存 |
|---|---|---|---|---|---|---|---|

- **網頁版**：可依「網站」「品牌（英文為主）」篩選、搜尋、排序，手機也能看
- **Excel 版**：`docs/products.xlsx`，含商品縮圖，可用篩選功能

## 網站清單

| 代號 | 網站 | 抓法 | 狀態 |
|---|---|---|---|
| `my9` | [買酒網 MY9](https://www.my9.com.tw/) | Shopify 公開 JSON | 穩定 |
| `9city` | [洋酒城 9city](https://www.9city.com.tw/) | 逐一抓商品頁 | 穩定 |
| `changi` | [iShopChangi](https://www.ishopchangi.com/en/category/wine-and-spirits) | 瀏覽器開分類頁、按 LOAD MORE | 需要觀察 |
| `609` | [酒條通 609](https://www.609.com.tw/) | 瀏覽器開分類頁 | 需要觀察 |
| `hk` | [HK Airport Shop](https://hkairportshop.com/eshop_en/wines-spirits-liquors.html) | 瀏覽器（網站有防火牆） | 實驗中 |
| `cdf` | [中免日上](https://www.cdfsunrise.com/) | 瀏覽器（App 型網站） | 實驗中 |

某個網站失敗時，會保留它上一次成功的資料，網頁上的網站卡片會顯示「抓取失敗」和最後更新時間。

---

## 第一次設定（只要做一次）

### 1. 開啟網頁（GitHub Pages）

1. 進入這個 repo → 上方 **Settings**
2. 左邊選 **Pages**
3. **Source** 選 `Deploy from a branch`
4. **Branch** 選 `main`，資料夾選 `/docs`，按 **Save**
5. 等 1～2 分鐘，網址會是：**https://jayhuang861204.github.io/liquor-crawler/**

### 2. 第一次手動執行爬蟲

1. 上方 **Actions** 分頁 → 如果看到提示，按 **I understand my workflows, go ahead and enable them**
2. 左邊選 **每日爬蟲** → 右邊 **Run workflow** → 綠色 **Run workflow**
3. 大約 10～30 分鐘跑完，網頁和 Excel 就會更新

之後每天 **台灣時間早上 8 點**會自動執行。

---

## 常用操作

**只測某幾個網站、少量資料**：Actions → 每日爬蟲 → Run workflow，
`sites` 填 `my9,9city`，`limit` 填 `20`。

**改執行時間**：編輯 `.github/workflows/crawl.yml` 的 `cron`。
GitHub 用 UTC 時間，台灣時間要減 8 小時，例如晚上 9 點 → `0 13 * * *`。

**看執行紀錄 / 錯誤**：Actions → 點某次執行 → 點 `crawl` → 展開「執行爬蟲」。

**品牌名稱沒有變英文**：在 `crawler/brands.py` 的 `ZH_EN` 加一行對照，例如 `"格蘭傑": "Glenmorangie",`。

---

## 在自己電腦執行（Windows）

適合 GitHub 上被擋的網站（HK 機場、中免），或想立刻拿到 Excel。

1. 安裝 [Python 3.12](https://www.python.org/downloads/)，安裝時勾選 **Add python.exe to PATH**
2. 在這個 repo 頁面按綠色 **Code → Download ZIP**，解壓縮
3. 按兩下 `run_windows.bat`（第一次會自動安裝套件，要等幾分鐘）
4. 跑完會自動打開 `docs\products.xlsx`

只跑某些網站：在資料夾開命令列，輸入

```
run_windows.bat --sites hk,cdf
```

其他參數：`--limit 30`（每站最多 30 筆）、`--no-images`（Excel 不放縮圖，比較快）。

---

## 程式結構

```
crawler/
  run.py          主程式：逐站執行、輸出 JSON 與 Excel、失敗時沿用舊資料
  common.py       共用：商品格式、HTTP 重試、容量/濃度/價格解析
  browser.py      Playwright 瀏覽器：捲動、按「載入更多」、通用商品卡擷取
  brands.py       中文品牌 → 英文品牌對照
  excel.py        Excel 輸出（含縮圖）
  sites/          每個網站一個檔案，新增網站就加一個檔案再登記到 sites/__init__.py
docs/
  index.html      比價網頁（GitHub Pages）
  data/products.json  商品資料
  data/sites.json     各網站抓取狀態
  products.xlsx   Excel
.github/workflows/crawl.yml   每日排程
```

## 注意事項

- 價格與庫存僅供參考，以各網站實際顯示為準。
- 程式每次請求間會停 1～2 秒，避免對網站造成負擔；請勿把頻率調太高。
- 各網站改版時，對應的 `sites/*.py` 可能需要調整。
