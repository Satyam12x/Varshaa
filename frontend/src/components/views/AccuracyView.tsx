"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Verification } from "@/lib/api";
import { CHART, dayName, pct } from "@/lib/colors";
import { useFetch } from "../AppContext";
import { Card } from "../GridMap";
import { BigStat, Explainer, Loading } from "../ui";
import VerificationView from "./VerificationView";
import { UspTag } from "../usp";

export default function AccuracyView() {
  const { data } = useFetch<Record<string, Verification>>("/verification");
  const [tech, setTech] = useState(false);
  if (!data || !Object.keys(data).length) return <Loading what="Loading the accuracy check…" />;
  const v1 = data["1"];
  const raw = v1.overall.RAW["t64.5"], var_ = v1.overall.WARN["t64.5"];
  const leads = Object.keys(data).map(Number).sort();
  const byDay = leads.map((l) => ({
    day: dayName(l),
    "Raw model": Math.round(data[l].overall.RAW["t64.5"].ETS * 1000) / 1000,
    VARSHA: Math.round(data[l].overall.WARN["t64.5"].ETS * 1000) / 1000,
  }));
  const caught = leads.map((l) => ({ day: dayName(l), "Raw model": Math.round(data[l].overall.RAW["t64.5"].POD * 100), VARSHA: Math.round(data[l].overall.WARN["t64.5"].POD * 100) }));
  const gains = leads.map((l) => Math.round(100 * (data[l].overall.WARN["t64.5"].ETS / data[l].overall.RAW["t64.5"].ETS - 1)));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2"><UspTag n={2} /><UspTag n={3} /></div>
      <Explainer title="How do we know VARSHA works?">
        We replayed six monsoons (2021–2026) day by day. For each year, VARSHA was trained <b>only on the other years</b>, forecast that year, and was then compared
        with the rainfall IMD actually measured on every 25 km square of India: {v1.n.toLocaleString()} forecasts, including {v1.events.heavy.toLocaleString()} heavy-rain events.
        It is an honest exam, like testing a student on questions they have never seen.
      </Explainer>
      <div className="grid gap-3 md:grid-cols-4">
        <BigStat accent value={`+${gains[0]}%`} label="better heavy-rain score, tomorrow" sub={`and +${gains[gains.length - 1]}% five days ahead`} />
        <BigStat value={`${pct(var_.POD)}`} label="of heavy-rain spots caught" sub={`raw model: ${pct(raw.POD)}`} />
        <BigStat value={`${pct(var_.FAR)}`} label="of warnings were false alarms" sub={`raw model: ${pct(raw.FAR)} (lower is better)`} />
        <BigStat value={`${Math.round(100 * (1 - (v1.overall.ML.RMSE ?? 0) / (v1.overall.RAW.RMSE ?? 1)))}% smaller`} label="everyday rainfall error" sub="on all days, not just heavy rain" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Heavy-rain score by forecast day (higher is better)">
          <div className="h-64"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={byDay} margin={{ top: 18, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} /><XAxis dataKey="day" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} /><Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Raw model" fill={CHART.raw} isAnimationActive={false}><LabelList dataKey="Raw model" position="top" fontSize={10} /></Bar>
              <Bar dataKey="VARSHA" fill={CHART.varsha} isAnimationActive={false}><LabelList dataKey="VARSHA" position="top" fontSize={10} /></Bar>
            </BarChart></ResponsiveContainer></div>
          <p className="text-xs text-[var(--muted)]">This is the Equitable Threat Score (ETS): it rewards correct heavy-rain forecasts and penalises misses and false alarms. VARSHA&apos;s lead grows the further ahead you look.</p>
        </Card>
        <Card title="Share of heavy-rain spots caught (%)">
          <div className="h-64"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={caught} margin={{ top: 18, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} /><XAxis dataKey="day" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 11 }} unit="%" />
              <Tooltip contentStyle={{ fontSize: 12 }} formatter={(x) => `${x}%`} /><Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Raw model" fill={CHART.raw} isAnimationActive={false}><LabelList dataKey="Raw model" position="top" fontSize={10} formatter={(x) => `${x}%`} /></Bar>
              <Bar dataKey="VARSHA" fill={CHART.varsha} isAnimationActive={false}><LabelList dataKey="VARSHA" position="top" fontSize={10} formatter={(x) => `${x}%`} /></Bar>
            </BarChart></ResponsiveContainer></div>
          <p className="text-xs text-[var(--muted)]">Probability of detection (POD): of all the places where heavy rain really fell, how many had a warning.</p>
        </Card>
      </div>
      <Card title="Why regime-aware correction matters">
        <p className="text-sm">A single correction for all days does not fix heavy rain well. It was the second-weakest method in our test (heavy-rain score {v1.overall.QM_GLOBAL["t64.5"].ETS.toFixed(3)} vs VARSHA {var_.ETS.toFixed(3)}).
          VARSHA learns the correction separately for active, break, depression and normal days, and for mountains, coasts and plains, which is exactly what PS 26080 asks for.</p>
      </Card>
      <div>
        <button onClick={() => setTech((x) => !x)} className="rounded-lg border border-[var(--line)] bg-white px-4 py-2 text-sm font-medium hover:bg-[var(--panel)]">
          {tech ? "Hide technical details" : "Show technical details (RMSE, ETS, CSI, POD, FAR, FSS, reliability)"}
        </button>
      </div>
      {tech && <VerificationView />}
    </div>
  );
}
