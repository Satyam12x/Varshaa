"""Recompute every headline number in the VARSHA deck from the evaluation files, and say where each comes from.

    python tools/check_claims.py                 # reads data/ (local run)
    python tools/check_claims.py path/to/data    # e.g. a checkout of the deploy-data branch
    python tools/check_claims.py --json out.json # also write the numbers as JSON

All scores are leave-one-season-out on IMD's 0.25° grid, June to September 2021 to 2026: each monsoon is forecast by
models trained only on the other five. Regime labels use only information available at issue time (common.causal_spells).
"""
import json, os, sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = args[0] if args and not args[0].endswith(".json") else os.path.join(ROOT, "data")
OUT_JSON = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None

V = {l: json.load(open(os.path.join(DATA, "models", f"verification_lead{l}.json"))) for l in range(1, 6)}
DEMO = os.path.join(DATA, "products", "demo")
S = json.load(open(os.path.join(DEMO, "summary.json")))
RI = json.load(open(os.path.join(DATA, "products", "replay_index.json")))
pct = lambda new, old: round(100 * (new - old) / old)
K, rows = {}, []


def claim(key, value, text, source):
    K[key] = value
    rows.append((text, value, source))


v1 = V[1]
o = v1["overall"]
src1 = "models/verification_lead1.json"
claim("seasons", v1["seasons"], "Seasons scored (leave-one-season-out)", f"{src1}: seasons")
claim("n1", v1["n"], "Day-1 land cell-days scored", f"{src1}: n")
claim("days1", v1["days"], "Day-1 forecast days", f"{src1}: days")
claim("heavy1", v1["events"]["heavy"], "Day-1 heavy-rain events (>= 64.5 mm)", f"{src1}: events.heavy")
for k, name in (("RAW", "raw"), ("QM_GLOBAL", "qmg"), ("QM_REGIME", "qmr"), ("ML", "ml")):
    claim(f"rmse_{name}", round(o[k]["RMSE"], 1), f"Day-1 RMSE, mm/day, {k}", f"{src1}: overall.{k}.RMSE")
claim("rmse_cut_raw", -pct(o["ML"]["RMSE"], o["RAW"]["RMSE"]), "Everyday error cut vs raw GFS, % (ML amount track)", "rmse_ml vs rmse_raw")
claim("rmse_cut_qmg", -pct(o["ML"]["RMSE"], o["QM_GLOBAL"]["RMSE"]), "Everyday error cut vs global bias correction, %", "rmse_ml vs rmse_qmg")
for l in range(1, 6):
    ov = V[l]["overall"]
    claim(f"ets_raw{l}", round(ov["RAW"]["t64.5"]["ETS"], 3), f"Day-{l} heavy-rain ETS, raw GFS", f"verification_lead{l}.json: overall.RAW.t64.5.ETS")
    claim(f"ets_warn{l}", round(ov["WARN"]["t64.5"]["ETS"], 3), f"Day-{l} heavy-rain ETS, VARSHA warning", f"verification_lead{l}.json: overall.WARN.t64.5.ETS")
