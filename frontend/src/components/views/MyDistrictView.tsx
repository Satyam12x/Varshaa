"use client";

import { useState } from "react";
import { API_URL, type DistrictRow } from "@/lib/api";
import { LEVEL_ADVICE, LEVEL_COLOR, dayName, fmt, niceDate, pct, rainClass } from "@/lib/colors";
import { useFetch } from "../AppContext";
import { Card } from "../GridMap";
import { Explainer, Loading, WarningChip } from "../ui";
import { UspTag } from "../usp";

type Rows = { rows: DistrictRow[]; valid: string; lead: number };

export default function MyDistrictView({ initial }: { initial: number | null }) {
  const days = [1, 2, 3, 4, 5].map((l) => useFetch<Rows>(`/districts?lead=${l}`).data); // eslint-disable-line react-hooks/rules-of-hooks
  const first = days[0];
  const [picked, setPicked] = useState<number | null>(initial);
  const [state, setState] = useState<string>("");
  const [showAll, setShowAll] = useState(false);
  if (!first) return <Loading what="Loading districts…" />;
  const all = [...first.rows].sort((a, b) => a.state.localeCompare(b.state) || a.name.localeCompare(b.name));
  const states = [...new Set(all.map((r) => r.state))];
  const id = picked ?? null;
  const cur = id !== null ? all.find((r) => r.id === id) : null;
  const st = state || cur?.state || "";
  const inState = all.filter((r) => r.state === st);

  return (
    <div className="flex flex-col gap-4">
      <UspTag n={3} />
      <Explainer title="Rain forecast for your district">
        Choose your state and district to see the next 5 days: expected rain, the chance of heavy rain, and what to do.
        District boundaries are from the Survey of India.
      </Explainer>
      <div className="flex flex-wrap gap-2">
        <select value={st} onChange={(e) => { setState(e.target.value); setPicked(null); }} className="rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-[15px]">
          <option value="">Choose a state / UT…</option>{states.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={id ?? ""} disabled={!st} onChange={(e) => setPicked(Number(e.target.value))} className="rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-[15px] disabled:opacity-50">
          <option value="">Choose a district…</option>{inState.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
      </div>

      {cur ? (
        <Card title={<span className="text-lg">{cur.name}, {cur.state}</span>}>
          <div className="grid gap-3 sm:grid-cols-5">
            {days.map((d, i) => {
              const r = d?.rows.find((x) => x.id === cur.id);
              if (!d || !r) return <div key={i} className="rounded-xl border border-[var(--line)] p-3 text-sm text-[var(--muted)]">Loading…</div>;
              const cls = rainClass(r.mean);
              return (
                <div key={i} className="rounded-xl border-2 p-3" style={{ borderColor: LEVEL_COLOR[r.level] }}>
                  <div className="text-sm font-semibold">{dayName(d.lead)}</div>
                  <div className="text-xs text-[var(--muted)]">{niceDate(d.valid)}</div>
                  <div className="mt-2 text-2xl font-bold">{fmt(r.mean)} <span className="text-sm font-medium">mm</span></div>
                  <div className="text-xs text-[var(--muted)]">{cls?.name} on average · up to {fmt(r.max)} mm in parts</div>
                  <div className="mt-2 text-sm"><b>{pct(r.p_heavy)}</b> chance of heavy rain</div>
                  <div className="mt-2"><WarningChip level={r.level} /></div>
                  <div className="mt-1 text-xs text-[var(--muted)]">{LEVEL_ADVICE[r.level]}</div>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-[var(--muted)]">&ldquo;Up to&rdquo; is the wettest 25 km square inside the district. The raw weather model said {fmt(first.rows.find((x) => x.id === cur.id)?.raw_mean)} mm on average for tomorrow, before correction.</p>
        </Card>
      ) : (
        <Card><p className="text-sm text-[var(--muted)]">Pick a state and district above.</p></Card>
      )}

      <Card title="All districts" right={
        <div className="flex gap-2">
          <button onClick={() => setShowAll((x) => !x)} className="rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm">{showAll ? "Hide table" : "Show all districts"}</button>
          <a className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white" href={`${API_URL}/districts?lead=1&format=csv`}>Download tomorrow as CSV</a>
        </div>}>
        {showAll ? (
          <div className="max-h-[520px] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white"><tr className="text-left text-xs text-[var(--muted)]"><th className="py-1.5 font-medium">District</th><th className="font-medium">State / UT</th><th className="text-right font-medium">Tomorrow (avg)</th><th className="text-right font-medium">Chance of heavy rain</th><th className="pl-3 font-medium">Warning</th></tr></thead>
              <tbody>{all.map((r) => (
                <tr key={r.id} onClick={() => { setPicked(r.id); setState(r.state); window.scrollTo({ top: 0, behavior: "smooth" }); }} className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--panel)]">
                  <td className="py-1.5 font-medium">{r.name}</td><td className="text-xs">{r.state}</td><td className="text-right tabular-nums">{fmt(r.mean)} mm</td><td className="text-right tabular-nums">{pct(r.p_heavy)}</td><td className="pl-3"><WarningChip level={r.level} /></td>
                </tr>))}
              </tbody>
            </table>
          </div>
        ) : <p className="text-sm text-[var(--muted)]">{all.length} districts. The table and CSV use the same numbers as the maps.</p>}
      </Card>
    </div>
  );
}
