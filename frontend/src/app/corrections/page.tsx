"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { AuditEntry, RepairProposal } from "@/lib/types";
import { Badge, Button, Card, Empty, ErrorBox, Loading, Table, severityTone } from "@/components/ui";
import { PageHeader } from "@/components/page-header";

interface CorrectionResult {
  success: boolean;
  audit_log_id: number;
  previous_value: string | null;
  new_value: string | null;
  action: string;
  error: string | null;
}

export default function CorrectionsPage() {
  const [page, setPage] = useState(0);
  const pageSize = 25;
  const queue = useApi<AuditEntry[]>(`/api/quality/audit-log?severity=CRITICAL&limit=${pageSize}&offset=${page * pageSize}`);
  const proposals = useApi<RepairProposal[]>("/api/corrections/repair-proposals");
  const history = useApi<CorrectionResult[]>("/api/corrections/history");
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [message, setMessage] = useState<string | null>(null);

  const refresh = () => Promise.all([queue.reload(), history.reload()]);

  const apply = async (e: AuditEntry, value: string | null) => {
    const res = await api.post<CorrectionResult>("/api/corrections/apply", {
      audit_log_id: e.coId,
      case_id: e.case_id,
      column_name: e.column_name,
      new_value: value,
      action: "MANUAL_CORRECT",
      corrected_by: "dashboard",
    });
    setMessage(res.success ? `Saved: ${e.column_name} ${res.previous_value ?? "∅"} → ${res.new_value ?? "∅"}` : `Failed: ${res.error}`);
    await refresh();
  };

  const rollback = async (id: number) => {
    const res = await api.post<CorrectionResult>("/api/corrections/rollback", { audit_log_id: id });
    setMessage(res.success ? `Rolled back entry #${id}` : `Failed: ${res.error}`);
    await refresh();
  };

  return (
    <>
      <PageHeader
        title="Corrections"
        subtitle="Critical issues the pipeline could not fix on its own. Accept a value, type the right one, or roll a correction back. Every change is written to the audit log with who made it and when."
      />
      {message && <div className="mb-3 rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200">{message}</div>}

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Review queue (critical)" className="xl:col-span-2">
          {queue.error ? (
            <ErrorBox error={queue.error} onRetry={queue.reload} />
          ) : queue.loading && !queue.data ? (
            <Loading />
          ) : !queue.data?.length ? (
            <Empty>Nothing left to review.</Empty>
          ) : (
            <Table head={["Source → row", "Case", "Field", "Original", "Current", "Issue", "Fix"]}>
              {queue.data.map((e) => {
                const corrected = e.action_taken === "MANUAL_CORRECT";
                return (
                  <tr key={e.coId} className="align-top">
                    <td className="px-2 py-1.5 font-mono text-xs text-slate-400">
                      {e.source_file}
                      {e.row_number != null && ` #${e.row_number}`}
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
                    <td className="px-2 py-1.5 font-mono text-xs">{e.column_name}</td>
                    <td className="px-2 py-1.5 font-mono text-xs text-rose-300/90">{e.original_value ?? "∅"}</td>
                    <td className="px-2 py-1.5 font-mono text-xs text-emerald-300/90">{e.cleaned_value ?? "∅"}</td>
                    <td className="px-2 py-1.5">
                      <div className="font-mono text-xs">{e.error_type}</div>
                      <Badge tone={corrected ? "good" : severityTone(e.severity)}>{corrected ? `fixed by ${e.corrected_by}` : e.action_taken}</Badge>
                    </td>
                    <td className="px-2 py-1.5">
                      {corrected ? (
                        <Button variant="ghost" onClick={() => rollback(e.coId)}>
                          Roll back
                        </Button>
                      ) : (
                        <form
                          className="flex gap-1"
                          onSubmit={(ev) => {
                            ev.preventDefault();
                            apply(e, drafts[e.coId] ?? e.original_value);
                          }}
                        >
                          <input
                            value={drafts[e.coId] ?? e.original_value ?? ""}
                            onChange={(ev) => setDrafts((d) => ({ ...d, [e.coId]: ev.target.value }))}
                            className="w-24 rounded border border-slate-700 bg-slate-950 px-1.5 py-1 font-mono text-xs"
                          />
                          <Button type="submit">Save</Button>
                        </form>
                      )}
                    </td>
                  </tr>
                );
              })}
            </Table>
          )}
          <div className="mt-3 flex items-center justify-between text-sm text-slate-400">
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="disabled:opacity-40">
              ← Previous
            </button>
            <span>Page {page + 1}</span>
            <button disabled={(queue.data?.length ?? 0) < pageSize} onClick={() => setPage((p) => p + 1)} className="disabled:opacity-40">
              Next →
            </button>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="This session's corrections">
            {!history.data?.length ? (
              <div className="text-sm text-slate-500">No manual corrections yet.</div>
            ) : (
              <ul className="space-y-2 text-sm">
                {[...history.data].reverse().map((h, i) => (
                  <li key={i} className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs">
                      #{h.audit_log_id}: {h.previous_value ?? "∅"} → {h.new_value ?? "∅"}
                    </span>
                    <Badge tone={h.action === "ROLLBACK" ? "warn" : "good"}>{h.action}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Repair suggestions (not auto-applied)">
            {proposals.error ? (
              <ErrorBox error={proposals.error} />
            ) : !proposals.data ? (
              <Loading />
            ) : !proposals.data.length ? (
              <div className="text-sm text-slate-500">No suggestions.</div>
            ) : (
              <ul className="space-y-2 text-sm">
                {proposals.data.slice(0, 12).map((p) => (
                  <li key={p.passport_id} className="rounded border border-slate-800 p-2">
                    <div className="font-mono text-xs">
                      {p.field_name}: <span className="text-rose-300/90">{p.raw_value}</span> →{" "}
                      <span className="text-emerald-300/90">{p.proposed_value}</span>
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {p.reasoning} · confidence {Math.round(p.confidence * 100)}%
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
