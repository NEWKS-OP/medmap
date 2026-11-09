"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw, ShieldAlert, ClipboardCheck, Undo2, Circle, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, LoadingState } from "@/components/dashboard/api-state";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import type { AuditEntry, CorrectionResult } from "@/types/medmap";

interface Summary {
  audit_log: { total: number; critical: number; quarantined: number; auto_corrected: number };
  data_passports: { total: number; pending_review: number };
}

type SeverityFilter = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

const ACTION_ICONS: Record<string, React.ElementType> = {
  QUARANTINE: ShieldAlert,
  FLAGGED: AlertTriangle,
  AUTO_CORRECT: RefreshCw,
  MANUAL_CORRECT: ClipboardCheck,
  ROLLBACK: Undo2,
};

const ACTION_COLORS: Record<string, string> = {
  QUARANTINE: "text-anomaly bg-anomaly/10 border-anomaly/20",
  FLAGGED: "text-warning bg-warning/10 border-warning/20",
  AUTO_CORRECT: "text-primary bg-primary/10 border-primary/20",
  MANUAL_CORRECT: "text-success bg-success/10 border-success/20",
  ROLLBACK: "text-muted-foreground bg-muted/30 border-border",
};

const ACTION_LABELS: Record<string, string> = {
  QUARANTINE: "Quarantined",
  FLAGGED: "Flagged for review",
  AUTO_CORRECT: "Auto-corrected",
  MANUAL_CORRECT: "Corrected manually",
  ROLLBACK: "Rolled back",
};

const SEVERITIES: { value: SeverityFilter; label: string }[] = [
  { value: "CRITICAL", label: "Critical" },
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
];

const nf = new Intl.NumberFormat("en-US");
const PAGE = 40;

