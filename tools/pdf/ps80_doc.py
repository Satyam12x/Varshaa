"""PS 26080 solution document: problem understanding, expected outcomes, our solution (VARSHA), USPs, pilot evidence,
feasibility and viability. Numbers are read from ../pilot/pilot_results.json (real IMD + NWP data)."""
import json, os
import pandas as pd
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Image, KeepTogether,
                                NextPageTemplate, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, PolyLine
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from pdfkit import *

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.join(HERE, "..", "pilot")
OUT = os.path.join(HERE, "..", "..", "docs", "VARSHA_PS26080_Solution_Document.pdf")
R = json.load(open(os.path.join(PILOT, "pilot_results.json")))
RUNS = R["runs"]
KEYS = [("gfs_seamless|1", "NCEP GFS", 1), ("gfs_seamless|3", "NCEP GFS", 3), ("ukmo_seamless|1", "UK Met Office UM", 1), ("ukmo_seamless|3", "UK Met Office UM", 3)]
REG = pd.read_csv(os.path.join(PILOT, "regimes_2026.csv"), parse_dates=["date"])

big = ParagraphStyle("big", parent=ST["body"], fontSize=10, leading=14.6)
quote = ParagraphStyle("quote", parent=ST["callout"], fontName="UI-B", fontSize=10.8, leading=15.5, textColor=NAVY)


def B(t): return Paragraph(t, big)
def H1(t): return Heading(t, "h1", 0)
def H2(t): return Heading(t, "h2", 1)
def H3(t): return P(t, "h3")
def m(key, meth): return RUNS[key]["methods"][meth]
def pct(a, b): return 100 * (1 - a / b)


# ------------------------------------------------------------------ derived facts (computed, never typed)
ets = {k: {mm_: m(k, mm_)["t64.5"]["ETS"] for mm_ in ["RAW", "QM_GLOBAL", "QM_REGIME", "ML_REGIME"]} for k, _, _ in KEYS}
regime_beats_global = sum(ets[k]["QM_REGIME"] > ets[k]["QM_GLOBAL"] for k, _, _ in KEYS)
global_below_raw = sum(ets[k]["QM_GLOBAL"] < ets[k]["RAW"] for k, _, _ in KEYS)
regime_beats_raw = sum(ets[k]["QM_REGIME"] > ets[k]["RAW"] for k, _, _ in KEYS)
rmse_gain = [pct(m(k, "ML_REGIME")["RMSE"], m(k, "RAW")["RMSE"]) for k, _, _ in KEYS]
brier = {k: RUNS[k]["brier"] for k, _, _ in KEYS}
brier_best = sum(brier[k]["P_ML"] < min(brier[k]["P_RAW"], brier[k]["CLIM"]) for k, _, _ in KEYS)
n_cases = sum(RUNS[k]["n"] for k, _, _ in KEYS)
events = RUNS["gfs_seamless|1"]["methods"]["RAW"]["t64.5"]["events"]
spells = []
REG["blk"] = (REG.regime != REG.regime.shift()).cumsum()
for _, g in REG.groupby("blk"):
    if g.regime.iloc[0] != "Normal":
        spells.append((g.regime.iloc[0], g.date.min(), g.date.max(), len(g)))
raw_by_reg = m("gfs_seamless|1", "RAW")["by_regime"]
raw_by_lt = m("gfs_seamless|1", "RAW")["by_loctype"]
PERIOD = RUNS["gfs_seamless|1"]["period"]


class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Heading):
            key = "h%d" % id(f)
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (f.toc_level, f.toc_text, self.page, key))
            self.canv.addOutlineEntry(f.toc_text, key, level=f.toc_level, closed=f.toc_level > 0)


