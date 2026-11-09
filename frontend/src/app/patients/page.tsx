"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useApi } from "@/lib/use-api";
import type { Patient } from "@/lib/types";
import { Card, Empty, ErrorBox, Loading, Table } from "@/components/ui";
import { PageHeader } from "@/components/page-header";

export default function PatientsPage() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [ward, setWard] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);

  const path = debounced
    ? `/api/patients/search?q=${encodeURIComponent(debounced)}`
    : `/api/patients?limit=200${ward ? `&ward=${encodeURIComponent(ward)}` : ""}`;
  const list = useApi<Patient[]>(path);
  const wards = Array.from(new Set((list.data ?? []).map((p) => p.ward).filter(Boolean))) as string[];

  return (
    <>
      <PageHeader
        title="Patients"
        subtitle="Open a case to see its trajectory: diagnoses, labs, medication, motion sensor and nursing notes merged on one timeline."
      />
      <Card>
        <div className="mb-3 flex flex-wrap gap-3">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search case ID, patient ID or ward…"
            className="w-72 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
          />
          {!debounced && (
            <select value={ward} onChange={(e) => setWard(e.target.value)} className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm">
              <option value="">All wards</option>
              {wards.sort().map((w) => (
                <option key={w}>{w}</option>
              ))}
            </select>
          )}
        </div>
        {list.error ? (
          <ErrorBox error={list.error} onRetry={list.reload} />
        ) : list.loading && !list.data ? (
          <Loading />
        ) : !list.data?.length ? (
          <Empty>No patients found.</Empty>
        ) : (
          <Table head={["Case", "Patient", "Age / sex", "Ward", "Admission", "Primary diagnosis"]}>
            {list.data.map((p) => (
              <tr key={p.case_id} className="hover:bg-slate-800/40">
                <td className="px-2 py-1.5 font-mono text-xs">
                  <Link href={`/patients/${encodeURIComponent(p.case_id)}`} className="text-sky-400 hover:underline">
                    {p.case_id}
                  </Link>
                </td>
                <td className="px-2 py-1.5 font-mono text-xs text-slate-400">{p.patient_id ?? "—"}</td>
                <td className="px-2 py-1.5">
                  {p.age ?? "—"} {p.gender ?? ""}
                </td>
                <td className="px-2 py-1.5">{p.ward ?? "—"}</td>
                <td className="px-2 py-1.5 text-slate-400">{p.admission_date ?? "—"}</td>
                <td className="px-2 py-1.5">
                  {p.primary_icd10 && <span className="mr-2 font-mono text-xs text-slate-400">{p.primary_icd10}</span>}
                  {p.primary_icd10_desc ?? ""}
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
