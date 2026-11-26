import sys,json
from PIL import Image,ImageDraw
from corr import ll2px
src,out,gj=sys.argv[1],sys.argv[2],sys.argv[3];x0,y0,x1,y1=[int(v) for v in sys.argv[4:8]];s=float(sys.argv[8])
G=json.load(open(gj))
im=Image.open(src).convert('RGB').crop((x0,y0,x1,y1));im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
T=lambda p:((ll2px(*p)[0]-x0)*s,(ll2px(*p)[1]-y0)*s)
for k,v in G['seg'].items():
  if k.startswith('lr'):continue
  d.line([T(p) for p in v],fill=(255,0,255,150),width=3)
for k,parts in G['extra'].items():
  for v in parts:d.line([T(p) for p in v],fill=(0,160,255,170),width=3)
st=int(sys.argv[9]) if len(sys.argv)>9 else 50
for x in range((x0//st+1)*st,x1,st):X=(x-x0)*s;d.line([(X,0),(X,im.height)],fill=(0,120,255,60));d.text((X+2,2),str(x),fill=(0,0,255))
for y in range((y0//st+1)*st,y1,st):Y=(y-y0)*s;d.line([(0,Y),(im.width,Y)],fill=(0,120,255,60));d.text((2,Y+2),str(y),fill=(0,0,255))
im.save(out)
