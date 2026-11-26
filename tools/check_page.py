"""互動地圖的行為檢查（需要 playwright 與 Chrome）。

python tools/check_page.py site/index.html

1. 各年份顯示的側線、股道、分歧點數量；
2. 每條看得見的線，沿線取點都能被「路線查詢」找到（重疊路廊、虛線也要點得到）；
3. 頁面沒有 JavaScript 錯誤。
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

YEARS = [1900, 1930, 1945, 1960, 1977, 1995, 2010, 2024]
HOOKS = [
    ("L.control.zoom({position:'topright'}).addTo(m);", "L.control.zoom({position:'topright'}).addTo(m);window.__m=m;"),
    ("const exBox=document.getElementById('ex');",
     "const exBox=document.getElementById('ex');window.__lay=lay;window.__exL=exL;window.__yard=yard;window.__bp=bpL;window.__SEG=SEG;"),
    ("const _draw=draw;draw=function(y){", "const _draw=draw;draw=window.draw=function(y){"),
    ("function pickAt(pt,tol){", "window.__pick=(pt,tol)=>pickAt(pt,tol);function pickAt(pt,tol){"),
]
JS = """(y)=>{draw(y);const on=l=>__m.hasLayer(l);const miss=[];
 const chk=(name,l)=>{if(!on(l)||!l._parts)return;let ok=0,n=0;
  for(const part of l._parts)for(let i=0;i<part.length;i+=Math.max(1,Math.floor(part.length/8))){n++;if(__pick(part[i],8).some(x=>x.t===name))ok++}
  if(n&&ok<n)miss.push(name+' '+ok+'/'+n)};
 for(const s of __SEG)chk(s.name,__lay[s.id]);__exL.forEach(l=>chk(l._xn,l));
 return {extra:__exL.filter(on).length,yard:__yard.filter(on).length,branch:__bp.filter(on).length,miss}}"""


async def main(path):
    src = open(path, encoding='utf-8').read()
    for a, b in HOOKS:
        assert a in src, f'hook not found: {a[:40]}'
        src = src.replace(a, b)
    tmp = os.path.join(os.path.dirname(os.path.abspath(path)), '_check.html')
    open(tmp, 'w', encoding='utf-8').write(src)
    bad = False
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('CHROME', '/usr/bin/google-chrome'),
                                        args=['--allow-file-access-from-files'])
            pg = await b.new_page(viewport={'width': 1600, 'height': 1400})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto('file://' + tmp)
            await pg.wait_for_timeout(1500)
            for y in YEARS:
                r = await pg.evaluate(JS, y)
                print(y, f"側線 {r['extra']}  股道 {r['yard']}  分歧點 {r['branch']}", '點不到：' + '、'.join(r['miss']) if r['miss'] else '')
                bad |= bool(r['miss'])
            if errs:
                print('JavaScript 錯誤：', errs)
                bad = True
            await b.close()
    finally:
        os.remove(tmp)
    sys.exit(1 if bad else 0)

asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else 'site/index.html'))
