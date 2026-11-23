"""Aerial 'building lean': find the roof-photo shift per building, then fit shift/height smoothly over the campus."""
import pickle, json
from PIL import Image
from scipy import ndimage as nd
from common import *
R = pickle.load(open(WORK+'/mesh.pkl', 'rb')); cache = {}
PX = 4
def tile(tx, ty):
    if (tx, ty) not in cache:
        im = Image.open(f'{RAW}/aerial/{tx}_{ty}.jpg').convert('L').resize((TILE*PX, TILE*PX)); cache[tx, ty] = np.flipud(np.asarray(im, 'f4'))
    return cache[tx, ty]
def window(x0, y0, x1, y1):
    out = np.zeros((int((y1-y0)*PX), int((x1-x0)*PX)), 'f4')
    for tx in range(X0, X1, TILE):
        for ty in range(Y0, Y1, TILE):
            ax, bx, ay, by = max(x0, tx), min(x1, tx+TILE), max(y0, ty), min(y1, ty+TILE)
            if ax < bx and ay < by:
                t = tile(tx, ty); w = t[int((ay-ty)*PX):int((by-ty)*PX), int((ax-tx)*PX):int((bx-tx)*PX)]; oy, ox = int((ay-y0)*PX), int((ax-x0)*PX); h, ww = min(w.shape[0], out.shape[0]-oy), min(w.shape[1], out.shape[1]-ox); out[oy:oy+h, ox:ox+ww] = w[:h, :ww]
    return out
S = []
for r in R:
    if not r['codes'] or r['T'] is None or r['area'] < 500 or r['hsrc'] != 'lidar' or r['poly'].geom_type != 'Polygon': continue
    p = r['poly']; x0, y0, x1, y1 = [int(v) for v in p.bounds]; x0 -= 9; y0 -= 9; x1 += 10; y1 += 10
    if x0 < X0 or y0 < Y0 or x1 > X1 or y1 > Y1: continue
    w = nd.gaussian_filter(window(x0, y0, x1, y1), 1.2); gx = nd.sobel(w, 1); gy = nd.sobel(w, 0); c = np.array(p.exterior.coords); P = []; N = []
    for a, b in zip(c[:-1], c[1:]):
        l = np.hypot(*(b-a))
        if l < 3: continue
        t = np.arange(.7, l-.7, .4)[:, None]; P.append(a+(b-a)/l*t); N.append(np.repeat([[(b-a)[1]/l, -(b-a)[0]/l]], len(t), 0))
    if not P: continue
    P = np.vstack(P); N = np.vstack(N); rng = np.arange(-6, 6.01, .25); sc = np.zeros((len(rng),)*2)
    for i, dy in enumerate(rng):
        for j, dx in enumerate(rng):
            yy = (P[:, 1]+dy-y0)*PX; xx = (P[:, 0]+dx-x0)*PX; g = nd.map_coordinates(gx, [yy, xx], order=1)*N[:, 0]+nd.map_coordinates(gy, [yy, xx], order=1)*N[:, 1]; sc[i, j] = np.minimum(np.abs(g), 120).mean()
    i, j = np.unravel_index(sc.argmax(), sc.shape); pk = (sc.max()-sc.mean())/sc.std(); S.append((r['codes'][0]+'|'+r['id'], *r['c'], r.get('eave', r['h']), rng[j], rng[i], pk))
    cache = {k: v for k, v in cache.items()} if len(cache) < 12 else {}
S = [s for s in S if s[6] > 2.8 and abs(s[4]) < 5.9 and abs(s[5]) < 5.9]
A = np.array([s[1:] for s in S]); print(len(S)); M = np.c_[np.ones(len(A)), A[:, 0]/1000, A[:, 1]/1000]
print('mean shift', A[:, 3:5].mean(0), 'median', np.median(A[:, 3:5], 0))
for s in S[:60]: print('%s x%5.0f y%5.0f h%4.1f  dx%5.2f dy%5.2f pk%.1f' % s)
# model: shift = c0 + h*(a+bx+cy)
D = np.c_[np.ones(len(A)), A[:, 2:3]*M]
Q = []; RS = []
for k, n in ((3, 'dx'), (4, 'dy')):
    ok = np.ones(len(A), bool)
    for _ in range(10): q, *_ = np.linalg.lstsq(D[ok], A[ok, k], rcond=None); res = A[:, k]-D@q; ok = np.abs(res) < max(.8, 2*np.median(np.abs(res)))
    print(n, q.round(3), 'inliers', ok.mean().round(2), 'med res', np.median(np.abs(res)).round(2), 'med raw', np.median(np.abs(A[:, k])).round(2))
    Q.append(q.tolist()); RS.append(res)
res = {s[0].split('|')[1]: [float(a), float(b)] for s, a, b in zip(S, *RS) if s[6] > 3.4 and abs(a) < 1.3 and abs(b) < 1.3}
json.dump(dict(q=Q, res=res), open(WORK+'/lean.json', 'w')); print('per-building corrections', len(res))
