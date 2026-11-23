"""Map-style ground: disjoint flat-colour polygons cut onto the terrain grid. Also places street lamps."""
import json, sys, io, contextlib, pickle, math
with contextlib.redirect_stdout(io.StringIO()):
    from osm import *
import shapely, mapbox_earcut
from shapely.geometry import LineString, box, Point, Polygon
from shapely.strtree import STRtree
from scipy.spatial import cKDTree
import osm
E2 = json.load(open(RAW+'/osm2.json'))['elements']; ALL = {(e['type'], e['id']): e for e in D+E2}; D = list(ALL.values())
R = pickle.load(open(WORK+'/mesh.pkl', 'rb')); BT = STRtree([r['poly'] for r in R]); BP = [r['poly'] for r in R]
NAMES = ['grass', 'lawn', 'fairway', 'wood', 'farm', 'built', 'sand', 'water', 'parking', 'kerb', 'path', 'plaza', 'road', 'runway', 'pitch', 'track', 'court', 'rail', 'line', 'pool']
I = {n: i for i, n in enumerate(NAMES)}; A = {n: [] for n in NAMES}; lampsrc = []
WD = dict(motorway=11, trunk=10, primary=10, secondary=9.5, tertiary=9, residential=7.5, unclassified=7, service=4.6, primary_link=6, secondary_link=6, tertiary_link=6, raceway=6, track=3, cycleway=2.8, footway=2.2, path=1.9, steps=2.6, pedestrian=5)
WALKS = ('cycleway', 'footway', 'path', 'steps', 'pedestrian'); lines = []
for e in D:
    t = e.get('tags', {}); g = e.get('geometry')
    if e['type'] == 'node' or 'building' in t or t.get('tunnel') == 'yes' or t.get('indoor') == 'yes': continue
    hw = t.get('highway'); ae = t.get('aeroway')
    if e['type'] == 'way' and g and len(g) > 1 and ((hw in WD and t.get('area') != 'yes') or t.get('railway') in ('rail', 'spur') or ae in ('runway', 'taxiway') or t.get('golf') == 'cartpath'):
        closed = ae and g[0] == g[-1]
        if not closed:
            L = LineString(pts(g)); 
            if hw in WALKS: A['path'].append(L.buffer(WD[hw]/2, cap_style=1, quad_segs=2)); lampsrc.append((L, 'walk', hw))
            elif hw:
                w = WD[hw]
                try: w = max(w, min(22, float(t.get('lanes', 0))*3.4))
                except ValueError: pass
                A['road'].append(L.buffer(w/2, quad_segs=3)); lampsrc.append((L, hw, w))
                if hw not in ('service', 'track', 'raceway'): A['kerb'].append(L.buffer(w/2+(1.5 if hw not in ('motorway', 'trunk') else .8), quad_segs=3))
                if hw in ('primary', 'secondary', 'tertiary', 'trunk') and L.length > 14: lines.append(L)
            elif ae: A['runway'].append(L.buffer({'runway': 23, 'taxiway': 8}[ae], cap_style=2 if ae == 'runway' else 1)); lines += [L] if ae == 'runway' else []
            elif t.get('golf'): A['path'].append(L.buffer(1.2))
            else: A['rail'].append(L.buffer(1.7, cap_style=2))
            continue
    cl = None; lu, le, na, go, am = (t.get(k) for k in ('landuse', 'leisure', 'natural', 'golf', 'amenity'))
    if na == 'water' or t.get('waterway') == 'riverbank' or go in ('water_hazard', 'lateral_water_hazard'): cl = 'water'
    elif le == 'swimming_pool': cl = 'pool'
    elif go in ('fairway', 'green', 'tee'): cl = 'fairway'
    elif go == 'bunker' or na in ('sand', 'beach') or t.get('sport') == 'beachvolleyball': cl = 'sand'
    elif le == 'track': cl = 'track'
    elif le == 'pitch': cl = 'court' if t.get('sport') in ('tennis', 'basketball', 'volleyball') else 'pitch'
    elif am == 'parking' and t.get('parking') not in ('underground', 'multi-storey'): cl = 'parking'
    elif hw in ('pedestrian', 'footway', 'service') or t.get('place') == 'square': cl = 'plaza'
    elif ae in ('apron', 'runway', 'taxiway'): cl = 'runway'
    elif na in ('wood', 'scrub') or lu == 'forest': cl = 'wood'
    elif lu in ('farmland', 'meadow', 'allotments'): cl = 'farm'
    elif lu in ('retail', 'commercial', 'industrial', 'construction', 'brownfield'): cl = 'built'
    elif lu in ('grass', 'recreation_ground', 'cemetery') or le in ('park', 'garden', 'golf_course', 'nature_reserve', 'dog_park'): cl = 'lawn'
    if cl:
        q = poly(e)
        if q is not None and cl == 'track' and q.area > 25000: A['path'].append(q.boundary.buffer(1.5)); continue   # cross-country course, not a stadium track
        if q is not None: A[cl].append(q)
