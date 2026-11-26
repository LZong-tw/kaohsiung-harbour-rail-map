"""Regularise traced rail lines into railway-like geometry.
1) RDP -> straight runs; 2) refit straight runs to rail-symbol pixels on the 1989 map (robust);
3) rebuild as tangent-arc-tangent with radius caps; 4) branches leave parents tangentially (turnouts)."""
import json, math, sys, numpy as np
sys.setrecursionlimit(20000)
from corr import ll2px
DARK = np.load('dark2.npy')
H, W = DARK.shape
LAT0, LON0 = 22.62, 120.30
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110574
def toM(p): return np.array([(p[1] - LON0) * KX, (p[0] - LAT0) * KY])
def toLL(v): return [round(v[1] / KY + LAT0, 7), round(v[0] / KX + LON0, 7)]
def unit(v):
    n = np.hypot(*v); return v / n if n else v

def rdp(P, eps):
    P = np.asarray(P)
    def r(i, j):
        if j <= i + 1: return [i, j]
        a, b = P[i], P[j]; d = b - a; n = np.hypot(*d) or 1
        t = np.abs(d[0] * (P[i+1:j, 1] - a[1]) - d[1] * (P[i+1:j, 0] - a[0])) / n
        q = int(np.argmax(t))
        return (r(i, i+1+q)[:-1] + r(i+1+q, j)) if t[q] > eps else [i, j]
    return [P[k] for k in r(0, len(P) - 1)]

def drop_collinear(V, deg=1.5):
    out = [V[0]]
    for i in range(1, len(V) - 1):
        d1 = unit(V[i] - out[-1]); d2 = unit(V[i+1] - V[i])
        if math.degrees(math.acos(np.clip(d1 @ d2, -1, 1))) > deg: out.append(V[i])
    out.append(V[-1]); return out

# ---------- pixel refit of one straight run ----------
def is_dark(pm):
    x, y = ll2px(*toLL(pm)); xi, yi = int(round(x)), int(round(y))
    return 0 <= xi < W and 0 <= yi < H and DARK[yi, xi]

def refit(P, Q, maxshift=12.0, maxang=5.0, search=15):
    d = Q - P; L = np.hypot(*d)
    if L < 45: return None
    u = d / L; n = np.array([-u[1], u[0]])
    S, O = [], []
    for s in np.arange(0.12 * L, 0.88 * L, 2.0):
        c = P + u * s; hits = [o for o in np.arange(-search, search + 0.01, 1.0) if is_dark(c + n * o)]
        if not hits: continue
        # cluster contiguous offsets, take cluster centre nearest 0
        cl, cur = [], [hits[0]]
        for h in hits[1:]:
            if h - cur[-1] <= 1.01: cur.append(h)
            else: cl.append(cur); cur = [h]
        cl.append(cur)
        cl = [c_ for c_ in cl if len(c_) <= 5]          # drop wide blobs (text, buildings)
        if not cl: continue
        best = min(cl, key=lambda c_: abs(np.mean(c_)))
        S.append(s); O.append(float(np.mean(best)))
    nst = len(np.arange(0.12 * L, 0.88 * L, 2.0))
    if len(S) < max(8, 0.45 * nst): return None
    S = np.array(S); O = np.array(O); keep = np.ones(len(S), bool)
    for _ in range(6):
        A = np.vstack([np.ones(keep.sum()), S[keep]]).T
        a, b = np.linalg.lstsq(A, O[keep], rcond=None)[0]
        res = np.abs(O - (a + b * S)); nk = res < 2.5
        if (nk == keep).all(): break
        keep = nk
        if keep.sum() < 6: return None
    if keep.sum() < max(6, 0.35 * nst) or keep.mean() < 0.75: return None
    if abs(math.degrees(math.atan(b))) > maxang: return None
    o0, o1 = a, a + b * L
    if max(abs(o0), abs(o1)) > maxshift: return None
    return P + n * o0, Q + n * o1

def intersect(p1, d1, p2, d2):
    M = np.array([d1, -d2]).T
    if abs(np.linalg.det(M)) < 1e-6: return None
    t = np.linalg.solve(M, p2 - p1); return p1 + d1 * t[0]

