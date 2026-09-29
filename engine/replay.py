"""Event replay: the biggest observed heavy-rain days in the leave-one-season-out backtest, with IMD observed rain,
raw GFS, VARSHA corrected rain, heavy-rain probability and warnings, for lead days 1 and 3.
Every forecast shown was produced by models that never saw that season."""
import json, os
import numpy as np, pandas as pd
import common as C

OUT = os.path.join(C.DATA, "products", "replay")
os.makedirs(OUT, exist_ok=True)
L = C.land()
CELLS = np.argwhere(L)
pos = -np.ones((C.NLAT, C.NLON), int)
pos[CELLS[:, 0], CELLS[:, 1]] = np.arange(len(CELLS))
LEADS = [1, 3]
cases = {l: np.load(os.path.join(C.DATA, "models", f"cases_lead{l}.npz")) for l in LEADS if os.path.exists(os.path.join(C.DATA, "models", f"cases_lead{l}.npz"))}
if not cases:
    raise SystemExit("no backtest cases yet (run train.py)")
z = cases[min(cases)]
dates = z["date"]
heavy_cells = pd.Series((z["obs"] >= 64.5).astype(int)).groupby(dates).sum().sort_values(ascending=False)
top = [d for d in heavy_cells.index[:14]]
events = []
for d in top:
    d = np.datetime64(pd.Timestamp(d).date(), "D")
    ds = str(d)
    rec = {"date": ds, "heavy_cells": int(heavy_cells[d]), "regime": None, "leads": {}}
    for l, zz in cases.items():
        sel = zz["date"] == d
        if not sel.any(): continue
        ix = pos[zz["i"][sel], zz["j"][sel]]
        def grid(name):
            g = np.full(len(CELLS), np.nan, np.float32); g[ix] = zz[name][sel]; return [None if np.isnan(x) else round(float(x), 1) for x in g]
        o, raw, ml, warn, p1 = zz["obs"][sel], zz["raw"][sel], zz["ml"][sel], zz["warn"][sel], zz["p1"][sel]
        rec["regime"] = str(pd.Series(zz["regime"][sel]).mode()[0])
        rec["leads"][str(l)] = {
            "obs": grid("obs"), "raw": grid("raw"), "ml": grid("ml"), "qmr": grid("qmr"), "p_heavy": grid("p1"), "warn": grid("warn"),
            "scores": {"raw": C.cat(raw, o, 64.5), "warning": C.cat(warn, o, 64.5), "regime_qm": C.cat(zz["qmr"][sel], o, 64.5)},
        }
    json.dump(rec, open(os.path.join(OUT, f"{ds}.json"), "w"), separators=(",", ":"))
    s = rec["leads"].get("1", {}).get("scores", {})
    events.append({"date": ds, "heavy_cells": rec["heavy_cells"], "regime": rec["regime"],
                   "ets_raw": s.get("raw", {}).get("ETS"), "ets_varsha": s.get("warning", {}).get("ETS"),
                   "pod_raw": s.get("raw", {}).get("POD"), "pod_varsha": s.get("warning", {}).get("POD")})
json.dump({"cells": CELLS.tolist(), "events": sorted(events, key=lambda e: e["date"], reverse=True)},
          open(os.path.join(C.DATA, "products", "replay_index.json"), "w"), separators=(",", ":"))
print(f"{len(events)} replay events written")
