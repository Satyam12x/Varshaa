"""Engine unit tests: regime rules (incl. no look-ahead), verification metrics, corrections, features, masks."""
import numpy as np, pandas as pd
import pytest
import common as C
import forecast


def series(vals, start="2024-07-01"):
    return pd.Series(vals, index=pd.date_range(start, periods=len(vals)), dtype=float)


# ---------------------------------------------------------------- regimes
def test_E01_causal_spell_needs_three_days():
    """E01 Active needs the IMD anomaly >= +1 on 3 consecutive days; 2 days stay Normal."""
    lab = C.causal_spells(series([1.2, 1.3, 0.2, 1.1, 1.4, 1.5]))
    assert list(lab) == ["Normal", "Normal", "Normal", "Normal", "Normal", "Active"]


def test_E02_causal_break_spell():
    """E02 Break is labelled from the 3rd consecutive day <= -1."""
    lab = C.causal_spells(series([-1.1, -1.2, -1.5, -0.4]))
    assert list(lab) == ["Normal", "Normal", "Break", "Normal"]


def test_E03_no_look_ahead_property():
    """E03 No look-ahead: the causal label of every day is identical whether or not later days exist."""
    rng = np.random.default_rng(1)
    a = series(rng.normal(0, 1.2, 240))
    full = C.causal_spells(a)
    for t in range(len(a)):
        assert C.causal_spells(a.iloc[: t + 1]).iloc[-1] == full.iloc[t]


def test_E04_retrospective_labels_do_look_ahead():
    """E04 The retrospective (monitoring) rule labels spell starts using later days, which is why training no longer uses it."""
    a = series([0.0, 1.5, 1.5, 1.5, 0.0])
    assert C.classify_spells(a).iloc[1] == "Active" and C.causal_spells(a).iloc[1] == "Normal"


def test_E05_nan_anomaly_breaks_a_run():
    """E05 A missing IMD day (NaN anomaly) breaks a spell instead of counting towards it."""
    lab = C.causal_spells(series([1.2, np.nan, 1.3, 1.4]))
    assert (lab == "Normal").all()


def test_E06_live_regime_uses_causal_rule(monkeypatch):
    """E06 The live forecast (regime_now) uses only IMD days before issue and applies the causal rule."""
    seen = []
    def fake_rt(d, download=False):
        seen.append(pd.Timestamp(d)); return np.zeros((C.NLAT, C.NLON), np.float32)
    monkeypatch.setattr(C, "imd_rt", fake_rt)
    monkeypatch.setattr(C, "core_anomaly", lambda d, g, N: 1.5)
    issue = pd.Timestamp("2024-07-20")
    known, anom, ls, _ = forecast.regime_now(issue, None)
    assert max(seen) < issue and known == issue - pd.Timedelta(days=1) and ls == "Active"


def test_E07_depression_excludes_fixes_after_issue(monkeypatch):
    """E07 The depression regime ignores RSMC fixes later than the 00 UTC issue time."""
    t = pd.DataFrame({"time": pd.to_datetime(["2024-08-01 00:00", "2024-08-01 03:00"]), "lat": [20.0, 25.0],
                      "lon": [87.0, 80.0], "grade": ["D", "D"]})
    monkeypatch.setattr(C, "_tracks", t)
    m, pts = C.depression("2024-08-01")
    assert len(pts) == 1 and pts.iloc[0].lat == 20.0 and m.any()


def test_E08_no_depression_no_cells(monkeypatch):
    """E08 With no RSMC system nearby, no cell is labelled Depression."""
    monkeypatch.setattr(C, "_tracks", pd.DataFrame({"time": pd.to_datetime([]), "lat": [], "lon": [], "grade": []}))
    m, pts = C.depression("2024-08-01")
    assert not m.any() and len(pts) == 0


# ---------------------------------------------------------------- metrics
def test_E09_categorical_scores_hand_example():
    """E09 POD, FAR, CSI and ETS match a hand-worked contingency table."""
    o = np.array([80, 70, 10, 5, 90, 0, 0, 0], float)
    p = np.array([70, 10, 80, 0, 100, 0, 0, 0], float)
    s = C.cat(p, o, 64.5)  # hits 2, misses 1, false alarms 1, n 8
    assert (s["hits"], s["misses"], s["false_alarms"]) == (2, 1, 1)
    assert s["POD"] == pytest.approx(2 / 3) and s["FAR"] == pytest.approx(1 / 3) and s["CSI"] == pytest.approx(0.5)
    hr = 3 * 3 / 8
    assert s["ETS"] == pytest.approx((2 - hr) / (4 - hr))


