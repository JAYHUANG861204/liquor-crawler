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
| `9city` | [洋酒城 9city](https://www.9city.com.tw/) | 逐一抓商品頁 | **自己電腦跑**（網站擋 GitHub） |
| `changi` | [iShopChangi](https://www.ishopchangi.com/en/category/wine-and-spirits) | 瀏覽器開分類頁、按 LOAD MORE | 需要觀察 |
| `609` | [酒條通 609](https://www.609.com.tw/) | 瀏覽器開分類頁 | 需要觀察 |
| `hk` | [DUTY ZERO 香港](https://www.dutyzero.com.hk/) | 瀏覽器抓分類頁 | 試跑中（被擋就改自己電腦跑） |
| `cdf` | [中免日上](https://www.cdfsunrise.com/) | 瀏覽器（App 型網站） | **自己電腦跑**（實驗中） |

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

**檢查資料品質**：`python -m crawler.audit`，列出各網站不合理的品牌、價格、容量等。每次排程跑完也會自動檢查，結果在 `docs/data/run.log` 最後面。

**品牌名稱沒有變英文**：在 `crawler/brands.py` 的 `ZH_EN` 加一行對照，例如 `"格蘭傑": "Glenmorangie",`。

---

## 給使用者：在 Windows 電腦上安裝與使用

不需要會寫程式，全部用 bat 檔和中文選單操作。

### 一、取得程式（擇一）

- **要上傳到網頁**（GitHub Pages）：先安裝 [Git](https://git-scm.com/download/win)，開「命令提示字元」輸入
  `git clone https://github.com/JAYHUANG861204/liquor-crawler.git C:\liquor-crawler`
- **只要在自己電腦看報表／Excel**：在 GitHub 頁面按綠色 **Code → Download ZIP**，解壓縮到 `C:\liquor-crawler`

> 資料夾路徑請用英文、不要太長（建議 `C:\liquor-crawler`），排程才不會出問題。

### 二、第一次安裝：按兩下 `setup.bat`

會自動完成：檢查／安裝 Python → 安裝套件 → 下載爬蟲用的瀏覽器 → 打開中文選單。第一次大約 5～10 分鐘。

### 三、平常使用：按兩下 `menu.bat`

| 選單 | 做什麼 |
|---|---|
| 1. 立即執行 | 選擇要抓的網站（可多選或全部），馬上執行 |
| 2. 開啟報表 | 用瀏覽器打開 `docs\report.html`：可篩選網站／品牌、排序、點圖放大 |
| 3. 開啟 Excel | 打開 `docs\products.xlsx`（含商品縮圖） |
| 4. 查看各網站資料狀態 | 每個網站幾筆、最後成功時間 |
| 5. 新增每日排程 | 設定每天幾點、跑哪些網站（用 Windows 工作排程器，可設多組） |
| 6～8. 排程管理 | 查看、刪除、立刻試跑排程 |
| 9. 查看排程執行紀錄 | 背景執行的過程記錄在 `local-run.log` |
| 10. 檢查資料品質 | 列出不合理的品牌、價格、容量 |

### 其他 bat 檔

| 檔案 | 用途 |
|---|---|
| `run_all.bat` | 全部網站跑一次（跑完自動打開報表） |
| `run_9city.bat` | 只跑 9city |
| `run_windows.bat` | 上面兩個共用的核心，可加參數：`run_windows.bat --sites 609,my9` |

### 注意事項

- **排程時間電腦要開著**（可以鎖定螢幕，不能關機或睡眠）。排程在背景執行，不會跳視窗。
- **有用 git clone 而且登入過 GitHub**：跑完會自動上傳，網頁（GitHub Pages）1～3 分鐘後更新。
  第一次上傳會跳出 GitHub 登入視窗，登入一次之後就記住了。
- **沒有 Git**：跑完只更新自己電腦上的報表和 Excel，不會出錯。
- 如果出現「建立排程失敗」：對 `menu.bat` 按右鍵 →「以系統管理員身分執行」。
- 執行時 Excel 請先關閉，否則無法更新 `products.xlsx`（程式會提醒並等待）。

### 交接給別人時

- **只給報表功能**：把整個資料夾（不含 `.venv`、`.browser-profile`）壓縮給對方，對方按 `setup.bat` 即可。
- **連網頁一起交接**：在 GitHub 的 **Settings → Collaborators** 加入對方帳號，或用 **Settings → Transfer** 把 repo 轉給對方。
  GitHub 上的每日排程（Actions）會繼續跑 609、Changi、DUTY ZERO、MY9；9city 要在對方電腦用排程跑。

---

## 程式結構

```
crawler/
  run.py          主程式：逐站執行、輸出 JSON 與 Excel、失敗時沿用舊資料
  common.py       共用：商品格式、HTTP 重試、容量/濃度/價格解析
  browser.py      Playwright 瀏覽器：捲動、按「載入更多」、通用商品卡擷取
  brands.py       中文品牌 → 英文品牌對照
  excel.py        Excel 輸出（含縮圖）
  report.py       本機報表 docs/report.html（資料內嵌，雙擊即可開）
  wizard.py       中文操作選單（menu.bat）
  publish.py      上傳到 GitHub（以最新版為底，只替換這次跑的網站）
  clean.py        統一資料清理
  audit.py        資料品質檢查
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
