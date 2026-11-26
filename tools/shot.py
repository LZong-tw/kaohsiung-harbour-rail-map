"""互動地圖逐年截圖（需要 playwright 與 Chrome）。

python tools/shot.py site/index.html OUTDIR NAME LAT LON ZOOM YEAR [YEAR ...]
  例：python tools/shot.py site/index.html scratch ks 22.6212 120.2790 17 1945 1977 1995

輸出 OUTDIR/NAME_YEAR.png（只截地圖區，不含側欄）。
環境變數 W、H 指定視窗大小（預設 1200×900），DARK=1 用深色模式。
"""
import asyncio, os, sys
from playwright.async_api import async_playwright


async def main(path, out, name, lat, lon, z, years):
    W, H = int(os.environ.get('W', 1200)), int(os.environ.get('H', 900))
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=os.environ.get('CHROME', '/usr/bin/google-chrome'),
                                    args=['--allow-file-access-from-files'])
        pg = await b.new_page(viewport={'width': W, 'height': H},
                              color_scheme='dark' if os.environ.get('DARK') else 'light')
        await pg.goto('file://' + os.path.abspath(path))
        await pg.wait_for_timeout(1500)
        box = await pg.evaluate("(()=>{const r=document.getElementById('map').getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
        for y in years:
            await pg.evaluate(f"""(()=>{{const s=document.getElementById('sl');s.value={y};s.dispatchEvent(new Event('input'));
                __map.setView([{lat},{lon}],{z},{{animate:false}})}})()""")
            await pg.wait_for_timeout(900)
            f = os.path.join(out, f'{name}_{y}.png')
            await pg.screenshot(path=f, clip={'x': box[0], 'y': box[1], 'width': box[2], 'height': box[3]})
            print(f)
        await b.close()

a = sys.argv[1:]
asyncio.run(main(a[0], a[1], a[2], float(a[3]), float(a[4]), float(a[5]), [int(x) for x in a[6:]]))
