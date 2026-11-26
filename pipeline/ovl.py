import json,math,sys
from PIL import Image,ImageDraw
Z=16
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=xy(120.262,22.680)
def P(la,lo):x,y=xy(lo,la);return (x-OX,y-OY)
src,out=sys.argv[1],sys.argv[2];S,W,N,E=[float(v) for v in sys.argv[3:7]];draw=len(sys.argv)<8
im=Image.open(src).convert('RGB');d=ImageDraw.Draw(im,'RGBA')
if draw:
  G=json.load(open('geo_t.json'))
  for k,s in G['seg'].items():
    if k.startswith('lr'):continue
    d.line([P(*p) for p in s],fill=(255,0,255,130),width=3)
  for n,parts in G['extra'].items():
    for s in parts:d.line([P(*p) for p in s],fill=(0,150,255,150),width=3)
x0,y0=P(N,W);x1,y1=P(S,E)
c=im.crop((int(x0),int(y0),int(x1),int(y1)));c.save(out);print(c.size)
