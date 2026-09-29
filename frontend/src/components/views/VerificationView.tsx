"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend as RLegend, Line, LineChart, ResponsiveContainer, Scatter, ComposedChart, Tooltip, XAxis, YAxis } from "recharts";
import { METHOD_LABEL, type Verification } from "@/lib/api";
import { fmt } from "@/lib/colors";
import { useFetch } from "../AppContext";
import { Card } from "../GridMap";

const METHODS = ["RAW", "QM_GLOBAL", "QM_REGIME", "ML", "WARN"];
const COL: Record<string, string> = { RAW: "#aab7c1", QM_GLOBAL: "#cfd9e0", QM_REGIME: "#6b7c8a", ML: "#0f1f2b", WARN: "#0b4f6c" };

export default function VerificationView() {
  const { data } = useFetch<Record<string, Verification>>("/verification");
  const [lead, setLead] = useState("1");
  const [thr, setThr] = useState<"t64.5" | "t115.6">("t64.5");
  if (!data || !Object.keys(data).length) return <Card><p className="text-sm text-[var(--muted)]">No verification report yet (run the engine&apos;s training step).</p></Card>;
  const v = data[lead] ?? data[Object.keys(data)[0]];
  const leads = Object.keys(data);
  const best = (k: "POD" | "FAR" | "CSI" | "ETS", higher = true) => {
    const vals = METHODS.map((m) => v.overall[m][thr][k] as number);
    return higher ? Math.max(...vals) : Math.min(...vals);
  };
  const fssData = ["25km", "75km", "125km", "225km"].map((s) => ({ scale: s, ...Object.fromEntries(METHODS.map((m) => [m, v.fss[m]?.[s]])) }));
  const etsByLead = leads.map((l) => ({ lead: `Day ${l}`, ...Object.fromEntries(METHODS.map((m) => [m, data[l].overall[m][thr].ETS])) }));
  const regimes = Object.keys(v.by_regime.RAW ?? {});

  return (
    <div className="flex flex-col gap-4">
      <Card title="Verification report: VARSHA vs raw NWP, six monsoons, leave-one-season-out"
        right={<div className="flex gap-1 text-sm">{leads.map((l) => <button key={l} onClick={() => setLead(l)} className={`rounded-md px-2.5 py-1 ${lead === l ? "bg-[var(--accent)] text-white" : "border border-[var(--line)]"}`}>Day {l}</button>)}</div>}>
        <p className="mb-2 text-sm">Every score is out of sample: each season is forecast by models trained only on the <i>other</i> seasons, then compared with IMD&apos;s 0.25° gridded rainfall. Seasons {v.seasons.join(", ")} · {v.days} days · {v.n.toLocaleString()} grid-cell forecasts · {v.events.heavy.toLocaleString()} heavy and {v.events.very_heavy.toLocaleString()} very heavy rain events.</p>
        <div className="mb-2 flex gap-1 text-sm">
          {(["t64.5", "t115.6"] as const).map((t) => <button key={t} onClick={() => setThr(t)} className={`rounded-md px-2.5 py-1 ${thr === t ? "bg-[var(--brand-btn)] text-white" : "border border-[var(--line)]"}`}>{t === "t64.5" ? "Heavy ≥ 64.5 mm" : "Very heavy ≥ 115.6 mm"}</button>)}
        </div>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-[var(--muted)]"><th className="py-1 font-medium">Method</th><th className="text-right font-medium">RMSE (mm)</th><th className="text-right font-medium">POD ↑</th><th className="text-right font-medium">FAR ↓</th><th className="text-right font-medium">CSI ↑</th><th className="text-right font-medium">ETS ↑</th><th className="text-right font-medium">FSS 25 km ↑</th></tr></thead>
          <tbody>{METHODS.map((m) => {
            const s = v.overall[m][thr];
            const b = (x: number, t: number) => (Math.abs(x - t) < 1e-9 ? "font-bold text-[var(--good)]" : "");
            return (
              <tr key={m} className="border-t border-[var(--line)]">
                <td className="py-1.5"><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: COL[m] }} />{METHOD_LABEL[m]}</td>
                <td className="text-right tabular-nums">{fmt(v.overall[m].RMSE, 2)}</td>
                <td className={`text-right tabular-nums ${b(s.POD, best("POD"))}`}>{fmt(s.POD, 3)}</td>
                <td className={`text-right tabular-nums ${b(s.FAR, best("FAR", false))}`}>{fmt(s.FAR, 3)}</td>
                <td className={`text-right tabular-nums ${b(s.CSI, best("CSI"))}`}>{fmt(s.CSI, 3)}</td>
                <td className={`text-right tabular-nums ${b(s.ETS, best("ETS"))}`}>{fmt(s.ETS, 3)}</td>
                <td className="text-right tabular-nums">{fmt(v.fss[m]?.["25km"], 3)}</td>
              </tr>);
          })}</tbody>
        </table>
        <p className="mt-1 text-[11px] text-[var(--muted)]">Bold green = best in column. The warning track has no RMSE because it is a yes/no product. FSS is computed at the 64.5 mm threshold.</p>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={`ETS by forecast day (${thr === "t64.5" ? "heavy" : "very heavy"} rain)`}>
          <div className="h-56"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={etsByLead} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} /><XAxis dataKey="lead" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(x, n) => [fmt(Number(x), 3), METHOD_LABEL[String(n)]]} contentStyle={{ fontSize: 12 }} /><RLegend formatter={(n) => METHOD_LABEL[String(n)]} wrapperStyle={{ fontSize: 11 }} />
              {METHODS.map((m) => <Line key={m} dataKey={m} stroke={COL[m]} strokeWidth={m === "WARN" || m === "RAW" ? 2.5 : 1.5} dot={{ r: 3 }} isAnimationActive={false} />)}
            </LineChart></ResponsiveContainer></div>
        </Card>
        <Card title="Fractions Skill Score by scale (heavy rain)">
          <div className="h-56"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={fssData} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} /><XAxis dataKey="scale" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} domain={[0, 1]} />
              <Tooltip formatter={(x, n) => [fmt(Number(x), 3), METHOD_LABEL[String(n)]]} contentStyle={{ fontSize: 12 }} /><RLegend formatter={(n) => METHOD_LABEL[String(n)]} wrapperStyle={{ fontSize: 11 }} />
              {METHODS.map((m) => <Bar key={m} dataKey={m} fill={COL[m]} isAnimationActive={false} />)}
            </BarChart></ResponsiveContainer></div>
          <p className="text-[11px] text-[var(--muted)]">FSS rewards heavy rain placed in roughly the right area at each scale (1.0 = perfect).</p>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Heavy-rain probability: reliability and Brier score">
          <div className="h-52"><ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={v.reliability} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" /><XAxis dataKey="p" type="number" domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={(x) => `${Math.round(x * 100)}%`} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={(x) => `${Math.round(x * 100)}%`} />
              <Tooltip formatter={(x) => `${Math.round(Number(x) * 100)}%`} contentStyle={{ fontSize: 12 }} />
              <Line data={[{ p: 0, freq: 0 }, { p: 1, freq: 1 }]} dataKey="freq" stroke="#aab7c1" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
              <Scatter dataKey="freq" fill="#0b4f6c" isAnimationActive={false} />
            </ComposedChart></ResponsiveContainer></div>
          <p className="text-[11px] text-[var(--muted)]">Forecast probability (x) vs how often heavy rain actually happened (y). Points on the dashed line = perfectly calibrated.</p>
          <table className="mt-2 w-full text-sm"><thead><tr className="text-left text-xs text-[var(--muted)]"><th className="font-medium">Brier score (lower is better)</th><th className="text-right font-medium">VARSHA</th><th className="text-right font-medium">Raw GFS</th><th className="text-right font-medium">Climatology</th></tr></thead>
            <tbody>{Object.entries(v.brier).map(([k, b]) => <tr key={k} className="border-t border-[var(--line)]"><td className="py-1">{k === "heavy" ? "≥ 64.5 mm" : "≥ 115.6 mm"}</td><td className="text-right font-semibold tabular-nums">{fmt(b.VARSHA, 5)}</td><td className="text-right tabular-nums">{fmt(b.RAW, 5)}</td><td className="text-right tabular-nums">{fmt(b.CLIMATOLOGY, 5)}</td></tr>)}</tbody></table>
        </Card>
        <Card title="Heavy-rain ETS by regime: does regime-awareness help?">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-[var(--muted)]"><th className="py-1 font-medium">Method</th>{regimes.map((r) => <th key={r} className="text-right font-medium">{r}</th>)}</tr></thead>
            <tbody>{METHODS.map((m) => <tr key={m} className="border-t border-[var(--line)]"><td className="py-1.5">{METHOD_LABEL[m]}</td>{regimes.map((r) => <td key={r} className="text-right tabular-nums">{fmt(v.by_regime[m]?.[r]?.["t64.5"].ETS, 3)}</td>)}</tr>)}</tbody>
          </table>
          <h4 className="mt-4 text-sm font-semibold">District level ({v.district.districts} Survey of India districts)</h4>
          <table className="mt-1 w-full text-sm"><thead><tr className="text-left text-xs text-[var(--muted)]"><th className="py-1 font-medium">Method</th><th className="text-right font-medium">RMSE of district mean</th><th className="text-right font-medium">Heavy rain anywhere in district: ETS</th></tr></thead>
            <tbody>{METHODS.map((m) => <tr key={m} className="border-t border-[var(--line)]"><td className="py-1">{METHOD_LABEL[m]}</td><td className="text-right tabular-nums">{fmt(v.district.rmse_mean_rain[m], 2)}</td><td className="text-right tabular-nums">{fmt(v.district.heavy_any_cell[m]?.ETS, 3)}</td></tr>)}</tbody></table>
        </Card>
      </div>
    </div>
  );
}
