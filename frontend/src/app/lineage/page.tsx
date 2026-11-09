"use client";

import { useState } from "react";
import Link from "next/link";
import { useApi } from "@/lib/use-api";
import type { AuditEntry, QualityScore } from "@/lib/types";
import { Badge, Card, Empty, ErrorBox, Loading, Table, severityTone } from "@/components/ui";
import { PageHeader } from "@/components/page-header";

const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function LineagePage() {
  const [source, setSource] = useState("");
  const [severity, setSeverity] = useState("CRITICAL,HIGH");
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const sources = useApi<QualityScore[]>("/api/overview/quality-scores");
  const params = new URLSearchParams({ limit: String(pageSize), offset: String(page * pageSize) });
  if (source) params.set("source", source);
  if (severity) params.set("severity", severity);
  const log = useApi<AuditEntry[]>(`/api/quality/audit-log?${params}`);

  return (
    <>
      <PageHeader
        title="Data lineage"
        subtitle="Every transformation the pipeline applied, value by value: which file and row it came from, what it was, what it became, and why."
      />

      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <span className="text-slate-400">Source</span>
            <select
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                setPage(0);
              }}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1"
            >
              <option value="">All files</option>
              {(sources.data ?? []).map((s) => (
                <option key={s.source_file} value={s.source_file}>
                  {s.source_file}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Severity</span>
            {SEVERITIES.map((s) => {
              const active = severity.split(",").includes(s);
              return (
                <button
                  key={s}
                  onClick={() => {
                    const set = new Set(severity.split(",").filter(Boolean));
                    if (active) set.delete(s);
                    else set.add(s);
                    setSeverity([...set].join(","));
                    setPage(0);
                  }}
                  className={`rounded px-2 py-0.5 text-xs ${active ? "bg-slate-700 text-white" : "text-slate-500 ring-1 ring-slate-700"}`}
                >
                  {s}
                </button>
              );
            })}
          </div>
        </div>

        {log.error ? (
          <ErrorBox error={log.error} onRetry={log.reload} />
        ) : log.loading && !log.data ? (
          <Loading />
        ) : !log.data?.length ? (
          <Empty>No entries for these filters.</Empty>
        ) : (
          <Table head={["Source → row", "Case", "Field", "Original", "Result", "Issue", "Action"]}>
            {log.data.map((e) => (
              <tr key={e.coId} className="align-top">
                <td className="px-2 py-1.5 font-mono text-xs text-slate-400">
                  {e.source_file}
                  {e.row_number != null && <span className="text-slate-600"> #{e.row_number}</span>}
                </td>
                <td className="whitespace-nowrap px-2 py-1.5 font-mono text-xs">
                  {e.case_id ? (
                    <Link className="text-sky-400 hover:underline" href={`/patients/${encodeURIComponent(e.case_id)}`}>
                      {e.case_id}
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-2 py-1.5 font-mono text-xs text-slate-300">{e.column_name}</td>
                <td className="max-w-[12rem] truncate px-2 py-1.5 font-mono text-xs text-rose-300/90" title={e.original_value ?? ""}>
                  {e.original_value ?? "∅"}
                </td>
                <td className="max-w-[12rem] truncate px-2 py-1.5 font-mono text-xs text-emerald-300/90" title={e.cleaned_value ?? ""}>
                  {e.cleaned_value ?? "∅"}
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-xs">{e.error_type}</span>
                    <Badge tone={severityTone(e.severity)}>{e.severity}</Badge>
                  </div>
                </td>
                <td className="px-2 py-1.5 text-xs text-slate-400">
                  {e.action_taken}
                  {e.corrected_by && <div className="text-slate-500">by {e.corrected_by}</div>}
                </td>
              </tr>
            ))}
          </Table>
        )}

        <div className="mt-3 flex items-center justify-between text-sm text-slate-400">
          <button disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="disabled:opacity-40">
            ← Newer
          </button>
          <span>Page {page + 1}</span>
          <button disabled={(log.data?.length ?? 0) < pageSize} onClick={() => setPage((p) => p + 1)} className="disabled:opacity-40">
            Older →
          </button>
        </div>
      </Card>
    </>
  );
}
