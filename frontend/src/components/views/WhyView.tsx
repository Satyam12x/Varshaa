"use client";

import { useState } from "react";
import DistrictRecord from "../demos/DistrictRecord";
import MonsoonPlayer from "../demos/MonsoonPlayer";
import PatternSkill from "../demos/PatternSkill";
import StormSwipe from "../demos/StormSwipe";
import { PROOFS, useProofStats, type ProofId } from "../demos/proofs";

const DEMO: Record<ProofId, React.ReactNode> = {
  monsoon: <MonsoonPlayer />,
  pattern: <PatternSkill />,
  storm: <StormSwipe />,
  district: <DistrictRecord />,
};

export default function WhyView({ initial }: { initial?: string | null }) {
  const [cur, setCur] = useState<ProofId>(() => PROOFS.find((p) => p.id === initial)?.id ?? "monsoon");
  const { stat } = useProofStats();
  const i = PROOFS.findIndex((p) => p.id === cur);
  const next = PROOFS[(i + 1) % PROOFS.length];
  const open = (id: ProofId) => {
    setCur(id);
    document.getElementById("proof-stage")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight tracking-tight">Check it yourself</h1>
          <p className="mt-1 text-[15px] text-[var(--muted)]">Rainfall measured by IMD and forecasts issued by NOAA over six monsoons, 2021 to 2026.</p>
        </div>
      </div>

      <div role="tablist" aria-label="Proofs" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {PROOFS.map((p, k) => {
          const on = p.id === cur, s = stat[p.id];
          return (
            <button key={p.id} role="tab" aria-selected={on} onClick={() => open(p.id)}
              className={`group relative flex flex-col justify-start overflow-hidden rounded-2xl border p-4 text-left sm:p-5 transition-all ${on ? "border-[var(--brand)] bg-white shadow-[0_8px_28px_rgba(11,79,108,0.14)]" : "border-[var(--line)] bg-white/60 hover:border-[var(--faint)] hover:bg-white"}`}>
              <span className={`absolute inset-x-0 top-0 h-1 ${on ? "bg-[var(--brand)]" : "bg-transparent group-hover:bg-[var(--line)]"}`} />
              <div className="flex items-center gap-2 text-[12px] font-semibold">
                <span className={on ? "text-[var(--marigold)]" : "text-[var(--faint)]"}>0{k + 1}</span>
                <span className="rounded-full bg-[var(--panel2)] px-2 py-0.5 text-[10.5px] font-bold tracking-wide text-[#8a5a12]">USP {p.usp} · {p.tag}</span>
              </div>
              <div className={`mt-2 text-[15px] font-semibold leading-snug sm:text-[17px] ${on ? "text-[var(--ink)]" : "text-[var(--ink)]/80"}`}>{p.title}</div>
              <div className="mt-auto pt-3">
                {s ? <><div className={`text-[18px] font-semibold leading-none tabular-nums sm:text-[22px] ${on ? "text-[var(--brand)]" : "text-[var(--ink)]/70"}`}>{s.big}</div><div className="mt-1 hidden text-[12px] leading-snug text-[var(--muted)] sm:block">{s.small}</div></> : <div className="h-10 animate-pulse rounded bg-[var(--panel)]" />}
              </div>
            </button>
          );
        })}
      </div>

      <section id="proof-stage" role="tabpanel" className="scroll-mt-40 rounded-2xl border border-[var(--line)] bg-white p-6 md:p-8">
        <div className="mb-6 border-b border-[var(--line)] pb-5">
          <div className="text-[12px] font-semibold uppercase tracking-[0.12em] text-[var(--marigold)]">USP {PROOFS[i].usp} · {PROOFS[i].tag}</div>
          <h2 className="mt-1 text-[23px] font-semibold leading-tight">{PROOFS[i].title}</h2>
          <p className="mt-2 max-w-[880px] text-[15px] leading-relaxed text-[var(--muted)]">{PROOFS[i].claim}</p>
        </div>
        <div key={cur} className="animate-[fadein_.35s_ease-out]">{DEMO[cur]}</div>
        <div className="mt-8 flex justify-end border-t border-[var(--line)] pt-4">
          <button onClick={() => open(next.id)} className="text-[14px] font-medium text-[var(--brand)] hover:underline">Next: {next.title} →</button>
        </div>
      </section>
    </div>
  );
}
