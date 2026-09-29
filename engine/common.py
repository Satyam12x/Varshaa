"""VARSHA engine — shared data access, IMD regimes and features.

All inputs are official: IMD Pune 0.25° gridded rainfall (archive + real time), IMD RSMC New Delhi best tracks,
Survey of India district boundaries, and NOAA GFS forecasts from NOAA's archive (AWS Open Data).
"""
import datetime as dt
import glob, json, os, time, urllib.request
import numpy as np, pandas as pd
from scipy.ndimage import binary_dilation, maximum_filter, uniform_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
NLAT, NLON, LAT0, LON0, STEP = 129, 135, 6.5, 66.5, 0.25
LAT = LAT0 + STEP * np.arange(NLAT)
LON = LON0 + STEP * np.arange(NLON)
LAT2, LON2 = np.meshgrid(LAT, LON, indexing="ij")
LEADS = [1, 2, 3, 4, 5]
THRESH = {"heavy": 64.5, "very_heavy": 115.6, "extremely_heavy": 204.5}
SEASONS = [2021, 2022, 2023, 2024, 2025, 2026]
FEATURES = ["raw", "nb3_mean", "nb3_max", "nb7_mean", "nb7_max", "norm", "lat", "lon", "doy", "anom", "active", "break", "dep", "setting"]
SET_NAMES = {0: "Orographic", 1: "Coastal", 3: "Inland"}

os.makedirs(os.path.join(DATA, "imd_rt"), exist_ok=True)
PS81_RT = os.path.join(ROOT, "..", "PS 81", "backend", "data", "imd", "rain")


# ---------------------------------------------------------------- IMD gridded rainfall
def imd_year(y):
    a = np.fromfile(os.path.join(DATA, "imd_yearly", f"{y}.grd"), dtype="<f4")
    nd = a.size // (NLAT * NLON)
    return pd.date_range(f"{y}-01-01", periods=nd), a.reshape(nd, NLAT, NLON)


def imd_rt_path(date):
    return os.path.join(DATA, "imd_rt", f"{date:%Y-%m-%d}.grd")


def imd_rt(date, download=False):
    """IMD real-time 0.25° rainfall for a date (24 h ending 08:30 IST on that date)."""
    date = pd.Timestamp(date)
    for p in (imd_rt_path(date), os.path.join(PS81_RT, f"{date:%Y-%m-%d}.grd")):
        if os.path.exists(p) and os.path.getsize(p) == NLAT * NLON * 4:
            return np.fromfile(p, dtype="<f4").reshape(NLAT, NLON)
    if not download:
        return None
    for a in range(3):
        try:
            req = urllib.request.Request("https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php",
                                         data=f"rain={date:%d%m%Y}".encode(), method="POST")
            buf = urllib.request.urlopen(req, timeout=150).read()
            if len(buf) == NLAT * NLON * 4:
                open(imd_rt_path(date), "wb").write(buf)
                return np.frombuffer(buf, dtype="<f4").reshape(NLAT, NLON)
            if len(buf) == 0:
                return None
        except Exception:
            time.sleep(5 * (a + 1))
    return None


def observations(seasons=SEASONS):
    """JJAS daily IMD grids: yearly archive where available, real-time grids otherwise."""
    obs = {}
    for y in seasons:
        f = os.path.join(DATA, "imd_yearly", f"{y}.grd")
        if os.path.exists(f):
            d, a = imd_year(y)
            for t, g in zip(d, a):
                if 6 <= t.month <= 9: obs[t] = g
        else:
            for t in pd.date_range(f"{y}-06-01", f"{y}-09-30"):
                g = imd_rt(t)
                if g is not None: obs[t] = g
    return obs


_land = None


def land():
    global _land
    if _land is None:
        f = os.path.join(DATA, "land_mask.npy")  # shipped in the deploy bundle instead of the 25 MB IMD year file
        _land = np.load(f) if os.path.exists(f) else imd_year(2020)[1][200] > -998
    return _land


def core_zone():
    return land() & (LAT2 >= 18) & (LAT2 <= 28) & (LON2 >= 65) & (LON2 <= 88)


# ---------------------------------------------------------------- normals 1991-2020 (cached)
NORMALS = os.path.join(DATA, "normals_1991_2020.npz")


def normals():
    if os.path.exists(NORMALS):
        z = np.load(NORMALS, allow_pickle=True)
        return dict(md=list(z["md"]), cz_mean=z["cz_mean"], cz_std=z["cz_std"], cell=z["cell"])
    L, core = land(), core_zone()
    cz, cell = {}, {}
    for y in range(1991, 2021):
        d, a = imd_year(y)
        for t, g in zip(d, a):
            if 5 <= t.month <= 10:
                md = t.strftime("%m-%d")
                cz.setdefault(md, []).append(g[core].mean())
                cell.setdefault(md, []).append(np.where(L, g, 0).astype(np.float32))
    md = sorted(cz)
    cz_mean = pd.Series([np.mean(cz[k]) for k in md]).rolling(5, center=True, min_periods=1).mean().values
    cz_std = pd.Series([np.std(cz[k]) for k in md]).rolling(5, center=True, min_periods=1).mean().values
    stack = np.stack([np.mean(cell[k], axis=0) for k in md]).astype(np.float32)
    stack = uniform_filter(stack, size=(15, 1, 1), mode="nearest")
    np.savez_compressed(NORMALS, md=np.array(md), cz_mean=cz_mean, cz_std=cz_std, cell=stack)
    return dict(md=md, cz_mean=cz_mean, cz_std=cz_std, cell=stack)


