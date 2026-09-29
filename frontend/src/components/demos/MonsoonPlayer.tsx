"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { RAIN_CLASSES, REGIME_COLOR, niceDate } from "@/lib/colors";
import { px, py, useFetch } from "../AppContext";
import GridMap from "../GridMap";
import type { RegimeIndex } from "./proofs";

interface Day { date: string; anom: number | null; regime: string; rain: string }

const YEARS = [2021, 2022, 2023, 2024, 2025, 2026];
const STATE: Record<string, { name: string; does: string }> = {
  Active: { name: "Active monsoon", does: "VARSHA switches to its active-monsoon correction" },
  Break: { name: "Break in the monsoon", does: "VARSHA switches to its break-monsoon correction" },
  Normal: { name: "Normal monsoon", does: "VARSHA uses its normal-monsoon correction" },
};
const strip = (r: string, anom: number | null) => (anom === null ? "#eef3f6" : r === "Active" || r === "Break" ? REGIME_COLOR[r] : "#dbe4ea");

export default function MonsoonPlayer({ initialYear = 2023 }: { initialYear?: number }) {
  const { data: idx } = useFetch<RegimeIndex>("/demo/regime");
  const [year, setYear] = useState(initialYear);
  const [pos, setPos] = useState(0);
  const [playing, setPlaying] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const started = useRef(false);
  const days = useMemo(() => (idx?.days ?? []).filter((d) => d.date.startsWith(String(year))), [idx, year]);
  const cur = days[Math.min(pos, days.length - 1)];
  const { data: day } = useFetch<Day>(cur ? `/demo/regime/${cur.date}` : null);
  const values = useMemo(() => (day ? Array.from(day.rain, (c) => Number(c)) : undefined), [day]);

  // start playing by itself the first time the player scrolls into view
  useEffect(() => {
    if (!idx || started.current || !root.current || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting && !started.current) { started.current = true; setPlaying(true); } }, { threshold: 0.35 });
    io.observe(root.current);
    return () => io.disconnect();
  }, [idx]);

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setPos((p) => (p + 1 >= days.length ? (setPlaying(false), p) : p + 1)), 300);
    return () => clearInterval(t);
  }, [playing, days.length]);

  if (!idx || !cur) return <div className="h-[560px] animate-pulse rounded-xl bg-[var(--panel)]" />;
  const c = { ...idx.core, lon0: Math.max(idx.core.lon0, 66.6) }; // IMD's box starts at 65°E, west of the map edge
  const st = STATE[cur.regime] ?? STATE.Normal;
  const a = cur.anom;
  const gx = (x: number) => `${((Math.max(-3, Math.min(3, x)) + 3) / 6) * 100}%`;
  const soFar = days.slice(0, pos + 1);
  const n = (r: string) => soFar.filter((d) => d.regime === r).length;
  const atEnd = pos >= days.length - 1;
  const box = (
    <g pointerEvents="none">
      <rect x={px(c.lon0)} y={py(c.lat1)} width={px(c.lon1) - px(c.lon0)} height={py(c.lat0) - py(c.lat1)} fill="none" stroke="#0f1f2b" strokeWidth={1.4} strokeDasharray="6 4" />
      <rect x={px(c.lon0) + 4} y={py(c.lat1) + 4} width={118} height={19} rx={4} fill="white" opacity={0.9} />
      <text x={px(c.lon0) + 10} y={py(c.lat1) + 17.5} fontSize={11.5} fontWeight={600} fill="#0f1f2b">IMD monsoon zone</text>
    </g>
  );

  return (
    <div ref={root} className="grid items-start gap-8 lg:grid-cols-[minmax(0,540px)_minmax(0,1fr)]">
      <div>
        <GridMap cells={idx.cells} values={values} color={(v) => (v === null || v === undefined ? "#e6edf1" : RAIN_CLASSES[v as number].color)} overlay={box}
          tooltip={(k) => <>{values ? RAIN_CLASSES[values[k]].name : ""} rain, measured by IMD</>} />
        <div className="mt-2 flex flex-wrap gap-x-3.5 gap-y-1 text-[11.5px] text-[var(--muted)]">
          {RAIN_CLASSES.slice(1).map((r) => <span key={r.name} className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: r.color }} />{r.name}</span>)}
        </div>
      </div>

      <div className="flex flex-col gap-6">
        <div>
          <div className="text-[14px] font-medium text-[var(--muted)]">{niceDate(cur.date)} {year}</div>
          <div className="mt-2 inline-flex items-center rounded-xl px-5 py-2.5 text-[28px] font-semibold leading-tight text-white transition-colors duration-300" style={{ background: REGIME_COLOR[cur.regime] ?? "#6b7c8a" }}>{st.name}</div>
          <div className="mt-3 flex items-center gap-2 text-[15px]"><span className="text-[var(--marigold)]">➜</span>{st.does}</div>
        </div>

        <div>
          <div className="relative h-10 overflow-hidden rounded-lg bg-[var(--panel)]">
            <div className="absolute inset-y-0 left-0 bg-[#c9861f]/20" style={{ width: gx(-1) }} />
            <div className="absolute inset-y-0 right-0 bg-[#0b4f6c]/15" style={{ left: gx(1) }} />
            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[11.5px] font-medium text-[#8a5a12]">Break</span>
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[11.5px] font-medium text-[var(--brand)]">Active</span>
            {a !== null && <div className="absolute top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white shadow transition-all duration-300" style={{ left: gx(a), background: REGIME_COLOR[cur.regime] ?? "#6b7c8a" }} />}
          </div>
          <div className="mt-1.5 text-[12px] text-[var(--faint)]">Rain over the monsoon zone compared with IMD&apos;s 1991–2020 normal{a !== null && `: ${a > 0 ? "+" : ""}${a.toFixed(1)}`}</div>
        </div>

        <div>
          <div className="flex h-9 overflow-hidden rounded-md">
            {days.map((d, i) => (
              <button key={d.date} onClick={() => { setPos(i); setPlaying(false); }} title={`${niceDate(d.date)}: ${STATE[d.regime]?.name ?? d.regime}`} aria-label={d.date}
                className="h-full flex-1 transition-opacity" style={{ background: strip(d.regime, d.anom), opacity: i <= pos ? 1 : 0.35, boxShadow: i === pos ? "inset 0 0 0 2px #0f1f2b" : "none" }} />
            ))}
          </div>
          <div className="mt-1 flex justify-between text-[11.5px] text-[var(--faint)]"><span>1 Jun</span><span>Jul</span><span>Aug</span><span>30 Sep</span></div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => { if (atEnd) setPos(0); setPlaying((x) => !x); }} className="w-[132px] rounded-full bg-[var(--brand)] py-2.5 text-[14px] font-medium text-white hover:bg-[var(--accent-ink)]">
            {playing ? "❚❚  Pause" : atEnd ? "↻  Replay" : "▶  Play"}
          </button>
          <div className="flex flex-wrap gap-1.5">
            {YEARS.map((y) => (
              <button key={y} onClick={() => { setYear(y); setPos(0); setPlaying(true); }}
                className={`rounded-full border px-3 py-1 text-[13px] ${year === y ? "border-[var(--brand)] bg-[var(--brand)] text-white" : "border-[var(--line)] bg-white hover:border-[var(--faint)]"}`}>{y}</button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-[var(--line)] p-4"><div className="text-[30px] font-semibold leading-none tabular-nums text-[var(--brand)]">{n("Active")}</div><div className="mt-1 text-[13px] text-[var(--muted)]">active days so far</div></div>
          <div className="rounded-xl border border-[var(--line)] p-4"><div className="text-[30px] font-semibold leading-none tabular-nums text-[#a86d14]">{n("Break")}</div><div className="mt-1 text-[13px] text-[var(--muted)]">break days so far</div></div>
        </div>
      </div>
    </div>
  );
}
