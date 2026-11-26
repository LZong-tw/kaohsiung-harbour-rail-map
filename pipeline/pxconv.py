import math
def mk(Z,W,N,DL=0.0):
    def xy(lon,lat):
        n=2**Z;return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
    x0,y0=xy(W,N);ox=int(x0)*256+int((x0-int(x0))*256);oy=int(y0)*256+int((y0-int(y0))*256)
    def ll(px,py):
        n=2**Z*256;X,Y=ox+px,oy+py
        return [round(math.degrees(math.atan(math.sinh(math.pi*(1-2*Y/n))))-DL,6),round(X/n*360-180,6)]
    def px(la,lo):
        x,y=xy(lo,la+DL);return (x*256-ox,y*256-oy)
    return ll,px
