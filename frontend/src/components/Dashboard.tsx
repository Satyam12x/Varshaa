"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { REGIME_COLOR, REGIME_PLAIN, niceDate } from "@/lib/colors";
import { useApp } from "./AppContext";
import { DayPicker } from "./ui";
import AboutView from "./views/AboutView";
import AccuracyView from "./views/AccuracyView";
import AlertsView from "./views/AlertsView";
import HomeView from "./views/HomeView";
import MyDistrictView from "./views/MyDistrictView";
import PastDaysView from "./views/PastDaysView";
import PatternView from "./views/PatternView";
import RainMapView from "./views/RainMapView";
import WhyView from "./views/WhyView";

const TABS = [
  { id: "home", label: "Today" },
  { id: "why", label: "See it work" },
  { id: "rain", label: "Rain map" },
  { id: "alerts", label: "Heavy-rain alerts" },
  { id: "district", label: "My district" },
  { id: "pattern", label: "Monsoon pattern" },
  { id: "accuracy", label: "Accuracy" },
  { id: "past", label: "Past storms" },
  { id: "about", label: "About" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function Dashboard() {
  const { meta, error } = useApp();
  const q = useSearchParams();
  const [tab, setTab] = useState<Tab>(() => (TABS.some((t) => t.id === q.get("tab")) ? (q.get("tab") as Tab) : "home"));
  const [lead, setLead] = useState(() => Math.min(5, Math.max(1, Number(q.get("lead") ?? 1) || 1)));
  const [district, setDistrict] = useState<number | null>(q.get("district") ? Number(q.get("district")) : null);
  const [proof, setProof] = useState<string | null>(q.get("proof"));
  const go = (t: string, l?: number, d?: number, p?: string) => {
    if (l) setLead(l);
    setProof(p ?? null);
    if (d !== undefined) setDistrict(d);
    setTab(t as Tab);
    window.scrollTo({ top: 0 });
  };
  const r = meta?.regime;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-[var(--line)] bg-white/95 backdrop-blur">
        <div className="wrap flex flex-wrap items-center justify-between gap-4 pt-5 pb-3">
          <button onClick={() => go("home")} className="text-left">
            <div className="flex items-center gap-2.5"><svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3c5 7 9 11.5 9 16.5A9 9 0 0 1 7 19.5C7 14.5 11 10 16 3Z" fill="#0b4f6c" /><path d="M12 20.5a4 4 0 0 0 4 4" stroke="#e9a23b" strokeWidth={2.4} fill="none" strokeLinecap="round" /></svg><span className="text-[24px] font-semibold leading-none tracking-tight text-[var(--brand)]">VARSHA</span></div>
            <div className="mt-1 text-[13px] text-[var(--muted)]">Monsoon rain forecasts for every district of India</div>
          </button>
          {meta && (
            <div className="flex items-center gap-3 text-[13px]">
              {r && (
                <span className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] px-3 py-1.5">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: REGIME_COLOR[r.large_scale] ?? "#6b7c8a" }} />
                  <span className="font-medium">{REGIME_PLAIN[r.large_scale]?.title ?? r.large_scale}</span>
                </span>
              )}
              <span className="text-[var(--muted)]">Updated {meta.issue ? niceDate(meta.issue) : "–"}</span>
            </div>
          )}
        </div>
        <nav className="wrap no-scrollbar flex gap-6 overflow-x-auto">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => go(t.id)}
              className={`-mb-px shrink-0 border-b-2 pb-3 pt-1 text-[14px] transition-colors ${tab === t.id ? "border-[var(--accent)] font-semibold text-[var(--ink)]" : "border-transparent text-[var(--muted)] hover:text-[var(--ink)]"}`}>{t.label}</button>
          ))}
        </nav>
      </header>

      <main className="wrap flex flex-col gap-6 py-8">
        {error && <div className="rounded-xl border border-[var(--line)] bg-[var(--accent-soft)] p-4 text-[14px]">Cannot reach the Varsha server ({error}). Start it with <code>npm run dev</code> in <code>PS 80/backend</code>.</div>}
        {meta && (tab === "rain" || tab === "alerts") && <DayPicker leads={meta.leads} lead={lead} onChange={setLead} />}
        {meta && (
          <>
            {tab === "home" && <HomeView go={go} />}
            {tab === "why" && <WhyView key={proof ?? ""} initial={proof} />}
            {tab === "rain" && <RainMapView lead={lead} />}
            {tab === "alerts" && <AlertsView lead={lead} openDistrict={(id) => go("district", undefined, id)} />}
            {tab === "district" && <MyDistrictView key={district ?? -1} initial={district} />}
            {tab === "pattern" && <PatternView />}
            {tab === "accuracy" && <AccuracyView />}
            {tab === "past" && <PastDaysView />}
            {tab === "about" && <AboutView />}
          </>
        )}
      </main>
      <footer className="border-t border-[var(--line)]">
        <div className="wrap flex flex-wrap justify-between gap-2 py-6 text-[12.5px] text-[var(--muted)]">
          <span>SIH PS 26080 · Team IgniteZ</span>
          <span>Data: India Meteorological Department · NOAA · Survey of India</span>
        </div>
      </footer>
    </div>
  );
}
