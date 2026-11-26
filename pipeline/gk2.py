import json,math,sys
from PIL import Image,ImageDraw
src,Z,W,N,out,dlat=sys.argv[1],int(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]),sys.argv[5],float(sys.argv[6])
cx0,cy0,cx1,cy1=[int(v) for v in sys.argv[7:11]];sc=float(sys.argv[11])
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
x0,y0=xy(W,N);ox=int(x0)*256+int((x0-int(x0))*256);oy=int(y0)*256+int((y0-int(y0))*256)
P=lambda la,lo:((xy(lo,la+dlat)[0]*256-ox-cx0)*sc,(xy(lo,la+dlat)[1]*256-oy-cy0)*sc)
im=Image.open(src).convert('RGB').crop((cx0,cy0,cx1,cy1));im=im.resize((int(im.width*sc),int(im.height*sc)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
for la,lo,c in [(22.62173,120.27556,(255,0,0)),(22.62467,120.27725,(255,120,0))]:
  x,y=P(la,lo);d.ellipse((x-7,y-7,x+7,y+7),outline=c,width=3)
for k in range(0,200):
  lo=120.272+k*0.0002;x,_=P(22.62,lo)
  if 0<x<im.width:d.line([(x,0),(x,im.height)],fill=(0,0,255,45));d.text((x+2,2),f'{lo:.4f}'[-4:],fill=(0,0,255))
  la=22.615+k*0.0002;_,y=P(la,120.28)
  if 0<y<im.height:d.line([(0,y),(im.width,y)],fill=(0,0,255,45));d.text((2,y+2),f'{la:.4f}'[-4:],fill=(0,0,255))
im.save(out);print(im.size)
