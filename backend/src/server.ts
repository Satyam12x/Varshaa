/**
 * VARSHA API — serves the products written by the Python engine (../engine) and automates the daily cycle.
 * Every product is derived from official data: IMD gridded rainfall, IMD RSMC best tracks, Survey of India
 * district boundaries and NOAA GFS forecasts from NOAA's archive.
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import cors from "cors";
import express, { type Response } from "express";
import cron from "node-cron";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const DATA = path.join(ROOT, "data");
const ENGINE = path.join(ROOT, "engine");
const PYTHON = process.env.PYTHON ?? "python";
const PORT = Number(process.env.PORT ?? 4080);

const log = (m: string) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${m}`);
const readJson = <T = unknown>(p: string): T | null => (fs.existsSync(p) ? (JSON.parse(fs.readFileSync(p, "utf8")) as T) : null);

// ------------------------------------------------------------------ cached data
interface District { id: number; name: string; state: string; lgd: string | null; lat: number; lon: number; cells: [number, number][] }
interface Product {
  issue: string; generated: string; source: Record<string, string>; season_note: string | null;
  regime: { large_scale: string; anomaly: number | null; based_on: string | null; recent: unknown[]; depressions: unknown[]; depression_cells: number };
  cells: [number, number][];
  cell_district: number[]; cell_setting: number[]; cell_depression: number[];
  leads: { lead: number; valid: string; raw: number[]; corrected: number[]; p_heavy: number[]; p_very_heavy: number[]; level: number[];
    gate: { key: string; cells: number; amount: string; warning: string }[];
    districts: { id: number; mean: number; max: number; raw_mean: number; p_heavy: number; p_very_heavy: number; level: string }[];
    thresholds: Record<string, number> }[];
}

let districts: District[] = readJson<District[]>(path.join(DATA, "boundaries", "districts.json")) ?? [];
let product: Product | null = null;
let productMtime = 0;
function latest(): Product | null {
  const f = path.join(DATA, "products", "latest.json");
  if (!fs.existsSync(f)) return null;
  const m = fs.statSync(f).mtimeMs;
  if (m !== productMtime) { product = readJson<Product>(f); productMtime = m; }
  return product;
}

// ------------------------------------------------------------------ daily cycle
const status = { running: false, step: "idle", lastStarted: null as string | null, lastFinished: null as string | null, lastError: null as string | null, output: [] as string[] };

function py(script: string, args: string[] = []): Promise<void> {
  return new Promise((resolve, reject) => {
    const p = spawn(PYTHON, [script, ...args], { cwd: ENGINE, env: { ...process.env, PYTHONIOENCODING: "utf-8" } });
    const push = (b: Buffer) => b.toString().split(/\r?\n/).filter(Boolean).forEach((l) => { status.output.push(l); if (status.output.length > 200) status.output.shift(); });
    p.stdout.on("data", push); p.stderr.on("data", push);
    p.on("close", (code) => (code === 0 ? resolve() : reject(new Error(`${script} exited with ${code}`))));
  });
}

async function cycle() {
  if (status.running) return false;
  Object.assign(status, { running: true, lastStarted: new Date().toISOString(), lastError: null, output: [] });
  try {
    status.step = "Downloading latest NOAA GFS run and IMD rainfall"; await py("ingest.py");
    status.step = "Regime identification, correction and district product"; await py("forecast.py");
    status.step = "Updating event replays"; await py("replay.py");
  } catch (e) {
    status.lastError = (e as Error).message; log(`cycle failed: ${status.lastError}`);
  } finally {
    Object.assign(status, { running: false, step: "idle", lastFinished: new Date().toISOString() });
  }
  return true;
}

// ------------------------------------------------------------------ API
const app = express();
app.use(cors());
const api = express.Router();
app.use("/api", api);

const need = (res: Response) => { const p = latest(); if (!p) res.status(503).json({ error: "No forecast product yet: run the engine (POST /api/run)." }); return p; };
const LEVEL_RANK: Record<string, number> = { green: 0, yellow: 1, orange: 2, red: 3 };

api.get("/health", (_q, res) => res.json({ ok: true }));

api.get("/meta", (_q, res) => {
  const p = latest();
  res.json({
    issue: p?.issue ?? null, generated: p?.generated ?? null, leads: p?.leads.map((l) => ({ lead: l.lead, valid: l.valid })) ?? [],
    regime: p?.regime ?? null, seasonNote: p?.season_note ?? null, districts: districts.length, status,
    sources: [
      { name: "IMD 0.25° gridded daily rainfall (real time + 1991–2025 archive)", agency: "India Meteorological Department, MoES", url: "https://imdpune.gov.in/", role: "Truth, training, 1991–2020 normals, current regime" },
      { name: "Raw NWP rainfall: NOAA GFS 00 UTC, days 1–5", agency: "NOAA National Weather Service (official archive on AWS Open Data)", url: "https://registry.opendata.aws/noaa-gfs-bdp-pds/", role: "Forecast being corrected (model family of IMD's operational GFS). NCMRWF NCUM plugs in the same way." },
      { name: "Best-track data of depressions and cyclones, 1982–2026", agency: "IMD RSMC New Delhi", url: "https://rsmcnewdelhi.imd.gov.in/", role: "Depression regime (checksum-verified workbook)" },
      { name: "District boundaries (742 districts)", agency: "Survey of India", url: "https://onlinemaps.surveyofindia.gov.in/", role: "District-level product" },
      { name: "Active / break criterion", agency: "IMD Pune (Rajeevan et al.; Pai et al.)", url: "https://imdpune.gov.in/", role: "Regime classifier definition" },
    ],
  });
});

api.get("/forecast", (req, res) => {
  const p = need(res); if (!p) return;
  const lead = Number(req.query.lead ?? 1);
  const L = p.leads.find((l) => l.lead === lead) ?? p.leads[0];
  res.json({ issue: p.issue, regime: p.regime, seasonNote: p.season_note, cells: p.cells, cell_district: p.cell_district, cell_setting: p.cell_setting, cell_depression: p.cell_depression, ...L });
});

api.get("/districts", (req, res) => {
  const p = need(res); if (!p) return;
  const lead = Number(req.query.lead ?? 1);
  const L = p.leads.find((l) => l.lead === lead) ?? p.leads[0];
  const byId = new Map(districts.map((d) => [d.id, d]));
  const rows = L.districts.map((r) => ({ ...r, name: byId.get(r.id)?.name ?? "", state: byId.get(r.id)?.state ?? "", lgd: byId.get(r.id)?.lgd ?? null }))
    .sort((a, b) => LEVEL_RANK[b.level] - LEVEL_RANK[a.level] || b.p_heavy - a.p_heavy || b.max - a.max);
  if (req.query.format === "csv") {
    const head = "district,state,lgd_code,valid_date,mean_rain_mm,max_cell_rain_mm,raw_nwp_mean_mm,p_heavy,p_very_heavy,warning_level";
    const lines = rows.map((r) => [JSON.stringify(r.name), JSON.stringify(r.state), r.lgd ?? "", L.valid, r.mean, r.max, r.raw_mean, r.p_heavy, r.p_very_heavy, r.level].join(","));
    res.setHeader("Content-Type", "text/csv");
    res.setHeader("Content-Disposition", `attachment; filename="varsha_districts_${L.valid}_day${L.lead}.csv"`);
    return void res.send([head, ...lines].join("\n"));
  }
  res.json({ issue: p.issue, lead: L.lead, valid: L.valid, rows });
});

api.get("/geo/districts", (_q, res) => res.sendFile(path.join(DATA, "boundaries", "districts_simplified.geojson")));

let mask: unknown = null;
api.get("/geo/landmask", (_q, res) => {
  if (!mask) {
    const f = path.join(DATA, "imd_yearly", "2020.grd");
    const buf = fs.readFileSync(f);
    const g = new Float32Array(buf.buffer, buf.byteOffset + 200 * 129 * 135 * 4, 129 * 135);
    const runs: [number, number, number][] = [];
    for (let i = 0; i < 129; i++) { let s = -1; for (let j = 0; j <= 135; j++) { const land = j < 135 && g[i * 135 + j] > -998; if (land && s < 0) s = j; if (!land && s >= 0) { runs.push([i, s, j - 1]); s = -1; } } }
    mask = { lat0: 6.5, lon0: 66.5, step: 0.25, runs, source: "IMD 0.25° gridded rainfall land mask" };
  }
  res.json(mask);
});

api.get("/regime/history", (_q, res) => res.json(readJson(path.join(DATA, "models", "regime_history.json")) ?? { dates: [], anom: [], regime: [] }));

api.get("/verification", (_q, res) => {
  const out: Record<string, unknown> = {};
  for (let l = 1; l <= 5; l++) { const v = readJson(path.join(DATA, "models", `verification_lead${l}.json`)); if (v) out[l] = v; }
  res.json(out);
});

api.get("/replay", (_q, res) => res.json(readJson(path.join(DATA, "products", "replay_index.json")) ?? { events: [] }));
api.get("/replay/:date", (req, res) => {
  const f = path.join(DATA, "products", "replay", `${String(req.params.date).replace(/[^0-9-]/g, "")}.json`);
  if (!fs.existsSync(f)) return void res.status(404).json({ error: "no replay for that date" });
  res.sendFile(f);
});

// ---- demo data for the "See the proof" page (built by engine/demo.py)
const DEMO = path.join(DATA, "products", "demo");
api.get("/demo/summary", (_q, res) => res.sendFile(path.join(DEMO, "summary.json")));
api.get("/demo/regime", (_q, res) => res.sendFile(path.join(DEMO, "regime_index.json")));
api.get("/demo/regime/:date", (req, res) => {
  const f = path.join(DEMO, "regime", `${String(req.params.date).replace(/[^0-9-]/g, "")}.json`);
  if (!fs.existsSync(f)) return void res.status(404).json({ error: "no data for that day" });
  res.sendFile(f);
});
api.get("/demo/district/:id", (req, res) => {
  const f = path.join(DEMO, "district", `${Number(req.params.id)}.json`);
  if (!fs.existsSync(f)) return void res.status(404).json({ error: "no track record for that district" });
  res.sendFile(f);
});

api.get("/status", (_q, res) => res.json(status));
api.post("/run", (_q, res) => { if (status.running) return void res.status(409).json({ error: "already running", status }); void cycle(); res.status(202).json({ started: true }); });

app.listen(PORT, () => log(`VARSHA API on http://localhost:${PORT}/api (engine: ${ENGINE})`));

// Daily cycle at 10:15 IST: IMD's 24 h rainfall (ending 08:30 IST) and the 00 UTC GFS run are both published by then.
cron.schedule("15 10 * * *", () => { void cycle(); }, { timezone: "Asia/Kolkata" });