def cover(c, doc):
    c.saveState()
    c.setFillColor(NAVY); c.rect(0, PAGE_H - 118 * mm, PAGE_W, 118 * mm, stroke=0, fill=1)
    c.setFillColor(BLUE); c.rect(0, PAGE_H - 121 * mm, PAGE_W, 3 * mm, stroke=0, fill=1)
    x = MARGIN
    c.setFillColor(colors.HexColor("#9ec5f4")); c.setFont("UI-B", 9.5)
    c.drawString(x, PAGE_H - 30 * mm, "SMART INDIA HACKATHON 2026  ·  PROBLEM STATEMENT 26080  ·  SOFTWARE  ·  SMART AUTOMATION")
    c.setFillColor(WHITE); c.setFont("UI-B", 40); c.drawString(x, PAGE_H - 52 * mm, "VARSHA")
    c.setFont("UI-L", 15); c.drawString(x, PAGE_H - 62 * mm, "Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts")
    c.setFont("UI", 10.5); c.setFillColor(colors.HexColor("#cde2fb"))
    c.drawString(x, PAGE_H - 73 * mm, "Identify the monsoon regime the way IMD does, correct raw NWP rainfall for that regime,")
    c.drawString(x, PAGE_H - 79 * mm, "and deliver verified district-level heavy-rainfall guidance.")
    c.setFont("UI-I", 9); c.setFillColor(colors.HexColor("#9ec5f4"))
    c.drawString(x, PAGE_H - 100 * mm, "Varsha: Sanskrit and Hindi for rain.")
    y = PAGE_H - 140 * mm
    rows = [("Problem Statement ID", "26080"), ("Title", "Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts"),
            ("Organisation", "Ministry of Earth Sciences (MoES)"), ("Department", "National Centre for Medium Range Weather Forecasting (NCMRWF)"),
            ("Category / Theme", "Software  ·  Smart Automation"), ("Team", "IgniteZ"),
            ("Document", "Solution concept, USPs, pilot evidence, feasibility & viability  ·  v1.0")]
    for k, v in rows:
        c.setFillColor(MUTED); c.setFont("UI", 9); c.drawString(x, y, k.upper())
        c.setFillColor(INK); c.setFont("UI-B", 10.5); c.drawString(x + 48 * mm, y, v)
        c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(x, y - 3.2 * mm, PAGE_W - MARGIN, y - 3.2 * mm)
        y -= 10 * mm
    y -= 6 * mm
    c.setFillColor(PANEL); c.rect(x, y - 26 * mm, CONTENT_W, 28 * mm, stroke=0, fill=1)
    c.setFillColor(NAVY); c.setFont("UI-B", 9); c.drawString(x + 5 * mm, y - 3 * mm, "PILOT ON REAL IMD DATA (section 7)")
    items = [(f"{regime_beats_global}/4", "tests where regime-wise correction", "beat a single global correction"),
             (f"{min(rmse_gain):.0f}–{max(rmse_gain):.0f}%", "lower everyday error from", "regime-aware ML vs raw NWP"),
             (f"{brier_best}/4", "tests where our heavy-rain probability", "beat raw NWP and climatology")]
    w = CONTENT_W / 3
    for i, (n, a, b) in enumerate(items):
        cx = x + w * i + w / 2
        c.setFillColor(BLUE); c.setFont("UI-B", 20); c.drawCentredString(cx, y - 13 * mm, n)
        c.setFillColor(MUTED); c.setFont("UI", 8); c.drawCentredString(cx, y - 18 * mm, a); c.drawCentredString(cx, y - 21.5 * mm, b)
    c.restoreState()


def later(c, doc):
    c.saveState()
    c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(MARGIN, PAGE_H - 12 * mm, PAGE_W - MARGIN, PAGE_H - 12 * mm)
    c.setFont("UI-B", 7.5); c.setFillColor(NAVY); c.drawString(MARGIN, PAGE_H - 10 * mm, "VARSHA")
    c.setFont("UI", 7.5); c.setFillColor(MUTED)
    c.drawString(MARGIN + 36, PAGE_H - 10 * mm, "Regime-Aware AI Post-Processing of Monsoon Rainfall  ·  SIH PS 26080  ·  Team IgniteZ")
    c.drawRightString(PAGE_W - MARGIN, 10 * mm, f"{doc.page}")
    c.restoreState()


def fig(name, caption, width=CONTENT_W):
    p = os.path.join(PILOT, "fig", name)
    iw, ih = ImageReader(p).getSize()
    return KeepTogether([Image(p, width=width, height=width * ih / iw), P(caption, "caption")])


# ------------------------------------------------------------------ diagrams
def architecture():
    W, H = CONTENT_W, 300
    d = Drawing(W, H)
    label(d, 62, H - 10, "Inputs (official)", 7.8, NAVY, font="UI-B")
    ins = [("Raw NWP rainfall", "NCUM / IMD-GFS (target);", "GFS · UKMO · ECMWF (pilot)"),
           ("IMD gridded rainfall", "0.25° real-time + 1991–2020", "(truth and normals)"),
           ("Circulation fields", "850 hPa wind · MSLP", "500 hPa height (IMDAA / NWP)"),
           ("IMD records", "depression tracks (RSMC)", "district rainfall (CRIS)"),
           ("Static maps", "terrain (orography)", "coastline · district boundaries")]
    for i, t in enumerate(ins):
        y = H - 22 - (i + 1) * 50 - i * 5 + 5
        dbox(d, 0, y, 124, 50, list(t), fill=colors.HexColor("#eef0f3"), stroke=colors.HexColor("#8a8984"), size=7.2)
        arrow(d, 124, y + 25, 148, H / 2 + 20, c=colors.HexColor("#8a8984"), w=0.8)
    cx, cw = 150, 192
    label(d, cx + cw / 2, H - 10, "VARSHA core", 7.8, NAVY, font="UI-B")
    steps = [("1  Regime classifier", "active · break · depression · WD (large scale)", "orographic · coastal · inland (local)"),
             ("2  Regime-specific correction", "regime-wise quantile mapping (intensity)", "regime-aware gradient boosting (amount)"),
             ("3  Heavy-rain probability", "calibrated classifier per IMD threshold", "64.5 · 115.6 · 204.5 mm"),
             ("4  Do-no-harm gate", "per regime × lead × area: use correction", "only where it beats raw NWP out of sample"),
             ("5  District product + verification", "grid → district · IMD colour codes", "RMSE · ETS · CSI · POD · FAR · FSS")]
    ys = []
    for i, t in enumerate(steps):
        y = H - 24 - (i + 1) * 50 - i * 6 + 6
        ys.append(y)
        dbox(d, cx, y, cw, 50, list(t), fill=NAVY if i == 3 else PANEL, stroke=NAVY if i == 3 else BLUE, tc=WHITE if i == 3 else INK, size=7.2)
        if i: arrow(d, cx + cw / 2, ys[i - 1], cx + cw / 2, y + 50.5)
    ox = cx + cw + 24; ow = W - ox
    label(d, ox + ow / 2, H - 10, "Expected outcomes", 7.8, NAVY, font="UI-B")
    outs = [("Weather regime classifier", "daily regime map + timeline"), ("Bias-corrected rainfall", "grid and district, days 1–5"),
            ("Heavy-rainfall probability", "P(≥ IMD thresholds)"), ("District-level product", "table + map, IMD colours, CSV"),
            ("Verification report", "all 6 metrics, by regime")]
    for i, (a, b) in enumerate(outs):
        y = H - 22 - (i + 1) * 50 - i * 5 + 5
        dbox(d, ox, y, ow, 50, [a, b], fill=colors.HexColor("#fdf1eb"), stroke=ORANGE, size=7.3)
        arrow(d, cx + cw, ys[min(i, 4)] + 25, ox - 1, y + 25, c=ORANGE, w=0.8)
    return d


