import json, os, subprocess, urllib.request, urllib.parse
from common import *
def get(url, path, data=None):
    p = os.path.join(RAW, path)
    if os.path.exists(p): return p
    b = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=240).read()
    open(p, 'wb').write(b); print(path, len(b)); return p
bb = f'{S},{W},{N},{E}'
q = f'''[out:json][timeout:200];(way["building"]({bb});relation["building"]({bb});way["building:part"]({bb});relation["building:part"]({bb});
way["highway"]({bb});way["leisure"]({bb});relation["leisure"]({bb});way["natural"]({bb});relation["natural"]({bb});way["waterway"]({bb});
node["natural"="tree"]({bb});way["aeroway"]({bb});way["amenity"~"fountain|parking"]({bb});node["amenity"="fountain"]({bb});
nwr["tourism"="artwork"]({bb});nwr["man_made"]({bb});way["landuse"]({bb}););out geom;'''
get('https://overpass-api.de/api/interpreter', 'osm.json', urllib.parse.urlencode({'data': q}).encode())
get('https://web.archive.org/web/20260216192211id_/https://www.purdue.edu/auxiliary-services/documents/wl-building-list.pdf', 'wl-building-list.pdf')
q2 = f'''[out:json][timeout:200];(way["railway"~"rail|spur"]({bb});relation["highway"="pedestrian"]({bb});way["place"="square"]({bb});relation["amenity"="parking"]({bb});relation["landuse"]({bb}););out geom;'''
get('https://overpass-api.de/api/interpreter', 'osm2.json', urllib.parse.urlencode({'data': q2}).encode())
