# VARSHA: Regime-Aware AI Post-Processing of Monsoon Rainfall (SIH PS 26080)

VARSHA identifies the monsoon regime the way IMD does. It then corrects raw NWP rainfall for that regime and publishes verified district-level heavy-rainfall guidance for India.

- `engine/`: Python engine (regime classifier, corrections, heavy-rain probabilities, district product, verification)
- `backend/`: Express + TypeScript API, and the daily automation that runs the engine
- `frontend/`: Next.js dashboard (one tab per expected outcome)
- `docs/`: solution document (PDF)
- `tools/`: data download scripts, pilot studies and the PDF generator
- `data/`: official source files (not for git; about 1 GB)

## Run it

```bash
# one-off: data (skip anything already present)
cd tools/data && python gfs_download.py        # NOAA GFS rain, monsoons 2021–2026
                 python rsmc_parse.py          # IMD RSMC best tracks -> CSV
                 python districts.py           # Survey of India districts -> IMD grid
cd ../../engine && python train.py             # six-season verification + final models (~40 min)
                   python ingest.py            # today's GFS run + recent IMD grids
                   python forecast.py          # today's products
                   python replay.py            # event replays

# servers
cd backend && npm install && npm run dev       # http://localhost:4080/api
cd frontend && npm install && npm run dev      # http://localhost:3000
```

Python needs `numpy pandas scipy scikit-learn eccodes openpyxl shapely`. The backend runs the daily cycle (ingest, forecast, replay) at 10:15 IST, or on demand with `POST /api/run` or the *Data & automation* tab.

## Data: official sources only

| Data | Source | Use |
|---|---|---|
| Daily 0.25° gridded rainfall, 1991–2025 archive and 2026 real time | **IMD** Pune (imdpune.gov.in) | Truth, training, 1991–2020 normals, current regime |
| GFS 00 UTC rainfall, lead days 1–5 | **NOAA** official archive (AWS Open Data `noaa-gfs-bdp-pds`); only the rain field is downloaded | Raw NWP being corrected (model family of IMD's operational GFS) |
| Best tracks of depressions and cyclones, 1982–2026 | **IMD RSMC New Delhi**; workbook checksum-verified | Depression regime |
| District boundaries (742) | **Survey of India** | District product |
| Active/break criterion | **IMD Pune** (Rajeevan et al.; Pai et al.) | Regime classifier definition |

NCMRWF's NCUM output is not publicly downloadable. The engine is model-agnostic, so NCUM plugs in by adding one loader in `engine/common.py`.

Verified conventions:
- The IMD rainfall grid for date D is the 24 h total ending 08:30 IST on D.
- GFS lead L uses forecast hours 24L−21 to 24L+3. Day-1 spatial correlation with IMD is 0.41 on the intended date, against 0.32 and 0.30 a day either side.

## How it works

1. **Regime.** The large-scale regime uses IMD's criterion: the standardised core-zone rainfall anomaly (1991–2020 normals) is ≥ +1 (active) or ≤ −1 (break) for at least 3 consecutive days. The depression regime covers cells within 6° of an IMD RSMC system at issue time. The local setting (orographic, coastal or inland) comes from IMD's land mask and geography.
2. **Correction.** Two methods, each learnt per regime and setting:
   - regime-wise quantile mapping, which preserves intensity
   - regime-aware gradient boosting, which gives the smallest everyday error
   
   Features: raw rain, the surrounding 25–75 km, the IMD daily normal, the regime and the setting.
3. **Heavy-rain probability.** Calibrated classifiers for 64.5 and 115.6 mm, with warning thresholds chosen on past seasons only.
4. **Do-no-harm gate.** For each regime and setting, the method that beat raw GFS out of sample is used. Where nothing beat it, the raw forecast is issued.
5. **District product and verification.** Survey of India districts, with IMD colour codes and CSV export. Verification reports RMSE, POD, FAR, CSI, ETS and FSS by regime, setting and district.

All verification is leave-one-season-out: each monsoon is forecast by models trained only on the other seasons.
