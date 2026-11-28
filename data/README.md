# 開放資料：高雄臨港線 1900–2024（GeoJSON）

這個資料夾是互動地圖上全部線形的**開放格式副本**。格式是 GeoJSON（[RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946)，WGS84 經緯度），不需要本專案的網頁或腳本就能檢視、修改、轉檔。

## 檔案

| 檔案 | 內容 |
|---|---|
| `kaohsiung-harbour-rail-1900-2024.geojson` | 全部（以下四檔合併） |
| `kaohsiung-harbour-rail-1900-2024_lines.geojson` | 主線、支線、環狀輕軌 |
| `kaohsiung-harbour-rail-1900-2024_sidings.geojson` | 專用側線、主線旁的並行股、糖業鐵道 |
| `kaohsiung-harbour-rail-1900-2024_yard-tracks.geojson` | 站場股道（每股一筆） |
| `kaohsiung-harbour-rail-1900-2024_points.geojson` | 車站與車場、分歧點、轉車台 |

下載網址（GitHub Pages）：

- <https://lzong-tw.github.io/kaohsiung-harbour-rail-map/data/kaohsiung-harbour-rail-1900-2024.geojson>
- 分層檔把檔名換成上表的名稱即可。

## 怎麼看、怎麼改

- **只是看**：在 GitHub 上點開 `.geojson` 檔，GitHub 會直接畫成地圖，點線可以看欄位。
- **在瀏覽器裡改**：到 <https://geojson.io>，用 Open → File 開啟下載的檔；左邊改線形，右邊改欄位，改完 Save → GeoJSON。
- **用 GIS 軟體**：QGIS、ArcGIS 直接拖進去就是圖層；用 `start_year`、`end_year` 設篩選條件就能看某一年（見下方範例）。
- **轉成別的格式**：`ogr2ogr -f KML out.kml kaohsiung-harbour-rail-1900-2024.geojson`（GeoPackage、Shapefile 同理）。
- **寫程式用**：任何讀 GeoJSON 的函式庫（Leaflet、OpenLayers、MapLibre、GeoPandas、Turf）都能直接讀。

看某一年（例如 1983 年）營運中的線，篩選條件：

```
(start_year IS NULL OR start_year <= 1983) AND (end_year IS NULL OR end_year > 1983)
AND (geometry_from IS NULL OR geometry_from <= 1983) AND (geometry_to IS NULL OR geometry_to > 1983)
```

## 欄位

一筆 feature 是「**一條線在一段年代的線形**」。同一條線如果依年代換過線形（例如穿過高雄港站的線隨站場改建換股道、第三貨櫃線末段 1999 年前後不同），每個年代各一筆，`id` 相同，`geometry_from`／`geometry_to` 不同。

| 欄位 | 說明 |
|---|---|
| `id` | 識別碼。主線、支線是路段代碼（如 `w1`）；側線是 `x-` 加線名；股道是 `yard-組-序`；點是 `st-`、`br-`、`tt-` 開頭 |
| `name` | 線名或站名。股道沒有名字（`null`） |
| `label` | 地圖上的短標籤（只有主線、支線有） |
| `layer` | `line`（主線、支線、輕軌）、`siding`（側線、並行股、糖鐵）、`yard_track`（站場股道）、`station`、`junction`、`turntable` |
| `kind`、`kind_zh` | 細類的代碼與中文：`trunk` 縱貫線與屏東線、`harbour_main` 臨港線、`harbour_branch` 臨港線支線、`second_harbour` 第二臨港線、`light_rail` 環狀輕軌、`siding` 專用側線與並行股、`sugar_railway` 糖業鐵道、`yard_track` 站場股道 |
| `start_year`、`end_year` | 這條線的營運年代，區間是 **[start_year, end_year)**：`end_year` 當年起不再營運。`null` 表示不詳或仍在營運 |
| `geometry_from`、`geometry_to` | 這一筆線形適用的年代，同樣是 [from, to)。`null` 表示整個營運期間都是這個線形 |
| `history` | 一句話的沿革（主線、支線） |
| `today` | 現況（主線、支線） |
| `basis` | 判讀依據：依哪一年的哪一張圖、哪些地方是推定（側線） |
| `source` | 描線來源的圖（股道、轉車台） |
| `name_periods` | 車站各年代的站名（例如鼓山 1929–1949 為田町） |
| `radius_m` | 轉車台半徑（公尺） |
| `stroke`、`stroke-width`、`stroke-opacity` | [simplestyle](https://github.com/mapbox/simplestyle-spec) 樣式欄位，顏色與互動地圖的圖例相同；GitHub、geojson.io 會照這個上色。不需要可以刪 |

座標順序是 `[經度, 緯度]`，小數七位（約 1 公分；實際精度見下）。

## 使用前要知道的

- **年份有三種來源**：文獻日期、地圖上最早與最晚出現的年份、推定。差別寫在 `basis`、`history` 與研究文件裡；線名裡有「推定」「用途未查明」的，就是字面上的意思。只在某一張圖上看到的線，年份取那張圖所屬的年代（例如只見於 1984 年圖的取 1977–1990），不代表實際只存在那幾年。
- **位置精度**：主線、支線以 1/5000 像片基本圖為準，各版互差 3–5 m；側線與股道多依 1984 年都市計畫航測地形圖人工定線；日治時期與糖鐵的線依 1/25,000 地形圖，誤差 20–30 m。
- **雙線畫成一條**：縱貫線、屏東線等雙線區間以兩股的中線代表。
- **這是單向輸出**：這些檔由 `pipeline/geo_v13.json` 與 `pipeline/tpl.html` 經 `pipeline/export_geojson.py` 產生，每次改線都會重新產生並由 CI 檢查一致。你在自己的副本上怎麼改都可以；但改這裡的檔**不會**回到互動地圖。要回饋修正，請在 [GitHub issue](https://github.com/LZong-tw/kaohsiung-harbour-rail-map/issues) 附上改過的 GeoJSON 或說明依據，由 pipeline 的來源檔改起。

## 來源與授權

線形是本研究依歷史地圖、像片基本圖與文獻判讀的結果，非商業學術用途；引用請註明「高雄臨港線歷史路線圖（LZong-tw/kaohsiung-harbour-rail-map）」。底圖與各歷史圖資的授權見 [`METHODS.md`](https://github.com/LZong-tw/kaohsiung-harbour-rail-map/blob/main/METHODS.md)〈資料授權與使用條款〉；本資料夾只含向量線形與文字，不含任何底圖影像。
