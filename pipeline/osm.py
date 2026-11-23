import json
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import polygonize, unary_union, linemerge
from shapely.geometry import LineString
from common import *
D = json.load(open(RAW+'/osm.json'))['elements']
def pts(g): 
    x, y = ll([p['lon'] for p in g], [p['lat'] for p in g]); return list(zip(x.tolist(), y.tolist()))
def rings(mem, role):
    ls = [LineString(pts([q for q in m['geometry'] if q])) for m in mem if m.get('role') == role and m.get('geometry') and len(m['geometry']) > 1]
    return list(polygonize(unary_union(ls))) if ls else []
def poly(e):
    """Polygon for a closed way or multipolygon relation, else None"""
    try:
        if e['type'] == 'way':
            g = e.get('geometry') or []
            if len(g) < 4 or g[0] != g[-1]: return None
            p = Polygon(pts(g))
        else:
            o = rings(e['members'], 'outer')
            if not o: return None
            p = unary_union(o); i = rings(e['members'], 'inner')
            if i: p = p.difference(unary_union(i))
        p = p.buffer(0)
        return p if p.area > 4 else None
    except Exception as ex:
        print('bad geom', e['type'], e['id'], ex); return None
def inside(p):
    c = p.centroid; return X0+20 < c.x < X1-20 and Y0+20 < c.y < Y1-20
def buildings():
    out = []
    for e in D:
        t = e.get('tags', {})
        if 'building' in t and t['building'] != 'no' and e['type'] != 'node':
            p = poly(e)
            if p and inside(p): out.append(dict(id=f"{e['type'][0]}{e['id']}", t=t, p=p))
    # drop relation/way duplicates and outlines fully inside a bigger one with same area
    return out
