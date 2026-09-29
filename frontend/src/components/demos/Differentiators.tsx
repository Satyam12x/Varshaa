"use client";

import type { ReactNode } from "react";
import { REGIME_COLOR } from "@/lib/colors";
import { Bars, PROOFS, useProofStats, type ProofId } from "./proofs";

/** Paired columns, raw model (grey) then VARSHA (brand), one pair per label. */
function Pairs({ items }: { items: { label: string; raw: number; varsha: number }[] }) {
  const max = Math.max(...items.flatMap((x) => [x.raw, x.varsha]), 1e-9);
  return (
    <div className="flex h-full items-end gap-2">
      {items.map((x) => (
        <div key={x.label} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
          <div className="flex h-full w-full items-end justify-center gap-0.5">
            <div className="w-1/3 max-w-3 rounded-t-sm bg-[#c3ccd3]" style={{ height: `${(100 * x.raw) / max}%` }} />
            <div className="w-1/3 max-w-3 rounded-t-sm bg-[var(--brand)]" style={{ height: `${(100 * x.varsha) / max}%` }} />
          </div>
          <span className="text-[10.5px] text-[var(--faint)]">{x.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function Differentiators({ open }: { open: (proof: ProofId) => void }) {
  const { reg, v, storm, sum, stat } = useProofStats();
  const season = (reg?.days ?? []).filter((d) => d.date.startsWith("2023"));
  const visual: Record<ProofId, ReactNode> = {
    monsoon: (
      <div className="flex h-full flex-col justify-end">
        <div className="flex h-9 overflow-hidden rounded-md">
          {season.map((d) => <div key={d.date} className="h-full flex-1" style={{ background: d.anom === null ? "#eef3f6" : d.regime === "Active" || d.regime === "Break" ? REGIME_COLOR[d.regime] : "#dbe4ea" }} />)}
        </div>
        <div className="mt-1.5 flex justify-between text-[10.5px] text-[var(--faint)]"><span>Jun 2023</span><span><span className="text-[var(--brand)]">■</span> active <span className="ml-1 text-[#c9861f]">■</span> break</span><span>Sep</span></div>
      </div>
    ),
    pattern: v && (
      <Pairs items={["Active", "Normal", "Break", "Depression"].map((r) => ({ label: r === "Depression" ? "Depr." : r, raw: v.by_regime.RAW[r]["t64.5"].ETS, varsha: v.by_regime.WARN[r]["t64.5"].ETS }))} />
    ),
    storm: storm && (
      <div className="flex h-full flex-col justify-end"><Bars raw={storm.pod_raw} varsha={storm.pod_varsha} max={Math.max(storm.pod_raw, storm.pod_varsha) * 1.15} fmt={(x) => `${Math.round(100 * x)}%`} /></div>
    ),
    district: sum && (
      <Pairs items={Object.entries(sum.seasons).map(([y, t]) => ({ label: `’${y.slice(2)}`, raw: t.raw, varsha: t.varsha }))} />
    ),
  };

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[12px] font-semibold uppercase tracking-[0.14em] text-[var(--marigold)]">What makes VARSHA different</div>
          <h2 className="mt-1 text-[24px] font-semibold tracking-tight">Four things you can check yourself</h2>
        </div>
        <div className="flex items-center gap-4 text-[12.5px] text-[var(--muted)]">
          <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[#c3ccd3]" />Raw weather model</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[var(--brand)]" />VARSHA</span>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {PROOFS.map((p, k) => {
          const s = stat[p.id];
          return (
            <button key={p.id} onClick={() => open(p.id)}
              className="group flex flex-col rounded-2xl border border-[var(--line)] bg-white p-5 text-left transition-all hover:-translate-y-0.5 hover:border-[var(--brand)] hover:shadow-[0_10px_30px_rgba(11,79,108,0.12)]">
              <div className="flex items-center gap-2 text-[12px] font-semibold">
                <span className="text-[var(--marigold)]">0{k + 1}</span>
                <span className="rounded-full bg-[var(--panel2)] px-2 py-0.5 text-[10.5px] font-bold tracking-wide text-[#8a5a12]">USP {p.usp} · {p.tag}</span>
              </div>
              <div className="mt-2 text-[17px] font-semibold leading-snug">{p.title}</div>
              <div className="mt-1.5 text-[13px] leading-relaxed text-[var(--muted)]">{p.claim}</div>
              <div className="mt-auto h-[68px] pt-4">{visual[p.id] ?? <div className="h-full animate-pulse rounded bg-[var(--panel)]" />}</div>
              <div className="mt-4 border-t border-[var(--line)] pt-3">
                {s ? <><div className="text-[22px] font-semibold leading-none tabular-nums text-[var(--brand)]">{s.big}</div><div className="mt-1 text-[12.5px] leading-snug text-[var(--muted)]">{s.small}</div></> : <div className="h-10" />}
              </div>
              <div className="pt-4 text-[13.5px] font-medium text-[var(--brand)]">See it live <span className="inline-block transition-transform group-hover:translate-x-1">→</span></div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
