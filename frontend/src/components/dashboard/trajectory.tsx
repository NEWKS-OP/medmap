"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimelineEvent } from "@/types/medmap";

const TRACKS = [
  { key: "LAB", label: "Labs", color: "#a78bfa" },
  { key: "MEDICATION", label: "Medication", color: "#38bdf8" },
  { key: "NURSING", label: "Nursing note", color: "#34d399" },
  { key: "FALL", label: "Fall / bed exit", color: "#f43f5e" },
] as const;

function toMs(ts: string): number | null {
  if (!ts) return null;
  const v = Date.parse(ts.length === 10 ? `${ts}T12:00:00` : ts.replace(" ", "T"));
  return Number.isNaN(v) ? null : v;
}

const dayFmt = (v: number) =>
  new Date(v).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" });
const fullFmt = (v: number) => new Date(v).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });

interface Point {
  t: number;
  y: number;
  track: string;
  label: string;
  detail: string;
  alert?: boolean;
}

export function Trajectory({
  events,
  admission,
  discharge,
}: {
  events: TimelineEvent[];
  admission?: string | null;
  discharge?: string | null;
}) {
  const adm = admission ? toMs(admission) : null;
  const dis = discharge ? toMs(discharge) : null;
  const hasStay = adm != null && dis != null;
  const [mode, setMode] = useState<"all" | "stay">("all");

  const { points, motion, domain, dropped } = useMemo(() => {
    const pts: Point[] = [];
    const mot: { t: number; movement: number }[] = [];
    let noTs = 0;
    for (const e of events) {
      const t = toMs(e.timestamp);
      if (t == null) {
        noTs++;
        continue;
      }
      const d = e.data as Record<string, unknown>;
      if (e.event_type === "MOTION_HOURLY") {
        const m = Number(d.movement_index);
        if (!Number.isNaN(m)) mot.push({ t, movement: m });
        if (String(d.fall_event) === "1" || String(d.bed_exit) === "1") {
          pts.push({
            t,
            y: 3,
            track: "FALL",
            label: String(d.fall_event) === "1" ? "Fall detected" : "Bed exit",
            detail: `movement index ${d.movement_index ?? "—"}`,
            alert: String(d.fall_event) === "1",
          });
        }
      } else if (e.event_type === "LAB") {
        pts.push({
          t,
          y: 0,
          track: "LAB",
          label: "Lab panel",
          detail: Object.entries(d)
            .filter(([, v]) => v != null)
            .map(([k, v]) => `${k} ${v}`)
            .join(" · "),
        });
      } else if (e.event_type === "MEDICATION") {
        pts.push({
          t,
          y: 1,
          track: "MEDICATION",
          label: String(d.name ?? "Medication"),
          detail: [d.dose, d.route, d.status, d.event_type].filter(Boolean).join(" · "),
        });
      } else if (e.event_type === "NURSING") {
        pts.push({
          t,
          y: 2,
          track: "NURSING",
          label: `${d.shift ?? ""} note${d.pain_level != null ? ` · pain ${d.pain_level}/10` : ""}`,
          detail: String(d.note ?? ""),
          alert: Boolean(d.deterioration_flag),
        });
      }
    }
    mot.sort((a, b) => a.t - b.t);
    // Break the line where the sensor has no data for more than 6 hours,
    // instead of drawing a misleading interpolation across the gap.
    const motWithGaps: { t: number; movement: number | null }[] = [];
    for (let i = 0; i < mot.length; i++) {
      if (i > 0 && mot[i].t - mot[i - 1].t > 6 * 3600000) {
        motWithGaps.push({ t: mot[i - 1].t + 1, movement: null });
      }
      motWithGaps.push(mot[i]);
    }
    let lo: number, hi: number;
    if (mode === "stay" && hasStay) {
      lo = adm! - 86400000;
      hi = dis! + 86400000;
    } else {
      const all = [...pts.map((p) => p.t), ...mot.map((m) => m.t), ...(hasStay ? [adm!, dis!] : [])];
      lo = all.length ? Math.min(...all) : Date.now();
      hi = all.length ? Math.max(...all) : Date.now() + 1;
      const pad = Math.max((hi - lo) * 0.02, 3600000);
      lo -= pad;
      hi += pad;
    }
    const inRange = (t: number) => t >= lo && t <= hi;
    return {
      points: pts.filter((p) => inRange(p.t)),
      motion: motWithGaps.filter((m) => inRange(m.t)),
      domain: [lo, hi] as [number, number],
      dropped: noTs,
    };
  }, [events, mode, adm, dis, hasStay]);

  if (!events.length) return <div className="py-6 text-sm text-muted-foreground">No time-stamped events for this case.</div>;

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex flex-wrap gap-3">
          {TRACKS.map((t) => (
            <span key={t.key} className="flex items-center gap-1 text-muted-foreground">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: t.color }} />
              {t.label}
            </span>
          ))}
          <span className="flex items-center gap-1 text-muted-foreground">
            <span className="inline-block h-0.5 w-4 bg-amber-400" /> Movement index
          </span>
          {hasStay && (
            <span className="flex items-center gap-1 text-muted-foreground">
              <span className="inline-block h-2 w-4 bg-primary/20" /> Hospital stay
            </span>
          )}
        </div>
        {hasStay && (
          <div className="flex gap-1">
            {(["all", "stay"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`rounded px-2 py-0.5 ${mode === m ? "bg-primary/15 text-primary border border-primary/20" : "text-muted-foreground border border-border"}`}
              >
                {m === "all" ? "All data" : "Stay ±1 day"}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="h-44">
        <ResponsiveContainer>
          <ScatterChart margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid stroke="hsl(var(--border))" />
            {hasStay && <ReferenceArea x1={adm!} x2={dis!} fill="hsl(var(--primary))" fillOpacity={0.08} />}
            <XAxis type="number" dataKey="t" domain={domain} tickFormatter={dayFmt} stroke="hsl(var(--muted-foreground))" fontSize={10} allowDataOverflow />
            <YAxis
              type="number"
              dataKey="y"
              domain={[-0.5, 3.5]}
              ticks={[0, 1, 2, 3]}
              tickFormatter={(v) => TRACKS[v]?.label ?? ""}
              stroke="hsl(var(--muted-foreground))"
              fontSize={10}
              width={90}
            />
            <Tooltip content={<EventTooltip />} />
            {TRACKS.map((tr) => (
              <Scatter
                key={tr.key}
                data={points.filter((p) => p.track === tr.key)}
                fill={tr.color}
                shape={(props: { cx?: number; cy?: number; payload?: Point }) => (
                  <circle
                    cx={props.cx}
                    cy={props.cy}
                    r={props.payload?.alert ? 5 : 3.5}
                    fill={tr.color}
                    stroke={props.payload?.alert ? "#fff" : "none"}
                    strokeWidth={1}
                    opacity={0.85}
                  />
                )}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {motion.length > 0 && (
        <div className="h-28">
          <ResponsiveContainer>
            <ComposedChart data={motion} margin={{ left: 8, right: 16 }}>
              <CartesianGrid stroke="hsl(var(--border))" />
              {hasStay && <ReferenceArea x1={adm!} x2={dis!} fill="hsl(var(--primary))" fillOpacity={0.08} />}
              <XAxis type="number" dataKey="t" domain={domain} tickFormatter={dayFmt} stroke="hsl(var(--muted-foreground))" fontSize={10} allowDataOverflow />
              <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={10} width={90} label={{ value: "movement", angle: -90, fill: "#64748b", fontSize: 10 }} />
              <Tooltip
                labelFormatter={(v) => fullFmt(Number(v))}
                contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
              />
              <Line type="linear" connectNulls={false} dataKey="movement" stroke="#fbbf24" dot={false} strokeWidth={1.5} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {dropped > 0 && (
        <div className="mt-1 text-xs text-muted-foreground">{dropped} event(s) without a usable timestamp are not plotted.</div>
      )}
    </div>
  );
}

function EventTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="max-w-xs rounded border border-border bg-popover p-2 text-xs shadow">
      <div className="text-muted-foreground">{fullFmt(p.t)}</div>
      <div className="font-medium text-foreground">{p.label}</div>
      {p.detail && <div className="mt-1 text-muted-foreground">{p.detail}</div>}
    </div>
  );
}