def regime_tree():
    W, H = CONTENT_W, 150
    d = Drawing(W, H)
    dbox(d, W / 2 - 120, 118, 240, 28, ["Target day × grid cell / district"], fill=PANEL, stroke=BLUE, size=8.5)
    cols = [("Large-scale regime (one per day)", ["Active monsoon · Break monsoon", "IMD core-zone anomaly ≥ +1 / ≤ −1, ≥ 3 days", "Monsoon low / depression", "IMD RSMC tracks + MSLP minimum", "Western disturbance", "500 hPa trough over NW India"]),
            ("Local rainfall setting (per cell)", ["Orographic", "windward slope × onshore 850 hPa wind", "Coastal", "within 50 km of coast, onshore flow", "Inland / plains", "everything else"])]
    w = (W - 20) / 2
    for i, (title, lines) in enumerate(cols):
        x = i * (w + 20)
        dbox(d, x, 6, w, 96, [title] + lines, fill=WHITE, stroke=[BLUE, ORANGE][i], size=7.4)
        arrow(d, W / 2, 117, x + w / 2, 103)
    return d


# ------------------------------------------------------------------ story
story = [NextPageTemplate("later"), PageBreak()]
toc = TableOfContents(); toc.levelStyles = [ST["toc1"], ST["toc2"]]
story += [P("Contents", "h1"), toc, PageBreak()]

story += [H1("1. Executive Summary"),
          B("Rainfall forecasts from weather models go wrong in different ways depending on the weather situation. A model may "
            "under-forecast Western Ghats downpours in an active monsoon, spread drizzle everywhere in a break spell, and misplace the "
            "heavy rain of a monsoon depression. PS 26080 asks for an AI/ML system that <b>first recognises the regime, then applies "
            "the right correction</b>, improving district and grid-level rainfall, especially heavy and very heavy events."),
          B("<b>VARSHA</b> does exactly that, in five steps: (1) a regime classifier built on <b>IMD's own operational definitions and "
            "data</b>; (2) regime-specific correction of raw NWP rainfall; (3) calibrated probabilities of crossing IMD's heavy-rain "
            "thresholds; (4) a “do-no-harm” gate that uses a correction only where it has beaten the raw model; and (5) a district "
            "rainfall table and map with a full verification report."),
          B(f"<b>We tested the core idea on real data before writing this document.</b> Using IMD's 0.25° rainfall grids for the 2026 "
            f"monsoon, IMD's 1991–2020 gridded archive for normals, and archived forecasts from NOAA GFS and the UK Met Office model "
            f"(the same model family as NCMRWF's NCUM) at 36 cities, we ran {n_cases:,} forecast-versus-IMD comparisons:"),
          kpis([(f"{regime_beats_global}/4", "tests where regime-wise correction beat one global correction on heavy rain (ETS)"),
                (f"{global_below_raw}/4", "tests where a single global correction made heavy-rain skill worse than raw"),
                (f"{min(rmse_gain):.0f}–{max(rmse_gain):.0f}%", "lower everyday error (RMSE) from regime-aware ML"),
                (f"{brier_best}/4", "tests where our heavy-rain probability beat raw NWP and climatology")]),
          Spacer(1, 8),
          B("This directly confirms the problem statement's premise: <b>a single correction does not work equally well in all "
            "situations, and a regime-aware one does better.</b>"),
          B("<b>Our differentiators (section 6):</b>"),
          *bullets(["<b>USP 1, official and auditable regimes:</b> regimes are computed with IMD's published active/break criterion, "
                    "IMD's own gridded data and IMD's depression records, so NCMRWF can check every label against IMD's monitoring. "
                    "It is not a black-box clustering that nobody can verify.",
                    "<b>USP 2, the right correction for each job, with a do-no-harm gate:</b> separate products for rainfall amount, "
                    "heavy-rain intensity and heavy-rain probability, each using the method that verifies best, plus an automatic "
                    "fallback to raw NWP wherever a correction has not proven itself.",
                    "<b>USP 3, verified where it is used:</b> district forecasts are verified against IMD's official district rainfall, "
                    "with all six required scores broken down by regime, and every number is traceable to official data."]),
          PageBreak()]

