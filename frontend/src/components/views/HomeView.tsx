"use client";

import type { DistrictRow, Verification } from "@/lib/api";
import { LEVELS, LEVEL_COLOR, REGIME_COLOR, REGIME_PLAIN, dayName, niceDate, pct } from "@/lib/colors";
import { useApp, useFetch } from "../AppContext";
import { Loading, Section, WarningChip } from "../ui";
import Differentiators from "../demos/Differentiators";

type Rows = { rows: DistrictRow[]; valid: string; lead: number };
const RANK = { green: 0, yellow: 1, orange: 2, red: 3 } as const;

export default function HomeView({ go }: { go: (tab: string, lead?: number, district?: number, proof?: string) => void }) {
  const { meta } = useApp();
  const d1 = useFetch<Rows>("/districts?lead=1").data;
  const d2 = useFetch<Rows>("/districts?lead=2").data;
  const d3 = useFetch<Rows>("/districts?lead=3").data;
  const d4 = useFetch<Rows>("/districts?lead=4").data;
  const d5 = useFetch<Rows>("/districts?lead=5").data;
  const { data: ver } = useFetch<Record<string, Verification>>("/verification");
  if (!meta) return <Loading />;
  const r = meta.regime;
  const plain = REGIME_PLAIN[r?.large_scale ?? "Normal"] ?? REGIME_PLAIN.Normal;
  const days = [d1, d2, d3, d4, d5].filter(Boolean) as Rows[];
  const risky = days.flatMap((d) => d.rows.filter((x) => x.level !== "green").map((x) => ({ ...x, lead: d.lead, valid: d.valid })))
    .sort((a, b) => RANK[b.level] - RANK[a.level] || b.p_heavy - a.p_heavy);
  const seen = new Set<number>();
  const watch = risky.filter((x) => (seen.has(x.id) ? false : (seen.add(x.id), true)));
  const v = ver?.["1"];
  const gain = v ? Math.round(100 * (v.overall.WARN["t64.5"].ETS / v.overall.RAW["t64.5"].ETS - 1)) : null;
  const totalAlerts = days.reduce((s, d) => s + d.rows.filter((x) => x.level !== "green").length, 0);

  return (
    <div className="flex flex-col gap-10">
      {/* hero */}
      <section className="grid gap-8 pt-2 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div>
          <div className="text-[12px] font-semibold uppercase tracking-[0.14em] text-[var(--faint)]">Monsoon today · IMD rainfall up to {r?.based_on ? niceDate(r.based_on) : "–"}</div>
          <h1 className="mt-3 text-[40px] font-semibold leading-[1.1] tracking-tight">
            <span style={{ color: REGIME_COLOR[r?.large_scale ?? "Normal"] }}>{plain.title}.</span>
          </h1>
          <p className="mt-4 max-w-[640px] text-[18px] leading-relaxed text-[var(--muted)]">{plain.text}</p>
          <p className="mt-4 max-w-[640px] text-[16px] leading-relaxed">
            {totalAlerts === 0
              ? "No district is expected to receive heavy rain over the next five days."
              : <>Over the next five days, <b>{watch.length} district{watch.length > 1 ? "s" : ""}</b> may receive heavy rain. The strongest signal is for <b>{watch[0]?.name}</b> ({watch[0]?.state}), {dayName(watch[0]?.lead ?? 1).toLowerCase()}.</>}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button onClick={() => go("alerts")} className="rounded-full bg-[var(--brand)] px-5 py-2.5 text-[14px] font-medium text-white hover:bg-[var(--accent-ink)]">See heavy-rain alerts</button>
            <button onClick={() => go("district")} className="rounded-full border border-[var(--brand)] px-5 py-2.5 text-[14px] font-medium text-[var(--brand)] hover:bg-white">Check my district</button>
          </div>
        </div>
        <div className="rounded-2xl border border-[var(--line)] bg-white p-6">
          <div className="text-[12px] font-semibold uppercase tracking-[0.14em] text-[var(--faint)]">How reliable is Varsha?</div>
          {v ? (
            <div className="mt-3 flex flex-col gap-4">
              <div><div className="text-[38px] font-semibold leading-none text-[var(--accent)]">+{gain}%</div><div className="mt-1 text-[14px]">better heavy-rain forecasts than the raw weather model</div></div>
              <div className="h-px bg-[var(--line)]" />
              <div><div className="text-[26px] font-semibold leading-none">{pct(v.overall.WARN["t64.5"].POD)} <span className="text-[16px] font-normal text-[var(--muted)]">vs {pct(v.overall.RAW["t64.5"].POD)}</span></div><div className="mt-1 text-[14px]">of heavy-rain areas warned a day ahead</div></div>
              <div className="text-[12.5px] text-[var(--muted)]">Tested on six monsoons (2021–2026) against rainfall measured by IMD, each year unseen during training.</div>
              <button onClick={() => go("accuracy")} className="self-start text-[13.5px] font-medium text-[var(--accent)] hover:underline">How we tested it →</button>
            </div>
          ) : <p className="mt-3 text-[14px] text-[var(--muted)]">Loading…</p>}
        </div>
      </section>


      <Differentiators open={(p) => go("why", undefined, undefined, p)} />

      {/* five days */}
      <Section kicker="Outlook" title="Heavy rain over the next five days">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {days.map((d) => {
            const n = Object.fromEntries(LEVELS.map((l) => [l, d.rows.filter((x) => x.level === l).length])) as Record<string, number>;
            const worst = n.red ? "red" : n.orange ? "orange" : n.yellow ? "yellow" : "green";
            const total = n.yellow + n.orange + n.red;
            return (
              <button key={d.lead} onClick={() => go("alerts", d.lead)} className="overflow-hidden rounded-xl border border-[var(--line)] text-left transition-shadow hover:shadow-[0_4px_18px_rgba(15,31,43,0.08)]">
                <div className="h-1.5" style={{ background: LEVEL_COLOR[worst] }} />
                <div className="p-4">
                  <div className="text-[14px] font-semibold">{dayName(d.lead)}</div>
                  <div className="text-[12.5px] text-[var(--muted)]">{niceDate(d.valid)}</div>
                  <div className="mt-3 text-[26px] font-semibold leading-none">{total}</div>
                  <div className="mt-1 text-[12.5px] text-[var(--muted)]">{total === 1 ? "district on watch or alert" : "districts on watch or alert"}</div>
                </div>
              </button>
            );
          })}
        </div>
        {watch.length > 0 ? (
          <div className="mt-6">
            <div className="mb-2 text-[13px] font-semibold uppercase tracking-[0.12em] text-[var(--faint)]">Districts to watch</div>
            <div className="divide-y divide-[var(--line)] border-y border-[var(--line)]">
              {watch.slice(0, 8).map((x) => (
                <button key={x.id} onClick={() => go("district", undefined, x.id)} className="grid w-full grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_auto] items-center gap-3 py-3 text-left hover:bg-[var(--panel)]">
                  <span><span className="font-semibold">{x.name}</span> <span className="text-[var(--muted)]">{x.state}</span></span>
                  <span className="text-[13.5px] text-[var(--muted)]">{dayName(x.lead)}, {niceDate(x.valid)} · {pct(x.p_heavy)} chance</span>
                  <WarningChip level={x.level} />
                </button>
              ))}
            </div>
          </div>
        ) : days.length === 5 && (
          <p className="mt-5 text-[14.5px] text-[var(--muted)]">It is the end of the monsoon season, so little heavy rain is expected. To see Varsha during real storms, open <button onClick={() => go("past")} className="font-medium text-[var(--accent)] underline">Past storms</button>.</p>
        )}
      </Section>

    </div>
  );
}
