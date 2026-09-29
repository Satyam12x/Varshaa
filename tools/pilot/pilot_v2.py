"""PS 26080 pilot v2 — full IMD 0.25° grid, six monsoon seasons, leave-one-season-out.

Raw NWP  : NOAA GFS 00 UTC (NOAA's official archive), lead days 1-5, rain on the IMD day (24 h ending 03 UTC)
Truth    : IMD 0.25° gridded rainfall (yearly archive 2021-2025; real-time grids 2026)
Normals  : IMD 0.25° gridded rainfall 1991-2020 (per-cell daily climatology + core-zone statistics)
Regimes  : large-scale  - IMD core-zone active/break criterion (persistence from the last observed day at issue)
                         - depression: an IMD RSMC best-track system within 6° of the cell at issue time
           local       - coastal (within ~50 km of the sea, from IMD's own land mask)
                         - orographic (Western Ghats windward belt, north-east hills, Himalayan belt)
Methods  : RAW, QM_GLOBAL, QM_REGIME, ML (amount), PROB (heavy-rain probability) and WARN (probability -> warning
           with a threshold chosen on the training seasons only)
Metrics  : RMSE, POD, FAR, CSI, ETS at 64.5 and 115.6 mm, FSS at 64.5 mm (25/75/125/225 km), Brier.
"""
import glob, json, os, sys
import numpy as np, pandas as pd
from scipy.ndimage import maximum_filter, uniform_filter, binary_dilation
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
PS81 = os.path.join(HERE, "..", "..", "..", "PS 81", "backend", "data", "imd", "rain")
NLAT, NLON, LAT0, LON0, STEP = 129, 135, 6.5, 66.5, 0.25
LAT = LAT0 + STEP * np.arange(NLAT); LON = LON0 + STEP * np.arange(NLON)
LAT2, LON2 = np.meshgrid(LAT, LON, indexing="ij")
SEASONS = [2021, 2022, 2023, 2024, 2025, 2026]
LEADS = [int(x) for x in (sys.argv[1:] or ["1", "3"])]
rng = np.random.default_rng(0)


def yearly(y):
    a = np.fromfile(os.path.join(DATA, "imd_yearly", f"{y}.grd"), dtype="<f4")
    nd = a.size // (NLAT * NLON)
    return pd.date_range(f"{y}-01-01", periods=nd), a.reshape(nd, NLAT, NLON)


# ---------------------------------------------------------------- truth + land mask
def truth():
    obs = {}
    for y in SEASONS[:-1]:
        d, a = yearly(y)
        for t, g in zip(d, a):
            if 6 <= t.month <= 9: obs[t] = g
    for f in sorted(glob.glob(os.path.join(PS81, "2026-*.grd"))):
        t = pd.Timestamp(os.path.basename(f)[:10])
        if 6 <= t.month <= 9 and os.path.getsize(f) == NLAT * NLON * 4:
            obs[t] = np.fromfile(f, dtype="<f4").reshape(NLAT, NLON)
    return obs


OBS = truth()
LAND = np.all(np.stack([g > -998 for g in list(OBS.values())[:50]]), axis=0)
core = LAND & (LAT2 >= 18) & (LAT2 <= 28) & (LON2 >= 65) & (LON2 <= 88)

# ---------------------------------------------------------------- normals (1991-2020): per-cell daily + core-zone
cz, cell = {}, {}
for y in range(1991, 2021):
    d, a = yearly(y)
    for t, g in zip(d, a):
        if 5 <= t.month <= 10:
            md = t.strftime("%m-%d")
            cz.setdefault(md, []).append(g[core].mean())
            cell.setdefault(md, []).append(np.where(LAND, g, 0))
mds = sorted(cz)
cz_mean = pd.Series({k: np.mean(v) for k, v in cz.items()})[mds].rolling(5, center=True, min_periods=1).mean()
cz_std = pd.Series({k: np.std(v) for k, v in cz.items()})[mds].rolling(5, center=True, min_periods=1).mean()
cell_norm = {k: np.mean(v, axis=0) for k, v in cell.items()}
keys = list(cell_norm)
stack = np.stack([cell_norm[k] for k in keys])
smooth = uniform_filter(stack, size=(15, 1, 1), mode="nearest")  # 15-day smoothing of the daily normal
CELL_NORM = {k: smooth[i] for i, k in enumerate(keys)}
del cell, stack, smooth

