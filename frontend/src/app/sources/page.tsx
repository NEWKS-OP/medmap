"use client";

import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/use-api";
import type { ErrorCategory, QualityScore } from "@/lib/types";
import { Badge, Card, ErrorBox, Loading, Table, fmt, scoreTone } from "@/components/ui";
import { PageHeader } from "@/components/page-header";

const TABLE_LABELS: Record<string, string> = {
  tbImportLabsData: "Labs",
  tbImportIcd10Data: "ICD-10 / OPS",
  tbImportDeviceMotionData: "Motion (hourly)",
  tbImportDevice1HzMotionData: "Motion (1 Hz)",
  tbImportMedicationInpatientData: "Medication",
  tbImportNursingDailyReportsData: "Nursing notes",
  tbImportAcData: "Care assessments",
};

function sourceGroup(file: string) {
  const m = file.match(/^clinic_(\d)/);
  if (m) return `Clinic ${m[1]}`;
  if (file === "cross_source") return "Cross-source checks";
  return "Central export (dirty)";
}

export default function SourcesPage() {
  const scores = useApi<QualityScore[]>("/api/overview/quality-scores");
  const categories = useApi<ErrorCategory[]>("/api/quality/error-categories");
  const completeness = useApi<Record<string, Record<string, number>>>("/api/quality/completeness");
  const [selected, setSelected] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const g: Record<string, QualityScore[]> = {};
    for (const s of scores.data ?? []) (g[sourceGroup(s.source_file)] ??= []).push(s);
    return Object.entries(g).sort(([a], [b]) => a.localeCompare(b));
  }, [scores.data]);

  if (scores.error) return <ErrorBox error={scores.error} onRetry={scores.reload} />;

  const sel = scores.data?.find((s) => s.source_file === selected) ?? null;

  return (
    <>
      <PageHeader
        title="Sources & quality"
        subtitle="Every input file, how much of it made it into the model, and what had to be fixed. The score drops with quarantined rows and unresolved critical issues."
      />

      {!scores.data ? (
        <Loading />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            {grouped.map(([group, items]) => (
              <Card key={group} title={group}>
                <Table head={["Source file", "Score", "Imported", "Quarantined", "Auto-fixed"]}>
                  {items.map((q) => (
                    <tr
                      key={q.source_file}
                      onClick={() => setSelected(q.source_file)}
                      className={`cursor-pointer hover:bg-slate-800/50 ${selected === q.source_file ? "bg-slate-800/70" : ""}`}
                    >
                      <td className="px-2 py-1.5 font-mono text-xs text-slate-300">{q.source_file}</td>
                      <td className="px-2 py-1.5">
                        <Badge tone={scoreTone(q.score)}>{q.score}</Badge>
                      </td>
                      <td className="px-2 py-1.5 tabular-nums">{fmt(q.rows_imported)}</td>
                      <td className="px-2 py-1.5 tabular-nums">{fmt(q.rows_quarantined)}</td>
                      <td className="px-2 py-1.5 tabular-nums">{fmt(q.values_auto_corrected)}</td>
                    </tr>
                  ))}
                </Table>
              </Card>
            ))}
          </div>

          <div className="space-y-4">
            <Card title={sel ? `Issues in ${sel.source_file}` : "Select a source"}>
              {!sel ? (
                <div className="text-sm text-slate-500">Click a row to see what was detected in that file.</div>
              ) : (
                <ul className="space-y-1 text-sm">
                  {Object.entries(sel.errors_by_category)
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, v]) => (
                      <li key={k} className="flex justify-between gap-2">
                        <span className="font-mono text-xs text-slate-300">{k}</span>
                        <span className="tabular-nums text-slate-400">{fmt(v)}</span>
                      </li>
                    ))}
                </ul>
              )}
            </Card>

            <Card title="Issue types (all sources)">
              {!categories.data ? (
                <Loading />
              ) : (
                <div className="h-80">
                  <ResponsiveContainer>
                    <BarChart
                      layout="vertical"
                      data={categories.data.slice(0, 10).map((c) => ({
                        name: c.error_type,
                        CRITICAL: c.by_severity.CRITICAL ?? 0,
                        HIGH: c.by_severity.HIGH ?? 0,
                        MEDIUM: c.by_severity.MEDIUM ?? 0,
                        LOW: c.by_severity.LOW ?? 0,
                      }))}
                    >
                      <CartesianGrid stroke="#1e293b" horizontal={false} />
                      <XAxis type="number" stroke="#64748b" fontSize={10} scale="sqrt" />
                      <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={10} width={170} />
                      <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="CRITICAL" stackId="a" fill="#f43f5e" />
                      <Bar dataKey="HIGH" stackId="a" fill="#f59e0b" />
                      <Bar dataKey="MEDIUM" stackId="a" fill="#38bdf8" />
                      <Bar dataKey="LOW" stackId="a" fill="#475569" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      <Card title="Field completeness after cleaning (% non-null)" className="mt-4">
        {!completeness.data ? (
          <Loading />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(completeness.data).map(([table, cols]) => {
              const entries = Object.entries(cols)
                .filter(([c]) => !/ref_(low|high)$/i.test(c))
                .sort((a, b) => a[1] - b[1])
                .slice(0, 8);
              return (
                <div key={table}>
                  <div className="mb-1 text-xs font-medium text-slate-300">{TABLE_LABELS[table] ?? table}</div>
                  <ul className="space-y-1">
                    {entries.map(([c, pct]) => (
                      <li key={c} className="flex items-center gap-2 text-xs">
                        <span className="w-40 truncate font-mono text-slate-400" title={c}>
                          {c.replace(/^co/, "")}
                        </span>
                        <div className="h-1.5 flex-1 rounded bg-slate-800">
                          <div
                            className={`h-full rounded ${pct >= 90 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-rose-500"}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="w-10 text-right tabular-nums text-slate-400">{Math.round(pct)}%</span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </>
  );
}
