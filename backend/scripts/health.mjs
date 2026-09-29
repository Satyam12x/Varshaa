#!/usr/bin/env node
/**
 * VARSHA API health check / uptimer ping.
 *
 *   npm run health                                  # http://localhost:4080
 *   npm run health -- https://varsha-api.onrender.com
 *   npm run health -- https://varsha-api.onrender.com --strict   # also fail if today's forecast is stale
 *
 * The URL can also come from HEALTH_URL. Exits 0 when healthy, 1 otherwise, so it works in cron and CI.
 * Each attempt waits up to 60 s, which covers a Render free-tier cold start.
 */
const args = process.argv.slice(2);
const strict = args.includes("--strict");
const base = (args.find((a) => !a.startsWith("--")) ?? process.env.HEALTH_URL ?? "http://localhost:4080").replace(/\/+$/, "");
const url = (base.endsWith("/api/health") ? base : base.endsWith("/api") ? `${base}/health` : `${base}/api/health`) + (strict ? "?strict=1" : "");
const TRIES = Number(process.env.HEALTH_TRIES ?? 4);
const TIMEOUT_MS = Number(process.env.HEALTH_TIMEOUT_MS ?? 60000);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

for (let attempt = 1; attempt <= TRIES; attempt++) {
  const t0 = Date.now();
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_MS), headers: { "user-agent": "varsha-uptimer" } });
    const ms = Date.now() - t0;
    const body = await res.json().catch(() => ({}));
    const p = body.product;
    const summary = p ? `forecast ${p.issue}, ${p.age_hours} h old${p.fresh ? "" : " (STALE)"}` : "no forecast product";
    if (res.ok && body.ok) {
      console.log(`OK   ${res.status} in ${ms} ms | ${summary} | cycle: ${body.cycle?.step ?? "?"}`);
      process.exit(0);
    }
    console.log(`FAIL ${res.status} in ${ms} ms | ${summary}${body.cycle?.lastError ? ` | last error: ${body.cycle.lastError}` : ""}`);
    if (res.status === 503 && strict) process.exit(1); // stale forecast: retrying will not help
  } catch (e) {
    console.log(`FAIL attempt ${attempt}/${TRIES} after ${Date.now() - t0} ms: ${e.name === "TimeoutError" ? "timed out" : e.message}`);
  }
  if (attempt < TRIES) await sleep(10000 * attempt);
}
console.log(`UNHEALTHY: ${url}`);
process.exit(1);
