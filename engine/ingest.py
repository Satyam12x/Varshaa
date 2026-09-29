"""Daily ingest: NOAA GFS 00 UTC rain forecast (official NOAA archive) and IMD real-time rainfall grids."""
import os, sys, threading, time, urllib.request
import numpy as np, pandas as pd
import common as C

BASE = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
ROWS = [int(round((90 - lat) / 0.25)) for lat in C.LAT]
COLS = [int(round(lon / 0.25)) for lon in C.LON]
HOURS = [3, 27, 51, 75, 99, 123]
_lock = threading.Lock()


def _get(url, headers=None, tries=4):
    for a in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=120).read()
        except Exception:
            if a == tries - 1: raise
            time.sleep(3 * (a + 1))


def _apcp(date, fh):
    import eccodes
    url = f"{BASE}/gfs.{date}/00/atmos/gfs.t00z.pgrb2.0p25.f{fh:03d}"
    idx = _get(url + ".idx").decode().splitlines()
    for i, l in enumerate(idx):
        p = l.split(":")
        if p[3] == "APCP" and p[5] == f"0-{fh} hour acc fcst":
            buf = _get(url, {"Range": f"bytes={int(p[1])}-{int(idx[i + 1].split(':')[1]) - 1}"})
            with _lock:
                h = eccodes.codes_new_from_message(buf)
                v = eccodes.codes_get_values(h).reshape(eccodes.codes_get(h, "Nj"), eccodes.codes_get(h, "Ni"))
                eccodes.codes_release(h)
            return v[np.ix_(ROWS, COLS)].astype(np.float32)
    raise KeyError(fh)


def gfs_issue(date):
    """Download and store lead 1-5 IMD-day rain for the 00 UTC run of `date`. Returns True if available."""
    date = pd.Timestamp(date)
    f = os.path.join(C.GFS_DIR, f"{date:%Y-%m-%d}.npy")
    if os.path.exists(f): return True
    try:
        acc = [_apcp(f"{date:%Y%m%d}", h) for h in HOURS]
    except Exception as e:
        print(f"GFS {date.date()} not available: {e}", flush=True)
        return False
    np.save(f, np.stack([np.maximum(acc[i + 1] - acc[i], 0) for i in range(5)]).astype(np.float16))
    return True


def latest_gfs(today=None):
    today = pd.Timestamp(today or pd.Timestamp.utcnow().tz_localize(None).normalize())
    for back in range(0, 4):
        if gfs_issue(today - pd.Timedelta(days=back)):
            return today - pd.Timedelta(days=back)
    return None


def imd_recent(days=20, today=None):
    today = pd.Timestamp(today or pd.Timestamp.utcnow().tz_localize(None).normalize())
    got = 0
    for back in range(1, days + 1):
        if C.imd_rt(today - pd.Timedelta(days=back), download=True) is not None: got += 1
    return got


if __name__ == "__main__":
    issue = latest_gfs()
    print("latest GFS issue:", issue)
    print("IMD days available (last 20):", imd_recent())
