"use client";

import { useState } from "react";
import type { DistrictRow, Forecast } from "@/lib/api";
import { RAIN_CLASSES, dayName, fmt, niceDate, pct, rainClass, rainColor } from "@/lib/colors";
import { useApp, useFetch } from "../AppContext";
import GridMap, { Card } from "../GridMap";
import { Explainer, Loading, RainLegend, Toggle } from "../ui";
import { UspTag } from "../usp";

export default function RainMapView({ lead }: { lead: number }) {
  const { data: f } = useFetch<Forecast>(`/forecast?lead=${lead}`);
  const { data: d } = useFetch<{ rows: DistrictRow[] }>(`/districts?lead=${lead}`);
  const { districtName } = useApp();
  const [mode, setMode] = useState<"varsha" | "raw">("varsha");
  const [sel, setSel] = useState<number | null>(null);
  if (!f || !d) return <Loading what="Loading the rain map…" />;
  const vals = mode === "varsha" ? f.corrected : f.raw;
  const tip = (k: number) => (
    <>VARSHA: <b>{fmt(f.corrected[k])} mm</b> ({rainClass(f.corrected[k])?.name})<br />Raw model: {fmt(f.raw[k])} mm · chance of heavy rain {pct(f.p_heavy[k])}</>
  );
  const wettest = [...d.rows].sort((a, b) => (mode === "varsha" ? b.max - a.max : b.raw_mean - a.raw_mean)).slice(0, 10);
  const share = RAIN_CLASSES.map((c, i) => {
    const lo = i === 0 ? -Infinity : RAIN_CLASSES[i - 1].max;
    const n = vals.filter((x) => x >= lo && x < c.max).length;
    return { ...c, n, frac: n / vals.length };
  });
  const changed = [...d.rows].map((r) => ({ ...r, diff: r.mean - r.raw_mean })).sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff)).slice(0, 5);
  const selRow = sel !== null ? d.rows.find((r) => r.id === sel) : null;

  return (
    <div className="flex flex-col gap-4">
      <Explainer title={`How much rain will fall · ${dayName(lead)}, ${niceDate(f.valid)}`}>
        Each small square is a 25 km × 25 km area, coloured by the expected rain in 24 hours (8:30 am to 8:30 am, as IMD measures it).
        <b> VARSHA</b> is the corrected forecast; the <b>raw model</b> is NOAA GFS before correction. Click a district on the right to find it on the map.
      </Explainer>
      <div className="flex flex-wrap items-center gap-3">
        <Toggle options={[["varsha", "VARSHA forecast"], ["raw", "Raw model"]]} value={mode} onChange={setMode} />
        <UspTag n={2} />
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <Card title={mode === "varsha" ? "VARSHA corrected forecast" : "Raw model (NOAA GFS), before correction"}>
          <GridMap cells={f.cells} values={vals} color={rainColor} tooltip={tip} selectedDistrict={sel} onDistrict={setSel} legend={<RainLegend />} />
        </Card>
        <div className="flex flex-col gap-4">
          {selRow && (
            <Card title={districtName(selRow.id)} right={<button onClick={() => setSel(null)} className="text-[12.5px] text-[var(--muted)] hover:text-[var(--ink)]">Clear ✕</button>}>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div><div className="text-[22px] font-semibold">{fmt(selRow.mean)}</div><div className="text-[12px] text-[var(--muted)]">mm on average</div></div>
                <div><div className="text-[22px] font-semibold">{fmt(selRow.max)}</div><div className="text-[12px] text-[var(--muted)]">mm in the wettest part</div></div>
                <div><div className="text-[22px] font-semibold">{pct(selRow.p_heavy)}</div><div className="text-[12px] text-[var(--muted)]">chance of heavy rain</div></div>
              </div>
            </Card>
          )}
          <Card title="Wettest districts">
            <div className="flex flex-col">
              {wettest.map((r, i) => {
                const v = mode === "varsha" ? r.max : r.raw_mean;
                const c = rainClass(v);
                return (
                  <button key={r.id} onClick={() => setSel(r.id)}
                    className={`grid grid-cols-[22px_minmax(0,1fr)_auto] items-center gap-2 border-t border-[var(--line)] py-2 text-left text-[14px] first:border-0 hover:bg-[var(--panel)] ${sel === r.id ? "bg-[var(--panel)]" : ""}`}>
                    <span className="text-[12px] text-[var(--faint)]">{i + 1}</span>
                    <span className="truncate"><b>{r.name}</b> <span className="text-[var(--muted)]">{r.state}</span></span>
                    <span className="inline-flex items-center gap-2 text-[13px]"><span className="h-3 w-3 rounded-sm border border-black/10" style={{ background: c?.color }} /><b>{fmt(v)} mm</b></span>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-[12px] text-[var(--muted)]">{mode === "varsha" ? "Ranked by the wettest 25 km square in each district." : "Ranked by the raw model's district average."}</p>
          </Card>
          <Card title="How much of India gets what">
            <div className="flex h-4 overflow-hidden rounded-full border border-black/5">
              {share.filter((s) => s.n > 0).map((s) => <div key={s.name} title={`${s.name}: ${pct(s.frac)}`} style={{ width: `${s.frac * 100}%`, background: s.color }} />)}
            </div>
            <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-[13px]">
              {share.map((s) => (
                <div key={s.name} className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm border border-black/10" style={{ background: s.color }} />{s.name}</span>
                  <span className="tabular-nums text-[var(--muted)]">{s.frac > 0 && s.frac < 0.01 ? "<1%" : pct(s.frac)}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Biggest corrections vs the raw model">
            <div className="flex flex-col">
              {changed.map((r) => (
                <button key={r.id} onClick={() => setSel(r.id)} className="flex items-center justify-between gap-2 border-t border-[var(--line)] py-2 text-left text-[14px] first:border-0 hover:bg-[var(--panel)]">
                  <span className="truncate"><b>{r.name}</b> <span className="text-[var(--muted)]">{r.state}</span></span>
                  <span className="whitespace-nowrap text-[13px]">{fmt(r.raw_mean)} → <b>{fmt(r.mean)} mm</b></span>
                </button>
              ))}
            </div>
            <p className="mt-2 text-[12px] text-[var(--muted)]">District average, raw model → VARSHA. The raw model often spreads light rain where it stays dry; VARSHA learnt this from six monsoons of IMD data.</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
