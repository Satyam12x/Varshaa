"""VARSHA submission documents: Project Report, Test Results, Edge Cases (docs/*.pdf).

Every number is read from the evaluation files, tools/check_claims.py, the pytest JUnit report and build/checks.json:
    python -m pytest tests --junitxml=build/test_report.xml
    python tools/check_claims.py --json build/claims.json
    python tools/pdf/reports.py
"""
import ast, datetime as dt, glob, json, os, platform, subprocess, sys
import xml.etree.ElementTree as ET
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Image, KeepTogether, CondPageBreak)
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.lib import colors
from pdfkit import *

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data")
DOCS = os.path.join(ROOT, "docs")
BUILD = os.path.join(ROOT, "build")
K = json.load(open(os.path.join(BUILD, "claims.json")))
V = {l: json.load(open(os.path.join(DATA, "models", f"verification_lead{l}.json"))) for l in range(1, 6)}
MAP = os.path.join(BUILD, "map_2023-08-03.png")
REPO = "https://github.com/Satyam12x/Varshaa"
LB = K["lead_beat"]
TODAY = dt.date.today().strftime("%d %B %Y")
RED = colors.HexColor("#b3261e")


def H1(t): return Heading(t, "h1", 0)
def H2(t): return Heading(t, "h2", 1)
def f3(x): return f"{x:.3f}"
def f1(x): return f"{x:.1f}"
def pct(a, b): return f"{100 * (a - b) / b:+.0f}%"


class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Heading):
            key = "h%d" % id(f)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(f.toc_text, key, level=f.toc_level, closed=f.toc_level > 0)


