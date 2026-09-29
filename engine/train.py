"""VARSHA training + verification.

For each lead day:
  1. leave-one-season-out (LOSO) verification of RAW, QM_GLOBAL, QM_REGIME, ML and WARN on the IMD grid
     -> verification report (RMSE, POD, FAR, CSI, ETS at IMD thresholds, FSS, Brier, reliability) overall,
        by regime and by setting, plus district-level scores
  2. do-no-harm gate: for every (regime, setting) choose the amount and warning method that verified best
  3. final models fitted on all seasons for live forecasting

Usage: python train.py [lead ...]
"""
import json, os, sys, pickle, time
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
import common as C

OUT = os.path.join(C.DATA, "models")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(0)
REGIMES = ["Active", "Break", "Normal", "Depression"]


def gbr():
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, random_state=0)


def gbc():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, random_state=0)


def build(lead, obs, anom, LS, N, S, L):
    X, meta = [], []
    for t in sorted(obs):
        issue = t - pd.Timedelta(days=lead)
        known = issue - pd.Timedelta(days=1)
        g = C.gfs(issue)
        if g is None or known not in LS.index or pd.isna(anom.get(known)): continue
        dep, _ = C.depression(issue)
        F = C.features(g[lead - 1], t, anom[known], LS[known], dep, N, S)
        o = obs[t]
        m = L & (o > -998)
        X.append(np.stack([F[k][m] for k in C.FEATURES], 1).astype(np.float32))
        meta.append(pd.DataFrame({"date": t, "season": t.year, "i": np.where(m)[0].astype(np.int16), "j": np.where(m)[1].astype(np.int16),
                                  "obs": o[m].astype(np.float32), "ls": LS[known], "dep": dep[m], "setting": S[m]}))
    M = pd.concat(meta, ignore_index=True)
    M["regime"] = np.where(M.dep, "Depression", M.ls)
    return np.concatenate(X), M


def qm_tables(raw, o, M, sel):
    """Regime-wise QM tables with pooling fallback; key = regime|setting."""
    tabs = {"GLOBAL": C.qm_fit(raw[sel], o[sel])}
    for r in REGIMES:
        rs = sel & (M.regime.values == r)
        if rs.sum() >= 5000: tabs[r] = C.qm_fit(raw[rs], o[rs])
        for s in (0, 1, 3):
            ss = rs & (M.setting.values == s)
            if ss.sum() >= 5000: tabs[f"{r}|{s}"] = C.qm_fit(raw[ss], o[ss])
    return tabs


def qm_regime(tabs, raw, regime, setting):
    out = np.empty(len(raw), np.float32)
    keys = np.char.add(np.char.add(regime.astype(str), "|"), setting.astype(str))
    for k in np.unique(keys):
        idx = keys == k
        r = k.split("|")[0]
        tab = tabs.get(k) or tabs.get(r) or tabs["GLOBAL"]
        out[idx] = C.qm_apply(tab, raw[idx])
    return out


def fit_models(X, o, sel):
    trn = np.where(sel)[0]
    heavy, rest = trn[o[trn] >= 64.5], trn[o[trn] < 64.5]
    keep = np.concatenate([heavy, rng.choice(rest, size=int(0.12 * len(rest)), replace=False)])
    w = np.where(o[keep] >= 64.5, 1.0, 1 / 0.12)
    reg = gbr().fit(X[keep], np.sqrt(o[keep]), sample_weight=w * np.where(o[keep] >= 64.5, 3.0, 1.0))
    c1 = gbc().fit(X[keep], (o[keep] >= 64.5).astype(int), sample_weight=w)
    c2 = gbc().fit(X[keep], (o[keep] >= 115.6).astype(int), sample_weight=w)
    p1, p2 = c1.predict_proba(X[sel])[:, 1], c2.predict_proba(X[sel])[:, 1]
    t1 = max(np.arange(0.05, 0.8, 0.05), key=lambda t: C.cat(np.where(p1 >= t, 100, 0), o[sel], 64.5)["ETS"])
    t2 = max(np.arange(0.03, 0.6, 0.03), key=lambda t: C.cat(np.where(p2 >= t, 150, 0), o[sel], 115.6)["ETS"])
    return dict(reg=reg, c1=c1, c2=c2, t1=float(t1), t2=float(t2))


