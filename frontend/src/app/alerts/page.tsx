"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { Alert, AlertSummary } from "@/lib/types";
import { Badge, Button, Card, Empty, ErrorBox, Loading, Stat, fmt, severityTone } from "@/components/ui";
import { PageHeader } from "@/components/page-header";

const RULE_LABELS: Record<string, string> = {
  MULTI_SOURCE_DETERIORATION: "Deterioration seen in several sources",
  DANGEROUS_MED_AKI: "Nephrotoxic drug with kidney injury",
  HIGH_FALL_RISK: "High fall risk",
  CLINICAL_OUTLIER: "Implausible clinical value",
  DATA_QUALITY_CRITICAL: "Critical data quality issue",
};

export default function AlertsPage() {
  const summary = useApi<AlertSummary>("/api/alerts/summary");
  const [rule, setRule] = useState<string>("MULTI_SOURCE_DETERIORATION");
  const [showTreated, setShowTreated] = useState(false);
  const params = new URLSearchParams({ limit: "30" });
  if (rule) params.set("rule", rule);
  if (!showTreated) params.set("treated", "false");
  const alerts = useApi<Alert[]>(`/api/alerts?${params}`);
  const [busy, setBusy] = useState<string | null>(null);

  const markTreated = async (a: Alert) => {
    const key = `${a.case_id}/${a.rule_name}`;
    setBusy(key);
    try {
      await api.patch(`/api/alerts/${encodeURIComponent(a.case_id)}/${encodeURIComponent(a.rule_name)}`, { treated_by: "dashboard" });
      await Promise.all([alerts.reload(), summary.reload()]);
    } finally {
      setBusy(null);
    }
  };

  if (summary.error) return <ErrorBox error={summary.error} onRetry={summary.reload} />;

  return (
    <>
      <PageHeader
        title="Alerts"
        subtitle="Rules that cross-check sources: e.g. a fall on the motion sensor plus deterioration in the nursing notes, or a nephrotoxic drug while creatinine is rising."
      />
      {!summary.data ? (
        <Loading />
      ) : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Total alerts" value={fmt(summary.data.total_alerts)} />
          <Stat label="Critical" value={fmt(summary.data.by_severity.CRITICAL ?? 0)} />
          <Stat label="High" value={fmt(summary.data.by_severity.HIGH ?? 0)} />
          <Stat label="Treated" value={`${fmt(summary.data.treated_count)} / ${fmt(summary.data.total_alerts)}`} />
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {Object.entries(summary.data?.by_rule ?? {})
          .sort((a, b) => a[1] - b[1])
          .map(([r, n]) => (
            <button
              key={r}
              onClick={() => setRule(r)}
              className={`rounded-full px-3 py-1 text-xs ${rule === r ? "bg-sky-600 text-white" : "text-slate-300 ring-1 ring-slate-700 hover:bg-slate-800"}`}
            >
              {RULE_LABELS[r] ?? r} <span className="opacity-70">({fmt(n)})</span>
            </button>
          ))}
        <label className="ml-auto flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={showTreated} onChange={(e) => setShowTreated(e.target.checked)} />
          Show treated
        </label>
      </div>

      <div className="mt-4 space-y-3">
        {alerts.error ? (
          <ErrorBox error={alerts.error} onRetry={alerts.reload} />
        ) : alerts.loading && !alerts.data ? (
          <Loading />
        ) : !alerts.data?.length ? (
          <Empty>No alerts for this rule.</Empty>
        ) : (
          alerts.data.map((a) => {
            const key = `${a.case_id}/${a.rule_name}`;
            return (
              <Card key={key}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={severityTone(a.severity)}>{a.severity}</Badge>
                      <Link href={`/patients/${encodeURIComponent(a.case_id)}`} className="font-mono text-sm text-sky-400 hover:underline">
                        {a.case_id}
                      </Link>
                      <span className="text-sm text-slate-300">{RULE_LABELS[a.rule_name] ?? a.rule_name}</span>
                      {a.is_treated && <Badge tone="good">treated by {a.treated_by}</Badge>}
                    </div>
                    <p className="mt-1 text-sm text-slate-200">{a.message}</p>
                    {a.sources_involved?.length > 0 && (
                      <div className="mt-1 text-xs text-slate-500">Sources: {a.sources_involved.join(", ")}</div>
                    )}
                    {a.sbar && (
                      <div className="mt-2 grid gap-1 text-xs text-slate-300 sm:grid-cols-2">
                        {Object.entries(a.sbar).map(([k, v]) => (
                          <div key={k}>
                            <span className="font-semibold text-slate-400">{k}: </span>
                            {v}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {!a.is_treated && (
                    <Button variant="ghost" onClick={() => markTreated(a)} disabled={busy === key}>
                      {busy === key ? "Saving…" : "Mark treated"}
                    </Button>
                  )}
                </div>
              </Card>
            );
          })
        )}
      </div>
    </>
  );
}