def refit_poly(V, fixed_ends=(True, True), mask=None):
    """V: list of vertices (metres). mask(i)->bool whether segment i may be refit."""
    segs = []
    for i in range(len(V) - 1):
        r = refit(V[i], V[i+1]) if (mask is None or mask(i)) else None
        segs.append(r if r else (V[i], V[i+1]))
    out = [V[0] if fixed_ends[0] else segs[0][0]]
    for i in range(1, len(V) - 1):
        (a0, a1), (b0, b1) = segs[i-1], segs[i]
        x = intersect(a0, unit(a1 - a0), b0, unit(b1 - b0))
        if x is not None and np.hypot(*(x - V[i])) < 20: out.append(x)
        else: out.append((a1 + b0) / 2)
    out.append(V[-1] if fixed_ends[1] else segs[-1][1]); return out

# ---------- fillet ----------
def arc_pts(A, d1, d2, T, theta):
    R = T / math.tan(theta / 2); cr = d1[0] * d2[1] - d1[1] * d2[0]
    nrm = np.array([-d1[1], d1[0]]) if cr > 0 else np.array([d1[1], -d1[0]])
    C = A + nrm * R; a0 = math.atan2(*(A - C)[::-1]); sgn = 1 if cr > 0 else -1
    k = max(2, int(math.ceil(R * theta / 4)))
    return [C + R * np.array([math.cos(a0 + sgn * theta * j / k), math.sin(a0 + sgn * theta * j / k)]) for j in range(k + 1)]

def _bis_dev(Vi, d1, d2, trace):
    """distance from vertex Vi to the traced polyline along the inner bisector"""
    if trace is None: return None
    b = unit(d2 - d1)
    if not np.hypot(*b): return None
    best = None
    for k in range(len(trace) - 1):
        a, c = trace[k], trace[k + 1]; e = c - a
        M = np.array([b, -e]).T
        if abs(np.linalg.det(M)) < 1e-9: continue
        t, u = np.linalg.solve(M, a - Vi)
        if t >= 0 and 0 <= u <= 1 and (best is None or t < best): best = t
    return best

RTURN = 100
def fillet(V, Rmax, lead=None, tail=None, Tlead=70, trace=None, Rmin=60):
    """V vertices (metres). trace: original dense polyline (metres) - arc radius is fitted so the
    arc passes where the trace passes (bisector deviation), clamped to [Rmin, Rmax]."""
    V = [np.asarray(v, float) for v in V]; n = len(V)
    seglen = [np.hypot(*(V[i+1] - V[i])) for i in range(n - 1)]
    out = []
    if lead is not None and n >= 2:
        # turnout: slide the junction back along the parent until the diverging curve reaches R >= Rturn
        for _ in range(0):
            d2 = unit(V[1] - V[0]); th = math.acos(np.clip(lead @ d2, -1, 1))
            avail = np.hypot(*(V[1] - V[0])) * (0.5 if n > 2 else 0.9)
            if th < math.radians(0.5) or avail / math.tan(th / 2) >= RTURN: break
            V[0] = V[0] - lead * 4.0
        d2 = unit(V[1] - V[0]); th = math.acos(np.clip(lead @ d2, -1, 1))
        seglen[0] = np.hypot(*(V[1] - V[0]))
        if math.radians(0.5) < th < math.radians(150):
            avail = seglen[0] * (0.5 if n > 2 else 0.9)
            T = min(avail, max(Tlead, RTURN * math.tan(th / 2)))
            out += arc_pts(V[0] - lead * T, lead, d2, T, th)
        else: out.append(V[0])
    else: out.append(V[0])
    for i in range(1, n - 1):
        d1 = unit(V[i] - V[i-1]); d2 = unit(V[i+1] - V[i]); th = math.acos(np.clip(d1 @ d2, -1, 1))
        if th < math.radians(0.5): continue
        R = Rmax
        dv = _bis_dev(V[i], d1, d2, trace)
        if dv is not None and dv > 0.2:
            sec = 1 / math.cos(th / 2) - 1
            if sec > 1e-6: R = max(Rmin, min(Rmax, dv / sec))
        a1 = seglen[i-1] * (0.5 if (i - 1 > 0 or lead is not None) else 0.9)
        a2 = seglen[i] * (0.5 if (i + 1 < n - 1 or tail is not None) else 0.9)
        T = min(a1, a2, R * math.tan(th / 2))
        out += arc_pts(V[i] - d1 * T, d1, d2, T, th)
    if tail is not None and n >= 2:
        for _ in range(0):
            d1 = unit(V[-1] - V[-2]); th = math.acos(np.clip(d1 @ tail, -1, 1))
            avail = np.hypot(*(V[-1] - V[-2])) * (0.5 if n > 2 else 0.9)
            if th < math.radians(0.5) or avail / math.tan(th / 2) >= RTURN: break
            V[-1] = V[-1] + tail * 4.0
        d1 = unit(V[-1] - V[-2]); th = math.acos(np.clip(d1 @ tail, -1, 1))
        seglen[-1] = np.hypot(*(V[-1] - V[-2]))
        if math.radians(0.5) < th < math.radians(150):
            avail = seglen[-1] * (0.5 if n > 2 else 0.9)
            T = min(avail, max(Tlead, RTURN * math.tan(th / 2)))
            out += arc_pts(V[-1] - d1 * T, d1, tail, T, th)
        else: out.append(V[-1])
    else: out.append(V[-1])
    res = [out[0]]
    for p in out[1:]:
        if np.hypot(*(p - res[-1])) > 0.3: res.append(p)
    return res

