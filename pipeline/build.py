"""Footprints + LiDAR heights -> simple, clean toy-style buildings. Writes data/work/mesh.pkl"""
import sys, io, contextlib, pickle, time, math
with contextlib.redirect_stdout(io.StringIO()):
    from match import *
import shapely, mapbox_earcut
from shapely.geometry import Polygon, MultiPolygon, LineString, box
from shapely.strtree import STRtree
from PIL import Image
from heights import *
top, solid, dtm = load()
gnd = lambda x, y: sample(dtm, 2.0, x, y)
O = json.load(open(ROOT+'/pipeline/overrides.json')); HO = json.load(open(ROOT+'/pipeline/heights_override.json'))
A = {k: [v[0]] for k, v in M.items()}
A.update({a[4]: [a[2]] for a in amb if a[4] not in O['reject'] and a[4] not in A})
A.update(O['set'])
for b in B:
    if b['t'].get('name') in O['accept_named']: A[b['id']] = O['accept_named'][b['t']['name']]
for k in O['reject']: A.pop(k, None)
def polys(g): return [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon' and p.area > 3]
# --- resolve overlaps -------------------------------------------------------
B.sort(key=lambda b: b['p'].area); tr = STRtree([b['p'] for b in B]); drop = set()
for i, b in enumerate(B):
    for j in tr.query(b['p']):
        if j <= i or i in drop or j in drop: continue
        c = B[j]['p'].intersection(b['p']).area
        if c < .5*b['p'].area: 
            if c > 1: B[j]['p'] = B[j]['p'].difference(b['p'].buffer(.01))
            continue
        if b['p'].area > .85*B[j]['p'].area: drop.add(j if (b['id'] in A and B[j]['id'] not in A) else i)
        else: B[j]['p'] = B[j]['p'].difference(b['p'].buffer(.01))
B = [b for i, b in enumerate(B) if i not in drop and not b['p'].is_empty]
print(len(B), 'buildings, dropped', len(drop))
CUSTOM = {'BELL', 'SCPA'}
def roofgrid(p, codes, t):
    """Local cleaned height window (metres above base) or None if LiDAR predates the building."""
    x0, y0, x1, y1 = p.bounds; i0 = int((y0-Y0)/.5)-3; j0 = int((x0-X0)/.5)-3; i1 = int((y1-Y0)/.5)+4; j1 = int((x1-X0)/.5)+4
    i0, j0 = max(i0, 0), max(j0, 0); z = np.array(solid[i0:i1, j0:j1]); tz = np.array(top[i0:i1, j0:j1])
    ny, nx = z.shape; xs = X0+(np.arange(j0, j0+nx)+.5)*.5; ys = Y0+(np.arange(i0, i0+ny)+.5)*.5; X, Y = np.meshgrid(xs, ys)
    g = gnd(X, Y); ext = np.array([c for q in polys(p) for c in q.exterior.coords]); base = float(np.percentile(gnd(ext[:, 0], ext[:, 1]), 10))
    inn = p.buffer(-.8); inn = p if inn.area < .4*p.area else inn
    m = shapely.contains_xy(inn, X, Y); ok = m & (z > 0); hag = z-g
    if any(c in HO for c in codes): return base, None
    n = ok.sum()
    if n < 6: return base, None
    low = (hag[ok] < 2.2).mean(); bowl = 'STDM' in codes
    if low > .7 and not bowl: return base, None
    good = ok & (hag > (0.4 if bowl else 2.2))
    if good.sum() < 5: return base, None
    ii = nd.distance_transform_edt(~good, return_distances=False, return_indices=True); h = (z-base)[tuple(ii)]
    k = 5 if p.area > 300 else 3
    h = nd.median_filter(h, k); h = nd.grey_opening(h, 4 if p.area > 300 else 3); h = nd.median_filter(h, k)
    # snap flat areas to one level
    rng = nd.maximum_filter(h, 3)-nd.minimum_filter(h, 3); flat = rng < .45
    lab, nl = nd.label(flat & (m | nd.binary_dilation(m, iterations=3)))
    if nl:
        ids = np.arange(1, nl+1); med = nd.median(h, lab, ids); sz = nd.sum(flat, lab, ids); p10 = nd.labeled_comprehension(h, lab, ids, lambda v: np.percentile(v, 8), float, 0); p90 = nd.labeled_comprehension(h, lab, ids, lambda v: np.percentile(v, 92), float, 0)
        for a in range(nl):
            if sz[a] > 40 and p90[a]-p10[a] < .9: h[lab == a+1] = med[a]
        if p.area > 150:
            keep = np.isin(lab, ids[(sz > 40) & (p90-p10 < .9)]); st = (rng > 1.4) & ~keep
            if keep.any():   # step cells snap to nearest flat tier -> crisp vertical steps
                ix = nd.distance_transform_edt(~keep, return_distances=False, return_indices=True); h[st] = h[tuple(ix)][st]
    return base, (h, xs[0], ys[0])
def polys_small(g): return [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon' and p.area > 1e-3]
# --- roof colours: median of the aerial photo, snapped to a small palette ---------
LN = json.load(open(ROOT+'/pipeline/lean.json')); PX = 2; _c = {}
PAL = ['#f1eee6', '#cfccc5', '#a5a29c', '#66656a', '#c2654c', '#94705a', '#d3bd98', '#7fa17f', '#707e90', '#c9a074']
PALN = ['white', 'light', 'grey', 'dark', 'tile', 'brown', 'tan', 'green', 'slate', 'bronze']
def tile(tx, ty):
    if (tx, ty) not in _c:
        if len(_c) > 16: _c.clear()
        _c[tx, ty] = np.flipud(np.asarray(Image.open(f'{RAW}/aerial/{tx}_{ty}.jpg').convert('RGB').resize((TILE*PX, TILE*PX), Image.BOX)))
    return _c[tx, ty]
def colour(g, hag, rid):
    """Palette index for roof polygon g at height hag."""
    g = g.buffer(-.8) if g.buffer(-.8).area > .3*g.area else g; x0, y0, x1, y1 = g.bounds; st = max(.5, math.sqrt(g.area)/40)
    X, Y = np.meshgrid(np.arange(x0, x1, st), np.arange(y0, y1, st)); m = shapely.contains_xy(g, X, Y); X, Y = X[m], Y[m]
    if len(X) < 4: return 1
    o = []
    for k in (0, 1): q = LN['q'][k]; o.append(q[0]+LN['res'].get(rid, [0, 0])[k]+hag*(q[1]+q[2]*X/1000+q[3]*Y/1000))
    X, Y = np.clip(X+o[0], X0, X1-1), np.clip(Y+o[1], Y0, Y1-1); C = np.zeros((len(X), 3)); tx = (np.floor((X-X0)/TILE)*TILE+X0).astype(int); ty = (np.floor((Y-Y0)/TILE)*TILE+Y0).astype(int)
    for t in set(zip(tx.tolist(), ty.tolist())):
        k = (tx == t[0]) & (ty == t[1]); C[k] = tile(*t)[((Y[k]-t[1])*PX).astype(int), ((X[k]-t[0])*PX).astype(int)]
    L = C.mean(1); c = np.median(C[L >= np.percentile(L, 35)], 0)*1.12; r, gg, b = c; l = c.mean(); sat = (c.max()-c.min())/max(c.max(), 1)
    if r > gg*1.13 and r > b*1.18 and l < 205: return 4 if r > gg*1.16 and r > 84 else (5 if l < 150 else 6)
    if gg > r*1.06 and gg > b*1.04 and sat > .1: return 7
    if b > r*1.1 and sat > .12: return 8
    if sat > .13 and r > b and l > 120: return 6
    if sat > .17 and r > b: return 5
    return 0 if l > 205 else 1 if l > 160 else 2 if l > 112 else 3
class Out:
    def __init__(s): s.T = []; s.C = []; s.W = []; s.E = []
    def flat(s, g, z, c):
        for q in polys(g):
            rs = [np.array(q.exterior.coords)[:-1]]+[np.array(r.coords)[:-1] for r in q.interiors]; v = np.vstack(rs)
            t = mapbox_earcut.triangulate_float64(v, np.cumsum([len(r) for r in rs]).astype('u4')).reshape(-1, 3)
            if len(t): s.tri(np.c_[v, z if np.ndim(z) else np.full(len(v), z)][t], c)
    def tri(s, T, c):
        ar = (T[:, 1, 0]-T[:, 0, 0])*(T[:, 2, 1]-T[:, 0, 1])-(T[:, 2, 0]-T[:, 0, 0])*(T[:, 1, 1]-T[:, 0, 1]); T = T.copy(); n = ar < 0; T[n] = T[n][:, ::-1]; T = T[np.abs(ar) > 1e-3]; s.T.append(T); s.C.append(np.full(len(T), c))
    def slope(s, outer, z0, inner, z1, c):
        """Sloped band between a polygon and its inset."""
        band = outer.difference(inner) if inner is not None else outer
        if inner is None: return s.flat(outer, z0, c)
        ib = inner.boundary
        for q in polys_small(band):
            rs = [np.array(q.exterior.coords)[:-1]]+[np.array(r.coords)[:-1] for r in q.interiors]; v = np.vstack(rs); on = shapely.distance(ib, shapely.points(v)) < .02
            t = mapbox_earcut.triangulate_float64(v, np.cumsum([len(r) for r in rs]).astype('u4')).reshape(-1, 3); z = np.where(on, z1, z0)
            if len(t): s.tri(np.c_[v, z][t], c)
    def wall(s, g, zb, zt, edges=True):
        for q in polys(g):
            for k, r in enumerate([q.exterior, *q.interiors]):
                c = np.array(r.coords); ccw = r.is_ccw
                if ccw != (k == 0): c = c[::-1]
                n = len(c)-1; d = np.diff(c, axis=0); ln = np.hypot(*d.T); ang = np.arctan2(d[:, 1], d[:, 0])
                for i in range(n):
                    if ln[i] < .05: continue
                    a, b = c[i], c[i+1]; s.W.append([[*a, zb, 0, ln[i]], [*b, zb, ln[i], ln[i]], [*b, zt, ln[i], ln[i]], [*a, zt, 0, ln[i]]])
                    if edges:
                        s.E.append([*a, zt, *b, zt]); t = abs((ang[i]-ang[i-1]+np.pi) % (2*np.pi)-np.pi)
                        if t > .45: s.E.append([*a, zb, *a, zt])
def tiers(p, grid, pitched):
    """Superlevel polygons [(z, poly)] from the height window; first is the whole footprint."""
    h, gx, gy = grid; c = np.array(p.minimum_rotated_rectangle.exterior.coords); e = max((c[1]-c[0], c[2]-c[1]), key=lambda v: np.hypot(*v)); a = math.atan2(e[1], e[0]); R = np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]])
    ext = np.vstack([np.array(q.exterior.coords) for q in polys(p)])@R.T; lo, hi = ext.min(0)-1, ext.max(0)+1; s = 1.
    nx, ny = np.ceil((hi-lo)/s).astype(int)+1; U, V = np.meshgrid(lo[0]+(np.arange(nx)+.5)*s, lo[1]+(np.arange(ny)+.5)*s); W = np.c_[U.ravel(), V.ravel()]@R
    H = h[np.clip(np.rint((W[:, 1]-gy)/.5).astype(int), 0, h.shape[0]-1), np.clip(np.rint((W[:, 0]-gx)/.5).astype(int), 0, h.shape[1]-1)].reshape(ny, nx); M = shapely.contains_xy(p, W[:, 0], W[:, 1]).reshape(ny, nx)
    H = nd.median_filter(H, 5); v = H[M]
    if len(v) < 8: return [(float(np.median(v)) if len(v) else 4, p)]
    hist, be = np.histogram(v, bins=np.arange(v.min()-.5, v.max()+1.5, 1.)); cen = (be[:-1]+be[1:])/2; gap = 4.0 if pitched else 2.8
    sm = nd.uniform_filter1d(hist.astype(float), 3); pk = [i for i in range(len(sm)) if sm[i] == sm[max(0, i-2):i+3].max() and hist[max(0, i-1):i+2].sum() > max(30, .06*len(v))]
    Z = []
    for i in pk:
        if Z and cen[i]-Z[-1][0] < gap:
            if sm[i] > Z[-1][1]: Z[-1] = (cen[i], sm[i])
        else: Z.append((cen[i], sm[i]))
    Z = [z for z, _ in Z][:5] or [float(np.median(v))]
    out = []
    for k, z in enumerate(Z):
        if k == 0: out.append([z, p]); continue
        m = (H > (Z[k-1]+z)/2) & nd.binary_dilation(M, iterations=2); m = nd.binary_opening(m, np.ones((5, 5))); m = nd.binary_closing(m, np.ones((5, 5))); lab, n = nd.label(m)
        bx = []
        for j in range(1, n+1):
            if (lab == j).sum() < max(30, .025*len(v)): continue
            for y in range(ny):
                xs = np.where(lab[y] == j)[0]
                for run in np.split(xs, np.where(np.diff(xs) > 1)[0]+1):
                    if len(run): bx.append(box(lo[0]+run[0]*s, lo[1]+y*s, lo[0]+(run[-1]+1)*s, lo[1]+(y+1)*s))
        if not bx: continue
        g = shapely.unary_union(bx).simplify(1.6); g = shapely.transform(g, lambda q: q@R); prev = out[-1][1]
        near = prev.difference(prev.buffer(-2.6, join_style=2)); g = shapely.unary_union([g, g.buffer(2.6, join_style=2).intersection(near)]).intersection(prev); g = g.buffer(-.9, join_style=2).buffer(.9, join_style=2).intersection(prev); g = MultiPolygon([Polygon(q.exterior, [r for r in q.interiors if Polygon(r).area > 12]) for q in polys(g) if q.area > 25])
        if g.is_empty: continue
        if g.area > .93*prev.area: out[-1][0] = z; continue
        out.append([z, g])
    return [tuple(o) for o in out]
