import json,sys,numpy as np
from PIL import Image,ImageDraw
from corr import ll2px
from qa import resample,toll,DT,W,H
G=json.load(open(sys.argv[1]));S=G['seg'];X=G['extra']
lines={k:v for k,v in S.items() if not k.startswith('lr')};lines.update({k:v[0] for k,v in X.items()})
BASE=Image.open('h89_16.png').convert('RGB')
def view(c,half,out,s=1.6):
    cx,cy=ll2px(*c);x0,y0,x1,y1=int(cx-half),int(cy-half),int(cx+half),int(cy+half)
    im=BASE.crop((x0,y0,x1,y1)).resize((int(2*half*s),int(2*half*s)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
    for n,L in lines.items():
        R,_=resample(L,2)
        pts=[ll2px(*toll(v)) for v in R]
        for (ax,ay),(bx,by) in zip(pts,pts[1:]):
            if not(x0-5<ax<x1+5 and y0-5<ay<y1+5):continue
            dd=DT[int(ay),int(ax)] if 0<=int(ax)<W and 0<=int(ay)<H else 99
            col=(0,170,0,200) if dd<6 else (230,170,0,220) if dd<12 else (230,0,0,230)
            d.line([((ax-x0)*s,(ay-y0)*s),((bx-x0)*s,(by-y0)*s)],fill=col,width=3)
    im.save(out)
pts=[(a,float(b),float(c)) for a,b,c in [x.split(',') for x in sys.argv[2:]]]
for n,la,lo in pts:view((la,lo),110,f'/tmp/qv_{n}.png')