# ---------- helpers on lat/lon polylines ----------
def nearest_on(p, L):
    P = toM(p); best = None
    for i in range(len(L) - 1):
        a, b = toM(L[i]), toM(L[i+1]); d = b - a; l2 = d @ d or 1e-9
        t = np.clip((P - a) @ d / l2, 0, 1); q = a + d * t; dist = np.hypot(*(P - q))
        if best is None or dist < best[0]: best = (dist, i, q, t, unit(d))
    return best

def insert_on(L, pm):
    d, i, q, t, u = nearest_on(toLL(pm), L); ll = toLL(q)
    if 0 < t < 1: L.insert(i + 1, ll)
    return L[i + 1] if 0 < t < 1 else (L[i] if t == 0 else L[i + 1])

PI_MIN = {}
def regularize(L, tol, Rmax, refit_mask=None, lead_parent=None, tail_parent=None, Tlead=70, lead_force=None, turn_R=100, maxback=140):
    """L lat/lon list. lead_parent/tail_parent: parent lat/lon polyline (already final)."""
    P = [toM(p) for p in L]
    V = simplify_pi(drop_collinear(rdp(P, tol)), minlen=PI_MIN.get('x', 40))
    if refit_mask is not None:
        V = refit_poly(V, (True, True), refit_mask)
        V = drop_collinear(V)
    lead = tail = None
    if lead_parent is not None:
        V, lead = seat_turnout(V, lead_parent, 0, force=lead_force, Rmin=turn_R, maxback=maxback)
    if tail_parent is not None:
        V, tl = seat_turnout(V, tail_parent, -1); tail = -tl
    out = fillet(V, Rmax, lead, tail, Tlead, trace=P)
    res = [toLL(p) for p in out]
    if lead_parent is not None: res[0] = insert_on(lead_parent, out[0])
    if tail_parent is not None: res[-1] = insert_on(tail_parent, out[-1])
    return res

# ---------- re-trace along rail pixels within a corridor of the current line ----------
from skimage.graph import route_through_array
from PIL import Image as _Im, ImageDraw as _Dr
from corr import px2ll
def route(L, buf_m=18):
    pts = [ll2px(*p) for p in L]; bpx = buf_m / 2.2
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0 = max(0, int(min(xs) - bpx - 4)); x1 = min(W, int(max(xs) + bpx + 4))
    y0 = max(0, int(min(ys) - bpx - 4)); y1 = min(H, int(max(ys) + bpx + 4))
    m = _Im.new('L', (x1 - x0, y1 - y0), 0); _Dr.Draw(m).line([(x - x0, y - y0) for x, y in pts], fill=255, width=max(3, int(2 * bpx)))
    M = np.asarray(m) > 0
    C = np.where(DARK[y0:y1, x0:x1], 1.0, 12.0); C[~M] = 1e6
    (ax, ay), (bx, by) = pts[0], pts[-1]
    path, _ = route_through_array(C, (int(round(ay - y0)), int(round(ax - x0))), (int(round(by - y0)), int(round(bx - x0))), fully_connected=True, geometric=True)
    out = [list(px2ll(c + x0, r + y0)) for r, c in path]
    out[0] = L[0]; out[-1] = L[-1]
    return out

