"""把 geo_v13.json 注入 tpl.html，輸出 ../site2/index.html"""
import json
g = open('geo_v13.json').read()
t = open('tpl.html').read()
assert '__GEO__' in t
open('../site2/index.html', 'w').write(t.replace('__GEO__', g))
print('built', len(t) + len(g))
