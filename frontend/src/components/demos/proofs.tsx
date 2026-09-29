"use client";

import type { Cell, ReplayEvent, Verification } from "@/lib/api";
import { niceDate } from "@/lib/colors";
import { useFetch } from "../AppContext";

export interface Tally { heavy: number; varsha: number; raw: number; varsha_false: number; raw_false: number }
export interface Summary extends Tally { districts: number; seasons: Record<string, Tally>; best_2024: { id: number; heavy: number; varsha: number; raw: number }[] }
export interface RegimeIndex { cells: Cell[]; core: { lat0: number; lat1: number; lon0: number; lon1: number }; days: { date: string; anom: number | null; regime: string }[] }

/** The four things a visitor can check for themselves, in the order the "See it work" page shows them. */
export const PROOFS = [
  {
    id: "monsoon", usp: 1, tag: "Regime detection",
    title: "Knows each day if the monsoon is active or on a break",
    claim: "It compares IMD's measured rain with the 30-year normal using IMD's own rule, so anyone at IMD can check every label.",
  },
  {
    id: "pattern", usp: 2, tag: "Regime-aware correction",
    title: "Corrects the forecast differently for each monsoon state",
    claim: "Weather models go wrong in different ways in an active spell, a break, near a depression, and over mountains, coasts and plains. VARSHA fixes each case separately, and never where the fix would make things worse.",
  },
  {
    id: "storm", usp: 3, tag: "Proven on real storms",
    title: "Warns of more heavy rain a day before a storm",
    claim: "On India's biggest storm days since 2021, it flagged more of the places that really got heavy rain than NOAA's raw forecast.",
  },
  {
    id: "district", usp: 3, tag: "Proven in every district",
    title: "Tested in every district on real IMD rainfall",
    claim: "Six monsoons, 687 districts and every heavy-rain day IMD recorded. Each year was forecast by a model that never saw it.",
  },] as const;
export type ProofId = (typeof PROOFS)[number]["id"];

export const REGIME_NAME: Record<string, string> = { Active: "Active monsoon", Break: "Break", Normal: "Normal", Depression: "Depression nearby" };
export const TERRAIN_NAME: Record<string, string> = { Orographic: "Mountains", Coastal: "Coast", Inland: "Plains" };

export const biggestStorm = (events: ReplayEvent[] | undefined) => events?.slice().sort((a, b) => b.heavy_cells - a.heavy_cells)[0];

/** One headline number pair per proof, all computed from the live API. */
export function useProofStats() {
  const { data: reg } = useFetch<RegimeIndex>("/demo/regime");
  const { data: ver } = useFetch<Record<string, Verification>>("/verification");
  const { data: rep } = useFetch<{ events: ReplayEvent[] }>("/replay");
  const { data: sum } = useFetch<Summary>("/demo/summary");
  const v = ver?.["1"];
  const storm = biggestStorm(rep?.events);
  const count = (r: string) => reg?.days.filter((d) => d.regime === r).length ?? 0;
  const groups = v ? [
    ...Object.keys(v.by_regime.RAW).map((r) => v.by_regime.WARN[r]["t64.5"].ETS > v.by_regime.RAW[r]["t64.5"].ETS),
    ...Object.keys(v.by_setting.RAW).map((s) => v.by_setting.WARN[s]["t64.5"].ETS > v.by_setting.RAW[s]["t64.5"].ETS),
  ] : [];
  return {
    reg, v, storm, sum,
    stat: {
      monsoon: reg ? { big: `${count("Active")} + ${count("Break")}`, small: `active and break days found in ${new Set(reg.days.map((d) => d.date.slice(0, 4))).size} monsoons` } : null,
      pattern: v ? { big: `${groups.filter(Boolean).length} of ${groups.length}`, small: "monsoon states and terrains where it beats the raw model" } : null,
      storm: storm ? { big: `${Math.round(storm.pod_varsha * storm.heavy_cells)} vs ${Math.round(storm.pod_raw * storm.heavy_cells)}`, small: `heavy-rain areas caught on ${niceDate(storm.date)} ${storm.date.slice(0, 4)}` } : null,
      district: sum ? { big: `${sum.varsha.toLocaleString("en-IN")} vs ${sum.raw.toLocaleString("en-IN")}`, small: "heavy-rain district-days warned a day before" } : null,
    } as Record<ProofId, { big: string; small: string } | null>,
  };
}

/** VARSHA's number, big, with the raw model's beside it. */
export function Duel({ v, r, label, vs = "raw model" }: { v: number | string; r: number | string; label: string; vs?: string }) {
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span className="text-[34px] font-semibold leading-none tabular-nums text-[var(--brand)]">{v}</span>
        <span className="text-[15px] text-[var(--muted)]">vs <b className="font-semibold tabular-nums">{r}</b> {vs}</span>
      </div>
      <div className="mt-1.5 text-[13.5px] text-[var(--muted)]">{label}</div>
    </div>
  );
}

/** Two stacked horizontal bars, raw model then VARSHA. */
export function Bars({ raw, varsha, max, fmt = (x: number) => String(x), dark = false }: { raw: number; varsha: number; max: number; fmt?: (x: number) => string; dark?: boolean }) {
  const row = (name: string, x: number, c: string) => (
    <div className="flex items-center gap-2 text-[12.5px]">
      <span className={`w-[74px] shrink-0 ${dark ? "text-white/75" : "text-[var(--muted)]"}`}>{name}</span>
      <div className={`h-2.5 flex-1 rounded-full ${dark ? "bg-white/10" : "bg-[var(--panel)]"}`}><div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(100, (100 * x) / max)}%`, background: c }} /></div>
      <span className="w-12 text-right font-semibold tabular-nums">{fmt(x)}</span>
    </div>
  );
  return <div className="flex flex-col gap-1.5">{row("Raw model", raw, "#aab7c1")}{row("VARSHA", varsha, dark ? "#e9a23b" : "var(--brand)")}</div>;
}
