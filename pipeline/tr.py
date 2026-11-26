import sys;sys.setrecursionlimit(20000)
import math,json,numpy as np
from PIL import Image
from skimage.graph import route_through_array
Z=15
def mp(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
def inv(x,y):
    n=2**Z*256;lon=x/n*360-180;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*y/n))));return lat,lon
OX,OY=mp(120.262,22.680)
def ll2px(la,lo):x,y=mp(lo,la);return x-OX,y-OY
def px2ll(x,y):return inv(x+OX,y+OY)
def crop2ll(box,px,py):  # box S W N E, crop scaled 2x
    x0,y0=ll2px(box[2],box[1]);return px2ll(x0+px/2,y0+py/2)
_im=None
def cost():
    global _im
    if _im is None:
        a=np.asarray(Image.open('h_TM25K_1989_15.png').convert('RGB')).astype(int)
        mx=a.max(2);mn=a.min(2)
        dark=(mx<120)&((mx-mn)<45)
        _im=np.where(dark,1.0,30.0)
    return _im
def rdp(pts,eps):
    if len(pts)<3:return pts
    a,b=np.array(pts[0]),np.array(pts[-1]);ab=b-a;L=np.hypot(*ab) or 1
    d=[abs(ab[0]*(p[1]-a[1])-ab[1]*(p[0]-a[0]))/L for p in pts[1:-1]];i=int(np.argmax(d))
    if d[i]>eps:return rdp(pts[:i+2],eps)[:-1]+rdp(pts[i+1:],eps)
    return [pts[0],pts[-1]]
def trace(*wps,eps=1.2):
    C=cost();out=[]
    for a,b in zip(wps,wps[1:]):
        ax,ay=ll2px(*a);bx,by=ll2px(*b)
        path,_=route_through_array(C,(int(round(ay)),int(round(ax))),(int(round(by)),int(round(bx))),fully_connected=True,geometric=True)
        pts=[(c,r) for r,c in path];out+=pts if not out else pts[1:]
    s=rdp(out,eps);return [[round(v,5) for v in px2ll(x,y)] for x,y in s]
