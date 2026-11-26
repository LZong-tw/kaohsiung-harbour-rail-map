import math,sys
from PIL import Image
Z=15
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=xy(120.262,22.680)
src,out=sys.argv[1],sys.argv[2];S,W,N,E=[float(v) for v in sys.argv[3:7]];s=float(sys.argv[7])
x0,y0=xy(W,N);x1,y1=xy(E,S)
c=Image.open(src).convert('RGB').crop((int(x0-OX),int(y0-OY),int(x1-OX),int(y1-OY)));c=c.resize((int(c.width*s),int(c.height*s)),Image.LANCZOS);c.save(out);print(c.size)