# ---------------------------------------------------------------- large-scale regime per day (IMD criterion)
anom = pd.Series({t: (g[core].mean() - cz_mean[t.strftime("%m-%d")]) / cz_std[t.strftime("%m-%d")] for t, g in OBS.items()}).sort_index()
anom = anom.reindex(pd.date_range(anom.index.min(), anom.index.max())).where(lambda s: s.index.month.isin([6, 7, 8, 9]))
LS = pd.Series("Normal", index=anom.index)
for sign, name in [(1, "Active"), (-1, "Break")]:
    hit = (anom * sign >= 1).fillna(False).values
    i = 0
    while i < len(hit):
        if hit[i]:
            j = i
            while j < len(hit) and hit[j]: j += 1
            if j - i >= 3: LS.iloc[i:j] = name
            i = j
        else:
            i += 1

# depression proximity at issue time (IMD RSMC best track)
TR = pd.read_csv(os.path.join(DATA, "rsmc", "rsmc_tracks.csv"), parse_dates=["time"])
TR = TR[TR.grade.isin(["D", "DD", "CS", "SCS", "VSCS", "ESCS", "SUCS"])]


def depression_mask(issue):
    pts = TR[(TR.time >= issue - pd.Timedelta(hours=6)) & (TR.time <= issue + pd.Timedelta(hours=3))]
    m = np.zeros((NLAT, NLON), bool)
    for _, p in pts.iterrows():
        m |= ((LAT2 - p.lat) ** 2 + ((LON2 - p.lon) * np.cos(np.radians(p.lat))) ** 2) <= 6 ** 2
    return m


# ---------------------------------------------------------------- local rainfall setting (static)
sea = ~LAND
COAST = LAND & binary_dilation(sea, iterations=2)  # within ~2 cells (~50 km) of the sea
WGHATS = LAND & (LAT2 >= 8) & (LAT2 <= 21.5) & (LON2 <= 77) & binary_dilation(sea, iterations=5)  # windward west-coast belt (~125 km)
NEHILL = LAND & (LAT2 >= 22) & (LAT2 <= 29.5) & (LON2 >= 89.5)
HIMAL = LAND & (LAT2 >= 29.5)
SETTING = np.full((NLAT, NLON), 3, np.int8)  # 3 = inland
SETTING[COAST] = 1
SETTING[WGHATS | NEHILL | HIMAL] = 0  # orographic takes precedence
SET_NAMES = {0: "Orographic", 1: "Coastal", 3: "Inland"}


# ---------------------------------------------------------------- assemble cases
def gfs(issue):
    f = os.path.join(DATA, "gfs", f"{issue:%Y-%m-%d}.npy")
    return np.load(f).astype(np.float32) if os.path.exists(f) else None


def build(lead):
    X, meta, grids = [], [], {}
    for t in sorted(OBS):
        issue = t - pd.Timedelta(days=lead)
        known = issue - pd.Timedelta(days=1)
        g = gfs(issue)
        if g is None or known not in LS.index or pd.isna(anom.get(known)): continue
        f = g[lead - 1]
        o = OBS[t]
        dep = depression_mask(issue)
        md = t.strftime("%m-%d")
        feats = {
            "raw": f, "nb3_mean": uniform_filter(f, 3), "nb3_max": maximum_filter(f, 3),
            "nb7_mean": uniform_filter(f, 7), "nb7_max": maximum_filter(f, 7),
            "norm": CELL_NORM.get(md, np.zeros_like(f)), "lat": LAT2, "lon": LON2,
            "doy": np.full_like(f, t.dayofyear), "anom": np.full_like(f, anom[known]),
            "active": np.full_like(f, LS[known] == "Active"), "break": np.full_like(f, LS[known] == "Break"),
            "dep": dep.astype(np.float32), "setting": SETTING.astype(np.float32),
        }
        m = LAND & (o > -998)
        X.append(np.stack([v[m] for v in feats.values()], 1).astype(np.float32))
        meta.append(pd.DataFrame({"date": t, "season": t.year, "i": np.where(m)[0], "j": np.where(m)[1], "obs": o[m],
                                  "ls": LS[known], "dep": dep[m], "setting": SETTING[m]}))
        grids[t] = (f, o, m)
    return np.concatenate(X), pd.concat(meta, ignore_index=True), list(feats), grids


def qm_fit(f, o):
    q = np.concatenate([np.linspace(0, 0.99, 100), np.linspace(0.991, 1, 10)])
    return np.quantile(f, q), np.quantile(o, q)


def qm_apply(fit, x):
    fq, oq = fit
    y = np.interp(x, fq, oq)
    top = x > fq[-1]
    y[top] = oq[-1] + (x[top] - fq[-1]) * min(oq[-1] / max(fq[-1], 1e-3), 1.5)
    return np.maximum(y, 0)


