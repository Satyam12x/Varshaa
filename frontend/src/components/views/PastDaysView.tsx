"use client";

import { useState } from "react";
import type { Cell, ReplayDay, ReplayEvent } from "@/lib/api";
import { LEVEL_COLOR, REGIME_PLAIN, fmt, niceDate, rainColor } from "@/lib/colors";
import { useFetch } from "../AppContext";
import GridMap, { Card, Legend } from "../GridMap";
import { Explainer, Loading, RainLegend, Toggle } from "../ui";
import { UspTag } from "../usp";

export default function PastDaysView() {
  const { data: idx } = useFetch<{ cells: Cell[]; events: ReplayEvent[] }>("/replay");
  const [date, setDate] = useState<string | null>(null);
  const [lead, setLead] = useState<"1" | "3">("1");
  const [compare, setCompare] = useState<"varsha" | "raw">("varsha");
  const sel = date ?? idx?.events[0]?.date ?? null;
  const { data: day } = useFetch<ReplayDay>(sel ? `/replay/${sel}` : null);
  if (!idx) return <Loading what="Loading past heavy-rain days…" />;
  const L = day?.leads[lead];
  const warnColor = (v: number | null) => (v === null ? "#e6edf1" : v >= 150 ? LEVEL_COLOR.orange : v >= 100 ? LEVEL_COLOR.yellow : "#f8fbfc");
  const rawWarn = (v: number | null) => (v === null ? "#e6edf1" : v >= 115.6 ? LEVEL_COLOR.orange : v >= 64.5 ? LEVEL_COLOR.yellow : "#f8fbfc");
  const sv = L?.scores.warning, sr = L?.scores.raw;
  const leadText = lead === "1" ? "one day before" : "three days before";

  return (
    <div className="flex flex-col gap-4">
      <UspTag n={3} />
      <Explainer title="Would VARSHA have warned us? Replaying real heavy-rain days">
        These are the days with the most heavy rain in India from 2021 to 2026. For each one, see <b>where heavy rain really fell</b> (measured by IMD)
        next to <b>where VARSHA warned</b> in advance. The forecasts come from a VARSHA that had never seen that year.
      </Explainer>
      <div className="grid gap-4 lg:grid-cols-[250px_minmax(0,1fr)]">
        <Card title="Pick a day">
          <div className="flex max-h-[620px] flex-col gap-1.5 overflow-auto">
            {idx.events.map((e) => {
              const better = e.ets_varsha > e.ets_raw;
              return (
                <button key={e.date} onClick={() => setDate(e.date)} className={`rounded-lg border px-2.5 py-2 text-left text-sm ${sel === e.date ? "border-[var(--accent)] bg-[var(--panel)]" : "border-[var(--line)] hover:bg-[var(--panel)]"}`}>
                  <div className="font-semibold">{niceDate(e.date)} {e.date.slice(0, 4)}</div>
                  <div className="text-xs text-[var(--muted)]">{e.heavy_cells} areas with heavy rain</div>
                  <div className={`text-xs font-medium ${better ? "text-[var(--accent)]" : "text-[var(--muted)]"}`}>{better ? "VARSHA did better" : "Raw model did about the same or better"}</div>
                </button>
              );
            })}
          </div>
        </Card>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-2">
            <Toggle options={[["1", "Warning given 1 day before"], ["3", "Warning given 3 days before"]]} value={lead} onChange={setLead} />
            <Toggle options={[["varsha", "Show VARSHA"], ["raw", "Show raw model instead"]]} value={compare} onChange={setCompare} />
          </div>
          {day && L && sv && sr ? (
            <>
              <Card>
                <p className="text-[16px] leading-relaxed">
                  On <b>{niceDate(day.date)} {day.date.slice(0, 4)}</b>, heavy rain (64.5 mm or more) fell over <b>{day.heavy_cells}</b> areas of 25 km × 25 km.
                  Warning {leadText}, <b className="text-[var(--accent)]">VARSHA covered {sv.hits}</b> of them ({Math.round(sv.POD * 100)}%), while the
                  <b> raw model covered {sr.hits}</b> ({Math.round(sr.POD * 100)}%). VARSHA raised {sv.false_alarms} warnings where heavy rain did not come (raw model: {sr.false_alarms}).
                </p>
                <p className="mt-1 text-xs text-[var(--muted)]">Weather pattern that day: {REGIME_PLAIN[day.regime]?.title ?? day.regime}.</p>
              </Card>
              <div className="grid gap-4 md:grid-cols-2">
                <Card title="What really fell (IMD measured)">
                  <GridMap cells={idx.cells} values={L.obs} color={rainColor} tooltip={(k) => <>Measured: <b>{fmt(L.obs[k])} mm</b></>} compact />
                </Card>
                <Card title={compare === "varsha" ? `Where VARSHA warned (${leadText})` : `Where the raw model showed heavy rain (${leadText})`}>
                  <GridMap cells={idx.cells} values={compare === "varsha" ? L.warn : L.raw} color={compare === "varsha" ? warnColor : rawWarn}
                    tooltip={(k) => <>{compare === "varsha" ? ((L.warn[k] ?? 0) >= 150 ? "Very heavy rain warning" : (L.warn[k] ?? 0) >= 100 ? "Heavy rain warning" : "No warning") : `Raw model: ${fmt(L.raw[k])} mm`}<br />Measured: {fmt(L.obs[k])} mm</>} compact />
                </Card>
              </div>
              <Card>
                <div className="flex flex-wrap justify-between gap-3">
                  <div><div className="mb-1 text-xs font-semibold text-[var(--muted)]">Left map: measured rain</div><RainLegend from={2} /></div>
                  <div><div className="mb-1 text-xs font-semibold text-[var(--muted)]">Right map: warnings</div><Legend items={[{ color: LEVEL_COLOR.yellow, label: "Heavy rain" }, { color: LEVEL_COLOR.orange, label: "Very heavy rain" }]} /></div>
                </div>
              </Card>
            </>
          ) : <Loading what="Loading maps…" />}
        </div>
      </div>
    </div>
  );
}
