"""API tests against a live server started from backend/src/server.ts (same code Render runs)."""
import json, os, subprocess
from conftest import ROOT, get, jget


def test_A01_health_ok(api):
    """A01 GET /api/health returns 200 with forecast age and cycle status."""
    s, b = jget(api + "/health")
    assert s == 200 and b["ok"] and b["product"]["issue"] and "age_hours" in b["product"] and "step" in b["cycle"]


def test_A02_health_head(api):
    """A02 HEAD /api/health answers 200 (uptime monitors often use HEAD)."""
    assert get(api + "/health", "HEAD")[0] == 200


def test_A03_health_strict_stale_is_503(api_stale):
    """A03 /api/health?strict=1 returns 503 when the forecast is older than STALE_HOURS; plain /health stays 200."""
    assert jget(api_stale + "/health?strict=1")[0] == 503 and jget(api_stale + "/health")[0] == 200


def test_A04_meta(api):
    """A04 /api/meta lists 5 lead days, the regime, 742 districts and the official sources."""
    s, b = jget(api + "/meta")
    assert s == 200 and len(b["leads"]) == 5 and b["districts"] == 742 and len(b["sources"]) >= 4


def test_A05_forecast_every_lead(api):
    """A05 /api/forecast returns the requested lead day for days 1 to 5."""
    for l in range(1, 6):
        s, b = jget(api + f"/forecast?lead={l}")
        assert s == 200 and b["lead"] == l and len(b["corrected"]) == len(b["cells"])


def test_A06_forecast_bad_lead_falls_back(api):
    """A06 An out-of-range or non-numeric lead falls back to day 1 instead of failing."""
    for q in ("99", "0", "abc"):
        s, b = jget(api + f"/forecast?lead={q}")
        assert s == 200 and b["lead"] == 1


def test_A07_districts_json_sorted(api):
    """A07 /api/districts is sorted by warning level, most severe first."""
    s, b = jget(api + "/districts?lead=5")
    rank = {"green": 0, "yellow": 1, "orange": 2, "red": 3}
    lv = [rank[r["level"]] for r in b["rows"]]
    assert s == 200 and lv == sorted(lv, reverse=True) and all(r["name"] for r in b["rows"])


def test_A08_districts_csv(api):
    """A08 CSV export has the documented header, one row per district, and quoted names (safe for commas)."""
    s, h, body = get(api + "/districts?lead=1&format=csv")
    lines = body.decode("utf-8").splitlines()
    assert s == 200 and "text/csv" in h.get("Content-Type", "") and lines[0].startswith("district,state,lgd_code,valid_date")
    assert len(lines) > 700 and lines[1].startswith('"')


def test_A09_geo_and_landmask(api):
    """A09 District boundaries and the land mask are served."""
    s, b = jget(api + "/geo/districts")
    assert s == 200 and len(b["features"]) > 700
    s, m = jget(api + "/geo/landmask")
    assert s == 200 and m["step"] == 0.25 and len(m["runs"]) > 0


def test_A10_verification_and_regime_history(api):
    """A10 The verification report covers leads 1 to 5 and the regime history covers six monsoons."""
    s, v = jget(api + "/verification")
    assert s == 200 and set(v) == {"1", "2", "3", "4", "5"}
    s, r = jget(api + "/regime/history")
    assert s == 200 and r["dates"][0].startswith("2021") and len(r["dates"]) == len(r["regime"])


def test_A11_replays(api):
    """A11 The 14 replayed storm days are listed and each one loads."""
    s, idx = jget(api + "/replay")
    assert s == 200 and len(idx["events"]) == 14
    s, d = jget(api + "/replay/" + idx["events"][0]["date"])
    assert s == 200 and "1" in d["leads"]


def test_A12_path_traversal_blocked(api):
    """A12 Crafted paths cannot escape the data folder: replay dates and district ids are sanitised."""
    assert get(api + "/replay/..%2F..%2Fmodels%2Flead1")[0] == 404
    assert get(api + "/demo/district/..%2F..%2Fsummary")[0] == 404
    assert get(api + "/demo/district/abc")[0] == 404


def test_A13_unknown_replay_404(api):
    """A13 A day with no replay returns a clear 404 JSON error."""
    s, b = jget(api + "/replay/1999-01-01")
    assert s == 404 and "error" in b


def test_A14_demo_district_record(api):
    """A14 A district's track record (Raigad, id 187) loads."""
    assert get(api + "/demo/district/187")[0] == 200


def test_A15_cors_open(api):
    """A15 CORS allows the Vercel dashboard to call the API from another origin."""
    s, h, _ = get(api + "/health")
    assert h.get("Access-Control-Allow-Origin") == "*"


def test_A16_health_cli_exit_codes(api):
    """A16 `npm run health` exits 0 against a healthy API and 1 when the API is unreachable."""
    node = "node"
    ok = subprocess.run([node, "scripts/health.mjs", api.rsplit("/api", 1)[0]], cwd=os.path.join(ROOT, "backend"), capture_output=True, text=True)
    bad = subprocess.run([node, "scripts/health.mjs", "http://127.0.0.1:9"], cwd=os.path.join(ROOT, "backend"), capture_output=True, text=True,
                         env={**os.environ, "HEALTH_TRIES": "1", "HEALTH_TIMEOUT_MS": "3000"})
    assert ok.returncode == 0 and "OK" in ok.stdout and bad.returncode == 1 and "UNHEALTHY" in bad.stdout
