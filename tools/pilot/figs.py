"""Figures for the PS 26080 solution document, from pilot outputs."""
import json, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "fig"); os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "figure.dpi": 200})
BLUE, ORANGE, GREY, INK, RED, GREEN = "#2a78d6", "#eb6834", "#b9b8b2", "#0b0b0b", "#d7262c", "#1baf7a"
R = json.load(open(os.path.join(HERE, "pilot_results.json")))

# ---- regime timeline
reg = pd.read_csv(os.path.join(HERE, "regimes_2026.csv"), parse_dates=["date"])
fig, ax = plt.subplots(figsize=(10, 2.9))
col = reg.regime.map({"Active": BLUE, "Break": ORANGE, "Normal": GREY})
ax.bar(reg.date, reg.anom, color=col, width=0.9)
for y in (1, -1): ax.axhline(y, color="#8a8984", lw=0.8, ls="--")
ax.axhline(0, color="#8a8984", lw=0.6)
ax.set_ylabel("Standardised anomaly")
ax.set_title("2026 monsoon: core-zone rainfall anomaly from IMD 0.25° grids (normals: IMD 1991–2020)", fontsize=9.5, color=INK, loc="left")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label="Active spell (≥ +1 for ≥ 3 days)"), Patch(color=ORANGE, label="Break spell (≤ −1 for ≥ 3 days)"),
                   Patch(color=GREY, label="Normal")], frameon=False, fontsize=8, loc="upper right", ncol=3)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "regime_timeline.png")); plt.close(fig)

# ---- raw error by regime and by location type (the PS premise)
run = R["runs"]["gfs_seamless|1"]["methods"]["RAW"]
run2 = R["runs"]["ukmo_seamless|1"]["methods"]["RAW"]
fig, axs = plt.subplots(1, 2, figsize=(10, 2.8))
for ax, key, title in [(axs[0], "by_regime", "Raw forecast error by monsoon regime (day 1)"), (axs[1], "by_loctype", "Raw forecast error by rainfall setting (day 1)")]:
    cats = list(run[key].keys())
    x = np.arange(len(cats)); w = 0.38
    ax.bar(x - w / 2, [run[key][c] for c in cats], w, color=BLUE, label="NCEP GFS")
    ax.bar(x + w / 2, [run2[key].get(c, np.nan) for c in cats], w, color=ORANGE, label="UK Met Office UM")
    ax.set_xticks(x); ax.set_xticklabels([c.replace(" / ", "/\n").replace("West-coast ", "West-coast\n") for c in cats], fontsize=8)
    ax.set_ylabel("RMSE (mm/day)"); ax.set_title(title, fontsize=9.5, color=INK, loc="left")
axs[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "error_by_regime.png")); plt.close(fig)

# ---- method comparison: RMSE and heavy-rain ETS
M = ["RAW", "QM_GLOBAL", "QM_REGIME", "ML_REGIME"]
LAB = {"RAW": "Raw NWP", "QM_GLOBAL": "Single global\ncorrection", "QM_REGIME": "Regime-wise\ncorrection", "ML_REGIME": "Regime-aware\nML"}
COL = {"RAW": GREY, "QM_GLOBAL": "#8a8984", "QM_REGIME": BLUE, "ML_REGIME": GREEN}
fig, axs = plt.subplots(1, 2, figsize=(10, 3.1))
keys = [("gfs_seamless|1", "GFS d1"), ("gfs_seamless|3", "GFS d3"), ("ukmo_seamless|1", "UKMO d1"), ("ukmo_seamless|3", "UKMO d3")]
x = np.arange(len(keys)); w = 0.2
for i, m in enumerate(M):
    axs[0].bar(x + (i - 1.5) * w, [R["runs"][k]["methods"][m]["RMSE"] for k, _ in keys], w, color=COL[m], label=LAB[m].replace("\n", " "))
    axs[1].bar(x + (i - 1.5) * w, [R["runs"][k]["methods"][m]["t64.5"]["ETS"] for k, _ in keys], w, color=COL[m])
for ax, t in [(axs[0], "Everyday error: RMSE (mm/day), lower is better"), (axs[1], "Heavy rain (≥ 64.5 mm): ETS, higher is better")]:
    ax.set_xticks(x); ax.set_xticklabels([n for _, n in keys]); ax.set_title(t, fontsize=9.5, color=INK, loc="left")
axs[0].legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "methods.png")); plt.close(fig)
print("figures written")
