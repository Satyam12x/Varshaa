"use client";

import { useState } from "react";
import type { Verification } from "@/lib/api";
import { useFetch } from "../AppContext";
import { Toggle } from "../ui";
import { REGIME_NAME, TERRAIN_NAME } from "./proofs";

const METHODS = [
  { key: "RAW", name: "Raw model", color: "#aab7c1" },
  { key: "QM_GLOBAL", name: "One fix for all days", color: "#e9c98f" },
  { key: "WARN", name: "VARSHA", color: "#0b4f6c" },
] as const;
const TERRAINS = [[0, "Mountains"], [1, "Coast"], [3, "Plains"]] as const;
const REGIMES = ["Active", "Normal", "Break", "Depression"];
const pctGain = (x: number, base: number) => `${x >= base ? "+" : "−"}${Math.abs(Math.round(100 * (x / base - 1)))}%`;

export default function PatternSkill() {
  const { data: ver } = useFetch<Record<string, Verification>>("/verification");
  const [by, setBy] = useState<"regime" | "terrain">("regime");
  const v = ver?.["1"];
  if (!v) return <div className="h-[520px] animate-pulse rounded-xl bg-[var(--panel)]" />;
  const table = by === "regime" ? v.by_regime : v.by_setting;
  const groups = by === "regime" ? REGIMES.filter((r) => table.RAW[r]) : Object.keys(TERRAIN_NAME);
  const ets = (m: string, g: string) => table[m]?.[g]?.["t64.5"].ETS ?? 0;
  const max = Math.max(...groups.flatMap((g) => METHODS.map((m) => ets(m.key, g)))) * 1.08;

  return (
    <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <div>
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <Toggle options={[["regime", "By monsoon state"], ["terrain", "By terrain"]]} value={by} onChange={setBy} />
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-[var(--muted)]">
            {METHODS.map((m) => <span key={m.key} className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: m.color }} />{m.name}</span>)}
          </div>
        </div>
        <div className="flex flex-col gap-5">
          {groups.map((g) => {
            const base = ets("RAW", g);
            return (
              <div key={g}>
                <div className="mb-1.5 text-[15px] font-semibold">{by === "regime" ? REGIME_NAME[g] : TERRAIN_NAME[g]}</div>
                <div className="flex flex-col gap-1">
                  {METHODS.map((m) => {
                    const x = ets(m.key, g), worse = m.key !== "RAW" && x < base;
                    return (
                      <div key={m.key} className="flex items-center gap-3">
                        <div className="h-[18px] flex-1">
                          <div className="h-full rounded-r-md transition-all duration-500" style={{ width: `${(100 * x) / max}%`, background: m.color }} />
                        </div>
                        <span className={`w-16 text-right text-[13px] font-semibold tabular-nums ${m.key === "RAW" ? "text-[var(--faint)]" : worse ? "text-[#b3261e]" : m.key === "WARN" ? "text-[var(--brand)]" : "text-[#8a6a2c]"}`}>
                          {m.key === "RAW" ? x.toFixed(2) : pctGain(x, base)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-5 text-[12px] leading-relaxed text-[var(--faint)]">Heavy-rain skill (Equitable Threat Score for 64.5 mm or more in a day), forecasts one day ahead, 2021–2026. Each season was scored by models trained without it.</div>
      </div>

      <div className="rounded-xl bg-[var(--panel)] p-5">
        <div className="text-[16px] font-semibold">Do-no-harm check</div>
        <div className="mt-1 text-[13px] text-[var(--muted)]">Each of the 12 pattern and terrain groups, tested on seasons the model never saw</div>
        <div className="mt-4 grid grid-cols-[auto_repeat(3,minmax(0,1fr))] gap-1.5 text-[12.5px]">
          <span />
          {TERRAINS.map(([, t]) => <span key={t} className="pb-1 text-center font-medium text-[var(--muted)]">{t}</span>)}
          {REGIMES.map((r) => (
            <div key={r} className="contents">
              <span className="flex items-center pr-2 font-medium">{REGIME_NAME[r]}</span>
              {TERRAINS.map(([s]) => {
                const g = v.gate[`${r}|${s}`] as (Verification["gate"][string] & { ets?: Record<string, number> }) | undefined;
                if (!g?.ets) return <span key={s} className="rounded-lg bg-white/60" />;
                const kept = g.warning === "WARN";
                const used = g.ets[g.warning] ?? g.ets.WARN;
                return (
                  <div key={s} className={`rounded-lg px-2 py-2.5 text-center ${kept ? "bg-[var(--brand)] text-white" : "border-2 border-dashed border-[var(--marigold)] bg-white"}`}
                    title={kept ? "VARSHA's warning model beat the raw model here" : `VARSHA's warning model would have been ${pctGain(g.ets.WARN, g.ets.RAW)} here, so the simpler pattern table is used`}>
                    <div className="text-[15px] font-semibold tabular-nums">{pctGain(used, g.ets.RAW)}</div>
                    <div className={`text-[11px] ${kept ? "text-white/75" : "text-[#8a5a12]"}`}>{kept ? "VARSHA" : `fallback · VARSHA ${pctGain(g.ets.WARN, g.ets.RAW)}`}</div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-col gap-1.5 text-[12.5px] text-[var(--muted)]">
          <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm bg-[var(--brand)]" />VARSHA beat the raw model, so it is used</span>
          <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm border-2 border-dashed border-[var(--marigold)] bg-white" />It did not, so VARSHA falls back to a safer correction</span>
        </div>
      </div>
    </div>
  );
}