claim("ets_qmg1", round(o["QM_GLOBAL"]["t64.5"]["ETS"], 3), "Day-1 heavy-rain ETS, global bias correction", f"{src1}: overall.QM_GLOBAL.t64.5.ETS")
E = lambda l, k: V[l]["overall"][k]["t64.5"]["ETS"]
claim("ets_gain1", pct(E(1, "WARN"), E(1, "RAW")), "Day-1 heavy-rain ETS gain vs raw, %", "ets_warn1 vs ets_raw1")
claim("ets_gain5", pct(E(5, "WARN"), E(5, "RAW")), "Day-5 heavy-rain ETS gain vs raw, %", "ets_warn5 vs ets_raw5")
claim("ets_gain_qmg", pct(E(1, "WARN"), E(1, "QM_GLOBAL")), "Day-1 heavy-rain ETS gain vs global bias correction, %", "ets_warn1 vs ets_qmg1")
claim("pod_raw1", round(o["RAW"]["t64.5"]["POD"], 2), "Day-1 heavy-rain POD, raw", f"{src1}: overall.RAW.t64.5.POD")
claim("pod_warn1", round(o["WARN"]["t64.5"]["POD"], 2), "Day-1 heavy-rain POD, VARSHA", f"{src1}: overall.WARN.t64.5.POD")
# lead-time gain: the latest VARSHA day that still beats raw GFS at a shorter lead
beat = [(lw, lr) for lw in range(5, 1, -1) for lr in range(1, lw) if E(lw, "WARN") > E(lr, "RAW")]
lw, lr = max(beat, key=lambda t: t[0] - t[1]) if beat else (None, None)
claim("lead_beat", [lw, lr], "VARSHA day L1 beats raw GFS day L2 (heavy-rain ETS)", "ets_warn{L1} > ets_raw{L2}")
b = v1["brier"]["heavy"]
claim("brier_raw", round(b["RAW"], 4), "Day-1 Brier, P(heavy), raw", f"{src1}: brier.heavy.RAW")
claim("brier_varsha", round(b["VARSHA"], 4), "Day-1 Brier, P(heavy), VARSHA", f"{src1}: brier.heavy.VARSHA")
claim("brier_clim", round(b["CLIMATOLOGY"], 4), "Day-1 Brier, P(heavy), climatology", f"{src1}: brier.heavy.CLIMATOLOGY")
claim("brier_cut", -pct(b["VARSHA"], b["RAW"]), "Brier score cut vs raw, %", "brier_varsha vs brier_raw")
bs = v1["by_setting"]
claim("oro_raw", round(bs["RAW"]["Orographic"]["t64.5"]["ETS"], 3), "Orographic heavy-rain ETS, raw", f"{src1}: by_setting.RAW.Orographic")
claim("oro_warn", round(bs["WARN"]["Orographic"]["t64.5"]["ETS"], 3), "Orographic heavy-rain ETS, VARSHA", f"{src1}: by_setting.WARN.Orographic")
br = v1["by_regime"]["RAW"]
claim("rmse_dep", round(br["Depression"]["RMSE"], 1), "Raw RMSE on depression days, mm/day", f"{src1}: by_regime.RAW.Depression.RMSE")
claim("rmse_break", round(br["Break"]["RMSE"], 1), "Raw RMSE on break days, mm/day", f"{src1}: by_regime.RAW.Break.RMSE")
# district record (day 1): a heavy-rain day = IMD recorded >= 64.5 mm somewhere in the district
srcd = "products/demo/summary.json"
claim("dist_n", S["districts"], "Districts with heavy rain in the record", f"{srcd}: districts")
claim("dist_heavy", S["heavy"], "District heavy-rain days", f"{srcd}: heavy")
claim("dist_varsha", S["varsha"], "District heavy-rain days warned by VARSHA", f"{srcd}: varsha")
claim("dist_raw", S["raw"], "District heavy-rain days warned by raw GFS", f"{srcd}: raw")
claim("dist_gain", pct(S["varsha"], S["raw"]), "More district heavy-rain days caught, %", "dist_varsha vs dist_raw")
claim("fa_varsha", S["varsha_false"], "District false alarms, VARSHA", f"{srcd}: varsha_false")
claim("fa_raw", S["raw_false"], "District false alarms, raw", f"{srcd}: raw_false")
claim("fa_cut", -pct(S["varsha_false"], S["raw_false"]), "Fewer district false alarms, %", "fa_varsha vs fa_raw")
dists = {d["id"]: d for d in json.load(open(os.path.join(DATA, "boundaries", "districts.json"), encoding="utf-8"))}
top = S["best_2024"][0] if S["best_2024"] else None
raigad = next((x for x in S["best_2024"] if x["id"] == 187), top)
if raigad:
    claim("raigad", [dists[raigad["id"]]["name"], raigad["heavy"], raigad["varsha"], raigad["raw"]],
          "2024 district example: name, heavy days, VARSHA caught, raw caught", f"{srcd}: best_2024 (id {raigad['id']})")
# replays (day 1): the 14 biggest observed heavy-rain days
ev = RI["events"]
claim("replay_n", len(ev), "Storm days replayed", "products/replay_index.json: events")
claim("replay_pod_up", sum(e["pod_varsha"] > e["pod_raw"] for e in ev), "Replays where heavy-rain POD rose", "pod_varsha > pod_raw")
claim("replay_ets_up", sum(e["ets_varsha"] > e["ets_raw"] for e in ev), "Replays where ETS rose", "ets_varsha > ets_raw")
claim("replays", {e["date"]: [e["regime"], round(e["pod_raw"], 2), round(e["pod_varsha"], 2), round(e["ets_raw"], 3), round(e["ets_varsha"], 3)] for e in ev},
      "Per-replay regime, POD raw/VARSHA, ETS raw/VARSHA", "products/replay_index.json")