story += [H1("2. Problem Understanding"),
          H2("2.1 Why rainfall forecast errors depend on the regime"),
          B("A numerical weather prediction (NWP) model solves the physics of the atmosphere on a grid. Rainfall is its hardest output, "
            "because it depends on processes smaller than the grid, such as clouds, convection and air being forced up mountains. "
            "Those processes behave differently in different weather regimes, so the model's errors change character with the regime:"),
          table([["Regime", "What happens", "Typical NWP error"],
                 ["Active monsoon", "Monsoon trough over central India; widespread, persistent rain; strong westerlies onto the west coast", "Under-forecast of peak intensity; west-coast totals too low"],
                 ["Break monsoon", "Trough shifts to the Himalayan foothills; central India dry; rain along the foothills and south-east India", "Too much light rain in dry areas; foothill heavy rain missed"],
                 ["Monsoon low / depression", "Low-pressure system moving west-north-west from the Bay of Bengal; very heavy rain in a band", "Track or speed errors put heavy rain in the wrong districts"],
                 ["Orographic rainfall", "Moist wind forced up the Western Ghats or north-eastern hills", "Coarse terrain in the model smooths out the peak"],
                 ["Coastal rainfall", "Onshore flow and land–sea contrast along the coasts", "Rain placed offshore or smeared inland"],
                 ["Western disturbance", "Mid-latitude trough reaching north-west India (mainly winter; can interact with the monsoon)", "Timing and extent of rain and snow over hills"]],
                [CONTENT_W * 0.2, CONTENT_W * 0.45, CONTENT_W * 0.35]),
          Spacer(1, 6),
          H2("2.2 Evidence from real data"),
          B(f"We measured the raw error of NOAA GFS's day-1 rainfall against IMD's grid at 36 cities ({PERIOD[0]} to {PERIOD[1]}). "
            f"The error clearly changes with the regime and with the local setting. Its typical size (RMSE) ranges from "
            f"{min(raw_by_reg.values()):.1f} to {max(raw_by_reg.values()):.1f} mm/day across monsoon regimes, and from "
            f"{min(raw_by_lt.values()):.1f} to {max(raw_by_lt.values()):.1f} mm/day across local settings."),
          fig("error_by_regime.png", "Raw day-1 rainfall error against IMD's 0.25° grid, split by the regime known when the forecast was issued "
              "(left) and by the local rainfall setting (right)."),
          H2("2.3 Why a single correction fails"),
          B("The usual fix is one statistical correction learnt from all past days together. But a correction learnt mostly from "
            "ordinary days is wrong for the unusual ones, and heavy-rain days are exactly the unusual ones. In our test, a single "
            f"global quantile-mapping correction made heavy-rain skill (ETS) <b>worse than the raw model in {global_below_raw} of 4 "
            f"cases</b>. The same method applied separately per regime beat it in {regime_beats_global} of 4 (section 7)."),
          H2("2.4 Why it matters"),
          *bullets(["Heavy and very heavy rain drive floods, landslides and urban waterlogging, among India's most damaging disasters.",
                    "District administrations act on <b>district</b> forecasts, while models produce grids. The product must bridge that gap.",
                    "IMD and NCMRWF issue warnings on fixed thresholds (64.5 / 115.6 / 204.5 mm), so success is measured on those thresholds, not just on averages."]),
          PageBreak()]

