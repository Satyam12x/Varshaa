"use client";

import dynamic from "next/dynamic";
import { Suspense } from "react";
import { AppProvider } from "./AppContext";

// The dashboard is driven entirely by live API data, so render it on the client only.
const Dashboard = dynamic(() => import("./Dashboard"), {
  ssr: false,
  loading: () => <p className="p-6 text-sm text-[var(--muted)]">Loading VARSHA…</p>,
});

export default function ClientRoot() {
  return (
    <AppProvider>
      <Suspense>
        <Dashboard />
      </Suspense>
    </AppProvider>
  );
}
