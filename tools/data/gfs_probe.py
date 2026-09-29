import urllib.request, time, numpy as np, eccodes
BASE = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
def field(date, fh):
    url = f"{BASE}/gfs.{date}/00/atmos/gfs.t00z.pgrb2.0p25.f{fh:03d}"
    idx = urllib.request.urlopen(url + ".idx", timeout=60).read().decode().splitlines()
    for i, l in enumerate(idx):
        p = l.split(":")
        if p[3] == "APCP" and p[5] == f"0-{fh} hour acc fcst" if fh else False:
            start = int(p[1]); end = int(idx[i + 1].split(":")[1]) - 1
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
            buf = urllib.request.urlopen(req, timeout=120).read()
            h = eccodes.codes_new_from_message(buf)
            ni, nj = eccodes.codes_get(h, "Ni"), eccodes.codes_get(h, "Nj")
            vals = eccodes.codes_get_values(h).reshape(nj, ni)
            lat1 = eccodes.codes_get(h, "latitudeOfFirstGridPointInDegrees")
            eccodes.codes_release(h)
            return vals, lat1, len(buf)
    raise KeyError(fh)
t=time.time()
a27, lat1, n = field("20210715", 27); a3, _, _ = field("20210715", 3)
print("bytes", n, "lat1", lat1, "shape", a27.shape, "secs", round(time.time()-t,1))
# IMD grid rows: lat 6.5..38.5 ; GFS rows from 90 down, step .25
rows = [int(round((90 - lat) / 0.25)) for lat in np.arange(6.5, 38.51, 0.25)]
cols = [int(round(lon / 0.25)) for lon in np.arange(66.5, 100.01, 0.25)]
day = (a27 - a3)[np.ix_(rows, cols)]
print("india 24h rain grid", day.shape, "max", day.max().round(1), "mean", day.mean().round(2))
imd = np.fromfile(r"C:/Users/Satyam Pandey/OneDrive/Desktop/IgniteZ PS 81/PS 80/data/imd_yearly/2020.grd", dtype="<f4")
print("imd yearly exists (2021 not yet)")
