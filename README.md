# 高雄臨港線歷史路線圖（1900–2024）

本研究重建 1900–2024 年高雄臨港線系統各線的位置與年代。成果分成兩部分：

| 部分 | 位置 | 內容 |
|---|---|---|
| 研究過程與方法 | [`METHODS.md`](METHODS.md)（同步自 Claude 文件「高雄臨港線歷史路線圖：研究過程與方法」） | 資料來源、定位方法、線形規整、檢查流程、關鍵判讀與修正、路線與年代表、限制、授權 |
| 互動地圖 | [`site/`](site/)（另發布為 Claude artifact「高雄臨港線 1900–2024」） | 地圖與年份操作，以及各年份營運中／已停用的路線清單 |

逐輪工作紀錄在 [`WORKLOG.md`](WORKLOG.md)，參考資料在 [`SOURCES.md`](SOURCES.md)，每個腳本與中繼檔的用途在 [`FILES.md`](FILES.md)。在這個 repo 工作的原則（給 Claude，也給人看）在 [`CLAUDE.md`](CLAUDE.md)。

## 網站（GitHub Pages）

repo 可直接發布成靜態網站：首頁是互動地圖，另有「研究過程與方法」「工作歷程」「參考資料」三頁（由上述 Markdown 轉成），以及「資料與檔案」頁，依資料夾列出 repo 內所有程式、中間資料、檢查圖與截圖，連回 GitHub 上的原檔。研究資料本身不複製進網站，網站只有幾 MB。

- 建置：`.github/workflows/pages.yml` 在每次推送到 `main` 時執行 `tools/build_site.py`，輸出 `_site/` 並部署。
- 設定：repo 的 Settings → Pages → Build and deployment → Source 為「GitHub Actions」。
- 網址：<https://lzong-tw.github.io/kaohsiung-harbour-rail-map/>（repo 與網站皆公開）。
- 本機預覽：`pip install markdown && python tools/build_site.py`，再開 `_site/index.html`。

## 目錄

| 路徑 | 內容 |
|---|---|
| `site/` | 最新的互動地圖：`index.html` 內嵌幾何資料，搭配 `leaflet.*` 與底圖 `base.jpg`，可離線開啟 |
| `site_v1/` | 最早一版頁面，留作對照 |
| `pipeline/` | 程式與中間資料，保留原工作目錄結構 |
| `pipeline/tpl.html` | 頁面模板；`build_page.py` 會把幾何資料注入 `__GEO__` |
| `pipeline/geo_*.json` | 各版幾何，`geo_v13.json` 為最新 |
| `pipeline/h/`、`pipeline/n/` | 中研院歷史地圖圖磚快取、國土測繪中心正射影像圖磚快取 |
| `pipeline/water.npy`、`dark*.npy` | OSM 底圖水域遮罩、1989 年圖鐵路符號遮罩 |
| `scratch/` | 每一輪的套圖檢查圖與檢查輸出 `qa*.txt` |
| `uploads/` | 研究過程中的地圖截圖與對話摘錄（街景只留連結，不收錄截圖） |
| `vendor/` | Leaflet 原始檔 |
| `tools/build_site.py`、`.github/workflows/pages.yml` | GitHub Pages 網站的建置與部署 |

## 重建

```bash
cd pipeline
python3 prep13.py        # geo_v12.json → geo_v12b.json：手動重描的線段、局部位移、三角線、經貿變電所側線
python3 apply_reg.py     # → geo_v13.json：線形規整（直線擬合、圓曲線、轉轍器接點）、岸壁線、淺野線
python3 qa.py geo_v13.json        # 重疊、折角／小半徑、懸空端點、與 1989 年圖的偏離
python3 wetcheck.py geo_v13.json  # 是否落在 OSM 底圖水域
python3 build_page.py    # tpl.html + geo_v13.json → ../site/index.html
python3 ../tools/check_page.py ../site/index.html  # 年份切換與路線查詢檢查
```

較早的檔案（`rb2.py`～`rb6.py`、`final*.py` 等）是前幾版的流程，留作紀錄。

## 授權

本研究為非商業的學術用途。詳細說明見 `METHODS.md` 的「資料授權與使用條款」一節。

- **中研院「臺灣百年歷史地圖」圖磚**（1945、1955、1966、1989 各圖層）：以 CC BY-NC 釋出。使用時須標示中研院人社中心與原圖名，且不得商業使用。
- **1989 經建版地形圖**：紙圖著作權屬中華民國，代表機關為內政部國土測繪中心。本研究透過中研院圖磚使用。
- **美軍 AMS 地圖**：美國聯邦政府作品。
- **國土測繪中心正射影像**：政府資料開放授權。
- **OpenStreetMap**：ODbL，© OpenStreetMap contributors。
- **臉書手繪路線圖**：著作權屬原作者，本 repo 不收錄，只在 `METHODS.md` 列出原貼文連結作為線索。
