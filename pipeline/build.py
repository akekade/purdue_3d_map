"""Footprints + LiDAR -> roofs, walls, terrain. Writes data/work/mesh.pkl"""
import sys, io, contextlib, pickle, time, math
with contextlib.redirect_stdout(io.StringIO()):
    from match import *
import shapely, mapbox_earcut
from shapely.geometry import Polygon, MultiPolygon, LineString, box
from shapely.strtree import STRtree
from pydelatin import Delatin
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
def flatmesh(p, hh):
    V = []; F = []
    for q in polys(p):
        rs = [np.array(q.exterior.coords)[:-1]]+[np.array(r.coords)[:-1] for r in q.interiors]
        v = np.vstack(rs); t = mapbox_earcut.triangulate_float64(v, np.cumsum([len(r) for r in rs]).astype('u4')).reshape(-1, 3)
        F.append(t+sum(map(len, V))); V.append(np.c_[v, np.full(len(v), hh)])
    return np.vstack(V), np.vstack(F)
def tinmesh(p, grid, purdue):
    h, gx, gy = grid; r = p.minimum_rotated_rectangle; c = np.array(r.exterior.coords); e = c[1]-c[0]; e2 = c[2]-c[1]
    e = e if np.hypot(*e) > np.hypot(*e2) else e2; a = math.atan2(e[1], e[0]); ca, sa = math.cos(a), math.sin(a)
    R = np.array([[ca, sa], [-sa, ca]]); ext = np.vstack([np.array(q.exterior.coords) for q in polys(p)]); lo = (ext@R.T).min(0)-1.2; hi = (ext@R.T).max(0)+1.2
    s = .5 if p.area < 12000 else .75
    nx, ny = np.maximum(np.ceil((hi-lo)/s).astype(int)+1, 4); U, Vv = np.meshgrid(lo[0]+np.arange(nx)*s, lo[1]+np.arange(ny)*s)
    W = np.c_[U.ravel(), Vv.ravel()]@R; gi = np.clip(np.rint((W[:, 1]-gy)/.5).astype(int), 0, h.shape[0]-1); gj = np.clip(np.rint((W[:, 0]-gx)/.5).astype(int), 0, h.shape[1]-1)
    H = h[gi, gj].reshape(ny, nx); H = nd.median_filter(H, 3 if not purdue else 5)
    t = Delatin(H.astype('f4'), max_error=.45 if purdue else 1.1); v = t.vertices.astype('f8'); f = np.array(t.triangles)
    P = np.c_[np.c_[lo[0]+v[:, 0]*s, lo[1]+(v[:, 1])*s]@R, v[:, 2]]
    # pydelatin may flip y: verify against the grid
    iy = np.clip(v[:, 1].astype(int), 0, ny-1); ix = np.clip(v[:, 0].astype(int), 0, nx-1)
    if np.abs(H[iy, ix]-v[:, 2]).mean() > 1e-3:
        P = np.c_[np.c_[lo[0]+v[:, 0]*s, lo[1]+(ny-1-v[:, 1])*s]@R, v[:, 2]]; assert np.abs(H[ny-1-iy, ix]-v[:, 2]).mean() < 1e-3
    return P, f
def clip(P, F, p):
    tri = P[F]; G = shapely.polygons(np.concatenate([tri[:, :, :2], tri[:, :1, :2]], 1)); shapely.prepare(p)
    ins = shapely.contains_properly(p, G); hit = shapely.intersects(p, G) & ~ins; out = [tri[ins]]
    for k in np.where(hit)[0]:
        for q in polys_small(shapely.intersection(p, G[k])):
            v = np.array(q.exterior.coords)[:-1]
            if len(q.interiors): rs = [v]+[np.array(i.coords)[:-1] for i in q.interiors]; v = np.vstack(rs); ends = np.cumsum([len(x) for x in rs])
            else: ends = np.array([len(v)])
            tt = mapbox_earcut.triangulate_float64(v, ends.astype('u4')).reshape(-1, 3); a, b, c = tri[k]
            d = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(d) < 1e-9: continue
            l = ((b[1]-c[1])*(v[:, 0]-c[0])+(c[0]-b[0])*(v[:, 1]-c[1]))/d; mm = ((c[1]-a[1])*(v[:, 0]-c[0])+(a[0]-c[0])*(v[:, 1]-c[1]))/d
            out.append(np.c_[v, l*a[2]+mm*b[2]+(1-l-mm)*c[2]][tt])
    T = np.concatenate(out) if out else np.zeros((0, 3, 3))
    ar = (T[:, 1, 0]-T[:, 0, 0])*(T[:, 2, 1]-T[:, 0, 1])-(T[:, 2, 0]-T[:, 0, 0])*(T[:, 1, 1]-T[:, 0, 1]); n = ar < 0; T[n] = T[n][:, ::-1]
    return T[np.abs(ar) > 2e-3]
