# Purdue Campus 3D

Interactive cartoon-style 3D model of Purdue's West Lafayette campus. Unofficial.

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
| Heights, trees | USGS LiDAR flown 2017, simplified to flat tiers, sloped roofs, a dome and a stadium bowl. Newer buildings are marked "estimated" |
| Roof colours | Typical colour of each roof in the State of Indiana 2023 aerial photo, snapped to a small palette |
| Roads, paths, lawns, courts, water | Drawn as flat shapes from OpenStreetMap |
| Street lamps | Decorative: spaced along roads and main paths, not surveyed |
| Wall colours | `pipeline/materials.json`. Each building's panel says whether it was checked against a photo, described in print, or assumed |
| Windows | Drawn procedurally; counts and positions are not real |

103 of the 343 listed buildings (mostly sheds, well houses and off-map sites) have no identifiable footprint: see `data/unmatched.md`.

## Fix a colour or a number
Roof type or shape: `pipeline/roofs.json`. Edit `pipeline/materials.json` (code: wall colour, trim colour, window style, note) or `pipeline/overrides.json` (footprint id to codes), then rebuild data:
```
python3 -m venv .venv && .venv/bin/pip install numpy "laspy[lazrs]" pyproj shapely pillow pypdf scipy mapbox_earcut pypdfium2
.venv/bin/python pipeline/fetch_vector.py     # OSM + building list
.venv/bin/python pipeline/ept_index.py && .venv/bin/python pipeline/lidar.py   # ~3 min
.venv/bin/python pipeline/imagery.py
.venv/bin/python pipeline/build.py && .venv/bin/python pipeline/ground.py && .venv/bin/python pipeline/export.py
```
Raw downloads are cached in `data/raw`; for a colour change only, `export.py` alone is enough (for a number, `build.py` then `export.py`).

Map data © OpenStreetMap contributors (ODbL). LiDAR: USGS 3DEP. Imagery: Indiana Geographic Information Office.