EXT = box(X0, Y0, X1, Y1); U = {n: shapely.intersection(shapely.unary_union(v).buffer(0), EXT) if v else Polygon() for n, v in A.items()}
U['track'] = U['track'].difference(U['pitch']) if not U['track'].is_empty else U['track']
for n in ('road', 'kerb', 'path', 'parking'): U[n] = U[n].simplify(.15)
# dashed centre lines
ml = shapely.line_merge(shapely.union_all(lines)); dash = []
for L in getattr(ml, 'geoms', [ml]):
    wide = False
    for s in np.arange(6, L.length-6, 11): dash.append(shapely.ops.substring(L, s, s+5).buffer(.17, cap_style=2))
junction = shapely.unary_union([Point(L.coords[k]).buffer(8) for L in getattr(ml, 'geoms', [ml]) for k in (0, -1)])
U['line'] = shapely.unary_union(dash).difference(junction).intersection(shapely.unary_union([U['road'], U['runway']]))
PO = lambda g: shapely.union_all([q for q in (g.geoms if hasattr(g, 'geoms') else [g]) if q.geom_type == 'Polygon'])
U = {n: shapely.set_precision(PO(g), .05) for n, g in U.items()}
ORDER = ['lawn', 'built', 'farm', 'wood', 'fairway', 'sand', 'water', 'pool', 'parking', 'kerb', 'plaza', 'path', 'rail', 'runway', 'track', 'pitch', 'court', 'road', 'line']   # later wins
# water stays above lawns but under roads (bridges)
V, C = [], []
def emit(g, c):
    for q in (g.geoms if hasattr(g, 'geoms') else [g]):
        if q.geom_type != 'Polygon' or q.area < .02: continue
        rs = [np.array(q.exterior.coords)[:-1]]+[np.array(r.coords)[:-1] for r in q.interiors]; v = np.vstack(rs)
        t = mapbox_earcut.triangulate_float64(v, np.cumsum([len(r) for r in rs]).astype('u4')).reshape(-1, 3)
        if not len(t): continue
        T = v[t]; ar = (T[:, 1, 0]-T[:, 0, 0])*(T[:, 2, 1]-T[:, 0, 1])-(T[:, 2, 0]-T[:, 0, 0])*(T[:, 1, 1]-T[:, 0, 1]); T[ar < 0] = T[ar < 0][:, ::-1]; V.append(T); C.append(np.full(len(T), c))
