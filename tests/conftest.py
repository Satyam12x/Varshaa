"""Shared fixtures: engine on sys.path, a live API server per test module, and data paths."""
import json, os, socket, subprocess, sys, time, urllib.request
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "engine"))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def start_api(env_extra=None):
    port = free_port()
    env = {**os.environ, "PORT": str(port), **(env_extra or {})}
    npx = "npx.cmd" if os.name == "nt" else "npx"
    p = subprocess.Popen([npx, "tsx", "src/server.ts"], cwd=os.path.join(ROOT, "backend"), env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/api"
    for _ in range(60):
        try:
            urllib.request.urlopen(base + "/health", timeout=2); return p, base
        except Exception:
            time.sleep(0.5)
    p.kill(); raise RuntimeError("API did not start")


def stop(p):
    if os.name == "nt":
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        p.kill()


@pytest.fixture(scope="session")
def api():
    p, base = start_api()
    yield base
    stop(p)


@pytest.fixture(scope="session")
def api_stale():
    p, base = start_api({"STALE_HOURS": "0"})
    yield base
    stop(p)


def get(url, method="GET"):
    """Return (status, headers, body bytes) without raising on 4xx/5xx."""
    req = urllib.request.Request(url, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=60)
        return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def jget(url):
    s, h, b = get(url)
    return s, json.loads(b) if b else None


@pytest.fixture(scope="session")
def latest():
    return json.load(open(os.path.join(DATA, "products", "latest.json")))


@pytest.fixture(scope="session")
def verif():
    return {l: json.load(open(os.path.join(DATA, "models", f"verification_lead{l}.json"))) for l in range(1, 6)}