# ---------------------------------------------------------------- regimes
def core_anomaly(date, grid, N):
    md = pd.Timestamp(date).strftime("%m-%d")
    if md not in N["md"]: return np.nan
    k = N["md"].index(md)
    return float((grid[core_zone()].mean() - N["cz_mean"][k]) / N["cz_std"][k])


def classify_spells(anom: pd.Series) -> pd.Series:
    """IMD / Rajeevan criterion: standardised core-zone anomaly >= +1 (active) or <= -1 (break) for >= 3 consecutive days."""
    anom = anom.sort_index()
    lab = pd.Series("Normal", index=anom.index)
    for sign, name in [(1, "Active"), (-1, "Break")]:
        hit = (anom * sign >= 1).fillna(False).values
        i = 0
        while i < len(hit):
            if hit[i]:
                j = i
                while j < len(hit) and hit[j]: j += 1
                if j - i >= 3: lab.iloc[i:j] = name
                i = j
            else:
                i += 1
    return lab


def causal_spells(anom: pd.Series) -> pd.Series:
    """The same criterion as it can be applied in real time: day t is Active (Break) only once the anomaly has been
    >= +1 (<= -1) on t and the two days before it. Used for training so labels match what the live system knows."""
    anom = anom.sort_index()
    lab = pd.Series("Normal", index=anom.index)
    for sign, name in [(1, "Active"), (-1, "Break")]:
        run = 0
        for k, h in enumerate((anom * sign >= 1).fillna(False).values):
            run = run + 1 if h else 0
            if run >= 3: lab.iloc[k] = name
    return lab


def regime_series(obs, N):
    idx = pd.date_range(min(obs), max(obs))
    anom = pd.Series({t: core_anomaly(t, obs[t], N) for t in obs}).reindex(idx)
    anom[~anom.index.month.isin([6, 7, 8, 9])] = np.nan
    return anom, classify_spells(anom)


_tracks = None


def tracks():
    global _tracks
    if _tracks is None:
        t = pd.read_csv(os.path.join(DATA, "rsmc", "rsmc_tracks.csv"), parse_dates=["time"])
        _tracks = t[t.grade.isin(["D", "DD", "CS", "SCS", "VSCS", "ESCS", "SUCS"])]
    return _tracks


def depression(issue):
    """Cells within 6° of an IMD RSMC depression (or stronger) in the 6 h up to issue time; returns mask and the systems."""
    T = tracks()
    issue = pd.Timestamp(issue)
    pts = T[(T.time >= issue - pd.Timedelta(hours=6)) & (T.time <= issue)]  # fixes up to the 00 UTC issue time only
    m = np.zeros((NLAT, NLON), bool)
    for _, p in pts.iterrows():
        m |= ((LAT2 - p.lat) ** 2 + ((LON2 - p.lon) * np.cos(np.radians(p.lat))) ** 2) <= 36
    return m, pts


def settings():
    L = land(); sea = ~L
    coast = L & binary_dilation(sea, iterations=2)
    wghats = L & (LAT2 >= 8) & (LAT2 <= 21.5) & (LON2 <= 77) & binary_dilation(sea, iterations=5)
    nehill = L & (LAT2 >= 22) & (LAT2 <= 29.5) & (LON2 >= 89.5)
    himal = L & (LAT2 >= 29.5)
    s = np.full((NLAT, NLON), 3, np.int8)
    s[coast] = 1
    s[wghats | nehill | himal] = 0
    return s


# ---------------------------------------------------------------- NOAA GFS
GFS_DIR = os.path.join(DATA, "gfs")


def gfs(issue):
    f = os.path.join(GFS_DIR, f"{pd.Timestamp(issue):%Y-%m-%d}.npy")
    return np.load(f).astype(np.float32) if os.path.exists(f) else None


def features(f, target, anom_known, ls_known, dep_mask, N, S):
    md = pd.Timestamp(target).strftime("%m-%d")
    norm = N["cell"][N["md"].index(md)] if md in N["md"] else np.zeros_like(f)
    one = np.ones_like(f)
    return {"raw": f, "nb3_mean": uniform_filter(f, 3), "nb3_max": maximum_filter(f, 3), "nb7_mean": uniform_filter(f, 7),
            "nb7_max": maximum_filter(f, 7), "norm": norm, "lat": LAT2, "lon": LON2, "doy": one * pd.Timestamp(target).dayofyear,
            "anom": one * (0.0 if np.isnan(anom_known) else anom_known), "active": one * (ls_known == "Active"),
            "break": one * (ls_known == "Break"), "dep": dep_mask.astype(np.float32), "setting": S.astype(np.float32)}


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
    h, mi, fa = int((f & e).sum()), int((~f & e).sum()), int((f & ~e).sum())
    n = len(o); hr = (h + mi) * (h + fa) / max(n, 1)
    return dict(events=h + mi, hits=h, misses=mi, false_alarms=fa, POD=h / max(h + mi, 1), FAR=fa / max(h + fa, 1),
                CSI=h / max(h + mi + fa, 1), ETS=(h - hr) / max(h + mi + fa - hr, 1e-9))


def fss(preds, obss, masks, thr, n):
    num = den = 0.0
    for p, o, m in zip(preds, obss, masks):
        pf = uniform_filter(((p >= thr) & m).astype(float), n)
        of = uniform_filter(((o >= thr) & m).astype(float), n)
        num += ((pf - of) ** 2)[m].sum(); den += (pf ** 2 + of ** 2)[m].sum()
    return float(1 - num / den) if den > 0 else float("nan")


def districts():
    B = os.path.join(DATA, "boundaries")
    return json.load(open(os.path.join(B, "districts.json"), encoding="utf-8"))
