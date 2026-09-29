"""Parse IMD RSMC New Delhi best-track workbook (official xlsx from rsmcnewdelhi.imd.gov.in) into a clean CSV of
6-hourly positions of depressions and stronger systems: storm, time (UTC), lat, lon, grade.
Handles the workbook's quirks: dates only on the first row of a day (or as '=Dn' formulas), remark rows, mixed time types."""
import datetime as dt, os, re
import openpyxl, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "data", "rsmc", "imd_best_tracks_1982_2026.xlsx")
OUT = os.path.join(HERE, "..", "..", "data", "rsmc", "rsmc_tracks.csv")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


rows = []
wb = openpyxl.load_workbook(SRC, read_only=True)
for sheet in wb.sheetnames:
    if not re.fullmatch(r"\d{4}", sheet):
        continue
    year = int(sheet)
    serial, basin, date = None, None, None
    for r in wb[sheet].iter_rows(values_only=True):
        if not r or len(r) < 12: continue
        if isinstance(r[0], (int, float)): serial = int(r[0])
        if isinstance(r[1], str) and r[1].strip() in ("BOB", "AS", "LAND", "Land"): basin = r[1].strip()
        if isinstance(r[3], dt.datetime): date = r[3].date()
        t = r[4]
        if isinstance(t, (int, float)): t = f"{int(t):04d}"
        if not (isinstance(t, str) and re.fullmatch(r"\d{3,4}", t.strip())): continue  # remark row
        lat, lon = num(r[5]), num(r[6])
        if date is None or lat is None or lon is None: continue
        hhmm = t.strip().zfill(4)
        rows.append(dict(storm=f"{year}-{serial:02d}" if serial else f"{year}-??", basin=basin,
                         time=dt.datetime.combine(date, dt.time(int(hhmm[:2]) % 24, int(hhmm[2:]))),
                         lat=lat, lon=lon, grade=str(r[11]).strip() if r[11] else None))
df = pd.DataFrame(rows).drop_duplicates(["storm", "time"])
df.to_csv(OUT, index=False)
m = df[df.time.dt.month.between(6, 9) & (df.time.dt.year >= 2021)]
print(len(df), "positions,", df.storm.nunique(), "systems; JJAS 2021+:", m.storm.nunique(), "systems")
print(m.groupby("storm").agg(start=("time", "min"), end=("time", "max"), basin=("basin", "first"), maxgrade=("grade", lambda g: ",".join(sorted(set(g.dropna())))) ).to_string())
