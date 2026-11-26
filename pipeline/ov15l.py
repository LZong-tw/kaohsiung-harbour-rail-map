import json,math,sys
from PIL import Image,ImageDraw
Z=15
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=xy(120.262,22.680)
src,out=sys.argv[1],sys.argv[2];S,W,N,E=[float(v) for v in sys.argv[3:7]];s=float(sys.argv[7]);dy=float(sys.argv[8]) if len(sys.argv)>8 else 0
x0,y0=xy(W,N);x1,y1=xy(E,S)
im=Image.open(src).convert('RGB').crop((int(x0-OX),int(y0-OY),int(x1-OX),int(y1-OY)));im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
G=json.load(open('geo_v13.json'))
T=lambda p:((xy(p[1],p[0])[0]-x0)*s,(xy(p[1],p[0])[1]-y0+dy)*s)
for k,v in G['seg'].items():
  if k.startswith('lr'):continue
  d.line([T(p) for p in v],fill=(255,0,255,160),width=3)
for k,parts in G['extra'].items():
  for v in parts:d.line([T(p) for p in v],fill=(0,170,255,180),width=3)
x,y=T((22.5938,120.3080));d.ellipse((x-8,y-8,x+8,y+8),outline=(255,0,0),width=3)
im.save(out);print(im.size)