story += [H1("3. What the PS Asks and the Expected Outcomes"),
          callout([Paragraph("Build an AI/ML-based rainfall post-processing system that <b>first identifies the prevailing weather "
                             "regime</b> and then <b>applies a suitable correction</b> to raw NWP rainfall, to improve district and grid-level "
                             "forecasts, <b>especially heavy and very heavy rainfall</b>.", quote)]), Spacer(1, 4),
          P("Our paraphrase of PS 26080.", "caption"),
          table([["Expected outcome (PS)", "What it means", "How VARSHA delivers it", "How we prove it"],
                 ["<b>Weather regime classifier</b>", "Label each day and area as active, break, depression, coastal or orographic", "IMD core-zone criterion + IMD depression records + terrain and onshore-wind rules (section 5.2)", "Match against IMD's published active/break monitoring; regime timeline (section 7)"],
                 ["<b>Bias-corrected rainfall forecast</b>", "Better rainfall than the raw NWP output", "Regime-specific quantile mapping and gradient boosting, behind a do-no-harm gate", "Out-of-sample RMSE, ETS, CSI vs raw NWP (section 7)"],
                 ["<b>Heavy-rainfall probability</b>", "Chance of exceeding operational thresholds", "Calibrated classifier per IMD threshold and regime", "Brier score vs raw NWP and climatology; reliability diagram"],
                 ["<b>District-level product</b>", "User-friendly table / map for districts", "Grid → district aggregation; IMD colour codes; CSV/API export", "Verified against IMD district-wise rainfall (CRIS)"],
                 ["<b>Verification report</b>", "RMSE, ETS, CSI, POD, FAR and FSS", "Automated report by regime, lead day and area, raw vs corrected", "All six metrics computed on each run"]],
                [CONTENT_W * 0.2, CONTENT_W * 0.22, CONTENT_W * 0.3, CONTENT_W * 0.28]),
          PageBreak()]

story += [H1("4. Our Solution: VARSHA"),
          B("VARSHA is a post-processing layer that sits after NCMRWF's models. It needs no new model runs, only the raw rainfall "
            "forecast and IMD's observations, so it is cheap to run and easy to plug in."),
          KeepTogether([architecture(), P("Figure: VARSHA architecture. The do-no-harm gate (dark box) is what makes the system safe to run operationally.", "caption")]),
          H2("4.1 Design principles"),
          *bullets(["<b>Use IMD's definitions, not invented ones.</b> Regimes and thresholds follow IMD's published practice.",
                    "<b>Causal by construction.</b> A regime is decided only from information available when the forecast is issued, so the system runs in real time exactly as tested.",
                    "<b>Different jobs, different tools.</b> The best estimate of rainfall amount and the best detector of heavy rain are different products.",
                    "<b>Never make things worse.</b> A correction is used only where it has beaten the raw model out of sample.",
                    "<b>Official data only.</b> Everything shown is downloaded from IMD, NCMRWF or national weather agencies."]),
          PageBreak()]

story += [H1("5. How It Works"),
          H2("5.1 Data"),
          table([["Data", "Source", "Use"],
                 ["Raw NWP rainfall (days 1–5)", "NCMRWF NCUM / IMD GFS (operational target); NOAA GFS, UK Met Office UM, ECMWF via open data (pilot)", "Input to be corrected"],
                 ["Daily gridded rainfall 0.25°, real time", "IMD Pune", "Truth; current regime"],
                 ["Daily gridded rainfall 0.25°, 1991–2020", "IMD Pune archive", "Daily normals for the regime criterion; training"],
                 ["850 hPa wind, MSLP, 500 hPa height", "IMDAA (NCMRWF reanalysis) / NWP analysis", "Depression, western disturbance, onshore flow"],
                 ["Depression / low tracks", "IMD RSMC New Delhi bulletins and best tracks", "Depression regime labels"],
                 ["District-wise daily rainfall", "IMD Hydromet (CRIS)", "District-level verification"],
                 ["Terrain, coastline, district boundaries", "Official DEM and administrative boundaries (Survey of India / Bhuvan)", "Orographic and coastal settings; district aggregation"]],
                [CONTENT_W * 0.3, CONTENT_W * 0.42, CONTENT_W * 0.28]),
          Spacer(1, 6),
          H2("5.2 Step 1: Regime classifier"),
          KeepTogether([regime_tree(), P("Two layers: one large-scale regime per day, and a local rainfall setting per grid cell or district.", "caption")]),
          *bullets(["<b>Active and break:</b> IMD's operational criterion (Rajeevan et al.; Pai et al.). Average rainfall over the core monsoon "
                    "zone, standardised with IMD's daily normals, ≥ +1 (active) or ≤ −1 (break) for at least 3 consecutive days. "
                    "Implemented and running in our pilot (section 7).",
                    "<b>Monsoon low / depression:</b> IMD RSMC records for training labels; for real time, a closed MSLP minimum with strong "
                    "850 hPa cyclonic vorticity over the Bay of Bengal and central India in the analysis and forecast fields.",
                    "<b>Western disturbance:</b> 500 hPa trough and upper-level westerlies over north-west India.",
                    "<b>Orographic and coastal settings:</b> terrain slope facing the 850 hPa wind (windward Western Ghats, north-eastern hills, "
                    "Himalayan foothills) and distance to the coast with onshore flow.",
                    "<b>AI layer:</b> a gradient-boosting classifier trained on these labelled days predicts the regime from forecast fields, so "
                    "day-3 to day-5 forecasts can use the regime expected on the target day, not just today's."]),
          H2("5.3 Step 2: Regime-specific correction"),
          *bullets(["<b>Intensity track (regime-wise quantile mapping):</b> reshapes the model's rainfall distribution to IMD's, separately for "
                    "each regime and setting, with pooling to a broader class when samples are few. It keeps heavy-rain intensity, so it is "
                    "used for threshold-based products.",
                    "<b>Amount track (regime-aware gradient boosting):</b> learns the correction from the raw forecast, regime, setting, location "
                    "and season, with extra weight on heavy-rain days. It gives the smallest everyday error.",
                    "<b>Grid version:</b> the same logic on IMD's full 0.25° grid, with a small convolutional network (U-Net) added once enough "
                    "seasons of gridded forecasts are collected. It is used only if the gate (Step 4) confirms it helps."]),
          H2("5.4 Step 3: Heavy-rainfall probability"),
          B("A classifier per IMD threshold (64.5, 115.6 and 204.5 mm) estimates the probability of exceedance from the raw forecast, the "
            "regime and the local setting. It is calibrated so that “40%” really means rain crossed the line on about 40% of such days, "
            "then mapped to IMD's Green / Yellow / Orange / Red colours."),
          H2("5.5 Step 4: The do-no-harm gate"),
          B("For every combination of regime, forecast day and area, VARSHA keeps a rolling out-of-sample scorecard of raw versus "
            "corrected forecasts. If a correction has not beaten the raw model there, the raw forecast is issued and the dashboard says "
            "so. This is what makes an AI correction safe for operational use."),
          H2("5.6 Step 5: District product and verification"),
          *bullets(["Grid-to-district aggregation using official boundaries (area-weighted mean, plus the maximum-cell value for heavy-rain "
                    "risk), producing a table and map with IMD colour codes and CSV/API export.",
                    "Verification report on every run: <b>RMSE, ETS, CSI, POD, FAR</b> (at IMD thresholds) and <b>FSS</b> (fractions skill score, "
                    "which rewards forecasts that place heavy rain in roughly the right area at 25–100 km scales), by regime, lead day and region."]),
          PageBreak()]