def inset_max(p):
    lo, hi = 0, 60
    for _ in range(14):
        m = (lo+hi)/2; lo, hi = (m, hi) if not p.buffer(-m, join_style=2).is_empty else (lo, m)
    return lo
def hip(o, p, z0, z1, d, cs, cf):
    """Sloped roof rising z0->z1 over inset d, flat (or ridge) inside."""
    for q in polys(p):
        mx = inset_max(q); dd = min(d, mx*.93); top = z0+(z1-z0)*min(1, dd/d)
        inn = q.buffer(-dd, join_style=2, mitre_limit=3)
        o.slope(q, z0, inn, top, cs); o.flat(inn, top, cf)
        for i in polys_small(inn): c = np.array(i.exterior.coords); o.E += [[*c[k], top, *c[k+1], top] for k in range(len(c)-1) if np.hypot(*(c[k+1]-c[k])) > .4]
RO = json.load(open(ROOT+'/pipeline/roofs.json'))
def stadium(o, p):
    f = Polygon([(x, y) for x, y in RO['_field']]).convex_hull; n = 11
    for k in range(n):
        d0 = k*4.2; g = p.difference(f.buffer(d0, quad_segs=6)) if k else p
        nxt = p.difference(f.buffer(d0+4.2, quad_segs=6)) if k < n-1 else None
        z = 1.2+k*1.35; r = g.difference(nxt) if nxt is not None else g; o.flat(r, z, [1, 2][k % 2]); o.wall(g, z-1.35 if k else 0, z, edges=k % 2 == 0)
