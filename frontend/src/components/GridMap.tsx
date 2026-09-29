"use client";

import { useMemo, useRef, useState, type ReactNode } from "react";
import type { Cell } from "@/lib/api";
import { MAP, px, py, useApp } from "./AppContext";

const LAT0 = 6.5, LON0 = 66.5, STEP = 0.25;

interface Props {
  cells: Cell[];
  values?: (number | null)[];          // one value per cell
  color?: (v: number | null) => string;
  districtFill?: Map<number, string>;  // colour whole districts instead of cells
  title?: string;
  legend?: ReactNode;
  tooltip?: (cellIndex: number, districtId: number) => ReactNode;
  onDistrict?: (id: number) => void;
  selectedDistrict?: number | null;
  compact?: boolean;
  overlay?: ReactNode;                 // extra SVG drawn on top (in map coordinates)
  noTooltip?: boolean;
}

export default function GridMap({ cells, values, color, districtFill, title, legend, tooltip, onDistrict, selectedDistrict, compact, overlay, noTooltip }: Props) {
  const { districtsGeo, cellMeta, districtName } = useApp();
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<{ x: number; y: number; k: number } | null>(null);
  const index = useMemo(() => { const m = new Map<number, number>(); cells.forEach(([i, j], k) => m.set(i * 1000 + j, k)); return m; }, [cells]);
  const cw = px(LON0 + STEP) - px(LON0), ch = py(LAT0) - py(LAT0 + STEP);

  const rects = useMemo(() => cells.map(([i, j], k) => {
    const v = values ? values[k] : null;
    return <rect key={k} x={px(LON0 + j * STEP - STEP / 2)} y={py(LAT0 + i * STEP + STEP / 2)} width={cw + 0.4} height={ch + 0.4} fill={color ? color(v) : "#e6edf1"} />;
  }), [cells, values, color, cw, ch]);

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = ref.current!.getBoundingClientRect();
    const sx = ((e.clientX - r.left) / r.width) * MAP.W, sy = ((e.clientY - r.top) / r.height) * MAP.H;
    const lon = MAP.lon0 + (sx / MAP.W) * (MAP.lon1 - MAP.lon0), lat = MAP.lat1 - (sy / MAP.H) * (MAP.lat1 - MAP.lat0);
    const k = index.get(Math.round((lat - LAT0) / STEP) * 1000 + Math.round((lon - LON0) / STEP));
    setHover(k === undefined ? null : { x: sx, y: sy, k });
  };
  const dId = hover && cellMeta ? cellMeta.cell_district[hover.k] : -1;

  return (
    <div className="relative w-full">
      {title && <div className="mb-1 text-sm font-semibold text-[var(--ink)]">{title}</div>}
      <svg ref={ref} viewBox={`0 0 ${MAP.W} ${MAP.H}`} className="h-auto w-full select-none" onMouseMove={onMove} onMouseLeave={() => setHover(null)}
        onClick={() => dId >= 0 && onDistrict?.(dId)} role="img" aria-label={title ?? "Map of India"}>
        <rect width={MAP.W} height={MAP.H} fill="var(--map-sea)" />
        {!districtFill && <g shapeRendering="crispEdges">{rects}</g>}
        <g>
          {districtsGeo.map((d) => (
            <path key={d.id} d={d.d} fill={districtFill ? districtFill.get(d.id) ?? "#e6edf1" : "none"}
              stroke={selectedDistrict === d.id ? "var(--ink)" : "var(--district-line)"} strokeWidth={selectedDistrict === d.id ? 1.6 : districtFill ? 0.35 : 0.25} />
          ))}
        </g>
        {overlay}
      </svg>
      {hover && !noTooltip && (
        <div className="pointer-events-none absolute z-10 rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-[12.5px] leading-snug shadow-[0_6px_24px_rgba(15,31,43,0.12)]"
          style={{ left: `${(hover.x / MAP.W) * 100}%`, top: `${(hover.y / MAP.H) * 100}%`, transform: "translate(12px, -50%)", maxWidth: 230 }}>
          <div className="font-semibold">{dId >= 0 ? districtName(dId) : "Outside districts"}</div>
          {tooltip?.(hover.k, dId)}
        </div>
      )}
      {legend && <div className={compact ? "mt-1" : "mt-2"}>{legend}</div>}
    </div>
  );
}

export function Legend({ items }: { items: { color: string; label: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-[12.5px] text-[var(--muted)]">
      {items.map((it) => (
        <span key={it.label} className="inline-flex items-center gap-2"><span className="inline-block h-3.5 w-3.5 rounded-sm border border-black/10" style={{ background: it.color }} />{it.label}</span>
      ))}
    </div>
  );
}

export function Card({ title, children, right }: { title?: ReactNode; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5">
      {(title || right) && <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h3 className="text-[15px] font-semibold text-[var(--ink)]">{title}</h3>{right}</div>}
      {children}
    </section>
  );
}
