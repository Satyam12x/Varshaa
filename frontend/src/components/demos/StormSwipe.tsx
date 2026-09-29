"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Cell, ReplayDay, ReplayEvent } from "@/lib/api";
import { niceDate } from "@/lib/colors";
import { useFetch } from "../AppContext";
import GridMap from "../GridMap";
import { REGIME_NAME, biggestStorm } from "./proofs";

const COL = { none: "#eef3f6", caught: "#0b4f6c", missed: "#b3261e", false: "#f2b134" };
type K = keyof typeof COL;
const ROWS = [["caught", "Heavy rain caught"], ["missed", "Heavy rain missed"], ["false", "False alarms"]] as const;

function hitMap(obs: (number | null)[], forecastHeavy: (i: number) => boolean) {
  const out: K[] = [];
  const n = { caught: 0, missed: 0, false: 0 };
  obs.forEach((o, i) => {
    const e = o !== null && o >= 64.5, f = forecastHeavy(i);
    const k: K = e && f ? "caught" : e ? "missed" : f ? "false" : "none";
    out.push(k);
    if (k !== "none") n[k]++;
  });
  return { cells: out, n };
}

export default function StormSwipe() {
  const { data: idx } = useFetch<{ cells: Cell[]; events: ReplayEvent[] }>("/replay");
  const [date, setDate] = useState<string | null>(null);
  const [lead, setLead] = useState<"1" | "3">("1");
  const [split, setSplit] = useState(50);
  const [drag, setDrag] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const hinted = useRef(false);
  const sel = date ?? biggestStorm(idx?.events)?.date ?? null;
  const { data: day } = useFetch<ReplayDay>(sel ? `/replay/${sel}` : null);
  const L = day?.leads[lead];
  const raw = useMemo(() => (L ? hitMap(L.obs, (i) => (L.raw[i] ?? 0) >= 64.5) : null), [L]);
  const vs = useMemo(() => (L ? hitMap(L.obs, (i) => (L.warn[i] ?? 0) >= 100) : null), [L]);

  // once the maps are in, sweep the divider so it is obvious it can be dragged
  useEffect(() => {
    if (!raw || hinted.current || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    hinted.current = true;
    const path = [50, 38, 26, 18, 26, 38, 50, 62, 74, 82, 74, 62, 50];
    const ts = path.map((x, i) => setTimeout(() => setSplit(x), 500 + i * 90));
    return () => ts.forEach(clearTimeout);
  }, [raw]);

  if (!idx) return <div className="h-[560px] animate-pulse rounded-xl bg-[var(--panel)]" />;
  const color = (arr: K[]) => (k: number | null) => COL[arr[k as number] ?? "none"];
  const ids = idx.cells.map((_, k) => k);
  const move = (x: number) => { const r = box.current!.getBoundingClientRect(); setSplit(Math.max(0, Math.min(100, ((x - r.left) / r.width) * 100))); };
  const events = idx.events.slice().sort((a, b) => b.heavy_cells - a.heavy_cells).slice(0, 8);
  const heavy = day?.heavy_cells ?? 0;

  return (
    <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,540px)_minmax(0,1fr)]">
      <div>
        <div ref={box} className="relative cursor-ew-resize touch-none select-none"
          onPointerDown={(e) => { setDrag(true); move(e.clientX); }} onPointerMove={(e) => drag && move(e.clientX)} onPointerUp={() => setDrag(false)} onPointerLeave={() => setDrag(false)}>
          {raw && vs ? (
            <>
              <GridMap cells={idx.cells} values={ids} color={color(raw.cells)} noTooltip />
              <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${split}%)` }}>
                <GridMap cells={idx.cells} values={ids} color={color(vs.cells)} noTooltip />
              </div>
              <div className="pointer-events-none absolute inset-y-0" style={{ left: `${split}%` }}>
                <div className="h-full w-0.5 -translate-x-1/2 bg-[var(--ink)]" />
                <div className="absolute top-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white bg-[var(--ink)] text-[15px] text-white shadow-lg">⇆</div>
              </div>
              <div className="pointer-events-none absolute left-3 top-3 rounded-md bg-white px-2.5 py-1 text-[12.5px] font-semibold shadow-sm">Raw model</div>
              <div className="pointer-events-none absolute right-3 top-3 rounded-md bg-[var(--brand)] px-2.5 py-1 text-[12.5px] font-semibold text-white shadow-sm">VARSHA</div>
            </>
          ) : <div className="aspect-[560/575] animate-pulse rounded-xl bg-[var(--panel)]" />}
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-[var(--muted)]">
          {ROWS.map(([k, t]) => <span key={k} className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: COL[k] }} />{t}</span>)}
          <span className="ml-auto text-[var(--faint)]">Drag the divider</span>
        </div>
      </div>

      <div className="flex flex-col gap-5">
        <div>
          <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.12em] text-[var(--faint)]">Pick a storm</div>
          <div className="flex flex-wrap gap-1.5">
            {events.map((e) => (
              <button key={e.date} onClick={() => setDate(e.date)} className={`rounded-full border px-3 py-1 text-[12.5px] ${sel === e.date ? "border-[var(--brand)] bg-[var(--brand)] text-white" : "border-[var(--line)] bg-white hover:border-[var(--faint)]"}`}>
                {niceDate(e.date).replace(/^\w+, /, "")} {e.date.slice(0, 4)}
              </button>
            ))}
          </div>
        </div>
        <div className="inline-flex self-start rounded-full border border-[var(--line)] bg-white p-1">
          {(["1", "3"] as const).map((l) => <button key={l} onClick={() => setLead(l)} className={`rounded-full px-4 py-1.5 text-[13px] ${lead === l ? "bg-[var(--brand)] text-white" : "text-[var(--muted)]"}`}>{l === "1" ? "Forecast 1 day before" : "3 days before"}</button>)}
        </div>

        {raw && vs && day && (
          <>
            <div>
              <div className="text-[14px] text-[var(--muted)]">{niceDate(day.date)} {day.date.slice(0, 4)} · {REGIME_NAME[day.regime] ?? day.regime} · IMD measured heavy rain in <b className="text-[var(--ink)]">{heavy}</b> areas of 25 km</div>
              <div className="mt-3 flex items-end gap-6">
                <div><div className="text-[44px] font-semibold leading-none tabular-nums text-[var(--brand)]">{Math.round((100 * vs.n.caught) / Math.max(heavy, 1))}%</div><div className="mt-1 text-[13px] font-medium">caught by VARSHA</div></div>
                <div><div className="text-[30px] font-semibold leading-none tabular-nums text-[#8795a1]">{Math.round((100 * raw.n.caught) / Math.max(heavy, 1))}%</div><div className="mt-1 text-[13px] text-[var(--muted)]">by the raw model</div></div>
              </div>
            </div>
            <table className="w-full text-[14px]">
              <thead><tr className="border-b border-[var(--line)] text-[12.5px] text-[var(--muted)]"><th className="py-2 text-left font-medium" /><th className="py-2 text-right font-medium">Raw model</th><th className="py-2 text-right font-semibold text-[var(--brand)]">VARSHA</th></tr></thead>
              <tbody>
                {ROWS.map(([k, t]) => {
                  const d = (k === "caught" ? 1 : -1) * (vs.n[k] - raw.n[k]);
                  return (
                    <tr key={k} className="border-b border-[var(--line)]">
                      <td className="py-2.5"><span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm" style={{ background: COL[k] }} />{t}</span></td>
                      <td className="py-2.5 text-right text-[20px] font-semibold tabular-nums text-[#8795a1]">{raw.n[k]}</td>
                      <td className={`py-2.5 pl-3 text-right text-[20px] font-semibold tabular-nums ${d > 0 ? "text-[var(--brand)]" : d < 0 ? "text-[#b3261e]" : ""}`}>{vs.n[k]}<span className={`ml-2 hidden w-14 text-left sm:inline-block text-[12px] font-medium ${d > 0 ? "text-[var(--brand)]" : d < 0 ? "text-[#b3261e]" : "text-[var(--faint)]"}`}>{d > 0 ? "better" : d < 0 ? "worse" : "same"}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
