# pipeline/

研究流程的程式與中繼檔（原工作目錄的完整複本）。每個腳本與中繼檔的用途見 [`../FILES.md`](../FILES.md)。

現行流程：

```bash
python3 prep13.py                 # geo_v12.json → geo_v12b.json
python3 apply_reg.py              # → geo_v13.json
python3 qa.py geo_v13.json        # 幾何檢查
python3 wetcheck.py geo_v13.json  # 水域檢查
python3 build_page.py             # → ../site/index.html
python3 ../tools/check_page.py ../site/index.html
```