from scipy.ndimage import distance_transform_edt as _edt
_DTPX = _edt(~DARK)
def route2(L, buf_m=30):
    """least-cost path hugging rail-symbol pixels (cost grows with distance from them) inside a corridor"""
    pts = [ll2px(*p) for p in L]; bpx = buf_m / 2.21
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0 = max(0, int(min(xs) - bpx - 4)); x1 = min(W, int(max(xs) + bpx + 4))
    y0 = max(0, int(min(ys) - bpx - 4)); y1 = min(H, int(max(ys) + bpx + 4))
    m = _Im.new('L', (x1 - x0, y1 - y0), 0); _Dr.Draw(m).line([(x - x0, y - y0) for x, y in pts], fill=255, width=max(3, int(2 * bpx)))
    Mk = np.asarray(m) > 0
    C = 0.3 + np.minimum(_DTPX[y0:y1, x0:x1], 8.0) ** 2; C[~Mk] = 1e6
    (ax, ay), (bx, by) = pts[0], pts[-1]
    path, _ = route_through_array(C, (int(round(ay - y0)), int(round(ax - x0))), (int(round(by - y0)), int(round(bx - x0))), fully_connected=True, geometric=True)
    out = [list(px2ll(c + x0, r + y0)) for r, c in path]
    out[0] = L[0]; out[-1] = L[-1]
    return out

def simplify_pi(V, minlen=40, maxjump=40):
    """merge short tangents: replace the two ends of the shortest interior segment (< minlen) by the
    intersection of the neighbouring tangents, so consecutive small bends become one curve."""
    V = [np.asarray(v, float) for v in V]
    while len(V) > 3:
        L = [np.hypot(*(V[i+1] - V[i])) for i in range(len(V) - 1)]
        cand = [(L[i], i) for i in range(1, len(V) - 2) if L[i] < minlen]
        if not cand: break
        _, i = min(cand)
        a0, a1, b0, b1 = V[i-1], V[i], V[i+1], V[i+2]
        x = intersect(a0, unit(a1 - a0), b1, unit(b0 - b1))
        if x is None or np.hypot(*(x - (a1 + b0) / 2)) > maxjump: x = (a1 + b0) / 2
        V = V[:i] + [x] + V[i+2:]
    return drop_collinear(V, 1.0)


def parent_samples(T, step=4.0):
    P = np.array([toM(p) for p in T]); seg = np.hypot(*np.diff(P, axis=0).T); c = np.concatenate([[0], np.cumsum(seg)])
    s_ = np.arange(0, c[-1], step); s_ = np.append(s_, c[-1])
    X_ = np.stack([np.interp(s_, c, P[:, 0]), np.interp(s_, c, P[:, 1])], 1)
    U = np.gradient(X_, axis=0); U = U / np.maximum(np.hypot(U[:, 0], U[:, 1]), 1e-9)[:, None]
    return X_, U

def seat_turnout(V, T, end=0, Rmin=100, maxback=140, force=None):
    """V: branch vertices in metres (V[0] or V[-1] = junction). Slides the junction along the real parent
    polyline T (lat/lon), away from the branch, until a diverging curve of radius >= Rmin fits.
    Returns (V_new, u) with u the parent tangent oriented towards the branch."""
    X_, U = parent_samples(T)
    Vb = V if end == 0 else V[::-1]
    j0 = int(np.argmin(np.hypot(*(X_ - Vb[0]).T)))
    hd = unit(Vb[min(2, len(Vb) - 1)] - Vb[0])
    sgn = force if force else (1 if U[j0] @ hd > 0 else -1)        # parent direction pointing along the branch
    best = None
    for k in range(0, int(maxback / 4) + 1):
        j = j0 - sgn * k
        if j < 0 or j >= len(X_): break
        J = X_[j]; u = U[j] * sgn
        # drop branch vertices that now lie behind/too close to J
        m = 1
        while m < len(Vb) - 1 and ((Vb[m] - J) @ u <= 0 or np.hypot(*(Vb[m] - J)) <= 8): m += 1
        rest = Vb[m:]
        d2 = unit(rest[0] - J); th = math.acos(np.clip(u @ d2, -1, 1))
        avail = np.hypot(*(rest[0] - J)) * (0.5 if len(rest) > 1 else 0.9)
        R = avail / math.tan(th / 2) if th > 1e-3 else 1e9
        cand = ([J] + rest, u, R)
        if best is None or R > best[2]: best = cand
        if R >= Rmin: best = cand; break
    Vn, u, _ = best
    return (Vn, u) if end == 0 else (Vn[::-1], u)
