"""Result-integrity tests: the saved evaluation and the daily product must support the headline claims."""
import json, os, subprocess, sys
import numpy as np
import pytest
from conftest import DATA, ROOT

LEADS = range(1, 6)


def test_R01_six_seasons_held_out(verif):
    """R01 Every lead day is scored on all six monsoons, 2021 to 2026."""
    for l in LEADS:
        assert verif[l]["seasons"] == [2021, 2022, 2023, 2024, 2025, 2026] and verif[l]["n"] > 3_000_000


def test_R02_warning_beats_raw_every_lead(verif):
    """R02 VARSHA heavy-rain ETS beats raw GFS on every lead day."""
    for l in LEADS:
        o = verif[l]["overall"]
        assert o["WARN"]["t64.5"]["ETS"] > o["RAW"]["t64.5"]["ETS"]


def test_R03_amount_track_lowers_rmse_every_lead(verif):
    """R03 The ML amount track has lower RMSE than raw GFS on every lead day."""
    for l in LEADS:
        o = verif[l]["overall"]
        assert o["ML"]["RMSE"] < o["RAW"]["RMSE"]


def test_R04_ps_premise_single_correction_hurts(verif):
    """R04 PS premise: one global correction makes daily RMSE worse than raw on every lead day."""
    for l in LEADS:
        o = verif[l]["overall"]
        assert o["QM_GLOBAL"]["RMSE"] > o["RAW"]["RMSE"]


def test_R05_probability_beats_raw_and_climatology(verif):
    """R05 VARSHA's P(heavy) has a lower Brier score than raw GFS and climatology on every lead day."""
    for l in LEADS:
        b = verif[l]["brier"]["heavy"]
        assert b["VARSHA"] < b["RAW"] and b["VARSHA"] < b["CLIMATOLOGY"]


def test_R06_metrics_in_valid_ranges(verif):
    """R06 Every score in every file is in its valid range (POD, FAR, CSI in [0,1]; ETS in [-1/3, 1]; RMSE > 0)."""
    for l in LEADS:
        for block in ("overall",):
            for m, s in verif[l][block].items():
                for t in ("t64.5", "t115.6"):
                    c = s[t]
                    assert 0 <= c["POD"] <= 1 and 0 <= c["FAR"] <= 1 and 0 <= c["CSI"] <= 1 and -1 / 3 <= c["ETS"] <= 1
                    assert c["hits"] + c["misses"] == c["events"]
                if "RMSE" in s and s["RMSE"] is not None: assert s["RMSE"] > 0


def test_R07_gate_choices_valid(verif):
    """R07 The do-no-harm gate only ever picks a known method for each regime × setting."""
    for l in LEADS:
        for k, g in verif[l]["gate"].items():
            assert g["amount"] in {"RAW", "QM_REGIME", "ML"} and g["warning"] in {"RAW", "QM_REGIME", "WARN"}


def test_R08_daily_product_shape(latest):
    """R08 Today's product: 5 lead days, one value per land cell for every field, sensible ranges."""
    n = len(latest["cells"])
    assert n == 4964 and len(latest["leads"]) == 5
    for L in latest["leads"]:
        for k in ("raw", "corrected", "p_heavy", "p_very_heavy", "level"):
            assert len(L[k]) == n
        assert min(L["corrected"]) >= 0 and min(L["raw"]) >= 0
        assert 0 <= min(L["p_heavy"]) and max(L["p_heavy"]) <= 1 and set(L["level"]) <= {0, 1, 2, 3}


def test_R09_district_rows_valid(latest):
    """R09 Every district row refers to a real Survey of India district and uses an IMD colour."""
    ids = {d["id"] for d in json.load(open(os.path.join(DATA, "boundaries", "districts.json"), encoding="utf-8"))}
    for L in latest["leads"]:
        assert len(L["districts"]) > 700
        for r in L["districts"]:
            assert r["id"] in ids and r["level"] in {"green", "yellow", "orange", "red"} and r["max"] >= r["mean"] >= 0


def test_R10_claims_script_reproduces_deck_numbers():
    """R10 tools/check_claims.py runs on the saved files and reproduces the deck's headline numbers."""
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_claims.py"), "--json", os.path.join(ROOT, "build", "claims_test.json")],
                         capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert out.returncode == 0, out.stderr
    K = json.load(open(os.path.join(ROOT, "build", "claims_test.json")))
    assert K["ets_warn1"] > K["ets_raw1"] and K["rmse_ml"] < K["rmse_raw"] < K["rmse_qmg"] and K["dist_varsha"] > K["dist_raw"]
