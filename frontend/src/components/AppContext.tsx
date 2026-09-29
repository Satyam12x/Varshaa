"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getJson, type CellMeta, type Meta } from "@/lib/api";

export interface DistrictGeo { id: number; name: string; state: string; d: string }

interface Ctx {
  meta: Meta | null;
  cellMeta: CellMeta | null;
  districtsGeo: DistrictGeo[];
  districtName: (id: number) => string;
  error: string | null;
  reload: () => void;
}

const AppCtx = createContext<Ctx>({ meta: null, cellMeta: null, districtsGeo: [], districtName: () => "", error: null, reload: () => undefined });
export const useApp = () => useContext(AppCtx);

// equirectangular projection shared by every map
export const MAP = { W: 560, H: 575, lon0: 66.5, lon1: 100, lat0: 6.5, lat1: 38.5 };
export const px = (lon: number) => ((lon - MAP.lon0) / (MAP.lon1 - MAP.lon0)) * MAP.W;
export const py = (lat: number) => ((MAP.lat1 - lat) / (MAP.lat1 - MAP.lat0)) * MAP.H;

type Ring = number[][];
interface Feature { properties: { id: number; name: string; state: string }; geometry: { type: string; coordinates: Ring[] | Ring[][] } }

function toPath(geom: Feature["geometry"]): string {
  const polys = (geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates) as Ring[][];
  return polys.map((rings) => rings.map((r) => "M" + r.map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join("L") + "Z").join("")).join("");
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [cellMeta, setCellMeta] = useState<CellMeta | null>(null);
  const [districtsGeo, setGeo] = useState<DistrictGeo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    getJson<Meta>("/meta").then((m) => { if (alive) { setMeta(m); setError(null); } }).catch((e: Error) => alive && setError(e.message));
    getJson<CellMeta>("/forecast?lead=1").then((f) => alive && setCellMeta(f)).catch(() => undefined);
    return () => { alive = false; };
  }, [tick]);

  useEffect(() => {
    getJson<{ features: Feature[] }>("/geo/districts")
      .then((g) => setGeo(g.features.map((f) => ({ id: f.properties.id, name: f.properties.name, state: f.properties.state, d: toPath(f.geometry) }))))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!meta?.status.running) return;
    const t = setInterval(() => setTick((x) => x + 1), 10000);
    return () => clearInterval(t);
  }, [meta?.status.running]);

  const names = new Map(districtsGeo.map((d) => [d.id, `${d.name}, ${d.state}`]));
  return (
    <AppCtx.Provider value={{ meta, cellMeta, districtsGeo, districtName: (id) => names.get(id) ?? "", error, reload: () => setTick((x) => x + 1) }}>
      {children}
    </AppCtx.Provider>
  );
}

export function useFetch<T>(path: string | null) {
  const [state, setState] = useState<{ path: string | null; data: T | null; error: string | null }>({ path: null, data: null, error: null });
  useEffect(() => {
    if (!path) return;
    let alive = true;
    getJson<T>(path)
      .then((d) => alive && setState({ path, data: d, error: null }))
      .catch((e: Error) => alive && setState((s) => ({ path, data: s.data, error: e.message })));
    return () => { alive = false; };
  }, [path]);
  return { data: state.data, error: state.error, loading: state.path !== path };
}
