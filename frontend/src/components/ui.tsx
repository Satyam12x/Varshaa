"use client";

import type { ReactNode } from "react";
import type { Level } from "@/lib/api";
import { LEVELS, LEVEL_COLOR, LEVEL_LONG, LEVEL_TEXT, RAIN_CLASSES, dayName, niceDate } from "@/lib/colors";

/** "What am I looking at?" note at the top of every page. */
export function Explainer({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-r-xl border-l-4 border-[var(--accent)] bg-[var(--surface)] px-5 py-4 shadow-[0_1px_2px_rgba(15,31,43,0.05)]">
      <h2 className="text-[19px] font-semibold leading-snug">{title}</h2>
      <div className="mt-1.5 max-w-[860px] text-[15px] leading-relaxed text-[var(--muted)]">{children}</div>
    </div>
  );
}

export function Section({ title, kicker, children, right }: { title?: ReactNode; kicker?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6">
      {(title || right) && (
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            {kicker && <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--faint)]">{kicker}</div>}
            {title && <h2 className="text-[19px] font-semibold leading-tight">{title}</h2>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export function BigStat({ value, label, sub, accent = false }: { value: ReactNode; label: string; sub?: ReactNode; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-white px-5 py-4">
      <div className={`text-[30px] font-semibold leading-none ${accent ? "text-[var(--accent)]" : "text-[var(--ink)]"}`}>{value}</div>
      <div className="mt-2 text-[14px] font-medium">{label}</div>
      {sub && <div className="mt-1 text-[12.5px] leading-snug text-[var(--muted)]">{sub}</div>}
    </div>
  );
}

export function DayPicker({ leads, lead, onChange }: { leads: { lead: number; valid: string }[]; lead: number; onChange: (l: number) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-[13px] font-medium text-[var(--muted)]">Forecast for</span>
      <div className="flex flex-wrap gap-1.5">
        {leads.map((l) => (
          <button key={l.lead} onClick={() => onChange(l.lead)}
            className={`rounded-full border px-4 py-1.5 text-[13.5px] transition-colors ${lead === l.lead ? "border-[var(--brand)] bg-[var(--brand)] text-white" : "border-[var(--line)] bg-white text-[var(--ink)] hover:border-[var(--faint)]"}`}>
            <span className="font-medium">{dayName(l.lead)}</span> <span className="opacity-70">{niceDate(l.valid)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function Toggle<T extends string>({ options, value, onChange }: { options: [T, string][]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex self-start rounded-full border border-[var(--line)] bg-white p-1">
      {options.map(([k, label]) => (
        <button key={k} onClick={() => onChange(k)}
          className={`rounded-full px-4 py-1.5 text-[13.5px] transition-colors ${value === k ? "bg-[var(--brand)] font-medium text-white" : "text-[var(--muted)] hover:text-[var(--ink)]"}`}>{label}</button>
      ))}
    </div>
  );
}

export function RainLegend({ from = 0 }: { from?: number }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-[12.5px]">
      {RAIN_CLASSES.slice(from).map((c) => (
        <span key={c.name} className="inline-flex items-center gap-2">
          <span className="inline-block h-3.5 w-6 rounded-sm border border-black/10" style={{ background: c.color }} />
          <span><b className="font-semibold">{c.name}</b> <span className="text-[var(--muted)]">{c.range}</span></span>
        </span>
      ))}
    </div>
  );
}

export function WarningLegend({ counts }: { counts?: Record<string, number> }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-[12.5px]">
      {LEVELS.map((l) => (
        <span key={l} className="inline-flex items-center gap-2">
          <span className="inline-block h-3.5 w-3.5 rounded-sm" style={{ background: LEVEL_COLOR[l] }} />
          <span><b className="font-semibold">{LEVEL_TEXT[l]}</b> <span className="text-[var(--muted)]">{l === "green" ? "" : LEVEL_LONG[l].toLowerCase()}{counts ? ` · ${counts[l] ?? 0}` : ""}</span></span>
        </span>
      ))}
    </div>
  );
}

export function WarningChip({ level }: { level: Level }) {
  const dark = level === "red" || level === "orange";
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[12px] font-semibold"
      style={{ background: level === "green" ? "#e9f0f4" : LEVEL_COLOR[level], color: dark ? "#fff" : level === "green" ? "#6b7c8a" : "#3a2600" }}>
      {LEVEL_TEXT[level]}{level !== "green" && <span className="font-normal opacity-90">· {LEVEL_LONG[level].toLowerCase()}</span>}
    </span>
  );
}

export function Loading({ what = "Loading…" }: { what?: string }) {
  return <div className="rounded-2xl border border-[var(--line)] bg-white p-8 text-[14px] text-[var(--muted)]">{what}</div>;
}
