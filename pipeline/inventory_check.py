"""線的清單檢查：防止改腳本時不小心把已經畫好的線弄丟。

第 36 輪之五改 manual_lines.py 的一段文字時，誤刪了中島西岸線等六筆定線，connect_check、overlap、check_page 都照樣通過
（它們只檢查「還在的線」），直到第 36 輪之八疊圖才發現，期間公開的地圖少了這些線。

用法：python3 inventory_check.py            與 line_inventory.json 比對；有線不見、或某組站場股道變少，就結束碼 1
      python3 inventory_check.py --update   確認是有意刪除或改名之後，更新清單
"""
import json, sys
G = json.load(open('geo_v13.json'))
cur = {'seg': sorted(G['seg']), 'extra': sorted(G['extra']),
       'yards': {f"{g['src']}|{g.get('o')}|{g.get('c')}": len(g['lines']) for g in G['yards']}}
F = 'line_inventory.json'
if '--update' in sys.argv:
    json.dump(cur, open(F, 'w'), ensure_ascii=False, indent=1); print('已更新', F); sys.exit(0)
old = json.load(open(F)); bad = []
for k in ('seg', 'extra'):
    for n in old[k]:
        if n not in cur[k]: bad.append(f'不見了：{n}')
for n, c in old['yards'].items():
    if cur['yards'].get(n, 0) < c: bad.append(f'站場股道變少：{n}  {c} → {cur["yards"].get(n, 0)}')
new = [n for k in ('seg', 'extra') for n in cur[k] if n not in old[k]]
if new: print('新增（請跑 --update 記入清單）：', '、'.join(new))
if bad:
    print('\n'.join(bad)); sys.exit(1)
print('線的清單：沒有線不見（主線、支線', len(cur['seg']), '條，側線、糖鐵', len(cur['extra']), '條，站場股道', sum(cur['yards'].values()), '股）')
