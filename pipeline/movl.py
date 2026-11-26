import json,math,sys
from PIL import Image,ImageDraw
# usage: movl.py mosaic Z W N geo out cropx0 cropy0 cropx1 cropy1 scale [dlat] [extra_json]
src=sys.argv[1];Z=int(sys.argv[2]);W=float(sys.argv[3]);N=float(sys.argv[4]);gj=sys.argv[5];out=sys.argv[6]
cx0,cy0,cx1,cy1=[int(v) for v in sys.argv[7:11]];s=float(sys.argv[11]);dlat=float(sys.argv[12]) if len(sys.argv)>12 else 0
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
x0,y0=xy(W,N);ox=int(x0)*256+int((x0-int(x0))*256);oy=int(y0)*256+int((y0-int(y0))*256)
def P(la,lo):
    x,y=xy(lo,la+dlat);return ((x*256-ox-cx0)*s,(y*256-oy-cy0)*s)
im=Image.open(src).convert('RGB').crop((cx0,cy0,cx1,cy1));im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
G=json.load(open(gj))
for k,v in G['seg'].items():
  if k.startswith('lr'):continue
  d.line([P(*p) for p in v],fill=(255,0,255,140),width=3)
for k,parts in G['extra'].items():
  for v in parts:d.line([P(*p) for p in v],fill=(0,160,255,160),width=3)
step=100
for gx in range((cx0//step+1)*step,cx1,step):X=(gx-cx0)*s;d.line([(X,0),(X,im.height)],fill=(0,0,255,50));d.text((X+2,2),str(gx),fill=(0,0,255))
for gy in range((cy0//step+1)*step,cy1,step):Y=(gy-cy0)*s;d.line([(0,Y),(im.width,Y)],fill=(0,0,255,50));d.text((2,Y+2),str(gy),fill=(0,0,255))
im.save(out);print(im.size)
