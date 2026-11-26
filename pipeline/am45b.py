import json
from am45 import px2ll,ll2px,q
from PIL import Image,ImageDraw
L={
 '表岸壁線':[(100,295),(320,385),(1160,770)],
 '中岸壁線':[(330,385),(440,408),(600,440),(1000,605),(1180,700)],
 '裏岸壁線':[(440,408),(500,382),(1150,640)],
 '北裏岸壁線':[(260,110),(480,212),(880,405),(1000,465),(1100,492),(1180,480),(1260,400),(1300,330)],
}
out={k:[px2ll(*q(x,y)) for x,y in v] for k,v in L.items()}
json.dump(out,open('am45_lines.json','w'))
im=Image.open('h_am45_16_harbor.png').convert('RGB');d=ImageDraw.Draw(im,'RGBA')
col={'表岸壁線':(255,0,0,220),'中岸壁線':(0,170,0,220),'裏岸壁線':(0,90,255,220),'北裏岸壁線':(255,0,255,220)}
for k,v in out.items():d.line([ll2px(*p) for p in v],fill=col[k],width=3)
for p in [(22.6163,120.2853),(22.6155,120.2871)]:x,y=ll2px(*p);d.ellipse((x-5,y-5,x+5,y+5),outline='orange',width=3)
im.crop((520,460,1180,880)).resize((1320,840)).save('/tmp/am45_t2.png')
