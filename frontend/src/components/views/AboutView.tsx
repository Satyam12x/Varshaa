"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";
import { useApp } from "../AppContext";
import { Card } from "../GridMap";
import { Explainer } from "../ui";

const GLOSSARY: [string, string][] = [
  ["Heavy rain", "64.5 mm or more in 24 hours (IMD). Very heavy: 115.6 mm or more. Extremely heavy: 204.5 mm or more."],
  ["Raw model", "The original NOAA GFS weather-model forecast, before VARSHA corrects it."],
  ["Weather pattern (regime)", "The state of the monsoon: active, break, depression or normal, decided with IMD's own rule."],
  ["Chance of heavy rain", "How likely it is that at least 64.5 mm falls. A 40% chance means heavy rain came on about 4 of every 10 such days in the past."],
  ["Heavy-rain score (ETS)", "One number that rewards correct warnings and penalises misses and false alarms. Higher is better."],
  ["Do-no-harm rule", "VARSHA only uses a correction where it has proven better than the raw model. Otherwise it keeps the raw forecast."],
];

export default function AboutView() {
  const { meta, reload } = useApp();
  const [msg, setMsg] = useState<string | null>(null);
  if (!meta) return null;
  const s = meta.status;
  const run = async () => {
    const r = await fetch(`${API_URL}/run`, { method: "POST" });
    setMsg(r.status === 202 ? "Update started. It takes a few minutes." : "An update is already running.");
    setTimeout(reload, 1500);
  };
  return (
    <div className="flex flex-col gap-4">
      <Explainer title="Where the data comes from">Only official government and national weather-service data is used. Nothing is made up or typed in by hand.</Explainer>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Data sources">
          <div className="flex flex-col gap-3">
            {meta.sources.map((x) => (
              <div key={x.name} className="border-t border-[var(--line)] pt-2 first:border-0 first:pt-0">
                <div className="text-sm font-semibold">{x.agency}</div>
                <div className="text-sm">{x.name}</div>
                <div className="text-xs text-[var(--muted)]">{x.role}</div>
              </div>
            ))}
          </div>
        </Card>
        <div className="flex flex-col gap-4">
          <Card title="Automatic daily update">
            <p className="text-sm">Every morning at <b>10:15 am IST</b>, VARSHA downloads the newest weather-model run and IMD&apos;s latest rainfall, works out the weather pattern, and updates all maps and district forecasts.</p>
            <div className="mt-3 rounded-lg bg-[var(--panel)] p-3 text-sm">
              <div>Latest forecast issued: <b>{meta.issue ?? "–"}</b></div>
              <div>Status: {s.running ? <b>updating now ({s.step})</b> : "up to date"}{s.lastError ? ` · last problem: ${s.lastError}` : ""}</div>
            </div>
            <button onClick={run} disabled={s.running} className="mt-3 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Update now</button>
            {msg && <p className="mt-2 text-xs">{msg}</p>}
          </Card>
          <Card title="Words used on this site">
            <dl className="flex flex-col gap-2 text-sm">{GLOSSARY.map(([t, d]) => <div key={t}><dt className="font-semibold">{t}</dt><dd className="text-[var(--muted)]">{d}</dd></div>)}</dl>
          </Card>
        </div>
      </div>
    </div>
  );
}