export default function ActivityPage() {
  const [severity, setSeverity] = useState<SeverityFilter>("CRITICAL");
  const [page, setPage] = useState(0);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const summary = useApi<Summary>("/api/overview/summary");
  const log = useApi<AuditEntry[]>(`/api/quality/audit-log?severity=${severity}&limit=${PAGE}&offset=${page * PAGE}`);

  if (summary.error) return <ApiError error={summary.error} onRetry={summary.reload} />;

  const apply = async (e: AuditEntry) => {
    setBusy(e.coId);
    try {
      const res = await api.post<CorrectionResult>("/api/corrections/apply", {
        audit_log_id: e.coId,
        case_id: e.case_id,
        column_name: e.column_name,
        new_value: drafts[e.coId] ?? e.original_value,
        action: "MANUAL_CORRECT",
        corrected_by: "dashboard",
      });
      setMessage(res.success ? `${e.column_name}: ${res.previous_value ?? "∅"} → ${res.new_value ?? "∅"} saved` : `Failed: ${res.error}`);
      await Promise.all([log.reload(), summary.reload()]);
    } finally {
      setBusy(null);
    }
  };

  const rollback = async (e: AuditEntry) => {
    setBusy(e.coId);
    try {
      const res = await api.post<CorrectionResult>("/api/corrections/rollback", { audit_log_id: e.coId });
      setMessage(res.success ? `${e.column_name}: correction rolled back` : `Failed: ${res.error}`);
      await Promise.all([log.reload(), summary.reload()]);
    } finally {
      setBusy(null);
    }
  };

  const s = summary.data;

  return (
    <div className="space-y-4 pb-8">
      {/* Stat bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Issues logged", value: s?.audit_log.total, color: "text-foreground" },
          { label: "Critical", value: s?.audit_log.critical, color: "text-anomaly" },
          { label: "Quarantined values", value: s?.audit_log.quarantined, color: "text-warning" },
          { label: "Auto-corrected", value: s?.audit_log.auto_corrected, color: "text-primary" },
        ].map((stat, i) => (
          <motion.div key={stat.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
            <Card>
              <CardContent className="p-4">
                <p className={cn("text-2xl font-bold tabular-nums", stat.color)}>{stat.value != null ? nf.format(stat.value) : "—"}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{stat.label}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Main feed */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1">
              <CardTitle>Audit Trail &amp; Corrections</CardTitle>
              <CardDescription>
                Every value the pipeline changed or rejected, traced to its file and row. Fix a quarantined value or roll a correction back.
              </CardDescription>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-success font-medium">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
              Audited
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            {SEVERITIES.map((sv) => (
              <Button
                key={sv.value}
                variant={severity === sv.value ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs"
                onClick={() => {
                  setSeverity(sv.value);
                  setPage(0);
                }}
              >
                {sv.label}
              </Button>
            ))}
          </div>
          {message && <p className="mt-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs">{message}</p>}
        </CardHeader>

        <CardContent>
          {log.error ? (
            <ApiError error={log.error} onRetry={log.reload} />
          ) : !log.data ? (
            <LoadingState />
          ) : (
            <div className="relative">
              <div className="absolute left-[19px] top-2 bottom-2 w-px bg-border" />
              <div className="space-y-1">
                {log.data.map((e, i) => {
                  const Icon = ACTION_ICONS[e.action_taken] ?? Circle;
                  const canFix = e.action_taken === "QUARANTINE" || e.action_taken === "FLAGGED" || e.action_taken === "ROLLBACK";
                  const canRollback = e.action_taken === "MANUAL_CORRECT";
                  return (
                    <motion.div
                      key={e.coId}
                      initial={{ opacity: 0, x: -16 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: Math.min(i, 15) * 0.03 }}
                      className="relative flex gap-4 py-2"
                    >
                      <div
                        className={cn(
                          "relative z-10 flex items-center justify-center w-10 h-10 rounded-full border shrink-0",
                          ACTION_COLORS[e.action_taken] ?? "text-muted-foreground bg-muted/20 border-border"
                        )}
                      >
                        <Icon className="w-4 h-4" />
                      </div>

                      <div className="flex-1 min-w-0 pt-1">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="text-sm font-semibold">
                                {ACTION_LABELS[e.action_taken] ?? e.action_taken} · <span className="font-mono font-normal">{e.column_name}</span>
                              </p>
                              <Badge
                                variant={
                                  e.severity === "CRITICAL" ? "critical" : e.severity === "HIGH" ? "high" : e.severity === "MEDIUM" ? "medium" : "low"
                                }
                                className="text-[9px] px-1.5"
                              >
                                {e.error_type}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                              <span className="text-anomaly/90">{e.original_value ?? "∅"}</span>
                              {" → "}
                              <span className="text-success">{e.cleaned_value ?? "∅"}</span>
                            </p>
                            <p className="text-[10px] text-muted-foreground mt-1">
                              {e.source_file}
                              {e.row_number != null && ` · row ${e.row_number}`}
                              {e.case_id && (
                                <>
                                  {" · "}
                                  <Link href={`/patients/${encodeURIComponent(e.case_id)}`} className="text-primary font-medium hover:underline">
                                    {e.case_id}
                                  </Link>
                                </>
                              )}
                              {e.corrected_by && e.corrected_by !== "cleaner" && ` · by ${e.corrected_by}`}
                            </p>
                          </div>

                          <div className="shrink-0">
                            {canFix && (
                              <form
                                className="flex items-center gap-1.5"
                                onSubmit={(ev) => {
                                  ev.preventDefault();
                                  apply(e);
                                }}
                              >
                                <Input
                                  value={drafts[e.coId] ?? e.original_value ?? ""}
                                  onChange={(ev) => setDrafts((d) => ({ ...d, [e.coId]: ev.target.value }))}
                                  className="h-7 w-24 font-mono text-xs"
                                />
                                <Button type="submit" size="sm" className="h-7 text-xs" disabled={busy === e.coId}>
                                  {busy === e.coId ? "…" : "Fix"}
                                </Button>
                              </form>
                            )}
                            {canRollback && (
                              <Button variant="outline" size="sm" className="h-7 text-xs" disabled={busy === e.coId} onClick={() => rollback(e)}>
                                <Undo2 className="mr-1 h-3 w-3" /> Roll back
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}

                {log.data.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <Filter className="w-8 h-8 text-muted-foreground mb-3" />
                    <p className="text-sm font-medium">No entries</p>
                    <p className="text-xs text-muted-foreground">Try another severity</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="mt-6 pt-4 border-t border-border text-xs text-muted-foreground flex items-center justify-between">
            <button className="disabled:opacity-40 hover:text-foreground" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              ← Newer
            </button>
            <span>
              Page {page + 1} · {s ? nf.format(s.data_passports.pending_review) : "—"} values awaiting review
            </span>
            <button
              className="disabled:opacity-40 hover:text-foreground"
              disabled={(log.data?.length ?? 0) < PAGE}
              onClick={() => setPage((p) => p + 1)}
            >
              Older →
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