def cat(p, o, t):
    f, e = p >= t, o >= t
    h, mi, fa = (f & e).sum(), (~f & e).sum(), (f & ~e).sum()
    n = len(o); hr = (h + mi) * (h + fa) / n
    return dict(events=int(e.sum()), POD=h / max(h + mi, 1), FAR=fa / max(h + fa, 1), CSI=h / max(h + mi + fa, 1),
                ETS=(h - hr) / max(h + mi + fa - hr, 1e-9))


def fss(pred_grids, obs_grids, masks, thr, n):
    num = den = 0.0
    for p, o, m in zip(pred_grids, obs_grids, masks):
        pf = uniform_filter(((p >= thr) & m).astype(float), n)
        of = uniform_filter(((o >= thr) & m).astype(float), n)
        num += ((pf - of) ** 2)[m].sum(); den += (pf ** 2 + of ** 2)[m].sum()
    return 1 - num / den if den > 0 else np.nan


def run(lead):
    X, M, names, grids = build(lead)
    raw = X[:, 0]
    o = M.obs.values
    print(f"lead {lead}: {len(M):,} cell-days, {M.date.nunique()} days, heavy events {(o >= 64.5).sum():,}", flush=True)
    P = {k: np.full(len(M), np.nan) for k in ["RAW", "QM_GLOBAL", "QM_REGIME", "ML", "WARN"]}
    PROB = np.full(len(M), np.nan)
    PROB2 = np.full(len(M), np.nan)  # P(>= 115.6 mm)
    regime_key = np.where(M.dep, "Depression", M.ls) + "|" + M.setting.astype(str)
    for s in SEASONS:
        te = (M.season == s).values; tr = ~te
        if te.sum() == 0: continue
        P["RAW"][te] = raw[te]
        P["QM_GLOBAL"][te] = qm_apply(qm_fit(raw[tr], o[tr]), raw[te])
        out = np.empty(te.sum()); rk_te = regime_key[te]
        for k in np.unique(rk_te):
            sel_tr = tr & (regime_key == k)
            if sel_tr.sum() < 5000: sel_tr = tr & (M.ls.values == k.split("|")[0]) if not k.startswith("Depression") else tr & M.dep.values
            if sel_tr.sum() < 5000: sel_tr = tr
            idx = rk_te == k
            out[idx] = qm_apply(qm_fit(raw[sel_tr], o[sel_tr]), raw[te][idx])
        P["QM_REGIME"][te] = out
        # training subsample: all heavy cases + 12% of the rest, re-weighted
        trn = np.where(tr)[0]
        heavy = trn[o[trn] >= 64.5]; rest = trn[o[trn] < 64.5]
        keep = np.concatenate([heavy, rng.choice(rest, size=int(0.12 * len(rest)), replace=False)])
        w = np.where(o[keep] >= 64.5, 1.0, 1 / 0.12)
        reg = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, random_state=0)
        reg.fit(X[keep], np.sqrt(o[keep]), sample_weight=w * np.where(o[keep] >= 64.5, 3.0, 1.0))
        P["ML"][te] = np.maximum(reg.predict(X[te]), 0) ** 2
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, random_state=0)
        clf.fit(X[keep], (o[keep] >= 64.5).astype(int), sample_weight=w)
        PROB[te] = clf.predict_proba(X[te])[:, 1]
        # choose warning threshold on the training seasons only (maximise ETS)
        ptr = clf.predict_proba(X[tr])[:, 1]
        best_t, best_e = 0.3, -1
        for thr in np.arange(0.05, 0.8, 0.05):
            e = cat(np.where(ptr >= thr, 100.0, 0.0), o[tr], 64.5)["ETS"]
            if e > best_e: best_t, best_e = thr, e
        # very heavy (>= 115.6 mm): its own classifier and training-chosen threshold
        clf2 = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, random_state=0)
        clf2.fit(X[keep], (o[keep] >= 115.6).astype(int), sample_weight=w)
        PROB2[te] = clf2.predict_proba(X[te])[:, 1]
        ptr2 = clf2.predict_proba(X[tr])[:, 1]
        best_t2, best_e2 = 0.2, -1
        for thr in np.arange(0.03, 0.6, 0.03):
            e = cat(np.where(ptr2 >= thr, 150.0, 0.0), o[tr], 115.6)["ETS"]
            if e > best_e2: best_t2, best_e2 = thr, e
        # warning product: very heavy where P2 passes, else heavy where P passes, else no warning
        P["WARN"][te] = np.where(PROB2[te] >= best_t2, 150.0, np.where(PROB[te] >= best_t, 100.0, 0.0))
        print(f"  season {s} done (thresholds heavy {best_t:.2f}, very heavy {best_t2:.2f})", flush=True)
    res = {"lead": lead, "n": len(M), "days": int(M.date.nunique()), "heavy_events": int((o >= 64.5).sum()),
           "very_heavy_events": int((o >= 115.6).sum()), "methods": {}}
    dates = M.date.values
    for k, p in P.items():
        r = {"t64.5": cat(p, o, 64.5), "t115.6": cat(p, o, 115.6)}
        if k != "WARN": r["RMSE"] = float(np.sqrt(np.mean((p - o) ** 2)))
        # FSS at 64.5 mm
        pg, og, mg = [], [], []
        for t, (f, ob, m) in grids.items():
            sel = dates == np.datetime64(t)
            g = np.zeros((NLAT, NLON)); g[M.i.values[sel], M.j.values[sel]] = p[sel]
            pg.append(g); og.append(np.where(m, ob, 0)); mg.append(m)
        r["FSS"] = {f"{n * 25}km": float(fss(pg, og, mg, 64.5, n)) for n in [1, 3, 5, 9]}
        r["by_regime_ETS"] = {g: cat(p[sel], o[sel], 64.5)["ETS"] for g in ["Active", "Break", "Normal"] if (sel := (M.ls.values == g) & ~M.dep.values).sum() > 1000}
        r["by_regime_ETS"]["Depression"] = cat(p[M.dep.values], o[M.dep.values], 64.5)["ETS"]
        r["by_setting_ETS"] = {SET_NAMES[s_]: cat(p[sel], o[sel], 64.5)["ETS"] for s_ in [0, 1, 3] if (sel := M.setting.values == s_).sum() > 1000}
        res["methods"][k] = r
    ev = (o >= 64.5).astype(float)
    res["brier"] = {"PROB": float(np.mean((PROB - ev) ** 2)), "RAW": float(np.mean(((raw >= 64.5) - ev) ** 2)), "CLIM": float(np.mean((ev.mean() - ev) ** 2))}
    ev2 = (o >= 115.6).astype(float)
    res["brier115"] = {"PROB": float(np.mean((PROB2 - ev2) ** 2)), "RAW": float(np.mean(((raw >= 115.6) - ev2) ** 2)), "CLIM": float(np.mean((ev2.mean() - ev2) ** 2))}
    # reliability of P(heavy): observed frequency per probability bin
    bins = np.array([0, .05, .1, .2, .3, .4, .5, .6, .8, 1.01])
    b = np.digitize(PROB, bins) - 1
    res["reliability"] = [{"p_mean": float(PROB[b == k].mean()), "obs_freq": float(ev[b == k].mean()), "n": int((b == k).sum())} for k in range(len(bins) - 1) if (b == k).sum() > 200]
    np.savez_compressed(os.path.join(HERE, f"v2_cases_lead{lead}.npz"), date=M.date.values.astype("datetime64[D]"), i=M.i.values, j=M.j.values,
                        obs=o.astype(np.float32), raw=raw, ml=P["ML"].astype(np.float32), qmr=P["QM_REGIME"].astype(np.float32),
                        prob=PROB.astype(np.float32), prob2=PROB2.astype(np.float32), warn=P["WARN"].astype(np.float32),
                        ls=M.ls.values.astype("U7"), dep=M.dep.values, setting=M.setting.values)
    res["regime_days"] = M.drop_duplicates("date").ls.value_counts().to_dict()
    res["depression_cell_days"] = int(M.dep.sum())
    return res


if __name__ == "__main__":
    out = {"leads": {}}
    for L in LEADS:
        r = run(L)
        out["leads"][str(L)] = r
        for k, v in r["methods"].items():
            print(f"  {k:10s} RMSE {v.get('RMSE', float('nan')):6.2f}  heavy ETS {v['t64.5']['ETS']:.3f} POD {v['t64.5']['POD']:.2f} FAR {v['t64.5']['FAR']:.2f}"
                  f"  v.heavy ETS {v['t115.6']['ETS']:.3f}  FSS {', '.join(f'{a} {b:.2f}' for a, b in v['FSS'].items())}", flush=True)
        print("  Brier 64.5", {k: round(v, 5) for k, v in r["brier"].items()}, " Brier 115.6", {k: round(v, 5) for k, v in r["brier115"].items()}, flush=True)
    json.dump(out, open(os.path.join(HERE, "pilot_v2_results.json"), "w"), indent=1, default=float)
