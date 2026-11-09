"use client";

import { use, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Activity, Footprints, Pill, NotebookPen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError, LoadingState } from "@/components/dashboard/api-state";
import { Trajectory } from "@/components/dashboard/trajectory";
import { useApi } from "@/hooks/use-api";
import type { Convergence, LabValue, NursingNote, Passport, PatientDetail, TimelineEvent } from "@/types/medmap";

interface MotionSummary {
  total_records: number;
  fall_events: number;
  bed_exits: number;
  avg_movement_index: number | null;
}

const RISK_VARIANT: Record<string, "critical" | "high" | "medium" | "low"> = {
  CRITICAL: "critical",
  HIGH: "high",
  MEDIUM: "medium",
  LOW: "low",
};

function flagVariant(flag: string | null): "critical" | "warning" | "none" {
  const f = (flag || "").toUpperCase();
  if (f === "HH" || f === "LL") return "critical";
  if (f === "H" || f === "L") return "warning";
  return "none";
}

function FadeIn({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay }} className={className}>
      {children}
    </motion.div>
  );
}

export default function PatientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const base = `/api/patients/${encodeURIComponent(id)}`;
  const patient = useApi<PatientDetail>(base);
  const timeline = useApi<TimelineEvent[]>(`${base}/timeline`);
  const convergence = useApi<Convergence>(`${base}/convergence`);
  const motionSummary = useApi<MotionSummary>(`${base}/motion-summary`);
  const sbar = useApi<{ sbar: Record<string, string> | null }>(`${base}/sbar`);

  if (patient.error) return <ApiError error={patient.error} onRetry={patient.reload} />;
  if (!patient.data) return <LoadingState label="Loading patient…" />;
  const p = patient.data;
  if (!p.case_id) {
    return (
      <div className="space-y-4">
        <BackLink />
        <p className="text-sm text-muted-foreground">Case {id} not found.</p>
      </div>
    );
  }

  const meds = (timeline.data ?? []).filter((e) => e.event_type === "MEDICATION");
  const m = motionSummary.data;

  return (
    <div className="space-y-6 pb-8">
      <BackLink />

      {/* Header */}
      <FadeIn>
        <Card>
          <CardContent className="flex flex-wrap items-start justify-between gap-4 p-5">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold tracking-tight">{p.case_id}</h2>
                <span className="text-sm text-muted-foreground">
                  {p.age ?? "?"}y · {p.gender ?? "?"} · {p.ward ?? "unknown ward"}
                </span>
              </div>
              <p className="mt-1 text-sm">
                {p.primary_icd10 && <span className="mr-2 font-mono text-xs text-muted-foreground">{p.primary_icd10}</span>}
                {p.primary_icd10_desc ?? "No diagnosis record"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Admitted {p.admission_date ?? "—"} · discharged {p.discharge_date ?? "—"} · patient ID {p.patient_id ?? "—"}
              </p>
            </div>
            {convergence.data && (
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Multi-source risk</p>
                <div className="mt-1 flex items-center justify-end gap-2">
                  <span className="text-3xl font-bold tabular-nums">{convergence.data.total_score}</span>
                  <Badge variant={RISK_VARIANT[convergence.data.risk_level] ?? "none"}>{convergence.data.risk_level}</Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </FadeIn>

      {/* Trajectory */}
      <FadeIn delay={0.08}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Patient Trajectory</CardTitle>
            <CardDescription>Labs, medication, nursing notes and motion sensor merged on one time axis</CardDescription>
          </CardHeader>
          <CardContent>
            {timeline.error ? (
              <ApiError error={timeline.error} />
            ) : !timeline.data ? (
              <LoadingState />
            ) : (
              <Trajectory events={timeline.data} admission={p.admission_date} discharge={p.discharge_date} />
            )}
          </CardContent>
        </Card>
      </FadeIn>

      {/* Small stats */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {[
          { label: "Sensor records", value: m?.total_records, icon: Activity },
          { label: "Falls detected", value: m?.fall_events, icon: Footprints, bad: (m?.fall_events ?? 0) > 0 },
          { label: "Medication events", value: meds.length || undefined, icon: Pill },
          { label: "Avg movement index", value: m?.avg_movement_index ?? undefined, icon: NotebookPen },
        ].map((s, i) => (
          <FadeIn key={s.label} delay={0.12 + i * 0.04}>
            <Card>
              <CardContent className="flex items-center gap-3 p-4">
                <div
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-lg border",
                    s.bad ? "border-anomaly/20 bg-anomaly/10 text-anomaly" : "border-primary/20 bg-primary/10 text-primary"
                  )}
                >
                  <s.icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-xl font-bold tabular-nums">{s.value ?? "—"}</p>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{s.label}</p>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <FadeIn delay={0.2} className="lg:col-span-2">
          <Card>
            <CardContent className="p-5">
              <Tabs defaultValue="labs">
                <TabsList>
                  <TabsTrigger value="labs">Labs</TabsTrigger>
                  <TabsTrigger value="meds">Medication</TabsTrigger>
                  <TabsTrigger value="nursing">Nursing notes</TabsTrigger>
                  <TabsTrigger value="lineage">Data lineage</TabsTrigger>
                </TabsList>
                <TabsContent value="labs" className="mt-4">
                  <LabsTab base={base} />
                </TabsContent>
                <TabsContent value="meds" className="mt-4">
                  <MedsTab events={meds} />
                </TabsContent>
                <TabsContent value="nursing" className="mt-4">
                  <NursingTab base={base} />
                </TabsContent>
                <TabsContent value="lineage" className="mt-4">
                  <LineageTab base={base} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </FadeIn>

        <div className="space-y-4">
          {convergence.data && (
            <FadeIn delay={0.24}>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle>Risk Breakdown</CardTitle>
                  <CardDescription>Contribution of each data source to the score</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {Object.entries(convergence.data.breakdown).map(([k, v]) => (
                    <div key={k} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="capitalize">{k}</span>
                        <span className="tabular-nums text-muted-foreground">{v}</span>
                      </div>
                      <Progress value={Math.min(100, (v / 30) * 100)} className="h-1.5 [&>div]:bg-warning" />
                    </div>
                  ))}
                  {convergence.data.top_contributors.length > 0 && (
                    <p className="pt-1 text-[11px] text-muted-foreground">{convergence.data.top_contributors.join(" · ")}</p>
                  )}
                </CardContent>
              </Card>
            </FadeIn>
          )}
          {sbar.data?.sbar && (
            <FadeIn delay={0.28}>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle>SBAR Handover</CardTitle>
                  <CardDescription>Generated offline from the merged record</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  {(["S", "B", "A", "R"] as const).map((k) => (
                    <div key={k}>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        {{ S: "Situation", B: "Background", A: "Assessment", R: "Recommendation" }[k]}
                      </p>
                      <p className="mt-0.5 leading-relaxed">{sbar.data!.sbar![k]}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </FadeIn>
          )}
        </div>
      </div>
    </div>
  );
}

function BackLink() {
  return (
    <Link href="/patients" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
      <ArrowLeft className="h-3.5 w-3.5" /> Patient monitor
    </Link>
  );
}

const th = "pb-3 text-left text-muted-foreground font-semibold uppercase tracking-wider";

function LabsTab({ base }: { base: string }) {
  const labs = useApi<LabValue[]>(`${base}/labs`);
  if (labs.error) return <ApiError error={labs.error} />;
  if (!labs.data) return <LoadingState />;
  if (!labs.data.length) return <p className="py-6 text-center text-xs text-muted-foreground">No lab results for this case.</p>;
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-border">
          <th className={th}>Parameter</th>
          <th className={th}>Value</th>
          <th className={th}>Reference</th>
          <th className={th}>Flag</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border/50">
        {labs.data.map((l, i) => (
          <tr key={i} className="hover:bg-muted/20">
            <td className="py-2.5 font-medium">{l.parameter_name}</td>
            <td className="py-2.5 tabular-nums">{l.value ?? "—"}</td>
            <td className="py-2.5 text-muted-foreground">
              {l.ref_low ?? "?"} – {l.ref_high ?? "?"}
            </td>
            <td className="py-2.5">{l.flag ? <Badge variant={flagVariant(l.flag)}>{l.flag}</Badge> : <span className="text-muted-foreground">—</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MedsTab({ events }: { events: TimelineEvent[] }) {
  if (!events.length) return <p className="py-6 text-center text-xs text-muted-foreground">No medication events for this case.</p>;
  return (
    <div className="max-h-[420px] overflow-y-auto">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-card">
          <tr className="border-b border-border">
            <th className={th}>Time</th>
            <th className={th}>Medication</th>
            <th className={th}>Dose</th>
            <th className={th}>Route</th>
            <th className={th}>Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {events.map((e, i) => {
            const d = e.data as Record<string, string | null>;
            return (
              <tr key={i} className="hover:bg-muted/20">
                <td className="py-2 text-muted-foreground">{e.timestamp || "—"}</td>
                <td className="py-2 font-medium">{d.name ?? <span className="text-muted-foreground">unnamed</span>}</td>
                <td className="py-2 tabular-nums">{d.dose ?? "—"}</td>
                <td className="py-2">{d.route ?? "—"}</td>
                <td className="py-2 capitalize text-muted-foreground">{d.status ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function NursingTab({ base }: { base: string }) {
  const notes = useApi<NursingNote[]>(`${base}/nursing`);
  if (notes.error) return <ApiError error={notes.error} />;
  if (!notes.data) return <LoadingState />;
  if (!notes.data.length) return <p className="py-6 text-center text-xs text-muted-foreground">No nursing notes for this case.</p>;
  return (
    <div className="space-y-2">
      {notes.data.map((n, i) => (
        <div
          key={i}
          className={cn("rounded-lg border p-3", n.deterioration_flag ? "border-anomaly/30 bg-anomaly/5" : "border-border")}
        >
          <div className="mb-1.5 flex flex-wrap items-center gap-1.5 text-[10px] text-muted-foreground">
            <span>{n.report_date}</span>
            {n.shift && <Badge variant="outline" className="text-[10px]">{n.shift}</Badge>}
            {n.pain_level != null && (
              <Badge variant={n.pain_level >= 7 ? "critical" : n.pain_level >= 4 ? "warning" : "none"}>pain {n.pain_level}/10</Badge>
            )}
            {n.mobility_status && <Badge variant="low">{n.mobility_status.toLowerCase()}</Badge>}
            {n.deterioration_flag && <Badge variant="critical">{n.deterioration_signs.join(", ") || "deterioration"}</Badge>}
          </div>
          <p className="text-xs leading-relaxed">{n.note_preview}</p>
        </div>
      ))}
    </div>
  );
}

function LineageTab({ base }: { base: string }) {
  const passports = useApi<Passport[]>(`${base}/passports`);
  if (passports.error) return <ApiError error={passports.error} />;
  if (!passports.data) return <LoadingState />;
  if (!passports.data.length) return <p className="py-6 text-center text-xs text-muted-foreground">No data issues recorded for this case.</p>;
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-border">
          <th className={th}>Source → row</th>
          <th className={th}>Field</th>
          <th className={th}>Raw</th>
          <th className={th}>Cleaned</th>
          <th className={th}>Problem</th>
          <th className={th}>Status</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border/50">
        {passports.data.map((p) => (
          <tr key={p.passport_id} className="hover:bg-muted/20">
            <td className="py-2.5 font-mono text-muted-foreground">
              {p.source_file}
              {p.row_number != null && ` #${p.row_number}`}
            </td>
            <td className="py-2.5 font-mono">{p.field_name}</td>
            <td className="py-2.5 font-mono text-anomaly/90">{p.raw_value ?? "∅"}</td>
            <td className="py-2.5 font-mono text-success">{p.cleaned_value ?? "∅"}</td>
            <td className="py-2.5">{p.problem_detail}</td>
            <td className="py-2.5">
              <Badge variant={p.status === "CLEAN" ? "success" : p.status === "QUARANTINE" ? "destructive" : "warning"}>{p.status}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
