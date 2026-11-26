import json,math,sys
from PIL import Image,ImageDraw
# usage: z17ov.py name W E S N scale
name,W,E,S,N,s=sys.argv[1],*map(float,sys.argv[2:7])
import subprocess
import os
LY=os.environ.get('LY','TM25K_1989');EX=os.environ.get('EX','jpg')
subprocess.run(['python3','hist.py',LY,EX,'17',str(W),str(E),str(S),str(N),f'/tmp/{name}_raw.png'],check=True,capture_output=True)
Z=17
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
ox,oy=xy(W,N);P=lambda la,lo:((xy(lo,la)[0]-ox)*s,(xy(lo,la)[1]-oy)*s)
im=Image.open(f'/tmp/{name}_raw.png').convert('RGB');im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
G=json.load(open('geo_v13.json'))
for k,v in G['seg'].items():
    if not k.startswith('lr'):d.line([P(*p) for p in v],fill=(0,120,255,150),width=2)
for k,v in G['extra'].items():d.line([P(*p) for p in v[0]],fill=(0,200,120,170),width=2)
for x in range(0,im.width,100):d.text((x+2,2),f'{W+x/s/(2**Z*256/360):.4f}',fill=(0,0,200))
for y in range(0,im.height,100):
    n=2**Z*256;gy=oy+y/s;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*gy/n))))
    d.text((2,y+2),f'{lat:.4f}',fill=(0,0,200))
im.save(f'/tmp/{name}.png');print(name,im.size)
