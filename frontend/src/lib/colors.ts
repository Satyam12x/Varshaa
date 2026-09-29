import type { Level } from "./api";

/** Warning levels: light cloud for "none", then amber, orange, red (reserved for danger). */
export const LEVEL_COLOR: Record<Level, string> = { green: "#dbe4ea", yellow: "#f2b134", orange: "#e8702a", red: "#b3261e" };
export const LEVEL_TEXT: Record<Level, string> = { green: "No warning", yellow: "Watch", orange: "Alert", red: "Warning" };
export const LEVEL_LONG: Record<Level, string> = {
  green: "No heavy rain expected", yellow: "Heavy rain possible", orange: "Heavy rain likely", red: "Very heavy rain likely",
};
export const LEVEL_ADVICE: Record<Level, string> = {
  green: "Nothing to prepare for.",
  yellow: "Keep an eye on updates.",
  orange: "Be prepared: clear drains, avoid low-lying areas, plan travel.",
  red: "Take action and follow local disaster-management advice.",
};
export const LEVELS: Level[] = ["green", "yellow", "orange", "red"];

/** Monsoon patterns: monsoon sea for active, marigold for break, storm cloud for depression, slate for normal. */
export const REGIME_COLOR: Record<string, string> = { Active: "#0b4f6c", Break: "#c9861f", Normal: "#6b7c8a", Depression: "#26323f" };
export const SETTING_COLOR: Record<number, string> = { 0: "#3f6273", 1: "#8dc1d4", 3: "#e6edf1" };

export const REGIME_PLAIN: Record<string, { title: string; text: string }> = {
  Active: { title: "Active monsoon", text: "The monsoon is stronger than usual. Rain is widespread, especially over central India and the west coast." },
  Break: { title: "Break in the monsoon", text: "The monsoon has paused. Central India is drier than usual, while the Himalayan foothills and the south-east can still get heavy rain." },
  Normal: { title: "Normal monsoon", text: "Monsoon rainfall is close to what is usual for this time of year." },
  Depression: { title: "Monsoon depression", text: "A low-pressure system is bringing a band of very heavy rain to the areas it moves across." },
};

const lerp = (a: string, b: string, t: number) => {
  const p = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return `#${x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("")}`;
};
const ramp = (stops: string[], t: number) => {
  const c = Math.min(Math.max(t, 0), 0.9999) * (stops.length - 1);
  const i = Math.floor(c);
  return lerp(stops[i], stops[i + 1], c - i);
};

/** IMD rainfall categories (mm in 24 h): cloud-to-rain blues for amounts, warm danger colours from heavy upwards. */
export const RAIN_CLASSES: { max: number; name: string; range: string; color: string }[] = [
  { max: 2.5, name: "Dry", range: "under 2.5 mm", color: "#f8fbfc" },
  { max: 15.6, name: "Light", range: "2.5–15.5 mm", color: "#cfe4ec" },
  { max: 35.6, name: "Moderate", range: "15.6–35.5 mm", color: "#86bcd1" },
  { max: 64.5, name: "Rather heavy", range: "35.6–64.4 mm", color: "#2f7b9c" },
  { max: 115.6, name: "Heavy", range: "64.5–115.5 mm", color: "#f2b134" },
  { max: 204.5, name: "Very heavy", range: "115.6–204.4 mm", color: "#e8702a" },
  { max: Infinity, name: "Extremely heavy", range: "204.5 mm or more", color: "#b3261e" },
];
export const rainClass = (x: number | null | undefined) => (x === null || x === undefined ? null : RAIN_CLASSES.find((c) => x < c.max)!);
export const rainColor = (x: number | null | undefined) => rainClass(x)?.color ?? "#e6edf1";
export const probColor = (p: number | null | undefined) => (p === null || p === undefined ? "#e6edf1" : p < 0.03 ? "#f8fbfc" : ramp(["#fdf0d5", "#f5c56a", "#e8702a", "#b3261e", "#6b1510"], Math.min(p / 0.6, 1)));

export const CHART = { raw: "#aab7c1", varsha: "#0b4f6c", ink: "#0f1f2b", mid: "#6b7c8a" };

export const fmt = (x: number | null | undefined, d = 1) => (x === null || x === undefined || !Number.isFinite(x) ? "–" : x.toFixed(d));
export const pct = (x: number | null | undefined) => (x === null || x === undefined ? "–" : `${Math.round(x * 100)}%`);
export const dayName = (lead: number) => (lead === 1 ? "Tomorrow" : `In ${lead} days`);
export const niceDate = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
