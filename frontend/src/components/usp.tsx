"use client";

import type { Verification } from "@/lib/api";

/** The three differentiators, shared by the home page, the "Why VARSHA" page and the page tags. */
export const USPS = [
  {
    n: 1, short: "IMD's own monsoon rule", tab: "pattern",
    title: "Monsoon patterns that IMD can check",
    text: "VARSHA decides whether the monsoon is active, on a break or has a depression using IMD's published rule, IMD's 30-year normals and IMD's official depression tracks. It uses no black-box clusters, so every label can be checked against IMD's own monitoring.",
  },
  {
    n: 2, short: "Right fix for every pattern, never worse", tab: "accuracy",
    title: "The right correction for every pattern and place, and never worse than the model",
    text: "A single fix for all days fails; in a break monsoon it is worse than doing nothing. VARSHA learns a separate correction for each monsoon pattern and for mountains, coasts and plains. A do-no-harm rule uses a correction only where it has beaten the raw model on years it never saw.",
  },
  {
    n: 3, short: "Proven on real IMD data, district by district", tab: "past",
    title: "Proven on six real monsoons, down to each district",
    text: "Every claim is measured against rainfall IMD actually recorded, on every 25 km square and all 742 Survey of India districts, from 2021 to 2026. Each year is forecast by a model that never saw it. There is no synthetic data anywhere.",
  },
] as const;

export function uspProof(v: Verification | undefined) {
  if (!v) return null;
  const e = (m: string) => v.overall[m]["t64.5"].ETS;
  const reg = (m: string, r: string) => v.by_regime[m]?.[r]?.["t64.5"].ETS ?? NaN;
  const set = (m: string, s: string) => v.by_setting[m]?.[s]?.["t64.5"].ETS ?? NaN;
  const groups = [...Object.keys(v.by_regime.RAW ?? {}).map((r) => [reg("WARN", r), reg("RAW", r)]), ...Object.keys(v.by_setting.RAW ?? {}).map((s) => [set("WARN", s), set("RAW", s)])];
  const gate = Object.values(v.gate);
  return {
    gain: Math.round(100 * (e("WARN") / e("RAW") - 1)),
    groupsWon: groups.filter(([a, b]) => a > b).length,
    groupsTotal: groups.length,
    breakRaw: reg("RAW", "Break"), breakGlobal: reg("QM_GLOBAL", "Break"), breakVarsha: reg("WARN", "Break"),
    mountRaw: set("RAW", "Orographic"), mountVarsha: set("WARN", "Orographic"),
    distRaw: v.district.heavy_any_cell.RAW.ETS, distVarsha: v.district.heavy_any_cell.WARN.ETS, districts: v.district.districts,
    n: v.n, heavy: v.events.heavy,
    gateTotal: gate.length, gateSwitched: gate.filter((g) => g.warning !== "WARN").length,
  };
}

export function UspTag({ n }: { n: 1 | 2 | 3 }) {
  const u = USPS[n - 1];
  return (
    <span className="inline-flex w-fit items-center gap-2 rounded-full border border-[var(--marigold)] bg-[var(--panel2)] px-3 py-1 text-[12.5px] font-medium text-[#7a4a00]">
      <span className="rounded-full bg-[var(--marigold)] px-1.5 text-[11px] font-bold text-white">USP {u.n}</span>{u.short}
    </span>
  );
}