story += [H1("6. What Makes VARSHA Stand Out"),
          B("Many teams are likely to build a deep-learning correction network with clusters for regimes. That can look impressive, but "
            "it is hard for NCMRWF to verify, easy to over-fit, and it can quietly make forecasts worse in rare regimes. VARSHA is built "
            "to be <b>checked and trusted</b>."),
          H2("USP 1: Official, auditable regimes"),
          callout([B("Regimes follow <b>IMD's own published criteria and data</b>, so every label can be checked against IMD's monitoring. "
                     "The AI learns to <i>predict</i> these official regimes rather than inventing its own.")]), Spacer(1, 4),
          *bullets(["Active and break spells computed exactly as IMD Pune does: core-zone standardised anomaly, ±1, 3 consecutive days, IMD 0.25° grid.",
                    "Depression days from IMD RSMC records; orographic and coastal settings from terrain and wind physics.",
                    "Forecasters can see <i>why</i> a regime was assigned, and NCMRWF gets error statistics per regime, which is direct feedback for model development."]),
          H2("USP 2: The right correction for each job, with a do-no-harm gate"),
          callout([B("Rainfall <b>amount</b>, heavy-rain <b>intensity</b> and heavy-rain <b>probability</b> are different products. Each "
                     "uses the method that verifies best, and no correction is used where it has not beaten the raw model.")], bg=PANEL2, bar=ORANGE), Spacer(1, 4),
          *bullets([f"Our pilot shows why: regime-aware ML cut everyday error by {min(rmse_gain):.0f}–{max(rmse_gain):.0f}%, but like "
                    "all average-minimising methods it weakened heavy-rain detection. Regime-wise quantile mapping kept heavy-rain skill.",
                    "The gate makes the system safe to switch on: in the worst case it issues the raw forecast, never something worse."]),
          H2("USP 3: Verified where it is used"),
          *bullets(["District forecasts are checked against <b>IMD's official district-wise rainfall</b>, not only against grids.",
                    "All six required metrics (RMSE, ETS, CSI, POD, FAR, FSS) are computed automatically by regime, lead day and region.",
                    "No synthetic data: every figure in the product can be traced to an official source file."]),
          PageBreak()]

# ---- pilot
spell_rows = [["Spell", "From", "To", "Days"]] + [[s[0], s[1].strftime("%d %b"), s[2].strftime("%d %b"), str(s[3])] for s in spells]
res_rows = [["Model · day", "Method", "RMSE (mm)", "Heavy-rain POD", "FAR", "CSI", "ETS"]]
LAB = {"RAW": "Raw NWP", "QM_GLOBAL": "Single global correction", "QM_REGIME": "Regime-wise correction", "ML_REGIME": "Regime-aware ML"}
for k, name, lead in KEYS:
    for i, meth in enumerate(["RAW", "QM_GLOBAL", "QM_REGIME", "ML_REGIME"]):
        s = m(k, meth); t = s["t64.5"]
        res_rows.append([f"<b>{name} · day {lead}</b>" if i == 0 else "", LAB[meth], f"{s['RMSE']:.2f}", f"{t['POD']:.2f}", f"{t['FAR']:.2f}", f"{t['CSI']:.3f}", f"<b>{t['ETS']:.3f}</b>"])
