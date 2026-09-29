"""PS 26080 pilot: regime-aware post-processing of raw NWP rainfall, verified against IMD gridded rainfall.

Data (all real, reused from the PS 81 cache + IMD yearly archive):
  * IMD real-time 0.25° daily rainfall grids, 2026 monsoon  -> truth + large-scale regime
  * IMD 0.25° yearly gridded rainfall 1991-2020             -> daily normals for the core monsoon zone
  * Archived NOAA GFS and UK Met Office UM forecasts (Open-Meteo Previous Runs), lead days 1 and 3, 36 cities

Regime (known at issue time):
  * large-scale: IMD/Rajeevan criterion — standardised core-zone rainfall anomaly >= +1 (active) or <= -1 (break)
    for >= 3 consecutive days; taken from the latest observed day before the forecast is issued (persistence)
  * local: west-coast orographic / hill-Himalayan orographic / east coast / inland

Evaluation: blocked leave-one-week-out cross-validation with a 3-day buffer (no training on neighbouring days).
"""
import glob, json, os
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

ROOT = os.path.dirname(os.path.abspath(__file__))
PS81 = os.path.join(ROOT, "..", "..", "..", "PS 81", "backend", "data")
YEARLY = os.path.join(ROOT, "..", "..", "data", "imd_yearly")
NLAT, NLON, LAT0, LON0, STEP = 129, 135, 6.5, 66.5, 0.25
LATS = LAT0 + STEP * np.arange(NLAT); LONS = LON0 + STEP * np.arange(NLON)

LOCS = json.load(open(os.path.join(ROOT, "locations.json"), encoding="utf-8"))
LOCTYPE = {  # rainfall-generating setting (PS: orographic / coastal regimes)
    **{k: "West-coast orographic" for k in ["mumbai", "panaji", "mangaluru", "kochi", "thiruvananthapuram", "surat"]},
    **{k: "Hill / Himalayan orographic" for k in ["shimla", "srinagar", "dehradun", "gangtok", "shillong"]},
    **{k: "East coast" for k in ["chennai", "visakhapatnam", "bhubaneswar", "kolkata"]},
}
MODELS = {"gfs_seamless": "NCEP GFS", "ukmo_seamless": "UK Met Office UM"}
THRESH = [15.6, 64.5, 115.6]

# ---------------------------------------------------------------- core monsoon zone (box 18–28N, 65–88E, land cells)
core = (LATS[:, None] >= 18) & (LATS[:, None] <= 28) & (LONS[None, :] >= 65) & (LONS[None, :] <= 88)


def core_mean(grid):
    g = grid.reshape(NLAT, NLON)
    m = core & (g > -998)
    return float(g[m].mean())


def normals():
    rows = []
    for f in sorted(glob.glob(os.path.join(YEARLY, "*.grd"))):
        y = int(os.path.basename(f)[:4])
        a = np.fromfile(f, dtype="<f4")
        nd = a.size // (NLAT * NLON)
        a = a.reshape(nd, NLAT, NLON)
        dates = pd.date_range(f"{y}-01-01", periods=nd)
        sel = (dates.month >= 6) & (dates.month <= 9)
        for d, g in zip(dates[sel], a[sel]):
            m = core & (g > -998)
            rows.append((y, d.strftime("%m-%d"), float(g[m].mean())))
    df = pd.DataFrame(rows, columns=["year", "md", "r"])
    stat = df.groupby("md")["r"].agg(["mean", "std"])
    # light smoothing across neighbouring calendar days (±2 days)
    stat = stat.rolling(5, center=True, min_periods=1).mean()
    return stat, df.year.nunique()


def imd_rt(date):
    f = os.path.join(PS81, "imd", "rain", f"{date}.grd")
    return np.fromfile(f, dtype="<f4") if os.path.exists(f) and os.path.getsize(f) == NLAT * NLON * 4 else None


def point(grid, lat, lon):
    g = grid.reshape(NLAT, NLON)
    fi, fj = (lat - LAT0) / STEP, (lon - LON0) / STEP
    best, bd = None, 1e9
    for di in range(-2, 3):
        for dj in range(-2, 3):
            i, j = round(fi) + di, round(fj) + dj
            if 0 <= i < NLAT and 0 <= j < NLON and g[i, j] > -998:
                dd = (i - fi) ** 2 + (j - fj) ** 2
                if dd < bd: bd, best = dd, float(g[i, j])
    return best


