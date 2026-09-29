"""Download NOAA GFS 00 UTC rainfall forecasts from NOAA's official archive (AWS Open Data: noaa-gfs-bdp-pds),
fetching only the accumulated-precipitation field via byte ranges, and save IMD-day rainfall for lead days 1-5
on the IMD 0.25° grid (6.5-38.5N, 66.5-100E; GFS 0.25° points coincide exactly with IMD grid points).

IMD rainfall for date D = 24 h ending 03 UTC on D. For a run issued 00 UTC on D0, lead L covers
forecast hours (24L-21, 24L+3], i.e. APCP(0-(24L+3)) - APCP(0-(24L-21)).

Output: ../../data/gfs/YYYY-MM-DD.npy (issue date), float16 array (5, 129, 135) = leads 1..5 valid D0+1..D0+5.
"""
import os, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd, eccodes

BASE = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "gfs")
os.makedirs(OUT, exist_ok=True)
ROWS = [int(round((90 - lat) / 0.25)) for lat in np.arange(6.5, 38.51, 0.25)]
COLS = [int(round(lon / 0.25)) for lon in np.arange(66.5, 100.01, 0.25)]
HOURS = [3, 27, 51, 75, 99, 123]
DECODE = threading.Lock()  # eccodes is not thread-safe; download in parallel, decode one at a time


def get(url, headers=None, tries=5):
    for a in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=120).read()
        except Exception as e:
            if a == tries - 1: raise
            time.sleep(3 * (a + 1))


def apcp(date, fh):
    url = f"{BASE}/gfs.{date}/00/atmos/gfs.t00z.pgrb2.0p25.f{fh:03d}"
    idx = get(url + ".idx").decode().splitlines()
    for i, l in enumerate(idx):
        p = l.split(":")
        if p[3] == "APCP" and p[5] == f"0-{fh} hour acc fcst":
            start, end = int(p[1]), int(idx[i + 1].split(":")[1]) - 1
            buf = get(url, {"Range": f"bytes={start}-{end}"})
            with DECODE:
                h = eccodes.codes_new_from_message(buf)
                vals = eccodes.codes_get_values(h).reshape(eccodes.codes_get(h, "Nj"), eccodes.codes_get(h, "Ni"))
                eccodes.codes_release(h)
            return vals[np.ix_(ROWS, COLS)].astype(np.float32)
    raise KeyError(f"APCP 0-{fh} missing for {date}")


def one(d):
    f = os.path.join(OUT, f"{d:%Y-%m-%d}.npy")
    if os.path.exists(f): return d, "cached"
    ds = f"{d:%Y%m%d}"
    acc = [apcp(ds, h) for h in HOURS]
    daily = np.stack([np.maximum(acc[i + 1] - acc[i], 0) for i in range(5)]).astype(np.float16)
    np.save(f, daily)
    return d, "ok"


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or [2021, 2022, 2023, 2024, 2025, 2026]
    # issue dates from 27 May so that lead 1..5 cover 1 June onwards; to 25 Sep (valid up to 30 Sep)
    dates = [d for y in years for d in pd.date_range(f"{y}-05-27", f"{y}-09-29" if y < 2026 else "2026-09-26")]
    one(dates[0])  # warm up eccodes definitions in the main thread
    done = err = 0
    with ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(one, d): d for d in dates}
        for fu in as_completed(futs):
            try:
                fu.result(); done += 1
            except Exception as e:
                err += 1; print("ERR", futs[fu].date(), e, flush=True)
            if (done + err) % 50 == 0: print(f"{done + err}/{len(dates)} (errors {err})", flush=True)
    print(f"DONE {done} ok, {err} errors", flush=True)