def polys_small(g): return [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon' and p.area > 1e-3]
def walls(T, p, base):
    segs = [];
    for q in polys(p):
        for r in [q.exterior, *q.interiors]:
            c = np.array(r.coords); segs += [(c[i], c[i+1]) for i in range(len(c)-1) if np.hypot(*(c[i+1]-c[i])) > .02]
    S = [LineString(s) for s in segs]; st = STRtree(S); bd = p.boundary; shapely.prepare(bd)
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); mid = E.mean(1)[:, :2]; L = np.hypot(*(E[:, 1]-E[:, 0])[:, :2].T)
    pt = lambda a: shapely.distance(bd, shapely.points(a[:, :2])) < 2e-3
    k = (L > .03); E, mid = E[k], mid[k]; k = pt(mid); E, mid = E[k], mid[k]; k = pt(E[:, 0]) & pt(E[:, 1]); E, mid = E[k], mid[k]
    if not len(E): return np.zeros((0, 4, 5))
    ix = st.nearest(shapely.points(mid)); Q = []
    for (a, b), s in zip(E, ix):
        s0, s1 = segs[s]; d = s1-s0; ln = np.hypot(*d); d = d/ln; ua = float((a[:2]-s0)@d); ub = float((b[:2]-s0)@d)
        Q.append([[a[0], a[1], base, ua, ln], [b[0], b[1], base, ub, ln], [b[0], b[1], base+b[2], ub, ln], [a[0], a[1], base+a[2], ua, ln]])
    return np.array(Q)
def keep(b): return True
if __name__ == '__main__':
    t0 = time.time(); out = []; bad = 0
    for n, b in enumerate(B):
        p = shapely.make_valid(b['p'].simplify(.12)); p = MultiPolygon(polys(p)) if len(polys(p)) != 1 else polys(p)[0]
        if p.is_empty: continue
        cs = A.get(b['id'], []); t = b['t']; est = None
        try: base, g = roofgrid(p, cs, t)
        except Exception as e: print('grid', b['id'], e); bad += 1; continue
        pu = bool(cs) or t.get('building') in ('university', 'dormitory') or t.get('operator') == 'Purdue University'
        rec = dict(id=b['id'], t=t, codes=cs, purdue=pu, area=p.area, base=base, c=list(p.representative_point().coords[0]), poly=p)
        if cs and cs[0] in CUSTOM: rec.update(T=None, W=None, h=49 if cs[0] == 'BELL' else 12, hsrc='custom'); out.append(rec); continue
        if g is None:
            o = next((HO[c] for c in cs if c in HO), None)
            try: lv = float(t.get('building:levels', 0))
            except ValueError: lv = 0
            try: th = float(t.get('height', '0').split()[0])
            except ValueError: th = 0
            hh = o['m'] if o else th or lv*3.4 or (4 if p.area < 60 else 6 if p.area < 400 else 8)
            rec['hsrc'] = 'estimated'; rec['hnote'] = o['src'] if o else ('OSM height' if th else 'OSM levels' if lv else 'estimate, no source found')
            if o and o.get('levels'): rec['levels'] = o['levels']
            P, F = flatmesh(p, hh); T = P[F]; ar = (T[:, 1, 0]-T[:, 0, 0])*(T[:, 2, 1]-T[:, 0, 1])-(T[:, 2, 0]-T[:, 0, 0])*(T[:, 1, 1]-T[:, 0, 1]); T[ar < 0] = T[ar < 0][:, ::-1]
        else:
            P, F = tinmesh(p, g, pu); T = clip(P, F, p); rec['hsrc'] = 'lidar'
        if not len(T): bad += 1; print('empty', b['id']); continue
        W = walls(T, p, base-1.2); W[:, 2:, 2] += 1.2; T = T.copy(); T[:, :, 2] += base
        a3 = np.abs((T[:, 1, 0]-T[:, 0, 0])*(T[:, 2, 1]-T[:, 0, 1])-(T[:, 2, 0]-T[:, 0, 0])*(T[:, 1, 1]-T[:, 0, 1])); zc = T[:, :, 2].mean(1)-base; o = np.argsort(zc); cw = np.cumsum(a3[o])/a3.sum()
        rec['h'] = float(zc[o][np.searchsorted(cw, .97).clip(0, len(o)-1)]); rec['eave'] = float(np.median(W[:, 2, 2])-base) if len(W) else rec['h']
        # wall coverage check: wall base length vs perimeter
        rec['wl'] = float(np.hypot(*(W[:, 1]-W[:, 0])[:, :2].T).sum()/p.length) if len(W) else 0
        rec.update(T=T.astype('f4'), W=W.astype('f4')); out.append(rec)
        if n % 800 == 0: print(n, round(time.time()-t0), 's', flush=True)
    pickle.dump(out, open(WORK+'/mesh.pkl', 'wb'))
    print(len(out), 'bad', bad, 'roof tris', sum(len(r['T']) for r in out if r['T'] is not None), 'wall quads', sum(len(r['W']) for r in out if r['W'] is not None), 'lidar', sum(r['hsrc'] == 'lidar' for r in out))
    w = [r for r in out if r['T'] is not None and not .97 < r['wl'] < 1.03]; print('wall gaps', len(w), [(r['id'], r['codes'], round(r['wl'], 2)) for r in w[:25]])
    for c in 'MATH HAWK YONG HOVD ELLT MACK PMU UNIV WALC STDM DUDL'.split():
        for r in out:
            if c in r['codes'] and r['T'] is not None: print(c, 'h %.1f eave %.1f roof %d walls %d' % (r['h'], r['eave'], len(r['T']), len(r['W'])), r['hsrc'])
