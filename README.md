# 高雄臨港線歷史路線圖（1900–2024）

互動地圖（Leaflet、年份滑桿、各線一覽、線形檢查）的完整工作檔：程式、歷史地圖參考、中間資料、每一輪的檢查截圖，以及使用者提供的原始圖片。

> **這個 repo 請保持 private。** 裡面有中研院「臺灣百年歷史地圖」圖磚快取、臉書社團的手繪圖掃描，以及第三方截圖。這些內容的再散布授權沒有確認過，只適合個人留存。若要公開，請先移除 `pipeline/h/`、`pipeline/h*_*.png`、`uploads/` 和 `scratch/` 中含歷史地圖的渲染圖。

## 目錄

| 路徑 | 內容 |
|---|---|
| `site/` | 最新版頁面（與已發布的 artifact 同一版）。`index.html` 內嵌所有幾何資料，搭配 `leaflet.*` 與底圖 `base.jpg` 即可離線開啟 |
| `site_v1/` | 最早一版頁面（手繪圖直譯版），留作對照 |
| `pipeline/` | 所有程式與中間資料，原樣保留工作目錄結構 |
| `pipeline/tpl.html` | 頁面模板，`__GEO__` 由 `build_page.py` 注入 |
| `pipeline/geo_*.json` | 各版幾何（`geo_v13.json` 為最新）；格式 `{seg:{id:[[lat,lon],…]}, extra:{名稱:[[[lat,lon],…]]}, st:{站名:[lat,lon]}, br:{…}}` |
| `pipeline/h/`、`pipeline/n/` | 歷史地圖圖磚快取（中研院）與國土測繪中心正射影像圖磚快取 |
| `pipeline/h*_*.png`、`base*.png` | 拼好的歷史地圖與 OSM 底圖 mosaic |
| `pipeline/water.npy`、`dark*.npy` | OSM 底圖水域遮罩、1989 年圖鐵路符號的暗色像素遮罩（線形擬合與檢查用） |
| `scratch/` | 工作過程中產生的檢查渲染圖（線疊在歷史地圖、正射影像、OSM 底圖上）與 QA 輸出 `qa*.txt` |
| `uploads/` | 使用者在對話中提供的圖片（手繪路線圖掃描、問題截圖）與引用片段 |
| `vendor/` | Leaflet 原始檔 |
| `WORKLOG.md` | 工作歷程：每一輪回饋、判斷依據、改了什麼、做錯了什麼 |
| `SOURCES.md` | 參考資料與資料來源 |

## 重建流程（最新版）

```bash
cd pipeline
python3 prep13.py        # geo_v12.json → geo_v12b.json：手動重描的線段、1945 年側線局部位移、裏岸壁線、獅子公園三角線東側
python3 apply_reg.py     # geo_v12b.json → geo_v13.json：線形規整（直線擬合、圓曲線、轉轍器接點）、岸壁線、淺野線、e1 彎道
python3 qa.py geo_v13.json > qa.txt      # 重疊、折角／小半徑、懸空端點、與 1989 年圖的偏離
python3 wetcheck.py geo_v13.json         # 連續 20 m 以上落在 OSM 底圖水域
python3 build_page.py    # tpl.html + geo_v13.json → ../site2/index.html
```

`apply_reg.py` 依賴 `regularize.py`（RDP 簡化、穩健直線擬合、切線—圓曲線—切線、轉轍器定位、距離場重新描線）、`corr.py`（1989 年圖像素座標換算）與上述遮罩檔。檢查用的套圖腳本：`povl.py`、`povl2.py`、`phov.py`、`movl.py`、`bchk.py`。圖磚下載：`hist.py`（中研院）、`nlsc.py`（國土測繪中心 WMTS）、`tiles.py`（OSM）。

較早的檔案（`rb2.py`～`rb6.py`、`final*.py`、`rebuild.py`、`connect.py`、`retrace.py` 等）是前幾版的流程，留作紀錄，不保證能單獨重跑。

## 授權與出處

- 底圖與部分軌跡：© OpenStreetMap contributors，ODbL。
- 正射影像：內政部國土測繪中心 2024 年正射影像（WMTS PHOTO2），政府資料開放授權。
- 歷史地圖：中央研究院人社中心「臺灣百年歷史地圖」圖磚服務（1945 AMS City Plan、1955／1966 AMS 1:25,000、1989 經建版 1:25,000）。
- 手繪路線圖：臉書社團貼文 <https://www.facebook.com/groups/openfind/posts/8293469417339893/>，作者未確認；頁面上只列為致謝與線索，不轉載。
