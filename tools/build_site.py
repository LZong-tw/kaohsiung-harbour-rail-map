"""Build the GitHub Pages site into _site/.

Pages:
  index.html    interactive map (site/index.html + a footer link to the research pages)
  methods.html  METHODS.md   研究過程與方法
  worklog.html  WORKLOG.md   工作歷程
  sources.html  SOURCES.md   參考資料
  files.html    FILES.md (what each script and intermediate file is for) + every repo file, linked to GitHub

Research data (pipeline/, scratch/, uploads/ …) is NOT copied into the site; files.html links
to it on GitHub so the Pages artifact stays small. Run from the repo root:

    pip install markdown
    python tools/build_site.py
"""
import html
import os
import re
import shutil
import subprocess
from collections import defaultdict

import markdown
import markdown.extensions.toc

REPO = 'LZong-tw/kaohsiung-harbour-rail-map'
BRANCH = 'main'
GH = f'https://github.com/{REPO}'
OUT = '_site'

PAGES = [  # (source, output, title)
    ('METHODS.md', 'methods.html', '研究過程與方法'),
    ('WORKLOG.md', 'worklog.html', '工作歷程'),
    ('SOURCES.md', 'sources.html', '參考資料'),
]
MD2HTML = {src: out for src, out, _ in PAGES}
MD2HTML['FILES.md'] = 'files.html'
NAV = [('index.html', '地圖')] + [(o, t) for _, o, t in PAGES] + [('files.html', '資料與檔案')]

# Directories described as a whole instead of file by file (tile caches, render dumps).
COLLAPSE_AT = 40
DIR_NOTES = {
    'site': '最新的互動地圖（本站首頁即此頁）',
    'site_v1': '最早一版頁面，留作對照',
    'pipeline': '程式、頁面模板、各版幾何與中間資料',
    'pipeline/h': '中研院臺灣百年歷史地圖圖磚快取（依圖層分資料夾）',
    'pipeline/n': '國土測繪中心正射影像圖磚快取',
    'scratch': '每一輪的套圖檢查圖與檢查輸出',
    'uploads': '研究過程中的截圖與街景觀察紀錄',
    'vendor': 'Leaflet 原始檔',
    'tools': '本站的建置程式',
}

CSS = """
:root{color-scheme:light dark;--bg:light-dark(#fff,#0e1418);--ink:light-dark(#14181d,#e7ecef);
--mute:light-dark(#5b6670,#9aa7b1);--soft:light-dark(#f3f4f2,#162027);--line:light-dark(#dfe3e6,#26323a);--acc:#7b2d8e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 "Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif}
nav{position:sticky;top:0;z-index:2;display:flex;flex-wrap:wrap;gap:4px 18px;padding:12px max(20px,calc(50% - 440px));
background:var(--bg);border-bottom:1px solid var(--line);font-size:14px}
nav a{color:var(--mute);text-decoration:none}nav a:hover{color:var(--ink)}nav a[aria-current]{color:var(--ink);font-weight:700}
main{max-width:920px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:1.9rem;line-height:1.3;margin:.2em 0 .6em}h2{font-size:1.35rem;margin:2.2em 0 .6em;padding-top:.6em;border-top:1px solid var(--line)}
h3{font-size:1.1rem;margin:1.8em 0 .5em}
a{color:var(--acc)}code{font:.88em ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:.1em .35em;border-radius:4px}
pre{background:var(--soft);padding:12px 14px;overflow:auto;border-radius:6px}pre code{background:none;padding:0}
.tw{overflow-x:auto;margin:1em 0}
table{border-collapse:collapse;font-size:14px;line-height:1.6;min-width:100%}
th,td{border-bottom:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--soft);white-space:nowrap}
.muted{color:var(--mute)}.files td:first-child{white-space:nowrap}
"""


def page(title, body, current):
    cur = ' aria-current="page"'
    nav = ''.join(f'<a href="{h}"{cur if h == current else ""}>{t}</a>' for h, t in NAV)
    return (f'<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}｜高雄臨港線</title><style>{CSS}</style></head>'
            f'<body><nav>{nav}</nav><main>{body}</main></body></html>')


