import math,json,sys,numpy as np
sys.setrecursionlimit(20000)
from PIL import Image,ImageDraw
from skimage.graph import route_through_array
Z=16
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
x0,y0=xy(120.264,22.632)
def px2ll(px,py):
    gx=(int(x0)*256+int((x0-int(x0))*256)+px)/256;gy=(int(y0)*256+int((y0-int(y0))*256)+py)/256
    n=2**Z;lon=gx/n*360-180;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*gy/n))));return [round(lat,6),round(lon,6)]
def ll2px(la,lo):
    gx,gy=xy(lo,la);return gx*256-(int(x0)*256+int((x0-int(x0))*256)),gy*256-(int(y0)*256+int((y0-int(y0))*256))
a=np.asarray(Image.open('h_am45_16_harbor.png').convert('RGB')).astype(int)
mx=a.max(2);mn=a.min(2);dark=(mx<110)&((mx-mn)<40)
C=np.where(dark,1.0,40.0)
q=lambda x,y:(520+x/2,460+y/2)
def tr(pts):
    out=[]
    for (ax,ay),(bx,by) in zip(pts,pts[1:]):
        p,_=route_through_array(C,(int(ay),int(ax)),(int(by),int(bx)),fully_connected=True,geometric=True)
        p=[(c,r) for r,c in p];out+=p if not out else p[1:]
    return out
L={
 '表岸壁線':[q(100,300),q(300,380),q(700,560),q(1180,760)],
 '中岸壁線':[q(440,410),q(800,530),q(1000,620),q(1170,705)],
 '裏岸壁線':[q(500,380),q(700,450),q(900,525),q(1180,640)],
 '北裏岸壁線':[q(300,150),q(480,215),q(880,400),q(1050,485),q(1180,480),q(1300,330)],
}
T={k:tr(v) for k,v in L.items()}
im=Image.open('h_am45_16_harbor.png').convert('RGB');d=ImageDraw.Draw(im,'RGBA')
col={'表岸壁線':(255,0,0,200),'中岸壁線':(0,170,0,200),'裏岸壁線':(0,90,255,200),'北裏岸壁線':(255,0,255,200)}
for k,v in T.items():d.line(v,fill=col[k],width=3)
im.crop((520,460,1180,880)).resize((1320,840)).save('/tmp/am45_t.png')
json.dump({k:[px2ll(x,y) for x,y in v] for k,v in T.items()},open('am45_raw.json','w'))
