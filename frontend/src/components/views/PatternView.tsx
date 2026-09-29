"use client";

import { Bar, BarChart, CartesianGrid, Cell as RCell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { REGIME_COLOR, REGIME_PLAIN, SETTING_COLOR, fmt, niceDate } from "@/lib/colors";
import { useApp, useFetch } from "../AppContext";
import GridMap, { Card, Legend } from "../GridMap";
import { Explainer, Loading } from "../ui";
import { UspTag } from "../usp";

interface History { dates: string[]; anom: (number | null)[]; regime: string[] }
const SETTING_PLAIN: Record<number, string> = { 0: "Mountains & hills", 1: "Coast", 3: "Plains / inland" };

export default function PatternView() {
  const { meta, cellMeta } = useApp();
  const { data: hist } = useFetch<History>("/regime/history");
  if (!meta) return <Loading />;
  const r = meta.regime;
  const plain = REGIME_PLAIN[r?.large_scale ?? "Normal"] ?? REGIME_PLAIN.Normal;
  const seasons = new Map<number, { date: string; regime: string; anom: number | null }[]>();
  hist?.dates.forEach((d, k) => {
    const y = Number(d.slice(0, 4)), mo = Number(d.slice(5, 7));
    if (mo < 6 || mo > 9) return;
    if (!seasons.has(y)) seasons.set(y, []);
    seasons.get(y)!.push({ date: d, regime: hist.regime[k], anom: hist.anom[k] });
  });

  return (
    <div className="flex flex-col gap-4">
      <UspTag n={1} />
      <Explainer title="What is the monsoon doing right now?">
        Weather models make different mistakes depending on the weather pattern, so VARSHA first works out which pattern we are in.
        It uses IMD&apos;s own rule: compare today&apos;s rain over central India with the 30-year average (1991–2020) for the same date.
      </Explainer>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <Card>
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-xl px-4 py-2 text-2xl font-bold text-white" style={{ background: REGIME_COLOR[r?.large_scale ?? "Normal"] }}>{plain.title}</span>
              <span className="text-sm text-[var(--muted)]">based on IMD rainfall of {r?.based_on ? niceDate(r.based_on) : "–"}</span>
            </div>
            <p className="mt-3 text-[15px]">{plain.text}</p>
            <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              {(["Active", "Break", "Depression", "Normal"] as const).map((k) => (
                <div key={k} className="flex items-start gap-2"><span className="mt-1 h-3 w-3 shrink-0 rounded-sm" style={{ background: REGIME_COLOR[k] }} /><span><b>{REGIME_PLAIN[k].title}:</b> {k === "Active" ? "rain well above normal for 3+ days" : k === "Break" ? "rain well below normal for 3+ days" : k === "Depression" ? "an IMD-tracked low-pressure system is nearby" : "close to normal"}</span></div>
              ))}
            </div>
            {r && r.depressions.length > 0 && <p className="mt-3 rounded-lg bg-[var(--panel)] p-3 text-sm">An IMD-tracked depression is active: {r.depression_cells} areas are treated as &ldquo;depression&rdquo; days.</p>}
          </Card>
          {r && (
            <Card title="Rain over central India vs normal, last 15 days">
              <div className="h-48"><ResponsiveContainer width="100%" height="100%">
                <BarChart data={r.recent} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={(d: string) => d.slice(8)} tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
                  <ReferenceLine y={1} stroke={REGIME_COLOR.Active} strokeDasharray="4 3" label={{ value: "active", fontSize: 10, fill: REGIME_COLOR.Active, position: "insideTopLeft" }} />
                  <ReferenceLine y={-1} stroke={REGIME_COLOR.Break} strokeDasharray="4 3" label={{ value: "break", fontSize: 10, fill: REGIME_COLOR.Break, position: "insideBottomLeft" }} />
                  <Tooltip formatter={(v) => fmt(Number(v), 2)} labelFormatter={(d) => niceDate(String(d))} contentStyle={{ fontSize: 12 }} />
                  <Bar dataKey="anom" name="Above (+) or below (−) normal" isAnimationActive={false}>{r.recent.map((x, k) => <RCell key={k} fill={REGIME_COLOR[x.regime] ?? "#aab7c1"} />)}</Bar>
                </BarChart></ResponsiveContainer></div>
              <p className="text-xs text-[var(--muted)]">Bars above the dark blue line for 3 days in a row mean an <b>active</b> spell; below the gold line means a <b>break</b>.</p>
            </Card>
          )}
          <Card title="The same rule on six monsoons (June to September)">
            <div className="space-y-1.5">
              {[...seasons.entries()].map(([y, ds]) => (
                <div key={y} className="flex items-center gap-2 text-xs">
                  <span className="w-10 font-semibold">{y}</span>
                  <div className="flex h-4 flex-1 overflow-hidden rounded">{ds.map((d) => <div key={d.date} title={`${d.date}: ${d.regime}`} className="h-full flex-1" style={{ background: d.anom === null ? "#e9f0f4" : d.regime === "Normal" ? "#dbe4ea" : REGIME_COLOR[d.regime] }} />)}</div>
                </div>
              ))}
            </div>
            <div className="mt-2"><Legend items={[{ color: REGIME_COLOR.Active, label: "Active spell" }, { color: REGIME_COLOR.Break, label: "Break spell" }, { color: "#dbe4ea", label: "Normal" }]} /></div>
          </Card>
        </div>
        <Card title="Where the land shape changes the rain">
          {cellMeta ? (
            <GridMap cells={cellMeta.cells} values={cellMeta.cells.map((_, k) => k)} color={(k) => SETTING_COLOR[cellMeta.cell_setting[k as number]]}
              tooltip={(k) => <>{SETTING_PLAIN[cellMeta.cell_setting[k]]}</>}
              legend={<Legend items={[{ color: SETTING_COLOR[0], label: "Mountains & hills (Western Ghats, North-East, Himalaya)" }, { color: SETTING_COLOR[1], label: "Coast (within ~50 km)" }, { color: SETTING_COLOR[3], label: "Plains / inland" }]} />} />
          ) : <Loading />}
          <p className="mt-2 text-sm text-[var(--muted)]">Moist monsoon winds pushed up mountains give much more rain, and coasts behave differently from plains. VARSHA learns a separate correction for each weather pattern in each of these areas.</p>
        </Card>
      </div>
    </div>
  );
}