def regimes(stat):
    days = sorted(os.path.basename(f)[:10] for f in glob.glob(os.path.join(PS81, "imd", "rain", "*.grd")))
    rec = []
    for d in days:
        g = imd_rt(d)
        if g is None: continue
        md = d[5:]
        if md not in stat.index: continue
        r = core_mean(g)
        rec.append((d, r, (r - stat.loc[md, "mean"]) / stat.loc[md, "std"]))
    s = pd.DataFrame(rec, columns=["date", "core_rain", "anom"]).set_index("date")
    s.index = pd.to_datetime(s.index)
    s = s.asfreq("D")
    lab = pd.Series("Normal", index=s.index)
    for sign, name in [(1, "Active"), (-1, "Break")]:
        hit = (s.anom * sign >= 1).fillna(False).values
        i = 0
        while i < len(hit):
            if hit[i]:
                j = i
                while j < len(hit) and hit[j]: j += 1
                if j - i >= 3: lab.iloc[i:j] = name
                i = j
            else:
                i += 1
    s["regime"] = lab
    return s


def model_rain(model, lead):
    """IMD-day rainfall (24 h ending 03 UTC on the date) for every city from archived runs."""
    out = {}
    for f in glob.glob(os.path.join(PS81, "openmeteo", "previous", model, "*.json")):
        for li, b in enumerate(json.load(open(f, encoding="utf-8"))):
            t = pd.to_datetime(b["hourly"]["time"])
            v = pd.Series(b["hourly"][f"precipitation_previous_day{lead}"], index=t, dtype=float)
            # value at hh:00 = rain in the preceding hour -> shift so each hour belongs to the IMD day ending 03 UTC
            day = (t - pd.Timedelta(hours=4)).normalize() + pd.Timedelta(days=1)
            grp = v.groupby(day)
            daily = grp.sum(min_count=22)
            for d, x in daily.dropna().items():
                out[(LOCS[li]["id"], d.strftime("%Y-%m-%d"))] = float(x)
    return out


def build(model, lead, reg):
    fc = model_rain(model, lead)
    rows = []
    for (loc, d), f in fc.items():
        g = imd_rt(d)
        if g is None: continue
        L = next(l for l in LOCS if l["id"] == loc)
        o = point(g, L["lat"], L["lon"])
        issue = pd.Timestamp(d) - pd.Timedelta(days=lead)
        known = issue - pd.Timedelta(days=1)  # latest IMD day available when the forecast is issued
        if known not in reg.index or pd.isna(reg.loc[known, "anom"]) or o is None: continue
        rows.append(dict(loc=loc, date=pd.Timestamp(d), fc=f, obs=o, lat=L["lat"], lon=L["lon"],
                         ls=reg.loc[known, "regime"], anom=reg.loc[known, "anom"], ltype=LOCTYPE.get(loc, "Inland")))
    return pd.DataFrame(rows).sort_values(["date", "loc"]).reset_index(drop=True)


# ---------------------------------------------------------------- correction methods
def qm_fit(f, o):
    q = np.linspace(0, 1, 101)
    return np.quantile(f, q), np.quantile(o, q)


def qm_apply(fit, x):
    fq, oq = fit
    y = np.interp(x, fq, oq)
    top = x > fq[-1]  # beyond training range: keep the multiplicative ratio at the top quantile
    y[top] = oq[-1] + (x[top] - fq[-1]) * min(oq[-1] / max(fq[-1], 1e-3), 1.5)
    return np.maximum(y, 0)


def features(df):
    X = pd.DataFrame({"fc": np.log1p(df.fc), "anom": df.anom, "lat": df.lat, "lon": df.lon,
                      "doy": df.date.dt.dayofyear})
    for k in ["Active", "Break", "Normal"]: X[f"ls_{k}"] = (df.ls == k).astype(float)
    for k in ["West-coast orographic", "Hill / Himalayan orographic", "East coast", "Inland"]: X[f"lt_{k}"] = (df.ltype == k).astype(float)
    return X


