"""Shared constants. Local frame: UTM 16N metres minus ORIGIN; x=east, y=north."""
import os
import numpy as np
from pyproj import Transformer
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
WORK = os.path.join(ROOT, 'data', 'work')
OUT = os.path.join(ROOT, 'public', 'data')
for d in (RAW, WORK, OUT): os.makedirs(d, exist_ok=True)
UA = {'User-Agent': 'campus-map-prototype/0.1'}
S, W, N, E = 40.405, -86.960, 40.450, -86.895
_f = Transformer.from_crs(4326, 26916, always_xy=True)
_m = Transformer.from_crs(3857, 26916, always_xy=True)
_b = Transformer.from_crs(26916, 4326, always_xy=True)
OX, OY = 506500.0, 4475000.0           # origin in UTM 16N
X0, X1, Y0, Y1 = -3000, 2500, -2500, 2500  # model extent, metres
TILE = 500
def ll(lon, lat):
    x, y = _f.transform(lon, lat); return np.asarray(x) - OX, np.asarray(y) - OY
def merc(x, y):
    a, b = _m.transform(x, y); return np.asarray(a) - OX, np.asarray(b) - OY
def lonlat(x, y): return _b.transform(np.asarray(x) + OX, np.asarray(y) + OY)