ST = 20
for tx in range(X0, X1, TILE):
    for ty in range(Y0, Y1, TILE):
        cell = box(tx, ty, tx+TILE, ty+TILE); rest = cell; parts = []
        for n in reversed(ORDER):
            g = PO(shapely.intersection(PO(shapely.intersection(U[n], cell, grid_size=.05)), rest, grid_size=.05))
            if g.is_empty: continue
            parts.append((I[n], g)); rest = PO(shapely.difference(rest, g, grid_size=.05))
        parts.append((0, rest))
        xs = np.arange(tx, tx+TILE, ST); ys = np.arange(ty, ty+TILE, ST); gx, gy = [a.ravel() for a in np.meshgrid(xs, ys)]
        p = lambda a, b: np.c_[gx+a*ST, gy+b*ST]
        tri = np.concatenate([np.stack([p(0, 0), p(1, 0), p(1, 1), p(0, 0)], 1), np.stack([p(0, 0), p(1, 1), p(0, 1), p(0, 0)], 1)]).astype(float); G = shapely.polygons(tri)
        for c, g in parts:
            shapely.prepare(g); hit = shapely.intersects(g, G); full = shapely.contains(g, G)
            if full.any(): V.append(tri[full][:, :3]); C.append(np.full(full.sum(), c))
            for k in np.where(hit & ~full)[0]: emit(shapely.intersection(g, G[k]), c)
V = np.concatenate(V); C = np.concatenate(C)
print('ground tris', len(V), {NAMES[i]: int((C == i).sum()) for i in range(len(NAMES))})
# ---- street lamps ----------------------------------------------------------------
pc = cKDTree(np.array([r['c'] for r in R if r['codes']])); P = []
for L, k, w in lampsrc:
    if k == 'walk':
        if w not in ('footway', 'pedestrian', 'cycleway') or L.length < 40: continue
        step, off, near = 62, 2.0, 70
    elif k == 'service': step, off, near = 40, w/2+1, 130
    elif k in ('track', 'raceway'): continue
    elif k in ('residential', 'unclassified'): step, off, near = 34, w/2+1, 900
    else: step, off, near = 30, w/2+1, 2600
    side = 1
    for s in np.arange(step/2, L.length, step):
        a = np.array(L.interpolate(s).coords[0]); b = np.array(L.interpolate(min(s+1, L.length)).coords[0])-np.array(L.interpolate(max(s-1, 0)).coords[0]); b = b/(np.hypot(*b)+1e-9); side = -side; q = a+side*off*np.array([-b[1], b[0]])
        if not (X0+5 < q[0] < X1-5 and Y0+5 < q[1] < Y1-5) or pc.query(q)[0] > near: continue
        P.append((0 if k != 'walk' else 1, *q, math.atan2(-side*b[0], side*b[1])))   # angle pointing back to the road
P.sort(key=lambda p: p[0]); roads = U['road'].buffer(.3); shapely.prepare(roads); xy = np.array([p[1:3] for p in P]); bad = shapely.contains_xy(roads, xy[:, 0], xy[:, 1]); bad |= np.array([any(BP[i].buffer(.8).contains(Point(q)) for i in BT.query(Point(q).buffer(1))) for q in xy]); bad |= shapely.contains_xy(U['water'], xy[:, 0], xy[:, 1])
kept = []; grid = {}
for i, p in enumerate(P):
    if bad[i]: continue
    mind = 17 if p[0] == 0 else 38; c = (int(p[1]//40), int(p[2]//40))
    if any(math.hypot(p[1]-o[1], p[2]-o[2]) < mind for a in (-1, 0, 1) for b in (-1, 0, 1) for o in grid.get((c[0]+a, c[1]+b), [])): continue
    grid.setdefault(c, []).append(p); kept.append(p)
print('lamps', len(kept), 'road', sum(p[0] == 0 for p in kept))
pickle.dump(dict(V=V, C=C, names=NAMES, lamps=np.array(kept), water=U['water'], clear=shapely.unary_union([U[n] for n in ('road', 'parking', 'runway', 'pitch', 'court', 'track', 'water', 'plaza', 'rail', 'fairway', 'sand')])), open(WORK+'/ground.pkl', 'wb'))