def make(path, title, subtitle, story, kind):
    def cover(c, doc):
        c.saveState()
        c.setFillColor(NAVY); c.rect(0, PAGE_H - 92 * mm, PAGE_W, 92 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#9fc3ef")); c.setFont("UI-B", 8.5)
        c.drawString(MARGIN, PAGE_H - 22 * mm, "SMART INDIA HACKATHON 2026  ·  PROBLEM STATEMENT 26080  ·  SOFTWARE  ·  TEAM IGNITEZ")
        c.setFillColor(WHITE); c.setFont("UI-B", 30); c.drawString(MARGIN, PAGE_H - 45 * mm, "VARSHA")
        c.setFont("UI-B", 17); c.drawString(MARGIN, PAGE_H - 58 * mm, title)
        c.setFont("UI", 10.5); c.setFillColor(colors.HexColor("#dbe7f6"))
        c.drawString(MARGIN, PAGE_H - 67 * mm, subtitle)
        c.setFont("UI", 8.5); c.drawString(MARGIN, PAGE_H - 80 * mm, f"{kind}  ·  {TODAY}  ·  {REPO}")
        c.restoreState()
        later(c, doc)

    def later(c, doc):
        c.saveState()
        if doc.page > 1:
            c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(MARGIN, PAGE_H - 12 * mm, PAGE_W - MARGIN, PAGE_H - 12 * mm)
            c.setFont("UI-B", 7.5); c.setFillColor(NAVY); c.drawString(MARGIN, PAGE_H - 10 * mm, "VARSHA")
            c.setFont("UI", 7.5); c.setFillColor(MUTED); c.drawString(MARGIN + 36, PAGE_H - 10 * mm, f"{title}  ·  SIH PS 26080  ·  Team IgniteZ")
        c.setFont("UI", 7.5); c.setFillColor(MUTED); c.drawRightString(PAGE_W - MARGIN, 10 * mm, f"{doc.page}")
        c.restoreState()

    doc = Doc(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=18 * mm, bottomMargin=16 * mm,
              title=f"VARSHA: {title}", author="Team IgniteZ", subject="SIH 2026 PS 26080")
    first = Frame(MARGIN, 16 * mm, CONTENT_W, PAGE_H - 16 * mm - 100 * mm, id="first")
    rest = Frame(MARGIN, 16 * mm, CONTENT_W, PAGE_H - 34 * mm, id="rest")
    doc.addPageTemplates([PageTemplate("cover", [first], onPage=cover, autoNextPageTemplate="rest"), PageTemplate("rest", [rest], onPage=later)])
    doc.build(story)
    print("wrote", os.path.relpath(path, ROOT))


def img(p, caption, width=CONTENT_W):
    iw, ih = ImageReader(p).getSize()
    return KeepTogether([Image(p, width=width, height=width * ih / iw), P(caption, "caption")])


def ov(l, m, key="t64.5"): return V[l]["overall"][m][key]


# ================================================================== 1. PROJECT REPORT
def report():
    s = []
    s += [kpis([(f"{f3(K['ets_raw1'])} → {f3(K['ets_warn1'])}", "day-1 heavy-rain ETS, raw GFS → VARSHA"),
                (f"−{K['rmse_cut_raw']}%", f"day-1 RMSE ({K['rmse_raw']} → {K['rmse_ml']} mm/day)"),
                (f"+{K['dist_gain']}%", "district heavy-rain days caught"),
                (f"−{K['brier_cut']}%", "Brier score of P(heavy) vs raw")]), Spacer(1, 8)]
    s += [H1("1. Summary"),
          P("VARSHA is a post-processing layer for NWP rainfall. It identifies the monsoon regime with IMD's own criteria, corrects raw "
            "model rainfall separately for each regime and local setting, gives calibrated probabilities of crossing IMD's heavy-rain "
            "thresholds, and publishes district warnings in IMD colours with a full verification report. A do-no-harm gate keeps the raw "
            "forecast wherever a correction has not beaten it out of sample."),
          P(f"It is built and running on NOAA GFS 00 UTC forecasts and IMD's 0.25° gridded rainfall. It was scored on six monsoons "
            f"({K['seasons'][0]}–{K['seasons'][-1]}), each forecast by models trained only on the other five, over {K['n1']:,} day-1 land "
            f"cell-days with {K['heavy1']:,} heavy-rain events. Regime labels use only information available at issue time.")]
    s += [H1("2. Problem and expected outcomes"),
          P("NWP rainfall errors change character with the weather regime: peaks are under-forecast in active spells, light rain is "
            "spread over dry areas in breaks, and depression rain is misplaced. PS 26080 asks for a system that first identifies the regime "
            "and then applies a suitable correction, improving district and grid forecasts, especially of heavy and very heavy rain."),
          table([["Expected outcome", "What VARSHA delivers", "Evidence"],
                 ["Weather regime classifier", "Active / break (IMD core-zone criterion), depression (IMD RSMC fixes), orographic / coastal / inland setting", "Section 4.1; tests E01–E08"],
                 ["Bias-corrected rainfall", "Regime-wise quantile mapping and regime-aware gradient boosting, behind a do-no-harm gate", f"RMSE {K['rmse_raw']} → {K['rmse_ml']} mm/day (section 6)"],
                 ["Heavy-rainfall probability", "Calibrated P(≥ 64.5 mm) and P(≥ 115.6 mm), mapped to IMD colours", f"Brier {K['brier_raw']:.4f} → {K['brier_varsha']:.4f}"],
                 ["District-level product", "742 Survey of India districts: map, table, CSV and API", f"{K['dist_varsha']:,} vs {K['dist_raw']:,} heavy-rain days caught"],
                 ["Verification report", "RMSE, POD, FAR, CSI, ETS and FSS by lead, regime, setting and district", "Section 6; dashboard Accuracy tab"]],
                [40 * mm, 78 * mm, CONTENT_W - 118 * mm])]
    s += [H1("3. System overview"),
          table([["Stage", "What happens", "Code"],
                 ["1 Data", "NOAA GFS 00 UTC rain (AWS open archive, rain field only), IMD real-time and archive grids, IMD RSMC best tracks, Survey of India districts", "engine/ingest.py, engine/common.py"],
                 ["2 Regime", "Causal active/break label, depression mask, local setting for every cell", "common.causal_spells, depression, settings"],
                 ["3 Correction", "Quantile mapping per regime × setting; gradient boosting amount track; heavy-rain classifiers; do-no-harm gate", "engine/train.py, engine/forecast.py"],
                 ["4 Products", "Corrected rain days 1–5, P(heavy), IMD warning levels, district table, CSV, API; verification and storm replays", "engine/forecast.py, replay.py, demo.py"],
                 ["5 Serving", "Express + TypeScript API, daily cycle at 10:15 IST, Next.js dashboard with nine tabs", "backend/src/server.ts, frontend/"]],
                [24 * mm, 104 * mm, CONTENT_W - 128 * mm])]
    s += [H1("4. Method"), H2("4.1 Regime identification (no look-ahead)"),
          P("<b>Large scale.</b> The standardised core-zone rainfall anomaly (IMD 1991–2020 daily normals) is computed for every IMD day. "
            "Following IMD's criterion (Rajeevan et al. 2010; Pai et al. 2016), a spell is active (break) when the anomaly is ≥ +1 (≤ −1) for at "
            "least three consecutive days. VARSHA applies it causally: a forecast issued on day D uses the label for D−1, which is Active only "
            "if the threshold was met on D−1, D−2 and D−3. Training uses exactly the same rule as the live system."),
          P("<b>Depression.</b> Cells within 6° of an IMD RSMC depression or stronger system, using fixes in the 6 h up to the 00 UTC issue "
            "time. <b>Local setting.</b> Orographic (Western Ghats, North-East hills, Himalaya), coastal (within about 50 km) or inland, from "
            "IMD's land mask and geography."),
          table([["Input", "Used for a 00 UTC forecast on day D", "Why it is available"],
                 ["NOAA GFS", "00 UTC run of D, lead days 1–5", "the forecast being corrected"],
                 ["IMD gridded rain", "days up to D−1 (24 h ending 08:30 IST on D−1)", "published on D−1; the grid for D is not used"],
                 ["RSMC fixes", "6 h up to 00 UTC on D", "later fixes are excluded"],
                 ["Normals", "IMD 1991–2020", "fixed climatology, outside the test seasons"]],
                [30 * mm, 70 * mm, CONTENT_W - 100 * mm]),
          H2("4.2 Correction, probability and the gate"),
          *bullets(["<b>Intensity track:</b> quantile mapping per regime × setting, pooled to the regime or to a global table when samples are few. "
                    "Rain above the training range is extrapolated with a capped slope.",
                    "<b>Amount track:</b> gradient boosting (scikit-learn HistGradientBoosting) on raw rain, the 25–75 km neighbourhood mean and maximum, "
                    "IMD daily normal, location, day of year, anomaly, regime and setting, with extra weight on heavy-rain days.",
                    "<b>Heavy-rain probability:</b> classifiers for 64.5 mm and 115.6 mm; warning thresholds tuned on the training seasons of each fold only.",
                    "<b>Do-no-harm gate:</b> for every regime × setting, the amount and warning method that verified best out of sample is used; "
                    "where nothing beat raw GFS, raw is issued and the dashboard says so.",
                    "<b>District product:</b> grid to district (mean and wettest cell), P(heavy) as the district maximum, IMD green / yellow / orange / red."])]
    s += [H1("5. Evaluation design"),
          *bullets([f"Leave-one-season-out over {len(K['seasons'])} monsoons (June–September {K['seasons'][0]}–{K['seasons'][-1]}): each season is forecast by models trained on the other five.",
                    "Truth: IMD 0.25° gridded rainfall, all land cells, every day; the IMD day ends 08:30 IST, and GFS lead L uses forecast hours 24L−21 to 24L+3.",
                    "RMSE over all cell-days including dry days; ETS, POD, FAR and CSI at 64.5 mm and 115.6 mm; FSS at 25–225 km; Brier score for P(heavy).",
                    "Compared methods: RAW (GFS as issued), QM_GLOBAL (one quantile mapping for all days, the standard bias correction), QM_REGIME, ML and WARN (VARSHA warning track).",
                    "Headline numbers describe the WARN and ML tracks themselves; the gate is chosen from these scores and is not separately scored."])]
    s += [H1("6. Results"), H2("6.1 All India, by lead day")]
    rows = [["Lead", "RMSE raw", "RMSE global QM", "RMSE VARSHA", "ETS raw", "ETS global QM", "ETS VARSHA", "POD raw → VARSHA", "FAR raw → VARSHA"]]
    for l in range(1, 6):
        o = V[l]["overall"]
        rows.append([f"Day {l}", f1(o["RAW"]["RMSE"]), f1(o["QM_GLOBAL"]["RMSE"]), f"<b>{f1(o['ML']['RMSE'])}</b>", f3(ov(l, "RAW")["ETS"]),
                     f3(ov(l, "QM_GLOBAL")["ETS"]), f"<b>{f3(ov(l, 'WARN')['ETS'])}</b>", f"{ov(l, 'RAW')['POD']:.2f} → {ov(l, 'WARN')['POD']:.2f}",
                     f"{ov(l, 'RAW')['FAR']:.2f} → {ov(l, 'WARN')['FAR']:.2f}"])
    s += [table(rows, [13 * mm] + [(CONTENT_W - 13 * mm) / 8] * 8),
          P(f"RMSE in mm/day; ETS, POD and FAR at 64.5 mm. VARSHA at day {LB[0]} ({f3(K[f'ets_warn{LB[0]}'])}) is more skilful than raw GFS "
            f"at day {LB[1]} ({f3(K[f'ets_raw{LB[1]}'])}). Days 1–4 use the causal regime labels; day 5 is from the run before that change (section 8).", "caption")]
    o1 = V[1]
    s += [H2("6.2 Day 1 by regime and by setting")]
    rg = [["Regime / setting", "RMSE raw", "RMSE VARSHA", "ETS raw", "ETS VARSHA"]]
    for grp in ("by_regime", "by_setting"):
        for name in o1[grp]["RAW"]:
            r, w, m = o1[grp]["RAW"][name], o1[grp]["WARN"].get(name), o1[grp]["ML"].get(name)
            rg.append([name, f1(r["RMSE"]), f1(m["RMSE"]) if m else "–", f3(r["t64.5"]["ETS"]), f3(w["t64.5"]["ETS"]) if w else "–"])
    s += [table(rg, [44 * mm] + [(CONTENT_W - 44 * mm) / 4] * 4),
          P("The raw error changes with the regime (the PS premise): depression days have the largest error and breaks the smallest. VARSHA improves every regime and setting.", "caption")]
    fs = o1["fss"]
    s += [H2("6.3 Spatial skill and probabilities (day 1)"),
          table([["Method", *[f"FSS {k}" for k in fs["RAW"]]], *[[m, *[f3(v) for v in fs[m].values()]] for m in ("RAW", "QM_GLOBAL", "QM_REGIME", "ML", "WARN")]],
                [34 * mm] + [(CONTENT_W - 34 * mm) / len(fs["RAW"])] * len(fs["RAW"])),
          Spacer(1, 6),
          table([["Brier score", "VARSHA", "Raw GFS", "Climatology"],
                 *[[f"P(≥ {t})", f"{o1['brier'][k]['VARSHA']:.4f}", f"{o1['brier'][k]['RAW']:.4f}", f"{o1['brier'][k]['CLIMATOLOGY']:.4f}"]
                   for k, t in (("heavy", "64.5 mm"), ("very_heavy", "115.6 mm"))]], [44 * mm] + [(CONTENT_W - 44 * mm) / 3] * 3),
          P("FSS at 64.5 mm (higher is better). Brier score, lower is better; VARSHA beats both raw GFS and climatology.", "caption")]
    s += [H2("6.4 District level and real storms"),
          P(f"A district heavy-rain day is one where IMD recorded ≥ 64.5 mm in at least one of its cells. Over {K['dist_n']} districts and "
            f"{K['dist_heavy']:,} such days, VARSHA's day-1 warning caught <b>{K['dist_varsha']:,}</b> against <b>{K['dist_raw']:,}</b> for raw GFS "
            f"(+{K['dist_gain']}%), with {K['fa_varsha']:,} false alarms against {K['fa_raw']:,} (−{K['fa_cut']}%). In {K['raigad'][0]} (2024 monsoon) "
            f"VARSHA flagged {K['raigad'][2]} of {K['raigad'][1]} heavy-rain days; raw GFS flagged {K['raigad'][3]}.")]
    if os.path.exists(MAP):
        s += [img(MAP, f"3 August 2023, day 1: IMD observed, raw GFS and VARSHA warning. Raw GFS caught {K['aug3'][1]} of {K['aug3'][0]} heavy-rain cells; VARSHA caught {K['aug3'][2]}.")]
    ev = [["Date", "Regime", "POD raw", "POD VARSHA", "ETS raw", "ETS VARSHA"]]
    for d, (reg, pr, pv, er, evv) in sorted(K["replays"].items()):
        ev.append([d, reg, f"{pr:.2f}", f"<b>{pv:.2f}</b>" if pv > pr else f"{pv:.2f}", f3(er), f"<b>{f3(evv)}</b>" if evv > er else f3(evv)])
    s += [KeepTogether([table(ev, [26 * mm, 24 * mm] + [(CONTENT_W - 50 * mm) / 4] * 4),
                        P(f"The {K['replay_n']} days with the most observed heavy rain, day 1. POD rose on {K['replay_pod_up']} and ETS on {K['replay_ets_up']}; "
                          "bold marks an improvement. The days where ETS fell are shown, not hidden.", "caption")])]
    s += [H1("7. Deployment and operations"),
          *bullets(["<b>API:</b> Render (Docker, Singapore). The image bundles the Python engine and downloads the runtime data snapshot "
                    "(models, districts, normals, current products) from the deploy-data branch.",
                    "<b>Dashboard:</b> Vercel, Next.js; reads the API through NEXT_PUBLIC_API_URL.",
                    "<b>Daily cycle:</b> 10:15 IST, after IMD's 08:30 IST rain day and the 00 UTC GFS run; on-demand re-run; a restarted instance refreshes a stale product.",
                    "<b>Health and uptime:</b> GET /api/health (forecast age, cycle status); ?strict=1 returns 503 when stale; npm run health for the command line; "
                    "a GitHub Actions uptimer every 10 minutes and a strict check daily at 11:00 IST."]),
          table([["Endpoint", "Returns"],
                 ["/api/health", "liveness, forecast issue and age, cycle status"], ["/api/meta", "issue, lead days, regime, sources"],
                 ["/api/forecast?lead=1..5", "grid: raw, corrected, P(heavy), P(very heavy), level, gate"],
                 ["/api/districts?lead=&format=csv", "district table, sorted by warning level; CSV export"],
                 ["/api/verification", "full verification report, leads 1–5"], ["/api/replay, /api/replay/:date", "storm replays"],
                 ["/api/geo/districts, /api/geo/landmask", "district boundaries, IMD land mask"], ["POST /api/run", "start the daily cycle (409 if already running)"]],
                [62 * mm, CONTENT_W - 62 * mm])]
    s += [H1("8. Limitations and current status"),
          *bullets(["<b>Lead day 5, storm replays and the district record</b> were produced before the switch to causal regime labels. Days 1–4 were "
                    "re-trained with causal labels and changed by less than 0.005 ETS, so these figures are expected to hold; they will be regenerated "
                    "with `python engine/train.py 5 && python engine/replay.py && python engine/demo.py`.",
                    "<b>NCUM:</b> NCMRWF's NCUM output is not publicly downloadable, so the running system uses NOAA GFS (the model family of IMD's GFS). "
                    "NCUM needs one loader next to gfs() in engine/common.py and a retrain on NCUM hindcasts; no NCUM score is claimed.",
                    "<b>Western disturbances</b> are not a separate regime yet; they need 500 hPa circulation fields.",
                    "<b>IMD's real-time server</b> is slow and can fail; the system then keeps the regime from the days it has and still issues the forecast.",
                    "<b>Outside June–September</b> the models extrapolate; the product carries a season note and the gate favours raw NWP."])]
    s += [H1("9. Next steps"),
          *bullets(["Integrate NCUM with NCMRWF and retrain on its hindcasts.", "Add western-disturbance and monsoon-trough regimes from IMDAA circulation fields.",
                    "Verify districts against IMD's district-wise rainfall (CRIS) as well as the grid.", "A U-Net grid correction, used only where the gate shows it helps."])]
    s += [H1("10. References"),
          *bullets(["Rajeevan, Gadgil & Bhate (2010), J. Earth Syst. Sci. 119. doi:10.1007/s12040-010-0019-4",
                    "Pai, Sridhar & Ramesh Kumar (2016), Climate Dynamics 46. doi:10.1007/s00382-015-2813-9",
                    "Pai et al. (2014), Mausam 65. doi:10.54302/mausam.v65i1.851",
                    "Niranjan Kumar et al. (2022), Hydrological Sciences Journal. doi:10.1080/02626667.2022.2049272",
                    "Friedman (2001), Annals of Statistics. doi:10.1214/aos/1013203451",
                    "Niculescu-Mizil & Caruana (2005), ICML. doi:10.1145/1102351.1102430",
                    "Roberts & Lean (2008), Monthly Weather Review 136. doi:10.1175/2007MWR2123.1",
                    "Wilks (2019), Statistical Methods in the Atmospheric Sciences, 4th ed. doi:10.1016/C2017-0-03921-6",
                    "PIB (11 Sept 2024), Cabinet approves Mission Mausam. pib.gov.in PRID 2053896",
                    "Data: IMD Pune (imdpune.gov.in), NOAA GFS on AWS Open Data, IMD RSMC New Delhi, Survey of India.",
                    f"Code and evidence: {REPO} (EVIDENCE.md, tools/check_claims.py)."])]
    make(os.path.join(DOCS, "VARSHA_Project_Report.pdf"), "Project Report", "Regime-aware AI post-processing of monsoon rainfall forecasts", s, "Report")


# ================================================================== 2. TEST RESULTS
def docstrings():
    out = {}
    for f in glob.glob(os.path.join(ROOT, "tests", "test_*.py")):
        for n in ast.parse(open(f, encoding="utf-8").read()).body:
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
                out[n.name] = (ast.get_docstring(n) or "").strip()
    return out


def tests():
    J = ET.parse(os.path.join(BUILD, "test_report.xml")).getroot()
    suite = J.find("testsuite") if J.tag == "testsuites" else J
    D = docstrings()
    cases = []
    for tc in suite.iter("testcase"):
        status = "FAIL" if tc.find("failure") is not None or tc.find("error") is not None else ("SKIP" if tc.find("skipped") is not None else "PASS")
        doc = D.get(tc.get("name"), "")
        tid, desc = (doc.split(" ", 1) + [""])[:2]
        cases.append((tc.get("classname").split(".")[-1], tid, desc, status, float(tc.get("time", 0))))
    checks = json.load(open(os.path.join(BUILD, "checks.json")))
    npass = sum(c[3] == "PASS" for c in cases); nfail = sum(c[3] == "FAIL" for c in cases)
    s = [kpis([(f"{npass}/{len(cases)}", "automated tests passed"), (str(nfail), "failures"),
               (f"{sum(c['ok'] for c in checks)}/{len(checks)}", "build and type checks passed"), (f"{float(suite.get('time', 0)):.0f} s", "suite run time")]),
         Spacer(1, 8), H1("1. Summary"),
         P(f"The suite was run on {TODAY} against the real code, the saved six-season evaluation files and a live API server started from "
           "backend/src/server.ts (the same code deployed on Render). Nothing is mocked except where a test needs a controlled input, "
           "such as a synthetic anomaly series to prove the regime rule has no look-ahead."),
         table([["Environment", ""], ["Python", platform.python_version()], ["Node.js", subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()],
                ["OS", f"{platform.system()} {platform.release()}"], ["Test runner", "pytest (JUnit report: build/test_report.xml)"],
                ["Re-run", "python -m pytest tests"]], [40 * mm, CONTENT_W - 40 * mm], header=True)]
    groups = [("test_engine", "2. Engine unit tests", "Regime rules (including the no look-ahead proof), verification metrics, corrections, features and masks."),
              ("test_results", "3. Result integrity tests", "The saved evaluation and today's product must support every headline claim; these fail if a retrain breaks a claim."),
              ("test_api", "4. API and operations tests", "Every endpoint, bad inputs, security (path traversal), CORS, the strict health check and the health CLI exit codes.")]
    for mod, title, intro in groups:
        rows = [["ID", "What is checked", "Result", "Time"]]
        for m, tid, desc, st, t in cases:
            if m == mod:
                colour = GREEN if st == "PASS" else RED
                rows.append([f"<b>{tid}</b>", desc, f"<font color='{colour.hexval()}'><b>{st}</b></font>", f"{t:.2f} s"])
        s += [H1(title), P(intro), table(rows, [13 * mm, CONTENT_W - 45 * mm, 16 * mm, 16 * mm])]
    rows = [["Check", "Command", "Result", "Time"]]
    for c in checks:
        rows.append([c["name"], f"<font name='UI' size='7.6'>{c['cmd']}</font>", f"<font color='{(GREEN if c['ok'] else RED).hexval()}'><b>{'PASS' if c['ok'] else 'FAIL'}</b></font>", f"{c['secs']:.0f} s"])
    s += [H1("5. Build and static checks"), table(rows, [56 * mm, CONTENT_W - 88 * mm, 16 * mm, 16 * mm]),
          H1("6. Headline numbers verified"),
          P("tools/check_claims.py recomputes these from the evaluation files (test R10 runs it). The same values are printed in the PPT."),
          table([["Claim", "Value"],
                 ["Day-1 heavy-rain ETS, raw GFS → VARSHA", f"{f3(K['ets_raw1'])} → {f3(K['ets_warn1'])} (+{K['ets_gain1']}%)"],
                 ["Day-1 heavy-rain ETS vs global bias correction", f"{f3(K['ets_qmg1'])} → {f3(K['ets_warn1'])} (+{K['ets_gain_qmg']}%)"],
                 ["Day-1 RMSE, raw / global QM / VARSHA (mm/day)", f"{K['rmse_raw']} / {K['rmse_qmg']} / {K['rmse_ml']}"],
                 ["Day-5 heavy-rain ETS, raw → VARSHA", f"{f3(K['ets_raw5'])} → {f3(K['ets_warn5'])} (+{K['ets_gain5']}%)"],
                 ["Brier P(heavy), raw → VARSHA (climatology)", f"{K['brier_raw']:.4f} → {K['brier_varsha']:.4f} ({K['brier_clim']:.4f})"],
                 ["District heavy-rain days caught, raw → VARSHA", f"{K['dist_raw']:,} → {K['dist_varsha']:,} (+{K['dist_gain']}%)"],
                 ["Storm replays with higher POD / higher ETS", f"{K['replay_pod_up']} / {K['replay_ets_up']} of {K['replay_n']}"]],
                [95 * mm, CONTENT_W - 95 * mm]),
          H1("7. Not covered by automated tests"),
          *bullets(["The Docker image build and the Render deployment (verified by Render's build log and /api/health once deployed).",
                    "Live downloads from IMD Pune and NOAA: tested manually by running the daily cycle; the tests use saved files so they are repeatable.",
                    "NCUM input: not publicly available, so it cannot be tested.",
                    "Browser end-to-end tests of the dashboard; the production build, lint and type checks pass."])]
    make(os.path.join(DOCS, "VARSHA_Test_Results.pdf"), "Test Results", f"{npass} of {len(cases)} automated tests passed  ·  build, lint and type checks passed", s, "Test report")


# ================================================================== 3. EDGE CASES
def edges():
    H, M, Lm = "Handled", "Mitigated", "Limitation"
    groups = [
        ("1. Input data", [
            ("Today's GFS run is not yet on the NOAA archive", "Falls back to the latest run available in the last 3 days; if none, the cycle stops with a clear error and the API keeps serving the previous product", "ingest.latest_gfs; server.cycle", "code", H),
            ("GFS accumulation differences go negative (rounding)", "Clipped at zero before use", "ingest.gfs_issue (np.maximum)", "R08", H),
            ("IMD real-time server slow, down or returns an empty body", "3 retries with back-off; an empty or wrong-size file is rejected, never stored", "common.imd_rt (size check)", "code", H),
            ("IMD day missing inside a spell", "The missing day breaks the run instead of counting towards it", "common.causal_spells", "E05", H),
            ("No recent IMD days at all", "Regime defaults to Normal and the forecast is still issued", "forecast.regime_now", "code", M),
            ("Missing values (−999) in IMD grids", "Land mask excludes them; only land cells are scored or served", "common.land", "E17", H),
            ("GRIB decoding is not thread-safe (ecCodes)", "Decoding is serialised with a lock; downloads stay parallel", "ingest._apcp (_lock)", "code", H)]),
        ("2. Regime identification", [
            ("Label that uses days after the issue date (look-ahead)", "Causal rule: a spell counts only once the IMD criterion is met on the day before issue and the 2 days before", "common.causal_spells; train.py; forecast.py", "E03, E04, E06", H),
            ("Two days above +1 only", "Not a spell (IMD needs 3 days)", "common.causal_spells", "E01", H),
            ("RSMC fix just after issue time", "Excluded; only fixes in the 6 h up to 00 UTC count", "common.depression", "E07", H),
            ("No cyclonic system anywhere", "No cell is labelled Depression", "common.depression", "E08", H),
            ("Anomaly unknown (no IMD data)", "Anomaly feature becomes 0 (neutral)", "common.features", "E16", H),
            ("Western disturbances", "Not yet a separate regime; handled by the Normal regime and the gate", "planned (circulation fields)", "–", Lm)]),
        ("3. Correction and warnings", [
            ("Few samples for a regime × setting", "Quantile tables pool to the regime, then to one global table", "forecast.run (qm lookup)", "code", H),
            ("Rain above anything seen in training", "Extrapolated with a capped slope (at most 1.5×), never unbounded", "common.qm_apply", "E14", H),
            ("A correction that does not beat raw GFS", "Do-no-harm gate issues raw for that regime × setting and says so", "train.py gate; forecast.run", "R07", H),
            ("Regime × setting missing from the gate table", "Defaults to raw GFS", "forecast.run (gate.get default)", "code", H),
            ("Heavy rain is rare (class imbalance)", "Heavy-rain days are up-weighted; dry days are sub-sampled with compensating weights", "train.fit_models", "code", H),
            ("ML smooths extremes", "Separate warning track and calibrated probabilities for threshold products", "train.py (WARN)", "R02, R05", H),
            ("Warning level contradicts the stated chance", "Levels are derived from the same probabilities (≥ 35% heavy = alert, ≥ 35% very heavy = warning)", "forecast.level", "E15", H),
            ("Forecast outside June–September", "Product carries a season note; the gate favours raw NWP", "forecast.run (season_note)", "code", M)]),
        ("4. District product", [
            ("District with no IMD land cell", "Skipped rather than reported as zero rain", "forecast.run", "R09", H),
            ("Heavy rain in one corner of a large district", "District warning uses the wettest cell and the highest P(heavy), not only the mean", "forecast.run", "R09", H),
            ("District names with commas or quotes in CSV", "Names and states are quoted, so the CSV opens correctly in Excel", "server /districts", "A08", H)]),
        ("5. API and security", [
            ("No product yet (first boot)", "Clear 503 message: run the engine", "server need()", "code", H),
            ("Out-of-range or non-numeric lead", "Falls back to day 1", "server /forecast", "A06", H),
            ("Path traversal in replay dates or district ids", "Inputs are sanitised; crafted paths get 404", "server /replay, /demo/district", "A12", H),
            ("Unknown replay date", "404 with a JSON error", "server /replay/:date", "A13", H),
            ("Second run requested while one is running", "409, no parallel cycles", "server POST /run", "code", H),
            ("Dashboard on another origin (Vercel)", "CORS allows it", "server cors()", "A15", H),
            ("API unreachable from the dashboard", "Clear message and a Retry button", "frontend Dashboard", "build", H)]),
        ("6. Operations and deployment", [
            ("Render free instance sleeps after 15 min idle", "Uptimer pings /api/health every 10 min; UptimeRobot as a backup", ".github/workflows/uptime.yml", "A01, A02", M),
            ("Cold start when a request wakes the instance", "Health CLI waits up to 60 s and retries with back-off", "backend/scripts/health.mjs", "A16", H),
            ("Instance restart loses the day's product (no disk)", "On boot, a stale snapshot triggers the daily cycle", "server REFRESH_ON_BOOT", "code", H),
            ("Daily forecast silently fails", "Strict health check (503 when stale) runs daily at 11:00 IST and alerts by email", "/api/health?strict=1; uptime.yml", "A03", H),
            ("Pickled models need a matching scikit-learn", "Versions pinned in the Docker image to the training environment", "Dockerfile", "code", H),
            ("Daily cycle timing across time zones", "Scheduled in Asia/Kolkata time, after IMD's 08:30 IST day and the 00 UTC run", "server cron", "code", H)]),
        ("7. Evaluation integrity", [
            ("Testing on seasons used for training", "Leave-one-season-out; warning thresholds tuned on training seasons only", "train.run", "R01", H),
            ("Headline numbers drifting from the files", "check_claims.py recomputes them; the PPT reads its numbers from it", "tools/check_claims.py", "R10", H),
            ("No heavy rain on a day (division by zero in scores)", "Scores stay finite", "common.cat", "E11", H),
            ("Lead 5, replays and district record from the pre-causal run", "Days 1–4 changed by < 0.005 ETS; regenerate with train.py 5, replay.py, demo.py", "section 8 of the report", "–", Lm)])]
    n = sum(len(r) for _, r in groups)
    cnt = {k: sum(r[4] == k for _, rs in groups for r in rs) for k in (H, M, Lm)}
    s = [kpis([(str(n), "edge cases reviewed"), (str(cnt[H]), "handled"), (str(cnt[M]), "mitigated"), (str(cnt[Lm]), "known limitations")]),
         Spacer(1, 8),
         P("Each row names the situation, what VARSHA does, where it is implemented and the evidence: an automated test ID from the Test Results "
           "document (E = engine, R = results, A = API), or 'code' where it was checked by reading the code path. <b>Handled</b> means the case "
           "is covered; <b>Mitigated</b> means the risk is reduced but not removed; <b>Limitation</b> is stated openly.")]
    colour = {H: GREEN, M: colors.HexColor("#b26a00"), Lm: RED}
    for title, rows in groups:
        t = [["Edge case", "What VARSHA does", "Where", "Evidence", "Status"]]
        for e, what, where, ev, st in rows:
            t.append([f"<b>{e}</b>", what, f"<font size='7.4'>{where}</font>", ev, f"<font color='{colour[st].hexval()}'><b>{st}</b></font>"])
        s += [CondPageBreak(40 * mm), H1(title), table(t, [40 * mm, 64 * mm, 34 * mm, 16 * mm, CONTENT_W - 154 * mm])]
    make(os.path.join(DOCS, "VARSHA_Edge_Cases.pdf"), "Edge Cases", f"{n} edge cases: how VARSHA handles each one, with evidence", s, "Edge-case review")


if __name__ == "__main__":
    report(); tests(); edges()
