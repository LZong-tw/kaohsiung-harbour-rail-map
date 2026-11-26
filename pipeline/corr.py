import math,json,sys,numpy as np
sys.setrecursionlimit(20000)
from PIL import Image,ImageDraw
from skimage.graph import route_through_array
Z=16
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=xy(120.262,22.680)
def ll2px(la,lo):x,y=xy(lo,la);return x-OX,y-OY
def px2ll(x,y):
    n=2**Z*256;gx,gy=x+OX,y+OY;return [round(math.degrees(math.atan(math.sinh(math.pi*(1-2*gy/n)))),6),round(gx/n*360-180,6)]
A=np.asarray(Image.open('h89_16.png').convert('RGB')).astype(np.int16)
mx=A.max(2);mn=A.min(2);DARK=(mx<125)&((mx-mn)<50)
H,W=DARK.shape
def corridor(approx,buf_m=45,ends=None):
    bpx=buf_m/2.2
    pts=[ll2px(*p) for p in approx]
    xs=[p[0] for p in pts];ys=[p[1] for p in pts]
    x0=max(0,int(min(xs)-bpx-5));x1=min(W,int(max(xs)+bpx+5));y0=max(0,int(min(ys)-bpx-5));y1=min(H,int(max(ys)+bpx+5))
    m=Image.new('L',(x1-x0,y1-y0),0);ImageDraw.Draw(m).line([(x-x0,y-y0) for x,y in pts],fill=255,width=int(2*bpx))
    M=np.asarray(m)>0
    C=np.where(DARK[y0:y1,x0:x1],1.0,25.0);C[~M]=1e6
    a=ends[0] if ends else approx[0];b=ends[1] if ends else approx[-1]
    ax,ay=ll2px(*a);bx,by=ll2px(*b)
    path,_=route_through_array(C,(int(ay-y0),int(ax-x0)),(int(by-y0),int(bx-x0)),fully_connected=True,geometric=True)
    return [px2ll(c+x0,r+y0) for r,c in path]