def predict(mod, X):
    ml = np.maximum(mod["reg"].predict(X), 0) ** 2
    p1, p2 = mod["c1"].predict_proba(X)[:, 1], mod["c2"].predict_proba(X)[:, 1]
    warn = np.where(p2 >= mod["t2"], 150.0, np.where(p1 >= mod["t1"], 100.0, 0.0))
    return ml.astype(np.float32), p1.astype(np.float32), p2.astype(np.float32), warn.astype(np.float32)


def scores(p, o, with_rmse=True):
    r = {"t64.5": C.cat(p, o, 64.5), "t115.6": C.cat(p, o, 115.6)}
    if with_rmse: r["RMSE"] = float(np.sqrt(np.mean((p - o) ** 2)))
    return r


def run(lead, obs, anom, LS, N, S, L, D):
    t0 = time.time()
    X, M = build(lead, obs, anom, LS, N, S, L)
    raw, o = X[:, 0], M.obs.values
    print(f"lead {lead}: {len(M):,} cell-days over {M.date.nunique()} days; heavy {(o >= 64.5).sum():,}, very heavy {(o >= 115.6).sum():,}", flush=True)
    P = {k: np.zeros(len(M), np.float32) for k in ["RAW", "QM_GLOBAL", "QM_REGIME", "ML", "WARN"]}
    PR1, PR2 = np.zeros(len(M), np.float32), np.zeros(len(M), np.float32)
    for s in sorted(M.season.unique()):
        te = (M.season == s).values; tr = ~te
        P["RAW"][te] = raw[te]
        tabs = qm_tables(raw, o, M, tr)
        P["QM_GLOBAL"][te] = C.qm_apply(tabs["GLOBAL"], raw[te])
        P["QM_REGIME"][te] = qm_regime(tabs, raw[te], M.regime.values[te], M.setting.values[te])
        mod = fit_models(X, o, tr)
        P["ML"][te], PR1[te], PR2[te], P["WARN"][te] = predict(mod, X[te])
        print(f"  held-out season {s}: done ({time.time() - t0:.0f}s)", flush=True)

    # ---- verification report
    rep = {"lead": lead, "n": len(M), "days": int(M.date.nunique()), "seasons": sorted(map(int, M.season.unique())),
           "events": {"heavy": int((o >= 64.5).sum()), "very_heavy": int((o >= 115.6).sum()), "extremely_heavy": int((o >= 204.5).sum())},
           "overall": {}, "by_regime": {}, "by_setting": {}, "fss": {}, "brier": {}, "reliability": [], "district": {}}
    for k, p in P.items():
        rep["overall"][k] = scores(p, o, k != "WARN")
        rep["by_regime"][k] = {r: scores(p[sel], o[sel], k != "WARN") for r in REGIMES if (sel := M.regime.values == r).sum() > 2000}
        rep["by_setting"][k] = {C.SET_NAMES[s_]: scores(p[sel], o[sel], k != "WARN") for s_ in (0, 1, 3) if (sel := M.setting.values == s_).sum() > 2000}
    # FSS on reconstructed daily grids
    dates = M.date.values
    ud = np.unique(dates)
    grid_idx = {d: np.where(dates == d)[0] for d in ud}
    for k, p in P.items():
        pg, og, mg = [], [], []
        for d in ud:
            ix = grid_idx[d]
            gp = np.zeros((C.NLAT, C.NLON), np.float32); go = np.zeros_like(gp); gm = np.zeros((C.NLAT, C.NLON), bool)
            gp[M.i.values[ix], M.j.values[ix]] = p[ix]; go[M.i.values[ix], M.j.values[ix]] = o[ix]; gm[M.i.values[ix], M.j.values[ix]] = True
            pg.append(gp); og.append(go); mg.append(gm)
        rep["fss"][k] = {f"{n * 25}km": C.fss(pg, og, mg, 64.5, n) for n in (1, 3, 5, 9)}
    for name, pr, thr in [("heavy", PR1, 64.5), ("very_heavy", PR2, 115.6)]:
        ev = (o >= thr).astype(np.float32)
        rep["brier"][name] = {"VARSHA": float(np.mean((pr - ev) ** 2)), "RAW": float(np.mean(((raw >= thr) - ev) ** 2)),
                              "CLIMATOLOGY": float(np.mean((ev.mean() - ev) ** 2))}
    bins = np.array([0, .05, .1, .2, .3, .4, .5, .6, .8, 1.01]); b = np.digitize(PR1, bins) - 1
    ev = o >= 64.5
    rep["reliability"] = [{"p": float(PR1[b == k].mean()), "freq": float(ev[b == k].mean()), "n": int((b == k).sum())} for k in range(len(bins) - 1) if (b == k).sum() > 200]
    # district level: mean rainfall RMSE; heavy rain = any cell in the district >= 64.5 mm
    cd = np.load(os.path.join(C.DATA, "boundaries", "cell_district.npy"))
    dist = cd[M.i.values, M.j.values]
    ok = dist >= 0
    frame = pd.DataFrame({"d": dist[ok], "date": dates[ok], "obs": o[ok], **{k: p[ok] for k, p in P.items()}})
    g_mean = frame.groupby(["d", "date"]).mean()
    g_max = frame.groupby(["d", "date"]).max()
    rep["district"] = {"n": int(len(g_mean)), "districts": int(frame.d.nunique()),
                       "rmse_mean_rain": {k: float(np.sqrt(np.mean((g_mean[k] - g_mean.obs) ** 2))) for k in P if k != "WARN"},
                       "heavy_any_cell": {k: C.cat(g_max[k].values, g_max.obs.values, 64.5) for k in P}}

    # ---- do-no-harm gate from LOSO results
    gate = {}
    for r in REGIMES:
        for s_ in (0, 1, 3):
            sel = (M.regime.values == r) & (M.setting.values == s_)
            if sel.sum() < 2000:
                gate[f"{r}|{s_}"] = {"amount": "RAW", "warning": "RAW", "n": int(sel.sum()), "reason": "too few verified cases"}
                continue
            rm = {k: float(np.sqrt(np.mean((P[k][sel] - o[sel]) ** 2))) for k in ["RAW", "QM_REGIME", "ML"]}
            et = {k: C.cat(P[k][sel], o[sel], 64.5)["ETS"] for k in ["RAW", "QM_REGIME", "WARN"]}
            amount = min(rm, key=rm.get)
            warning = max(et, key=et.get)
            gate[f"{r}|{s_}"] = {"amount": amount, "warning": warning, "n": int(sel.sum()), "rmse": rm, "ets": et}
    rep["gate"] = gate

    # ---- final models on all seasons
    allsel = np.ones(len(M), bool)
    final = fit_models(X, o, allsel)
    final["qm"] = qm_tables(raw, o, M, allsel)
    final["features"] = C.FEATURES
    pickle.dump(final, open(os.path.join(OUT, f"lead{lead}.pkl"), "wb"))
    np.savez_compressed(os.path.join(OUT, f"cases_lead{lead}.npz"), date=dates.astype("datetime64[D]"), i=M.i.values, j=M.j.values, obs=o,
                        raw=raw, ml=P["ML"], qmr=P["QM_REGIME"], warn=P["WARN"], p1=PR1, p2=PR2, regime=M.regime.values.astype("U10"))
    json.dump(rep, open(os.path.join(OUT, f"verification_lead{lead}.json"), "w"), indent=1, default=float)
    ov = rep["overall"]
    print(f"  RMSE raw {ov['RAW']['RMSE']:.2f} ML {ov['ML']['RMSE']:.2f} | heavy ETS raw {ov['RAW']['t64.5']['ETS']:.3f} "
          f"QMreg {ov['QM_REGIME']['t64.5']['ETS']:.3f} ML {ov['ML']['t64.5']['ETS']:.3f} WARN {ov['WARN']['t64.5']['ETS']:.3f} | "
          f"v.heavy ETS raw {ov['RAW']['t115.6']['ETS']:.3f} WARN {ov['WARN']['t115.6']['ETS']:.3f} | "
          f"FSS25 raw {rep['fss']['RAW']['25km']:.2f} WARN {rep['fss']['WARN']['25km']:.2f} | {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    leads = [int(x) for x in sys.argv[1:]] or C.LEADS
    N = C.normals()
    obs = C.observations()
    anom, LS = C.regime_series(obs, N)
    json.dump({"dates": [d.strftime("%Y-%m-%d") for d in anom.index], "anom": [None if np.isnan(x) else round(float(x), 3) for x in anom.values],
               "regime": list(LS.values)}, open(os.path.join(OUT, "regime_history.json"), "w"))
    S, L = C.settings(), C.land()
    for lead in leads:
        run(lead, obs, anom, LS, N, S, L, None)