def render_md(src):
    text = open(src, encoding='utf-8').read()
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'],
                           extension_configs={'toc': {'slugify': markdown.extensions.toc.slugify_unicode}})
    body = md.convert(text)
    # .md cross-links → the rendered pages; other relative repo paths → GitHub
    def fix(m):
        url = m.group(1)
        if re.match(r'^(https?:|mailto:|#)', url):
            return m.group(0)
        path = url.split('#')[0].rstrip('/')
        if path in MD2HTML:
            return f'href="{MD2HTML[path]}"'
        kind = 'tree' if url.endswith('/') or os.path.isdir(path) else 'blob'
        return f'href="{GH}/{kind}/{BRANCH}/{path}"'
    body = re.sub(r'href="([^"]+)"', fix, body)
    return re.sub(r'(<table>.*?</table>)', r'<div class="tw">\1</div>', body, flags=re.S)


def repo_files():
    out = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'HEAD'], capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if not p.startswith('.github/')]


def files_page():
    files = repo_files()
    tops = defaultdict(list)
    for p in files:
        tops[p.split('/')[0] if '/' in p else '.'].append(p)
    rows = []
    for top in sorted(tops, key=lambda t: (t != '.', t)):
        items = tops[top]
        if top == '.':
            for p in sorted(items):
                rows.append((p, f'<a href="{GH}/blob/{BRANCH}/{p}">{p}</a>', ''))
            continue
        rows.append((top, f'<strong><a href="{GH}/tree/{BRANCH}/{top}">{top}/</a></strong>',
                     f'{DIR_NOTES.get(top, "")}（{len(items)} 個檔案）'))
        sub = defaultdict(list)
        for p in items:
            parts = p.split('/')
            sub['/'.join(parts[:2]) if len(parts) > 2 else ''].append(p)
        for d in sorted(sub, key=lambda d: (d != '', d)):
            ps = sorted(sub[d])
            if d and len(ps) >= COLLAPSE_AT:
                rows.append((d, f'&nbsp;&nbsp;<a href="{GH}/tree/{BRANCH}/{d}">{d}/</a>',
                             f'{DIR_NOTES.get(d, "")}（{len(ps)} 個檔案，在 GitHub 上瀏覽）'))
                continue
            if not d and len(ps) >= COLLAPSE_AT * 4:
                exts = defaultdict(int)
                for p in ps: exts[os.path.splitext(p)[1] or '（無副檔名）'] += 1
                summary = '、'.join(f'{e} {n}' for e, n in sorted(exts.items(), key=lambda x: -x[1]))
                rows.append((top + '/*', f'&nbsp;&nbsp;<a href="{GH}/tree/{BRANCH}/{top}">{top}/ 內的檔案</a>',
                             f'{summary}，在 GitHub 上瀏覽'))
                continue
            for p in ps:
                rows.append((p, f'&nbsp;&nbsp;<a href="{GH}/blob/{BRANCH}/{p}">{p}</a>', ''))
    trs = ''.join(f'<tr><td>{a}</td><td class="muted">{b}</td></tr>' for _, a, b in rows)
    body = (render_md('FILES.md').replace('<h1', '<h1 id="files-top"', 1) +
            f'<h2 id="all-files">全部檔案</h2><p>repo 內所有檔案依資料夾列出，連到 '
            f'<a href="{GH}">GitHub</a> 上的原檔；檔案很多的資料夾只列總數。</p>'
            f'<div class="tw"><table class="files"><tr><th>路徑</th><th>說明</th></tr>{trs}</table></div>')
    return page('資料與檔案', body, 'files.html')


def map_page():
    t = open('site/index.html', encoding='utf-8').read()
    link = ('<p class="more" style="margin:18px 0 0;font-size:13px;color:var(--mute)">'
            '<a href="methods.html" style="color:inherit">研究過程與方法</a> · '
            '<a href="files.html" style="color:inherit">資料與檔案</a></p>\n</aside>')
    assert t.count('</aside>') == 1
    return t.replace('</aside>', link)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    open(f'{OUT}/.nojekyll', 'w').close()
    for f in os.listdir('site'):
        if f != 'index.html' and not f.startswith('_'):
            shutil.copy(f'site/{f}', f'{OUT}/{f}')
    open(f'{OUT}/index.html', 'w', encoding='utf-8').write(map_page())
    for src, out, title in PAGES:
        open(f'{OUT}/{out}', 'w', encoding='utf-8').write(page(title, render_md(src), out))
    open(f'{OUT}/files.html', 'w', encoding='utf-8').write(files_page())
    print('built', sorted(os.listdir(OUT)))


if __name__ == '__main__':
    main()
