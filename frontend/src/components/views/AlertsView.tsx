"use client";

import { useState } from "react";
import type { DistrictRow, Forecast } from "@/lib/api";
import { LEVELS, LEVEL_ADVICE, LEVEL_COLOR, LEVEL_LONG, LEVEL_TEXT, dayName, fmt, niceDate, pct, probColor } from "@/lib/colors";
import { useFetch } from "../AppContext";
import GridMap, { Card, Legend } from "../GridMap";
import { Explainer, Loading, Toggle, WarningChip, WarningLegend } from "../ui";
import { UspTag } from "../usp";

export default function AlertsView({ lead, openDistrict }: { lead: number; openDistrict: (id: number) => void }) {
  const { data: d } = useFetch<{ rows: DistrictRow[]; valid: string }>(`/districts?lead=${lead}`);
  const { data: f } = useFetch<Forecast>(`/forecast?lead=${lead}`);
  const [mode, setMode] = useState<"districts" | "chance">("districts");
  if (!d || !f) return <Loading what="Loading alerts…" />;
  const fill = new Map(d.rows.map((r) => [r.id, LEVEL_COLOR[r.level]]));
  const byId = new Map(d.rows.map((r) => [r.id, r]));
  const counts = Object.fromEntries(LEVELS.map((l) => [l, d.rows.filter((r) => r.level === l).length]));
  const alerts = d.rows.filter((r) => r.level !== "green");

  return (
    <div className="flex flex-col gap-4">
      <Explainer title={`Heavy-rain alerts · ${dayName(lead)}, ${niceDate(d.valid)}`}>
        &ldquo;Heavy rain&rdquo; means 64.5 mm or more in a day (IMD&apos;s definition), enough to flood streets and low-lying areas. Each district is coloured like IMD&apos;s warnings.
        Click a district to see its 5-day forecast.
      </Explainer>
      <div className="flex flex-wrap items-center gap-3"><Toggle options={[["districts", "District colours"], ["chance", "Chance of heavy rain (detailed map)"]]} value={mode} onChange={setMode} /><UspTag n={2} /></div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Card>
          {mode === "districts" ? (
            <GridMap cells={f.cells} districtFill={fill} onDistrict={openDistrict}
              tooltip={(_, id) => { const r = byId.get(id); return r ? <><WarningChip level={r.level} /><br />{pct(r.p_heavy)} chance of heavy rain · up to {fmt(r.max)} mm</> : null; }}
              legend={<WarningLegend counts={counts} />} />
          ) : (
            <GridMap cells={f.cells} values={f.p_heavy} color={probColor} tooltip={(k) => <>{pct(f.p_heavy[k])} chance of 64.5 mm or more</>}
              legend={<Legend items={[0.05, 0.15, 0.3, 0.5, 0.8].map((p) => ({ color: probColor(p), label: `${Math.round(p * 100)}% chance` }))} />} />
          )}
        </Card>
        <div className="flex flex-col gap-4">
          <Card title="What the colours mean">
            <div className="flex flex-col gap-2">
              {LEVELS.map((l) => (
                <div key={l} className="flex items-start gap-3">
                  <span className="mt-0.5 h-5 w-5 shrink-0 rounded-md" style={{ background: LEVEL_COLOR[l] }} />
                  <div><div className="text-sm font-semibold">{LEVEL_TEXT[l]}: {LEVEL_LONG[l].toLowerCase()} <span className="font-normal text-[var(--muted)]">· {counts[l]} districts</span></div><div className="text-xs text-[var(--muted)]">{LEVEL_ADVICE[l]}</div></div>
                </div>
              ))}
            </div>
          </Card>
          <Card title={alerts.length ? `Districts on alert (${alerts.length})` : "Districts on alert"}>
            {alerts.length === 0 ? (
              <p className="text-sm">No district is expected to get heavy rain on this day. Try another day above, or see <b>Past storms</b> to watch VARSHA during real storms.</p>
            ) : (
              <div className="flex max-h-80 flex-col divide-y divide-[var(--line)] overflow-auto">
                {alerts.map((r) => (
                  <button key={r.id} onClick={() => openDistrict(r.id)} className="flex items-center justify-between gap-2 py-2 text-left text-sm hover:bg-[var(--panel)]">
                    <span><b>{r.name}</b> <span className="text-[var(--muted)]">{r.state}</span></span><WarningChip level={r.level} />
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