def cv(df):
    wk = ((df.date - df.date.min()).dt.days // 7).values
    pred = {k: np.full(len(df), np.nan) for k in ["RAW", "QM_GLOBAL", "QM_REGIME", "ML_REGIME", "ML_REGIME_QM", "PROB_WARN"]}
    prob = {k: np.full(len(df), np.nan) for k in ["P_ML", "P_RAW"]}
    for w in np.unique(wk):
        te = wk == w
        dmin, dmax = df.date[te].min(), df.date[te].max()
        tr = (df.date < dmin - pd.Timedelta(days=3)) | (df.date > dmax + pd.Timedelta(days=3))
        T, S = df[tr], df[te]
        pred["RAW"][te] = S.fc
        g = qm_fit(T.fc.values, T.obs.values)
        pred["QM_GLOBAL"][te] = qm_apply(g, S.fc.values)
        out = np.empty(te.sum())
        for i, (_, r) in enumerate(S.iterrows()):
            sub = T[(T.ls == r.ls) & (T.ltype == r.ltype)]
            if len(sub) < 60: sub = T[T.ls == r.ls]
            if len(sub) < 60: sub = T
            out[i] = qm_apply(qm_fit(sub.fc.values, sub.obs.values), np.array([r.fc]))[0]
        pred["QM_REGIME"][te] = out
        Xtr, Xte = features(T), features(S)
        w_tr = np.where(T.obs >= 64.5, 3.0, 1.0)  # emphasise heavy-rain cases
        reg = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, random_state=0)
        reg.fit(Xtr, np.sqrt(T.obs), sample_weight=w_tr)
        ml_te = np.maximum(reg.predict(Xte), 0) ** 2
        pred["ML_REGIME"][te] = ml_te
        # restore intensity: regime-wise quantile mapping of the ML output onto observed rainfall
        ml_tr = np.maximum(reg.predict(Xtr), 0) ** 2
        out2 = np.empty(te.sum())
        for i, (idx, r) in enumerate(S.iterrows()):
            msk = ((T.ls == r.ls) & (T.ltype == r.ltype)).values
            if msk.sum() < 60: msk = (T.ls == r.ls).values
            if msk.sum() < 60: msk = np.ones(len(T), bool)
            out2[i] = qm_apply(qm_fit(ml_tr[msk], T.obs.values[msk]), np.array([ml_te[i]]))[0]
        pred["ML_REGIME_QM"][te] = out2
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, random_state=0)
        ytr = (T.obs >= 64.5).astype(int)
        prob["P_ML"][te] = clf.fit(Xtr, ytr).predict_proba(Xte)[:, 1] if ytr.sum() >= 5 else ytr.mean()
        prob["P_RAW"][te] = (S.fc >= 64.5).astype(float)
        # warning product: 70 mm (heavy) when P(heavy) >= 0.3, else the ML amount — only its categorical scores are used
        pred["PROB_WARN"][te] = np.where(prob["P_ML"][te] >= 0.3, np.maximum(ml_te, 70.0), np.minimum(ml_te, 64.0))
    return pred, prob


def cat_scores(p, o, t):
    f, e = p >= t, o >= t
    h, m, fa, cn = (f & e).sum(), (~f & e).sum(), (f & ~e).sum(), (~f & ~e).sum()
    n = h + m + fa + cn
    hr = (h + m) * (h + fa) / n
    return dict(events=int(e.sum()), hits=int(h), POD=h / max(h + m, 1), FAR=fa / max(h + fa, 1), CSI=h / max(h + m + fa, 1),
                ETS=(h - hr) / max(h + m + fa - hr, 1e-9))


def main():
    stat, nyears = normals()
    reg = regimes(stat)
    reg.to_csv(os.path.join(ROOT, "regimes_2026.csv"))
    print(f"normals from {nyears} IMD years; 2026 regime days:", reg.regime.value_counts().to_dict())
    results = {"normal_years": nyears, "regime_counts": reg.regime.value_counts().to_dict(), "runs": {}}
    for model, mname in MODELS.items():
        for lead in [1, 3]:
            df = build(model, lead, reg)
            pred, prob = cv(df)
            o = df.obs.values
            key = f"{model}|{lead}"
            R = {"model": mname, "lead": lead, "n": len(df), "period": [str(df.date.min().date()), str(df.date.max().date())], "methods": {}}
            for k, p in pred.items():
                R["methods"][k] = {"RMSE": float(np.sqrt(np.mean((p - o) ** 2))), "bias": float(np.mean(p - o)),
                                   **{f"t{t}": cat_scores(p, o, t) for t in THRESH}}
                # by regime
                R["methods"][k]["by_regime"] = {g: float(np.sqrt(np.mean((p[m] - o[m]) ** 2))) for g in ["Active", "Break", "Normal"] if (m := (df.ls == g).values).sum() > 20}
                R["methods"][k]["by_loctype"] = {g: float(np.sqrt(np.mean((p[m] - o[m]) ** 2))) for g in sorted(df.ltype.unique()) if (m := (df.ltype == g).values).sum() > 20}
            ev = (o >= 64.5).astype(float)
            R["brier"] = {k: float(np.mean((v - ev) ** 2)) for k, v in prob.items()}
            R["brier"]["CLIM"] = float(np.mean((ev.mean() - ev) ** 2))
            R["n_regime"] = df.ls.value_counts().to_dict()
            results["runs"][key] = R
            m = R["methods"]
            print(mname, "day", lead, "n", len(df), "| RMSE", {k: round(v["RMSE"], 2) for k, v in m.items()},
                  "| heavy ETS", {k: round(v["t64.5"]["ETS"], 3) for k, v in m.items()},
                  "POD", {k: round(v["t64.5"]["POD"], 2) for k, v in m.items()}, "events", m["RAW"]["t64.5"]["events"],
                  "| Brier", {k: round(v, 4) for k, v in R["brier"].items()})
            df.assign(**{k: v for k, v in pred.items()}, **prob).to_csv(os.path.join(ROOT, f"cases_{model}_d{lead}.csv"), index=False)
    json.dump(results, open(os.path.join(ROOT, "pilot_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
