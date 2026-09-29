"""Map IMD 0.25° grid cells to Survey of India districts and write a simplified boundary file for the dashboard.
Outputs (data/boundaries/):
  cell_district.npy   int16 (129, 135): district index per IMD grid cell (-1 = none)
  districts.json      [{id, name, state, lgd, lat, lon, cells:[[i,j],...]}]
  districts_simplified.geojson  boundaries simplified to ~0.02° for web display
"""
import json, os
import numpy as np
from shapely.geometry import Point, shape, mapping
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "..", "..", "data", "boundaries")
NLAT, NLON, LAT0, LON0, STEP = 129, 135, 6.5, 66.5, 0.25

gj = json.load(open(os.path.join(B, "SOI_Districts.geojson"), encoding="utf-8"))
geoms = [shape(f["geometry"]).buffer(0) for f in gj["features"]]
props = [f["properties"] for f in gj["features"]]
tree = STRtree(geoms)

land = np.fromfile(os.path.join(HERE, "..", "..", "data", "imd_yearly", "2020.grd"), dtype="<f4").reshape(-1, NLAT, NLON)[200] > -998
cell = np.full((NLAT, NLON), -1, np.int16)
for i in range(NLAT):
    for j in range(NLON):
        p = Point(LON0 + j * STEP, LAT0 + i * STEP)
        for k in tree.query(p):
            if geoms[k].contains(p):
                cell[i, j] = k
                break

out = []
for k, (g, pr) in enumerate(zip(geoms, props)):
    rp = g.representative_point()
    cells = np.argwhere(cell == k).tolist()
    if not cells:  # district smaller than a grid cell: use the nearest land cell
        i = int(round((rp.y - LAT0) / STEP)); j = int(round((rp.x - LON0) / STEP))
        cand = np.argwhere(land)
        d = (cand[:, 0] - i) ** 2 + (cand[:, 1] - j) ** 2
        cells = [cand[int(np.argmin(d))].tolist()]
    out.append(dict(id=k, name=pr["District_C"].title(), state=pr["STATE_C"].title(), lgd=pr.get("DISTRICT_L"),
                    lat=round(rp.y, 3), lon=round(rp.x, 3), cells=cells))
np.save(os.path.join(B, "cell_district.npy"), cell)
json.dump(out, open(os.path.join(B, "districts.json"), "w", encoding="utf-8"))
simp = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"id": k, "name": o["name"], "state": o["state"]},
     "geometry": mapping(g.simplify(0.02, preserve_topology=True))} for k, (g, o) in enumerate(zip(geoms, out))]}
json.dump(simp, open(os.path.join(B, "districts_simplified.geojson"), "w", encoding="utf-8"))
print(len(out), "districts;", int((cell >= 0).sum()), "cells assigned;", sum(len(o["cells"]) == 1 for o in out), "single-cell districts")
print("simplified geojson MB:", round(os.path.getsize(os.path.join(B, "districts_simplified.geojson")) / 1e6, 1))
