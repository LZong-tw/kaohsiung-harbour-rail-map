"""把 geo_v13.json 注入 tpl.html，輸出網頁。

預設寫到 repo 的 ../site/index.html；用環境變數 OUT 指定其他位置。
"""
import os

OUT = os.environ.get('OUT', '../site/index.html')
g = open('geo_v13.json').read()
t = open('tpl.html').read()
assert '__GEO__' in t
open(OUT, 'w').write(t.replace('__GEO__', g))
print('built', OUT, len(t) + len(g))
