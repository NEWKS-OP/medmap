"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { PipelineProgress, QualityScore, Summary, WardScore } from "@/lib/types";
import { Badge, Button, Card, ErrorBox, Loading, Stat, fmt, scoreTone } from "@/components/ui";
import { PageHeader } from "@/components/page-header";

const TABLE_LABELS: Record<string, string> = {
  tbCaseData: "Cases",
  tbImportLabsData: "Lab results",
  tbImportIcd10Data: "Diagnoses (ICD-10/OPS)",
  tbImportDeviceMotionData: "Motion sensor (hourly)",
  tbImportMedicationInpatientData: "Medication events",
  tbImportNursingDailyReportsData: "Nursing notes",
  tbImportAcData: "Care assessments (epaAC)",
};

export default function OverviewPage() {
  const summary = useApi<Summary>("/api/overview/summary");
  const scores = useApi<QualityScore[]>("/api/overview/quality-scores");
  const wards = useApi<WardScore[]>("/api/overview/ward-scores");

  if (summary.error) return <ErrorBox error={summary.error} onRetry={summary.reload} />;

  const s = summary.data;
  const worst = [...(scores.data ?? [])].sort((a, b) => a.score - b.score).slice(0, 8);

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle="Heterogeneous hospital exports (labs, diagnoses, medication, sensors, nursing notes, care assessments) from four clinics, cleaned and mapped into one SQL model."
        action={
          <PipelineControl
            onDone={() => {
              summary.reload();
              scores.reload();
              wards.reload();
            }}
          />
        }
      />

      {!s ? (
        <Loading />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Cases" value={fmt(s.total_patients)} />
            <Stat label="Issues logged" value={fmt(s.audit_log.total)} hint={`${fmt(s.audit_log.critical)} critical`} />
            <Stat label="Auto-corrected values" value={fmt(s.audit_log.auto_corrected)} />
            <Stat
              label="Awaiting review"
              value={fmt(s.data_passports.pending_review)}
              hint={<Link href="/corrections" className="underline">Open corrections →</Link>}
            />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card title="Rows in the unified model">
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart
                    layout="vertical"
                    data={Object.entries(s.table_counts).map(([k, v]) => ({ name: TABLE_LABELS[k] ?? k, rows: v }))}
                    margin={{ left: 40 }}
                  >
                    <CartesianGrid stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" stroke="#64748b" fontSize={11} />
                    <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={11} width={150} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Bar dataKey="rows" fill="#38bdf8" radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card title="Lowest-quality sources" action={<Link href="/sources" className="text-xs text-sky-400">All sources →</Link>}>
              {!scores.data ? (
                <Loading />
              ) : (
                <ul className="space-y-2">
                  {worst.map((q) => (
                    <li key={q.source_file} className="flex items-center gap-3">
                      <div className="w-56 truncate text-sm text-slate-300" title={q.source_file}>
                        {q.source_file}
                      </div>
                      <div className="h-2 flex-1 overflow-hidden rounded bg-slate-800">
                        <div
                          className="h-full rounded bg-sky-500"
                          style={{ width: `${Math.max(2, q.score)}%`, opacity: 0.4 + q.score / 170 }}
                        />
                      </div>
                      <Badge tone={scoreTone(q.score)}>{q.score}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card title="Data quality by ward" className="mt-4">
            {!wards.data ? (
              <Loading />
            ) : (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {wards.data.slice(0, 12).map((w) => (
                  <div key={w.ward_name} className="rounded-lg border border-slate-800 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-200">{w.ward_name}</span>
                      <Badge tone={scoreTone(w.score)}>{w.score}</Badge>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {fmt(w.nb_patients)} patients · {fmt(w.nb_errors)} issues
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </>
  );
}

function PipelineControl({ onDone }: { onDone: () => void }) {
  const [progress, setProgress] = useState<PipelineProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearInterval(timer.current);
  }, []);

  const poll = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(async () => {
      try {
        const p = await api.get<PipelineProgress>("/api/pipeline/progress");
        setProgress(p);
        const st = (p.status || "").toUpperCase();
        if (st === "COMPLETED" || st === "ERROR" || st === "IDLE") {
          if (timer.current) clearInterval(timer.current);
          if (st === "COMPLETED") onDone();
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        if (timer.current) clearInterval(timer.current);
      }
    }, 1500);
  };

  const start = async () => {
    setError(null);
    try {
      await api.post("/api/pipeline/start", { data_folder: "dirty" });
      poll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const running = (progress?.status || "").toUpperCase() === "RUNNING";
  return (
    <div className="flex items-center gap-3">
      {progress && (
        <div className="text-right text-xs text-slate-400">
          <div>
            Step {progress.step_number}/{progress.total_steps} · {progress.current_step}
          </div>
          <div className="mt-1 h-1.5 w-48 overflow-hidden rounded bg-slate-800">
            <div className="h-full bg-sky-500 transition-all" style={{ width: `${Math.round(progress.progress_pct * 100)}%` }} />
          </div>
        </div>
      )}
      {error && <span className="text-xs text-rose-400">{error}</span>}
      <Button onClick={start} disabled={running}>
        {running ? "Pipeline running…" : "Re-run pipeline"}
      </Button>
    </div>
  );
}
