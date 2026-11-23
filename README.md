# Purdue Campus 3D

Interactive 3D model of Purdue's West Lafayette campus. Unofficial.

## Run
```
npm install        # first time only
npm run dev        # then open the printed address
```
For hosting: `npm run build`, then upload `dist/` to any static host (GitHub Pages, Vercel, Netlify). All model data ships in `public/data`, so nothing else is needed and the app makes no outside requests.

## Use
- Drag to move, right-drag to rotate, scroll to zoom. Click a building for its number; double-click to fly to it.
- Press `/` to search by number (1154), code (POTR) or name. Links like `#POTR` open straight to a building.
- **Walk** drops you to street level.

## What is measured and what is assumed
| Thing | Source |
|---|---|
| Number, code, name | Purdue West Lafayette building list, March 2025 (archived copy) |
| Which footprint is which | OpenStreetMap names, plus label positions on Purdue's July 2025 campus map PDF |
| Heights, roof shapes, trees | USGS LiDAR flown 2017. Newer buildings are marked "estimated" |
| Roof and ground colours | State of Indiana aerial photo, 2023. Lawns are tinted green because the photo is leaf-off |
| Wall colours | `pipeline/materials.json`. Each building's panel says whether it was checked against a photo, described in print, or assumed |
| Windows | Drawn procedurally; counts and positions are not real |

103 of the 343 listed buildings (mostly sheds, well houses and off-map sites) have no identifiable footprint: see `data/unmatched.md`.

## Fix a colour or a number
Edit `pipeline/materials.json` (code: wall colour, trim colour, window style, note) or `pipeline/overrides.json` (footprint id to codes), then rebuild data:
```
python3 -m venv .venv && .venv/bin/pip install numpy "laspy[lazrs]" pyproj shapely pillow pypdf scipy mapbox_earcut pydelatin pypdfium2
.venv/bin/python pipeline/fetch_vector.py     # OSM + building list
.venv/bin/python pipeline/ept_index.py && .venv/bin/python pipeline/lidar.py   # ~3 min
.venv/bin/python pipeline/imagery.py
.venv/bin/python pipeline/build.py && .venv/bin/python pipeline/lean.py && .venv/bin/python pipeline/export.py && .venv/bin/python pipeline/textures.py
```
Raw downloads are cached in `data/raw`; for a colour change only, `export.py` alone is enough (for a number, `build.py` then `export.py`).

Map data © OpenStreetMap contributors (ODbL). LiDAR: USGS 3DEP. Imagery: Indiana Geographic Information Office.
