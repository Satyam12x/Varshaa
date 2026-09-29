"""VARSHA live forecast: regime identification -> regime-specific correction (behind the do-no-harm gate) ->
heavy-rain probabilities -> IMD-coloured warnings -> district product. Writes data/products/<issue>.json and latest.json.

Usage: python forecast.py [ISSUE_DATE]   (default: latest available GFS run)
"""
import json, os, pickle, sys
import numpy as np, pandas as pd
import common as C
import ingest

PROD = os.path.join(C.DATA, "products")
os.makedirs(PROD, exist_ok=True)
LEVELS = ["green", "yellow", "orange", "red"]


def regime_now(issue, N):
    """Large-scale regime from the latest IMD days before issue (IMD active/break criterion) + active depressions."""
    days = pd.date_range(issue - pd.Timedelta(days=15), issue - pd.Timedelta(days=1))
    obs = {d: g for d in days if (g := C.imd_rt(d, download=True)) is not None}
    if not obs:
        return None, np.nan, "Normal", []
    anom = pd.Series({d: C.core_anomaly(d, g, N) for d, g in obs.items()}).reindex(days)
    ls = C.causal_spells(anom.where(anom.index.month.isin([6, 7, 8, 9])))
    known = anom.last_valid_index()
    return known, float(anom[known]), ls[known] if known in ls.index else "Normal", [
        {"date": d.strftime("%Y-%m-%d"), "anom": None if np.isnan(a) else round(float(a), 2), "regime": ls.get(d, "Normal")} for d, a in anom.items()]


def level(p1, p2, warn):
    """Public warning level, always consistent with the stated chance:
    1 = watch (heavy rain possible: P(heavy) >= 15%, or the ETS-tuned early signal fires),
    2 = alert (heavy rain likely: P(heavy) >= 35%), 3 = warning (very heavy rain likely: P(very heavy) >= 35%)."""
    lv = np.zeros(p1.shape, np.int8)
    lv[(p1 >= 0.15) | (warn >= 100)] = 1
    lv[p1 >= 0.35] = 2
    lv[p2 >= 0.35] = 3
    return lv


def run(issue=None):
    issue = pd.Timestamp(issue) if issue else ingest.latest_gfs()
    if issue is None or C.gfs(issue) is None:
        raise SystemExit("no GFS run available")
    N, S, L = C.normals(), C.settings(), C.land()
    known, anom, ls, recent = regime_now(issue, N)
    dep, systems = C.depression(issue)
    g = C.gfs(issue)
    cd = np.load(os.path.join(C.DATA, "boundaries", "cell_district.npy"))
    D = C.districts()
    cells = np.argwhere(L)
    reg_cell = np.where(dep, "Depression", ls)
    out = {"issue": issue.strftime("%Y-%m-%d"), "generated": pd.Timestamp.utcnow().isoformat(),
           "source": {"nwp": "NOAA GFS 00 UTC (NOAA archive, AWS Open Data)", "truth": "IMD 0.25° gridded rainfall", "tracks": "IMD RSMC New Delhi best track"},
           "regime": {"large_scale": ls, "anomaly": None if np.isnan(anom) else round(anom, 2), "based_on": known.strftime("%Y-%m-%d") if known is not None else None,
                      "recent": recent, "depressions": [{"time": str(r.time), "lat": r.lat, "lon": r.lon, "grade": r.grade} for r in systems.itertuples()],
                      "depression_cells": int((dep & L).sum())},
           "season_note": None if 6 <= issue.month <= 9 else "Models are trained on June–September monsoon seasons; outside the monsoon the correction is extrapolated and the gate favours raw NWP.",
           "cells": cells.tolist(), "cell_district": cd[L].astype(int).tolist(), "cell_setting": S[L].astype(int).tolist(),
           "cell_depression": dep[L].astype(int).tolist(), "leads": []}
    for lead in C.LEADS:
        mf = os.path.join(C.DATA, "models", f"lead{lead}.pkl")
        vf = os.path.join(C.DATA, "models", f"verification_lead{lead}.json")
        if not os.path.exists(mf): continue
        mod = pickle.load(open(mf, "rb")); gate = json.load(open(vf))["gate"]
        target = issue + pd.Timedelta(days=lead)
        F = C.features(g[lead - 1], target, anom, ls, dep, N, S)
        X = np.stack([F[k][L] for k in C.FEATURES], 1).astype(np.float32)
        raw = X[:, 0]
        ml = np.maximum(mod["reg"].predict(X), 0) ** 2
        p1, p2 = mod["c1"].predict_proba(X)[:, 1], mod["c2"].predict_proba(X)[:, 1]
        warn = np.where(p2 >= mod["t2"], 150.0, np.where(p1 >= mod["t1"], 100.0, 0.0))
        rc, sc = reg_cell[L], S[L]
        qmr = np.empty(len(raw), np.float32)
        keys = np.char.add(np.char.add(rc.astype(str), "|"), sc.astype(str))
        for k in np.unique(keys):
            i = keys == k
            tab = mod["qm"].get(k) or mod["qm"].get(k.split("|")[0]) or mod["qm"]["GLOBAL"]
            qmr[i] = C.qm_apply(tab, raw[i])
        amount, used_amount, used_warn = np.empty(len(raw), np.float32), [], []
        warn_final = np.empty(len(raw), np.float32)
        for k in np.unique(keys):
            i = keys == k
            gk = gate.get(k, {"amount": "RAW", "warning": "RAW"})
            amount[i] = {"RAW": raw, "QM_REGIME": qmr, "ML": ml}[gk["amount"]][i]
            warn_final[i] = {"RAW": raw, "QM_REGIME": qmr, "WARN": warn}[gk["warning"]][i]
            used_amount.append({"key": k, "cells": int(i.sum()), "amount": gk["amount"], "warning": gk["warning"]})
        # warnings: probabilities always shown; categorical level uses the gated warning product
        lv = level(p1, p2, np.where(warn_final >= 115.6, 150, np.where(warn_final >= 64.5, 100, 0)))
        # district aggregation
        dist_rows = []
        dcell = cd[L]
        for d in D:
            idx = np.array([np.where((cells[:, 0] == a) & (cells[:, 1] == b))[0][0] for a, b in d["cells"] if L[a, b]], int)
            if len(idx) == 0: continue
            dist_rows.append({"id": d["id"], "mean": round(float(amount[idx].mean()), 1), "max": round(float(amount[idx].max()), 1),
                              "raw_mean": round(float(raw[idx].mean()), 1), "p_heavy": round(float(p1[idx].max()), 3),
                              "p_very_heavy": round(float(p2[idx].max()), 3), "level": LEVELS[int(lv[idx].max())]})
        out["leads"].append({"lead": lead, "valid": target.strftime("%Y-%m-%d"),
                             "raw": np.round(raw, 1).tolist(), "corrected": np.round(amount, 1).tolist(),
                             "p_heavy": np.round(p1, 3).tolist(), "p_very_heavy": np.round(p2, 3).tolist(), "level": lv.tolist(),
                             "gate": used_amount, "districts": dist_rows,
                             "thresholds": {"heavy_prob": mod["t1"], "very_heavy_prob": mod["t2"]}})
    f = os.path.join(PROD, f"{out['issue']}.json")
    json.dump(out, open(f, "w"), separators=(",", ":"))
    json.dump(out, open(os.path.join(PROD, "latest.json"), "w"), separators=(",", ":"))
    print(f"wrote {f}: regime {ls} (anomaly {anom:.2f} on {known.date() if known is not None else '-'}), "
          f"{len(systems)} depression fixes, {len(out['leads'])} lead days", flush=True)
    return out


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
