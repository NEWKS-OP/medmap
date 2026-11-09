"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useApi } from "@/lib/use-api";
import type { Convergence, LabValue, MotionSummary, NursingNote, Passport, Patient, TimelineEvent } from "@/lib/types";
import { Badge, Card, Empty, ErrorBox, Loading, Stat, Table, fmt, severityTone } from "@/components/ui";
import { Trajectory } from "@/components/trajectory";

const TABS = ["Labs", "Medication", "Nursing notes", "Data lineage"] as const;

export default function PatientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const base = `/api/patients/${encodeURIComponent(id)}`;
  const patient = useApi<Patient | null>(base);
  const timeline = useApi<TimelineEvent[]>(`${base}/timeline`);
  const convergence = useApi<Convergence>(`${base}/convergence`);
  const motion = useApi<MotionSummary>(`${base}/motion-summary`);
  const sbar = useApi<{ case_id: string; sbar: Record<string, string> | null }>(`${base}/sbar`);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Labs");

  if (patient.error) return <ErrorBox error={patient.error} onRetry={patient.reload} />;
  if (patient.loading && !patient.data) return <Loading />;
  const p = patient.data;
  if (!p || !(p as Patient).case_id) return <Empty>Case {id} not found.</Empty>;

  const risk = convergence.data?.risk_level;

  return (
    <>
      <div className="mb-1 text-xs text-slate-500">
        <Link href="/patients" className="hover:underline">
          Patients
        </Link>{" "}
        / {p.case_id}
      </div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-50">
            {p.case_id}{" "}
            <span className="text-base font-normal text-slate-400">
              · {p.age ?? "?"} y {p.gender ?? ""} · {p.ward ?? "unknown ward"}
            </span>
          </h1>
          <div className="mt-1 text-sm text-slate-300">
            {p.primary_icd10 && <span className="mr-2 font-mono text-xs text-slate-400">{p.primary_icd10}</span>}
            {p.primary_icd10_desc}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            Admitted {p.admission_date ?? "—"} · discharged {p.discharge_date ?? "—"} · patient ID {p.patient_id ?? "—"}
          </div>
        </div>
        {convergence.data && (
          <div className="text-right">
            <div className="text-xs text-slate-400">Multi-source risk score</div>
            <div className="flex items-center justify-end gap-2">
              <span className="text-2xl font-semibold tabular-nums">{convergence.data.total_score}</span>
              <Badge tone={risk === "CRITICAL" ? "bad" : risk === "HIGH" ? "warn" : risk === "MEDIUM" ? "info" : "good"}>{risk}</Badge>
            </div>
          </div>
        )}
      </div>

      <Card title="Trajectory">
        {timeline.error ? (
          <ErrorBox error={timeline.error} />
        ) : !timeline.data ? (
          <Loading />
        ) : (
          <Trajectory events={timeline.data} admission={p.admission_date} discharge={p.discharge_date} />
        )}
      </Card>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Sensor records" value={fmt(motion.data?.total_records)} />
        <Stat label="Falls detected" value={fmt(motion.data?.fall_events)} />
        <Stat label="Bed exits" value={fmt(motion.data?.bed_exits)} />
        <Stat label="Avg movement index" value={fmt(motion.data?.avg_movement_index, 1)} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-2 flex gap-1">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded px-3 py-1 text-sm ${tab === t ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"}`}
              >
                {t}
              </button>
            ))}
          </div>
          <Card>
            {tab === "Labs" && <LabsTab base={base} />}
            {tab === "Medication" && <MedsTab events={timeline.data ?? []} />}
            {tab === "Nursing notes" && <NursingTab base={base} />}
            {tab === "Data lineage" && <LineageTab base={base} />}
          </Card>
        </div>

        <div className="space-y-4">
          {convergence.data && (
            <Card title="Why this score">
              <ul className="space-y-1 text-sm">
                {Object.entries(convergence.data.breakdown).map(([k, v]) => (
                  <li key={k} className="flex items-center gap-2">
                    <span className="w-24 capitalize text-slate-400">{k}</span>
                    <div className="h-1.5 flex-1 rounded bg-slate-800">
                      <div className="h-full rounded bg-amber-500" style={{ width: `${Math.min(100, (v / 30) * 100)}%` }} />
                    </div>
                    <span className="w-6 text-right tabular-nums">{v}</span>
                  </li>
                ))}
              </ul>
              {convergence.data.top_contributors.length > 0 && (
                <div className="mt-2 text-xs text-slate-400">{convergence.data.top_contributors.join(" · ")}</div>
              )}
            </Card>
          )}
          {sbar.data?.sbar && (
            <Card title="SBAR handover (rule-based, offline)">
              <dl className="space-y-2 text-sm">
                {(["S", "B", "A", "R"] as const).map((k) => (
                  <div key={k}>
                    <dt className="text-xs font-semibold text-slate-400">
                      {{ S: "Situation", B: "Background", A: "Assessment", R: "Recommendation" }[k]}
                    </dt>
                    <dd className="text-slate-200">{sbar.data!.sbar![k]}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function LabsTab({ base }: { base: string }) {
  const labs = useApi<LabValue[]>(`${base}/labs`);
  if (labs.error) return <ErrorBox error={labs.error} />;
  if (!labs.data) return <Loading />;
  if (!labs.data.length) return <Empty>No lab results for this case.</Empty>;
  return (
    <Table head={["Parameter", "Value", "Reference", "Flag", "Cleaning"]}>
      {labs.data.map((l, i) => (
        <tr key={`${l.parameter_name}-${i}`}>
          <td className="px-2 py-1.5">{l.parameter_name}</td>
          <td className="px-2 py-1.5 tabular-nums">{l.value ?? "—"}</td>
          <td className="px-2 py-1.5 text-xs text-slate-400">
            {l.ref_low ?? "?"} – {l.ref_high ?? "?"}
          </td>
          <td className="px-2 py-1.5">{l.flag ? <Badge tone={severityTone(l.flag)}>{l.flag}</Badge> : "—"}</td>
          <td className="px-2 py-1.5 text-xs text-slate-400">
            {l.was_corrected ? `corrected from ${l.original_value ?? "∅"}` : ""}
          </td>
        </tr>
      ))}
    </Table>
  );
}

function MedsTab({ events }: { events: TimelineEvent[] }) {
  const meds = events.filter((e) => e.event_type === "MEDICATION");
  if (!meds.length) return <Empty>No medication events for this case.</Empty>;
  return (
    <Table head={["Time", "Medication", "Dose", "Route", "Status", "Record"]}>
      {meds.map((m, i) => {
        const d = m.data as Record<string, string | null>;
        return (
          <tr key={i}>
            <td className="px-2 py-1.5 text-xs text-slate-400">{m.timestamp || "—"}</td>
            <td className="px-2 py-1.5">{d.name ?? <span className="text-slate-500">unnamed</span>}</td>
            <td className="px-2 py-1.5 tabular-nums">{d.dose ?? "—"}</td>
            <td className="px-2 py-1.5">{d.route ?? "—"}</td>
            <td className="px-2 py-1.5">{d.status ?? "—"}</td>
            <td className="px-2 py-1.5 text-xs text-slate-400">{d.event_type ?? ""}</td>
          </tr>
        );
      })}
    </Table>
  );
}

function NursingTab({ base }: { base: string }) {
  const notes = useApi<NursingNote[]>(`${base}/nursing`);
  if (notes.error) return <ErrorBox error={notes.error} />;
  if (!notes.data) return <Loading />;
  if (!notes.data.length) return <Empty>No nursing notes for this case.</Empty>;
  return (
    <ul className="space-y-3">
      {notes.data.map((n, i) => (
        <li key={i} className="rounded-lg border border-slate-800 p-3">
          <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span>{n.report_date}</span>
            {n.shift && <Badge>{n.shift}</Badge>}
            {n.pain_level != null && <Badge tone={n.pain_level >= 7 ? "bad" : n.pain_level >= 4 ? "warn" : "neutral"}>pain {n.pain_level}/10</Badge>}
            {n.mobility_status && <Badge tone="info">{n.mobility_status.toLowerCase()}</Badge>}
            {n.deterioration_flag && <Badge tone="bad">deterioration: {n.deterioration_signs.join(", ")}</Badge>}
          </div>
          <p className="text-sm text-slate-200">{n.note_preview}</p>
        </li>
      ))}
    </ul>
  );
}

function LineageTab({ base }: { base: string }) {
  const passports = useApi<Passport[]>(`${base}/passports`);
  if (passports.error) return <ErrorBox error={passports.error} />;
  if (!passports.data) return <Loading />;
  if (!passports.data.length) return <Empty>No data issues recorded for this case.</Empty>;
  return (
    <Table head={["Source → row", "Field", "Raw", "Cleaned", "Problem", "Status"]}>
      {passports.data.map((p) => (
        <tr key={p.passport_id}>
          <td className="px-2 py-1.5 font-mono text-xs text-slate-400">
            {p.source_file}
            {p.row_number != null && ` #${p.row_number}`}
          </td>
          <td className="px-2 py-1.5 font-mono text-xs">{p.field_name}</td>
          <td className="px-2 py-1.5 font-mono text-xs text-rose-300/90">{p.raw_value ?? "∅"}</td>
          <td className="px-2 py-1.5 font-mono text-xs text-emerald-300/90">{p.cleaned_value ?? "∅"}</td>
          <td className="px-2 py-1.5 text-xs">{p.problem_detail}</td>
          <td className="px-2 py-1.5">
            <Badge tone={p.status === "CLEAN" ? "good" : p.status === "QUARANTINE" ? "bad" : "warn"}>{p.status}</Badge>
          </td>
        </tr>
      ))}
    </Table>
  );
}
