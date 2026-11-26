import json,math,sys
from PIL import Image,ImageDraw
Z=15
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=xy(120.262,22.680)
src,out,gj=sys.argv[1],sys.argv[2],sys.argv[3];S_,W,N,E=[float(v) for v in sys.argv[4:8]];s=float(sys.argv[8])
x0,y0=xy(W,N);x1,y1=xy(E,S_)
im=Image.open(src).convert('RGB').crop((int(x0-OX),int(y0-OY),int(x1-OX),int(y1-OY)));im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
T=lambda p:((xy(p[1],p[0])[0]-x0)*s,(xy(p[1],p[0])[1]-y0)*s)
if gj!='-':
  G=json.load(open(gj))
  for k,v in G['seg'].items():
    if not k.startswith('lr'):d.line([T(p) for p in v],fill=(255,0,255,140),width=2)
  for k,v in G['extra'].items():d.line([T(p) for p in v[0]],fill=(0,170,255,160),width=2)
# lat/lon grid every 0.001
n=2**Z*256
import numpy as np
for lo in np.arange(math.ceil(W*1000)/1000,E,0.001):
  X=(xy(lo,22.6)[0]-x0)*s;d.line([(X,0),(X,im.height)],fill=(0,0,255,70));d.text((X+2,2),f'{lo:.3f}',fill=(0,0,255))
for la in np.arange(math.ceil(S_*1000)/1000,N,0.001):
  Y=(xy(120.3,la)[1]-y0)*s;d.line([(0,Y),(im.width,Y)],fill=(0,0,255,70));d.text((2,Y+2),f'{la:.3f}',fill=(0,0,255))
im.save(out);print(im.size)
