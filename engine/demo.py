"""Demo data for the "See the proof" page — all from real IMD grids and the leave-one-season-out backtest.

  products/demo/regime_index.json          every JJAS day 2021–2026: date, core-zone anomaly, regime
  products/demo/regime/<date>.json         that day's IMD rainfall on the grid, as IMD category codes (one char per cell)
  products/demo/district/<id>.json         per district, per day (day-1 forecasts): IMD observed max, raw max, VARSHA warning / P(heavy)
  products/demo/summary.json               all-district totals of heavy-rain days warned, per season, and the strongest districts

  python demo.py --summary   rebuilds only summary.json from the district files
"""
import glob, json, os, sys
import numpy as np, pandas as pd
import common as C

OUT = os.path.join(C.DATA, "products", "demo")
os.makedirs(os.path.join(OUT, "regime"), exist_ok=True)
os.makedirs(os.path.join(OUT, "district"), exist_ok=True)
L = C.land()
CELLS = np.argwhere(L)
EDGES = [2.5, 15.6, 35.6, 64.5, 115.6, 204.5]  # IMD categories -> codes 0..6


def codes(grid):
    v = grid[L]
    c = np.digitize(np.where(v > -998, v, 0), EDGES)
    return "".join(map(str, c))


SUMMARY_ONLY = "--summary" in sys.argv
if SUMMARY_ONLY: L = None

if not SUMMARY_ONLY:
    # ---- 1. regime timeline + daily IMD maps
    N = C.normals()
    obs = C.observations()
    anom, LS = C.regime_series(obs, N)
    index = []
    for t in sorted(obs):
        if not (6 <= t.month <= 9): continue
        a = anom.get(t)
        rec = {"date": t.strftime("%Y-%m-%d"), "anom": None if a is None or np.isnan(a) else round(float(a), 2), "regime": LS.get(t, "Normal")}
        index.append(rec)
        json.dump({**rec, "rain": codes(obs[t])}, open(os.path.join(OUT, "regime", f"{rec['date']}.json"), "w"), separators=(",", ":"))
    core = {"lat0": 18, "lat1": 28, "lon0": 65, "lon1": 88}
    json.dump({"cells": CELLS.tolist(), "core": core, "days": index}, open(os.path.join(OUT, "regime_index.json"), "w"), separators=(",", ":"))
    print(f"regime demo: {len(index)} days")

    # ---- 2. district track record (day-1 forecasts, leave-one-season-out)
    z = np.load(os.path.join(C.DATA, "models", "cases_lead1.npz"))
    cd = np.load(os.path.join(C.DATA, "boundaries", "cell_district.npy"))
    dist = cd[z["i"], z["j"]]
    ok = dist >= 0
    df = pd.DataFrame({"d": dist[ok], "date": z["date"][ok], "obs": z["obs"][ok], "raw": z["raw"][ok], "warn": z["warn"][ok], "p1": z["p1"][ok]})
    g = df.groupby(["d", "date"]).agg(obs=("obs", "max"), raw=("raw", "max"), warn=("warn", "max"), p1=("p1", "max")).reset_index()
    for d, sub in g.groupby("d"):
        sub = sub.sort_values("date")
        json.dump({"id": int(d), "dates": [str(x)[:10] for x in sub.date.values], "obs": np.round(sub.obs.values, 1).tolist(),
                   "raw": np.round(sub.raw.values, 1).tolist(), "warn": (sub.warn.values >= 100).astype(int).tolist(), "p": np.round(sub.p1.values, 3).tolist()},
                  open(os.path.join(OUT, "district", f"{int(d)}.json"), "w"), separators=(",", ":"))
    print(f"district demo: {g.d.nunique()} districts")


# ---- 3. all-district totals (a heavy-rain day = IMD recorded >= 64.5 mm somewhere in the district)
tot = {"districts": 0, "heavy": 0, "varsha": 0, "raw": 0, "varsha_false": 0, "raw_false": 0}
season, best = {}, []
for f in glob.glob(os.path.join(OUT, "district", "*.json")):
    r = json.load(open(f))
    per = {"heavy": 0, "varsha": 0, "raw": 0}
    for d, o, w, x in zip(r["dates"], r["obs"], r["warn"], r["raw"]):
        s_ = season.setdefault(d[:4], {"heavy": 0, "varsha": 0, "raw": 0, "varsha_false": 0, "raw_false": 0})
        h, rw = o >= 64.5, x >= 64.5
        for t in (tot, s_):
            t["heavy"] += h; t["varsha"] += bool(h and w); t["raw"] += bool(h and rw)
            t["varsha_false"] += bool(w and not h); t["raw_false"] += bool(rw and not h)
        if d.startswith("2024"):
            per["heavy"] += h; per["varsha"] += bool(h and w); per["raw"] += bool(h and rw)
    tot["districts"] += any(o >= 64.5 for o in r["obs"])
    best.append({"id": r["id"], **per})
best.sort(key=lambda b: b["raw"] - b["varsha"])
json.dump({**tot, "seasons": dict(sorted(season.items())), "best_2024": best[:6]}, open(os.path.join(OUT, "summary.json"), "w"))
print(f"summary: {tot}")