brier_rows = [["Model · day", "Our probability", "Raw NWP (yes/no)", "Climatology"]] + \
             [[f"{n} · day {l}", f"<b>{brier[k]['P_ML']:.4f}</b>", f"{brier[k]['P_RAW']:.4f}", f"{brier[k]['CLIM']:.4f}"] for k, n, l in KEYS]

story += [H1("7. Pilot Evidence on Real Data"),
          H2("7.1 Set-up"),
          table([["Item", "Pilot configuration"],
                 ["Truth", f"IMD real-time 0.25° gridded rainfall, 2026 monsoon ({PERIOD[0]} to {PERIOD[1]} for verification)"],
                 ["Normals", f"IMD 0.25° gridded rainfall archive, {R['normal_years']} years (1991–2020), daily mean and standard deviation over the core monsoon zone"],
                 ["Raw NWP", "NOAA GFS (model family of IMD's operational GFS) and UK Met Office UM (same family as NCMRWF's NCUM), day 1 and day 3, archived runs"],
                 ["Locations", "36 cities, including west-coast orographic, hill/Himalayan, east-coast and inland sites"],
                 ["Regime", "Large-scale regime from the latest IMD day available at issue time (no look-ahead) × local setting"],
                 ["Validation", "Blocked leave-one-week-out cross-validation with a 3-day buffer; every score is out of sample"],
                 ["Heavy rain", f"IMD threshold 64.5 mm/day; {events} observed events per model and lead"]],
                [CONTENT_W * 0.18, CONTENT_W * 0.82]),
          Spacer(1, 6),
          H2("7.2 The regime classifier on the 2026 monsoon"),
          fig("regime_timeline.png", "Standardised core-zone rainfall anomaly, computed exactly as IMD's active/break monitoring does, from IMD grids and IMD 1991–2020 normals."),
          KeepTogether([table(spell_rows, [CONTENT_W * 0.2, CONTENT_W * 0.2, CONTENT_W * 0.2, CONTENT_W * 0.15]),
                        P("Spells detected (≥ 3 consecutive days beyond ±1). IMD applies the criterion formally in July–August; spells in June and September are shown for monitoring.", "caption")]),
          CondPageBreak(110 * mm), H2("7.3 Correction results"),
          fig("methods.png", "Out-of-sample comparison of the four approaches for two raw models and two lead days."),
          KeepTogether([P("Table: heavy-rain (≥ 64.5 mm) and everyday scores, all out of sample.", "caption"),
                        table(res_rows, [CONTENT_W * w for w in [0.2, 0.27, 0.11, 0.13, 0.08, 0.1, 0.11]])]),
          Spacer(1, 6),
          *bullets([f"<b>A single global correction hurts heavy-rain skill</b> (ETS below raw in {global_below_raw} of 4 tests). This confirms the PS premise.",
                    f"<b>Regime-wise correction beats the single correction</b> in {regime_beats_global} of 4 tests, and beats raw NWP in {regime_beats_raw} of 4.",
                    f"<b>Regime-aware ML has the smallest everyday error</b> ({min(rmse_gain):.0f}–{max(rmse_gain):.0f}% lower RMSE than raw), but "
                    "detects fewer heavy-rain days, which is why VARSHA keeps separate amount and intensity products (USP 2)."]),
          CondPageBreak(70 * mm), H2("7.4 Heavy-rain probability"),
          KeepTogether([table(brier_rows, [CONTENT_W * 0.3, CONTENT_W * 0.23, CONTENT_W * 0.25, CONTENT_W * 0.22]),
                        P("Brier score for P(rain ≥ 64.5 mm), lower is better. Climatology = always forecasting the observed event frequency.", "caption")]),
          H2("7.5 Honest limits of the pilot"),
          *bullets(["One monsoon season at 36 points; the prototype moves to the full 0.25° grid and multiple seasons.",
                    "Depression and western-disturbance regimes are not yet in the pilot; they need circulation fields and IMD RSMC records.",
                    "FSS needs gridded forecasts, so it is computed in the prototype, not the pilot.",
                    "NCMRWF's own NCUM output was not publicly downloadable; the UK Met Office model is the closest public equivalent."]),
          PageBreak()]