def dome(o, p, zw, zt, c):
    ce = p.centroid; o.wall(p, 0, zw); prev, pz = p, zw; n = 7; R = math.sqrt(p.area/math.pi)
    for k in range(1, n+1):
        t = k/n; z = zw+(zt-zw)*math.sin(t*math.pi/2); g = shapely.affinity.scale(p, 1-t*.97, 1-t*.97, origin=ce); o.slope(prev, pz, g, z, c); prev, pz = g, z
    o.flat(prev, pz, c)
def clean(p, tol):
    g = p.simplify(tol); g = shapely.make_valid(g); q = polys(g)
    q = [Polygon(a.exterior, [r for r in a.interiors if Polygon(r).area > 6]) for a in q]
    return q[0] if len(q) == 1 else MultiPolygon(q)
if __name__ == '__main__':
    import shapely.affinity
    from collections import Counter
    t0 = time.time(); out = []; kinds = Counter()
    for n, b in enumerate(B):
        cs = A.get(b['id'], []); t = b['t']; pu = bool(cs) or t.get('building') in ('university', 'dormitory') or t.get('operator') == 'Purdue University'
        raw = shapely.make_valid(b['p']); p = clean(raw, .55 if pu else .45)
        if p.is_empty: continue
        base, g = roofgrid(raw, cs, t)
        rec = dict(id=b['id'], t=t, codes=cs, purdue=pu, area=raw.area, base=base, c=list(p.representative_point().coords[0]), poly=p)
        if cs and cs[0] in CUSTOM: rec.update(T=None, W=None, h=49 if cs[0] == 'BELL' else 12, hsrc='custom'); out.append(rec); continue
        o = Out(); ov = next((RO[c] for c in cs if c in RO), RO.get(b['id'], {}))
        if g is None:
            hv = next((HO[c] for c in cs if c in HO), None)
            try: lv = float(t.get('building:levels', 0))
            except ValueError: lv = 0
            try: th = float(t.get('height', '0').split()[0])
            except ValueError: th = 0
            z = hv['m'] if hv else th or lv*3.4 or (4 if p.area < 60 else 6 if p.area < 400 else 8)
            rec.update(hsrc='estimated', hnote=hv['src'] if hv else ('OSM height' if th else 'OSM levels' if lv else 'estimate, no source found'))
            if hv and hv.get('levels'): rec['levels'] = hv['levels']
            o.wall(p, 0, z); o.flat(p, z, colour(p, z, b['id'])); rec['h'] = z; k = 'flat'
        else:
            h, gx, gy = g; rec['hsrc'] = 'lidar'; hs = nd.gaussian_filter(h, 1.5); G = np.hypot(nd.sobel(hs, 0), nd.sobel(hs, 1))/8/.5
            X, Y = np.meshgrid(gx+np.arange(h.shape[1])*.5, gy+np.arange(h.shape[0])*.5); m = shapely.contains_xy(raw, X, Y); mi = shapely.contains_xy(raw.buffer(-1.5), X, Y); mi = mi if mi.sum() > 20 else m
            v = h[m]; rec['h'] = float(np.percentile(v, 97)); sf = ((G[mi] > .17) & (G[mi] < 1.4)).mean(); k = ov.get('kind'); med = float(np.median(v)); ringc = None
            if k is None:
                if not pu and p.area < 520: k = 'hip' if sf > .3 else 'flat'
                else:
                    d = 5.; ring = p.difference(p.buffer(-d, join_style=2)); ringc = colour(ring, med, b['id']); k = 'hip' if sf > .42 or (ringc == 4 and pu) else 'tiers'
            kinds[k] += 1
            if k == 'stadium': stadium(o, p); rec['h'] = 16.
            elif k == 'dome': dome(o, p, ov['wall'], ov['top'], PALN.index(ov['colour'])); rec['h'] = float(ov['top'])
            elif k == 'flat': o.wall(p, 0, med); o.flat(p, med, colour(p, med, b['id']))
            elif k == 'hip' and not pu and p.area < 520:
                ring = m & ~shapely.contains_xy(raw.buffer(-1.6), X, Y); z0 = float(np.percentile(h[ring] if ring.sum() > 5 else v, 45)); z1 = float(np.percentile(v, 92)); z0 = max(2.6, min(z0, z1-1.2)); z1 = min(max(z1, z0+1.2), z0+min(4.2, .95*inset_max(p)+.6))
                cc = colour(p, z0, b['id']); o.wall(p, 0, z0); hip(o, p, z0, z1, max(inset_max(p)*.93, 1), cc, cc)
            else:
                TT = tiers(p, g, k == 'hip'); zprev = 0
                for j, (z, P) in enumerate(TT):
                    up = TT[j+1][1] if j+1 < len(TT) else None; roof = P.difference(up) if up is not None else P; 
                    if k == 'hip' and (j == 0 or P.area > .25*p.area):
                        mm = shapely.contains_xy(P.buffer(-.6), X, Y) & ~shapely.contains_xy(P.buffer(-2.2), X, Y); zz = float(np.percentile(h[mm], 35)) if mm.sum() > 20 else z-1.5; z0 = min(max(zz, zprev+1.5, z-4.5), z-.4); z1 = z+.9 if z-z0 < 2 else z+.4
                        o.wall(P, zprev, z0); ce = P.buffer(-11, join_style=2); ce = ce if ce.area > .07*P.area else P.buffer(-6.5, join_style=2); rc = ringc if ringc is not None and j == 0 else colour(P.difference(P.buffer(-5, join_style=2)), z, b['id'])
                        fc = colour(ce, z, b['id']) if ce.area > .06*P.area else rc
                        hip(o, P, z0, z1, 6., rc, fc); zprev = z0
                    else: o.wall(P, zprev, z); o.flat(roof, z, colour(roof, z, b['id'])); zprev = z
            rec['ntier'] = k
        if not o.T: print('empty', b['id'], cs); continue
        T = np.concatenate(o.T); T[:, :, 2] += base; W = np.array(o.W); W[:, :, 2][W[:, :, 2] <= 0] = -2.5; hh = W[:, :, 2].copy(); W[:, :, 2] += base; E = np.array(o.E).reshape(-1, 6); E[:, [2, 5]] += base
        rec['eave'] = float(np.median(W[:, 2, 2])-base); rec.update(T=T, C=np.concatenate(o.C), W=np.concatenate([W, hh[..., None]], 2), E=E); out.append(rec)
        if n % 1000 == 0: print(n, round(time.time()-t0), 's', flush=True)
    pickle.dump(out, open(WORK+'/mesh.pkl', 'wb')); print(len(out), kinds, 'tris', sum(len(r['T']) for r in out if r['T'] is not None), 'walls', sum(len(r['W']) for r in out if r['W'] is not None), 'edges', sum(len(r['E']) for r in out if r['T'] is not None), 'lidar', sum(r['hsrc'] == 'lidar' for r in out))
    print('roof colours (Purdue tris)', Counter(PALN[c] for r in out if r['codes'] and r['T'] is not None for c in r['C']).most_common())
