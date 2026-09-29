export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4080/api";

export type Level = "green" | "yellow" | "orange" | "red";
export type Cell = [number, number];

export interface Regime {
  large_scale: "Active" | "Break" | "Normal" | string;
  anomaly: number | null;
  based_on: string | null;
  recent: { date: string; anom: number | null; regime: string }[];
  depressions: { time: string; lat: number; lon: number; grade: string }[];
  depression_cells: number;
}

export interface Meta {
  issue: string | null;
  generated: string | null;
  leads: { lead: number; valid: string }[];
  regime: Regime | null;
  seasonNote: string | null;
  districts: number;
  status: { running: boolean; step: string; lastStarted: string | null; lastFinished: string | null; lastError: string | null; output: string[] };
  sources: { name: string; agency: string; url: string; role: string }[];
}

export interface Forecast {
  issue: string;
  regime: Regime;
  seasonNote: string | null;
  cells: Cell[];
  lead: number;
  valid: string;
  raw: number[];
  corrected: number[];
  p_heavy: number[];
  p_very_heavy: number[];
  level: number[];
  gate: { key: string; cells: number; amount: string; warning: string }[];
  thresholds: Record<string, number>;
}

export interface CellMeta { cells: Cell[]; cell_district: number[]; cell_setting: number[]; cell_depression: number[] }

export interface DistrictRow {
  id: number; name: string; state: string; lgd: string | null; mean: number; max: number; raw_mean: number;
  p_heavy: number; p_very_heavy: number; level: Level;
}

export interface CatScore { events: number; hits: number; misses: number; false_alarms: number; POD: number; FAR: number; CSI: number; ETS: number }
export interface MethodScore { "t64.5": CatScore; "t115.6": CatScore; RMSE?: number }
export interface Verification {
  lead: number; n: number; days: number; seasons: number[];
  events: { heavy: number; very_heavy: number; extremely_heavy: number };
  overall: Record<string, MethodScore>;
  by_regime: Record<string, Record<string, MethodScore>>;
  by_setting: Record<string, Record<string, MethodScore>>;
  fss: Record<string, Record<string, number>>;
  brier: Record<string, Record<string, number>>;
  reliability: { p: number; freq: number; n: number }[];
  district: { n: number; districts: number; rmse_mean_rain: Record<string, number>; heavy_any_cell: Record<string, CatScore> };
  gate: Record<string, { amount: string; warning: string; n: number }>;
}

export interface ReplayEvent { date: string; heavy_cells: number; regime: string; ets_raw: number; ets_varsha: number; pod_raw: number; pod_varsha: number }
export interface ReplayDay {
  date: string; heavy_cells: number; regime: string;
  leads: Record<string, { obs: (number | null)[]; raw: (number | null)[]; ml: (number | null)[]; qmr: (number | null)[]; p_heavy: (number | null)[]; warn: (number | null)[];
    scores: Record<string, CatScore> }>;
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(((await res.json().catch(() => ({}))) as { error?: string }).error ?? `HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const METHOD_LABEL: Record<string, string> = {
  RAW: "Raw NWP (GFS)", QM_GLOBAL: "Single global correction", QM_REGIME: "Regime-wise correction", ML: "Regime-aware ML (amount)", WARN: "VARSHA warning track",
};
export const SETTING_LABEL: Record<number, string> = { 0: "Orographic", 1: "Coastal", 3: "Inland" };