r = json.load(open(os.path.join(DATA, "products", "replay", "2023-08-03.json")))["leads"]["1"]["scores"]
claim("aug3", [r["raw"]["events"], r["raw"]["hits"], r["warning"]["hits"]], "3 Aug 2023, day 1: heavy cells, raw caught, VARSHA caught",
      "products/replay/2023-08-03.json: leads.1.scores")

w = max(len(t) for t, _, _ in rows)
for t, v, s in rows:
    if isinstance(v, dict): continue
    print(f"{t:<{w}}  {str(v):<28} {s}")
if OUT_JSON:
    json.dump(K, open(OUT_JSON, "w"), indent=1)
    print(f"wrote {OUT_JSON}")

if "--md" in sys.argv:
    md = sys.argv[sys.argv.index("--md") + 1]
    lines = [
        "# VARSHA evidence: where every headline number comes from", "",
        "Generated by `python tools/check_claims.py --md EVIDENCE.md`. The evaluation files are on the "
        "[`deploy-data`](https://github.com/Satyam12x/Varshaa/tree/deploy-data) branch (`models/`, `products/`); "
        "run `python tools/check_claims.py <checkout-of-deploy-data>` to recompute everything below.", "",
        "## How the scores are produced", "",
        f"- **Held out by season.** Seasons {K['seasons'][0]}–{K['seasons'][-1]} (June to September). Each monsoon is forecast by models "
        "trained only on the other five (`engine/train.py`, leave-one-season-out). Warning thresholds are also chosen without the test season.",
        "- **Grid and truth.** Every IMD 0.25° land cell, every day. Truth is IMD's gridded rainfall for the 24 h ending 08:30 IST.",
        f"- **Metrics.** RMSE in mm/day over all {K['n1']:,} day-1 land cell-days (dry days included). ETS, POD and FAR at IMD's 64.5 mm heavy-rain "
        "threshold. Brier score for P(rain ≥ 64.5 mm).",
        "- **Methods compared.** RAW = NOAA GFS 00 UTC as issued; QM_GLOBAL = one quantile-mapping correction for all days (the standard bias correction); "
        "QM_REGIME = quantile mapping per regime × setting; ML = regime-aware gradient boosting (amount track); WARN = VARSHA warning track.",
        "- **What the headline numbers describe.** The WARN and ML tracks themselves. The do-no-harm gate is chosen from these same "
        "out-of-sample scores, so it is used for live forecasting and is not itself scored in the claims below.", "",
        "## What a forecast can see (no look-ahead)", "",
        "For a forecast issued at 00 UTC (05:30 IST) on day D:", "",
        "| Input | Used | Why it is available at issue time |", "|---|---|---|",
        "| NOAA GFS 00 UTC run of D | lead days 1–5 | it is the forecast being corrected |",
        "| IMD gridded rainfall | days up to D−1 (24 h ending 08:30 IST on D−1) | published by IMD on D−1; the grid for D itself is **not** used |",
        "| Large-scale regime | IMD's criterion applied causally: Active/Break on D−1 only if the core-zone anomaly was ≥ +1 / ≤ −1 on D−1, D−2 and D−3 "
        "(`common.causal_spells`) | uses only the IMD days above; the same rule in training and in the live system |",
        "| Depression regime | IMD RSMC fixes in the 6 h up to 00 UTC on D | fixes after issue time are excluded |",
        "| Daily normals | IMD 1991–2020 | fixed climatology, outside the test seasons |",
        "| Regime for lead days 2–5 | the regime known at issue, carried forward | no future regime is used |", "",
        "The regime timeline in the dashboard uses IMD's retrospective labels (a spell is labelled from its first day). That is for monitoring only; "
        "training and forecasting use the causal labels above.", "",
        "## Headline numbers", "",
        "| Claim | Value | Source |", "|---|---|---|",
        *[f"| {t} | {v if not isinstance(v, list) else ', '.join(map(str, v))} | `{s}` |" for t, v, s in rows if not isinstance(v, dict)],
        "", "## Running today vs proposed", "",
        "- **Running today:** NOAA GFS 00 UTC (AWS Open Data) → regime → correction → district product, automatically at 10:15 IST (`backend/src/server.ts`).",
        "- **Proposed for NCMRWF:** NCUM output through one loader in `engine/common.py` (next to `gfs()`), then `engine/train.py` on NCUM hindcasts. "
        "NCUM is not publicly downloadable, so no NCUM score is claimed.", ""]
    open(md, "w", encoding="utf-8").write("\n".join(lines))
    print(f"wrote {md}")