def test_E10_perfect_forecast():
    """E10 A perfect forecast scores POD 1, FAR 0, ETS 1."""
    o = np.array([0, 70, 120, 3], float)
    s = C.cat(o.copy(), o, 64.5)
    assert s["POD"] == 1 and s["FAR"] == 0 and s["ETS"] == pytest.approx(1)


def test_E11_no_events_no_crash():
    """E11 A day with no heavy rain and no warnings gives finite scores (no division by zero)."""
    s = C.cat(np.zeros(10), np.zeros(10), 64.5)
    assert s["events"] == 0 and np.isfinite(s["ETS"]) and s["POD"] == 0


def test_E12_fss_identical_fields():
    """E12 Fractions Skill Score is 1 for identical fields and NaN when neither field has an event."""
    L = C.land(); g = np.where(L, 0.0, 0.0); g[60:64, 60:64] = 100
    assert C.fss([g], [g], [L], 64.5, 3) == pytest.approx(1)
    assert np.isnan(C.fss([g * 0], [g * 0], [L], 64.5, 3))


# ---------------------------------------------------------------- corrections
def test_E13_quantile_mapping_monotone_and_non_negative():
    """E13 Quantile mapping is monotone, never negative, and maps the forecast distribution onto the observed one."""
    rng = np.random.default_rng(0)
    f = rng.gamma(0.6, 8, 5000); o = rng.gamma(0.6, 12, 5000)
    fit = C.qm_fit(f, o)
    x = np.linspace(0, 150, 300)
    y = C.qm_apply(fit, x)
    assert (np.diff(y) >= -1e-9).all() and (y >= 0).all()
    assert np.quantile(C.qm_apply(fit, f), 0.9) == pytest.approx(np.quantile(o, 0.9), rel=0.05)


def test_E14_quantile_mapping_extreme_extrapolation_is_capped():
    """E14 Rain above anything seen in training is extrapolated with a capped slope (at most 1.5x), not unbounded."""
    fit = (np.linspace(0, 100, 110), np.linspace(0, 400, 110))
    y = C.qm_apply(fit, np.array([300.0]))
    assert y[0] == pytest.approx(400 + 200 * 1.5)


def test_E15_warning_levels_consistent_with_probability():
    """E15 Warning level never contradicts the stated chance: P(heavy) >= 35% is at least 'alert', P(very heavy) >= 35% is 'warning'."""
    p1 = np.array([0.0, 0.2, 0.4, 0.5]); p2 = np.array([0.0, 0.0, 0.1, 0.4]); w = np.zeros(4)
    assert list(forecast.level(p1, p2, w)) == [0, 1, 2, 3]
    assert list(forecast.level(np.zeros(1), np.zeros(1), np.array([100.0]))) == [1]


# ---------------------------------------------------------------- features and masks
def test_E16_feature_set_complete():
    """E16 The feature builder returns every model feature on the IMD grid, and a missing anomaly becomes 0."""
    N = C.normals(); S = C.settings()
    F = C.features(np.zeros((C.NLAT, C.NLON), np.float32), pd.Timestamp("2024-07-15"), np.nan, "Normal",
                   np.zeros((C.NLAT, C.NLON), bool), N, S)
    assert set(C.FEATURES) <= set(F) and all(np.shape(F[k]) == (C.NLAT, C.NLON) for k in C.FEATURES)
    assert (F["anom"] == 0).all()


def test_E17_land_mask_matches_imd_grid():
    """E17 The shipped land mask equals IMD's own grid mask (4,964 land cells)."""
    L = C.land()
    assert L.shape == (C.NLAT, C.NLON) and L.sum() == 4964


def test_E18_settings_only_valid_classes_on_land():
    """E18 Every land cell is orographic (0), coastal (1) or inland (3)."""
    S, L = C.settings(), C.land()
    assert set(np.unique(S[L])) <= {0, 1, 3} and (S[L] == 0).any() and (S[L] == 1).any()
