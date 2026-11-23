"""Terrain + height-above-ground grids, and per-building LiDAR coverage."""
import sys, io, contextlib
from scipy import ndimage as nd
from common import *
def load():
    top = np.load(WORK+'/top.npy', mmap_mode='r'); solid = np.load(WORK+'/solid.npy', mmap_mode='r')
    d = np.load(WORK+'/dtm_raw.npy'); m = ~np.isfinite(d)
    i = nd.distance_transform_edt(m, return_distances=False, return_indices=True); d = d[tuple(i)]
    d = nd.gaussian_filter(nd.median_filter(d, 5), 1.5)
    return top, solid, d
def sample(grid, res, x, y):
    c = [(np.asarray(y)-Y0)/res-.5, (np.asarray(x)-X0)/res-.5]
    return nd.map_coordinates(grid, c, order=1, mode='nearest')
