"use client";

import { useMemo, useState } from "react";
import { Bar, CartesianGrid, Cell as RCell, ComposedChart, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import type { DistrictRow } from "@/lib/api";
import { niceDate } from "@/lib/colors";
import { useFetch } from "../AppContext";
import { Bars, type Summary } from "./proofs";

interface Rec { id: number; dates: string[]; obs: number[]; raw: number[]; warn: number[]; p: number[] }
const YEARS = [2021, 2022, 2023, 2024, 2025, 2026];

export default function DistrictRecord({ defaultName = "Raygad" }: { defaultName?: string }) {
  const { data: list } = useFetch<{ rows: DistrictRow[] }>("/districts?lead=1");
  const { data: sum } = useFetch<Summary>("/demo/summary");
  const rows = useMemo(() => [...(list?.rows ?? [])].sort((a, b) => a.state.localeCompare(b.state) || a.name.localeCompare(b.name)), [list]);
  const byId = useMemo(() => new Map(rows.map((r) => [r.id, r])), [rows]);
  const [id, setId] = useState<number | null>(null);
  const [year, setYear] = useState(2024);
  const cur = id ?? rows.find((r) => r.name === defaultName)?.id ?? sum?.best_2024[0]?.id ?? null;
  const { data: rec } = useFetch<Rec>(cur !== null ? `/demo/district/${cur}` : null);
  const me = cur !== null ? byId.get(cur) : undefined;
  const states = [...new Set(rows.map((r) => r.state))];
  const data = useMemo(() => (rec && rec.id === cur ? rec.dates.map((d, i) => ({ d, obs: rec.obs[i], raw: rec.raw[i], warn: rec.warn[i] })).filter((x) => x.d.startsWith(String(year))) : []), [rec, cur, year]);
  const top = Math.ceil((Math.max(80, ...data.map((x) => x.obs)) * 1.3) / 50) * 50;
  const chart = data.map((x) => ({ ...x, vMark: x.warn ? top * 0.86 : null, rMark: x.raw >= 64.5 ? top * 0.94 : null }));
  const heavy = data.filter((x) => x.obs >= 64.5);
  const s = {
    v: heavy.filter((x) => x.warn).length, r: heavy.filter((x) => x.raw >= 64.5).length,
    vFa: data.filter((x) => x.warn && x.obs < 64.5).length, rFa: data.filter((x) => x.raw >= 64.5 && x.obs < 64.5).length,
  };
  const pick = (d: number) => setId(d);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <select aria-label="State" value={me?.state ?? ""} onChange={(e) => { const f = rows.find((r) => r.state === e.target.value); if (f) pick(f.id); }} className="rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-[14px]">
          {states.map((x) => <option key={x}>{x}</option>)}
        </select>
        <select aria-label="District" value={cur ?? ""} onChange={(e) => pick(Number(e.target.value))} className="rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-[14px]">
          {rows.filter((r) => r.state === me?.state).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
        {sum && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="ml-1 text-[12.5px] text-[var(--faint)]">Try</span>
            {sum.best_2024.slice(0, 5).map((b) => byId.get(b.id) && (
              <button key={b.id} onClick={() => { pick(b.id); setYear(2024); }} className={`rounded-full border px-3 py-1 text-[12.5px] ${cur === b.id ? "border-[var(--brand)] bg-[var(--panel)]" : "border-[var(--line)] bg-white hover:border-[var(--faint)]"}`}>{byId.get(b.id)!.name.replace(/\s+/g, " ")}</button>
            ))}
          </div>
        )}
        <div className="ml-auto flex flex-wrap gap-1.5">
          {YEARS.map((y) => <button key={y} onClick={() => setYear(y)} className={`rounded-full border px-3 py-1 text-[13px] ${year === y ? "border-[var(--brand)] bg-[var(--brand)] text-white" : "border-[var(--line)] bg-white hover:border-[var(--faint)]"}`}>{y}</button>)}
        </div>
      </div>

      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <div>
          <div className="mb-2 flex flex-wrap gap-x-5 gap-y-1 text-[12px] text-[var(--muted)]">
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-2 rounded-sm bg-[#f2b134]" />Heavy-rain day (IMD)</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-2 rounded-sm bg-[#86bcd1]" />Other days</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[#0b4f6c]" />VARSHA warned a day before</span>
            <span className="inline-flex items-center gap-1.5"><span className="text-[#8795a1]">▲</span>Raw model showed heavy rain</span>
            <span className="ml-auto text-[var(--faint)]">mm of rain per day</span>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chart} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="d" tickFormatter={(d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("en-IN", { month: "short" })} ticks={chart.filter((x) => x.d.endsWith("-01")).map((x) => x.d)} interval={0} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={44} allowDecimals={false} domain={[0, top]} tickFormatter={(v) => `${Math.round(Number(v))}`} />
                <Tooltip contentStyle={{ fontSize: 12 }} labelFormatter={(d) => niceDate(String(d))}
                  formatter={(v, n) => (n === "obs" ? [`${v} mm`, "IMD measured (wettest part)"] : n === "vMark" ? ["warned a day before", "VARSHA"] : ["showed heavy rain", "Raw model"])} />
                <ReferenceLine y={64.5} stroke="#b3261e" strokeDasharray="4 3" label={{ value: "heavy rain, 64.5 mm", fontSize: 10, fill: "#b3261e", position: "insideBottomRight" }} />
                <Bar dataKey="obs" isAnimationActive={false}>{chart.map((x, i) => <RCell key={i} fill={x.obs >= 64.5 ? "#f2b134" : "#86bcd1"} />)}</Bar>
                <Scatter dataKey="vMark" fill="#0b4f6c" isAnimationActive={false} shape="circle" />
                <Scatter dataKey="rMark" fill="#8795a1" isAnimationActive={false} shape="triangle" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="flex flex-col gap-5">
          <div>
            <div className="text-[14px] text-[var(--muted)]">{me ? `${me.name.replace(/\s+/g, " ")}, ${me.state}` : "…"} · monsoon {year}</div>
            <div className="mt-1 text-[14px] text-[var(--muted)]">IMD recorded heavy rain on <b className="text-[var(--ink)]">{heavy.length} days</b></div>
          </div>
          {heavy.length > 0 ? (
            <>
              <div className="flex items-end gap-6">
                <div><div className="text-[44px] font-semibold leading-none tabular-nums text-[var(--brand)]">{s.v}<span className="text-[20px] text-[var(--faint)]"> / {heavy.length}</span></div><div className="mt-1 text-[13px] font-medium">warned by VARSHA</div></div>
                <div><div className="text-[30px] font-semibold leading-none tabular-nums text-[#8795a1]">{s.r}<span className="text-[16px] text-[var(--faint)]"> / {heavy.length}</span></div><div className="mt-1 text-[13px] text-[var(--muted)]">by the raw model</div></div>
              </div>
              <div>
                <div className="mb-1.5 text-[12.5px] font-medium text-[var(--muted)]">False alarms on dry days</div>
                <Bars raw={s.rFa} varsha={s.vFa} max={Math.max(s.rFa, s.vFa, 1)} />
              </div>
            </>
          ) : <div className="rounded-xl bg-[var(--panel)] p-4 text-[14px] text-[var(--muted)]">No heavy rain here in {year}. False alarms: VARSHA {s.vFa}, raw model {s.rFa}.</div>}
        </div>
      </div>
    </div>
  );
}
