import json,math,sys
from PIL import Image,ImageDraw
src,out,Z,W,N=sys.argv[1],sys.argv[2],int(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5]);s=float(sys.argv[6]) if len(sys.argv)>6 else 1
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
ox,oy=xy(W,N);P=lambda la,lo:((xy(lo,la)[0]-ox)*s,(xy(lo,la)[1]-oy)*s)
im=Image.open(src).convert('RGB');im=im.resize((int(im.width*s),int(im.height*s)));d=ImageDraw.Draw(im,'RGBA')
G=json.load(open('geo_v13.json'))
for k,v in G['seg'].items():
  if not k.startswith('lr'):d.line([P(*p) for p in v],fill=(255,0,255,150),width=3)
cols={'裏岸壁線':(0,160,255,170),'中岸壁線':(0,200,80,170)}
for k,parts in G['extra'].items():
  for v in parts:d.line([P(*p) for p in v],fill=cols.get(k,(255,140,0,170)),width=3)
for x in range(0,im.width,100):d.text((x,2),str(int(x/s)),fill=(255,0,0))
for y in range(0,im.height,100):d.text((2,y),str(int(y/s)),fill=(255,0,0))
im.save(out)