story += [H1("8. Prototype Plan"),
          B("We already have a working multi-model forecasting prototype for India (built for a related NCMRWF problem). It already downloads "
            "IMD's grids, aligns model rainfall to IMD's 08:30 IST rain day (verified), computes heavy-rain probabilities and runs a live "
            "verification dashboard. VARSHA reuses that base, so the effort goes into what this PS is really about."),
          table([["Phase", "Build", "Demo-able result"],
                 ["Week 1", "Full-grid IMD ingest; NWP rainfall on the IMD 0.25° grid; regime classifier (active/break) as a service", "Daily regime map and timeline"],
                 ["Week 2", "Depression / WD detection from circulation fields; orographic and coastal settings from terrain and wind", "All PS regimes labelled daily"],
                 ["Week 3", "Regime-wise quantile mapping and gradient boosting on the grid; do-no-harm gate", "Corrected rainfall maps, days 1–5"],
                 ["Week 4", "Heavy-rain probability per IMD threshold; district aggregation; IMD colour codes", "District table and map with CSV export"],
                 ["Week 5", "Verification report (RMSE, ETS, CSI, POD, FAR, FSS) by regime; IMD district rainfall comparison", "Automated verification report"],
                 ["Week 6", "Scheduling, dashboard polish, documentation", "Fully automated live demo"]],
                [CONTENT_W * 0.1, CONTENT_W * 0.6, CONTENT_W * 0.3]),
          Spacer(1, 6),
          table([["Layer", "Technology"],
                 ["Data and ML", "Python: xarray, NumPy, pandas, scikit-learn (gradient boosting), PyTorch (U-Net, later), xskillscore-style metrics"],
                 ["Backend", "Express + TypeScript API (as in our existing prototype) or FastAPI for the ML service"],
                 ["Frontend", "Next.js dashboard: regime map, corrected rainfall, district table, verification report"],
                 ["Automation", "Scheduled daily cycle after IMD's 08:30 IST rainfall is published, with retries and status monitoring"]],
                [CONTENT_W * 0.2, CONTENT_W * 0.8]),
          H1("9. Feasibility and Viability"),
          *bullets(["<b>Technically feasible:</b> the pilot already runs end to end on real data in about a minute on a laptop; the grid version needs only modest compute.",
                    "<b>Data feasible:</b> IMD grids (real time and 1991–2020) are downloadable today; NCUM output and IMD RSMC records can be requested from the PS owner.",
                    "<b>Operationally safe:</b> the do-no-harm gate means switching VARSHA on can never degrade the forecast below the raw model.",
                    "<b>Low cost and easy to adopt:</b> post-processing only; standard gridded outputs and API; fits NCMRWF's existing daily cycle.",
                    "<b>Impact:</b> better district heavy-rain guidance for IMD, NDMA and SDMAs, and per-regime error feedback for NCMRWF model development."]),
          H2("9.1 Risks and mitigations"),
          table([["Risk", "Mitigation"],
                 ["Few heavy-rain events per regime to learn from", "Pool across similar settings; extra weight on heavy days; multiple seasons from the IMD archive"],
                 ["ML correction smooths extremes", "Separate intensity track (regime-wise quantile mapping) for threshold products"],
                 ["A correction degrades some regime", "Do-no-harm gate falls back to raw NWP there, visibly"],
                 ["NCUM data access delayed", "Model-agnostic pipeline, demonstrated on GFS and UK Met Office; NCUM plugs in unchanged"],
                 ["IMD server availability", "Local cache of all downloaded files; automatic retry and backfill"]],
                [CONTENT_W * 0.38, CONTENT_W * 0.62]),
          H1("10. References"),
          *[Paragraph(f"[{i + 1}]  {r}", ParagraphStyle("ref", parent=ST["bodyL"], fontSize=8.2, leading=10.8, spaceAfter=3, leftIndent=18, firstLineIndent=-18)) for i, r in enumerate([
              "IMD Pune, Active and break spells of the Indian summer monsoon (monsoon monitoring pages, 2024 and 2025 seasons), imdpune.gov.in.",
              "Rajeevan, M., Gadgil, S. & Bhate, J. (2010). Active and break spells of the Indian summer monsoon. J. Earth Syst. Sci. 119.",
              "Pai, D. S. et al. (2014). A new high spatial resolution (0.25°) long period (1901–2010) daily gridded rainfall data set over India. Mausam 65.",
              "Pai, D. S., Sridhar, L. & Ramesh Kumar, M. R. (2015). Active and break events of Indian summer monsoon during 1901–2014. Climate Dynamics.",
              "IMD Hydromet Division, Customised Rainfall Information System (CRIS): district-wise rainfall, hydro.imd.gov.in.",
              "Quantile mapping bias correction methods to IMDAA reanalysis for calibrating NCMRWF unified model operational forecasts (2022). Hydrological Sciences Journal 67(6).",
              "Roberts, N. & Lean, H. (2008). Scale-selective verification of rainfall accumulations (Fractions Skill Score). Monthly Weather Review 136.",
              "Wilks, D. S. Statistical Methods in the Atmospheric Sciences: ETS, CSI, POD, FAR and Brier score definitions.",
              "Open-Meteo Previous Runs API (archived NOAA GFS and UK Met Office forecasts), open-meteo.com."])]]

doc = Doc(OUT, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=17 * mm, bottomMargin=16 * mm,
          title="VARSHA: Regime-Aware AI Post-Processing of Monsoon Rainfall (SIH PS 26080)", author="Team IgniteZ", subject="SIH PS 26080")
frame = Frame(MARGIN, 16 * mm, CONTENT_W, PAGE_H - 33 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate("cover", [frame], onPage=cover), PageTemplate("later", [frame], onPage=later)])
doc.multiBuild(story)
print("built", OUT)
