"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MetricLineChart } from "@/components/charts/line-chart";
import { MetricBarChart } from "@/components/charts/bar-chart";
import { MetricPieChart } from "@/components/charts/pie-chart";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { ApiError, LoadingState } from "@/components/dashboard/api-state";
import { useApi } from "@/hooks/use-api";
import type { ErrorCategory, MonitorResponse, QualityScore } from "@/types/medmap";

const nf = new Intl.NumberFormat("en-US");

function sourceGroup(file: string) {
  const m = file.match(/^clinic_(\d)/);
  return m ? `Clinic ${m[1]}` : "Central export";
}

function FadeCard({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export default function AnalyticsPage() {
  const scoresApi = useApi<QualityScore[]>("/api/overview/quality-scores");
  const categoriesApi = useApi<ErrorCategory[]>("/api/quality/error-categories");
  const monitorApi = useApi<MonitorResponse>("/api/dashboard/patients?limit=1");

  if (scoresApi.error) return <ApiError error={scoresApi.error} onRetry={scoresApi.reload} />;
  if (!scoresApi.data) return <LoadingState label="Loading data quality…" />;

  const scores = scoresApi.data.filter((q) => q.source_file !== "cross_source");
  const counts = monitorApi.data?.counts ?? {};
  const totalPatients = monitorApi.data?.total ?? 0;
  const anomalyBreakdown = [
    { label: "Critical", count: counts.critical ?? 0, color: "bg-anomaly", textColor: "text-anomaly" },
    { label: "High", count: counts.high ?? 0, color: "bg-orange-500", textColor: "text-orange-400" },
    { label: "Medium", count: counts.medium ?? 0, color: "bg-yellow-500", textColor: "text-yellow-400" },
    { label: "Low", count: counts.low ?? 0, color: "bg-blue-500", textColor: "text-blue-400" },
    { label: "None", count: counts.none ?? 0, color: "bg-success", textColor: "text-success" },
  ];

  const byGroup: Record<string, { group: string; imported: number; quarantined: number }> = {};
  for (const q of scores) {
    const g = (byGroup[sourceGroup(q.source_file)] ??= { group: sourceGroup(q.source_file), imported: 0, quarantined: 0 });
    g.imported += q.rows_imported;
    g.quarantined += q.rows_quarantined;
  }
  const groupData = Object.values(byGroup).sort((a, b) => a.group.localeCompare(b.group));

  const totals = scores.reduce(
    (t, q) => ({
      imported: t.imported + q.rows_imported,
      quarantined: t.quarantined + q.rows_quarantined,
      fixed: t.fixed + q.values_auto_corrected,
    }),
    { imported: 0, quarantined: 0, fixed: 0 }
  );
  const cleanRows = Math.max(0, totals.imported - totals.fixed);
  const qualityPie = [
    { name: "Clean as received", value: cleanRows, fill: "#22c55e" },
    { name: "Auto-corrected", value: totals.fixed, fill: "#3b82f6" },
    { name: "Quarantined", value: totals.quarantined, fill: "#ef4444" },
  ];
  const pieTotal = qualityPie.reduce((s, p) => s + p.value, 0);
  const worst = [...scores].sort((a, b) => a.score - b.score).slice(0, 10);

  return (
    <div className="space-y-6 pb-8">
      {/* Anomaly breakdown header */}
      <FadeCard delay={0}>
        <Card>
          <CardHeader className="pb-4">
            <CardTitle>Clinical Alert Breakdown</CardTitle>
            <CardDescription>Cases by most severe cross-source alert ({nf.format(totalPatients)} cases with clinical data)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-4">
              {anomalyBreakdown.map((item) => (
                <div key={item.label} className="text-center space-y-2">
                  <p className={cn("text-2xl font-bold tabular-nums", item.textColor)}>{item.count}</p>
                  <Progress
                    value={totalPatients ? (item.count / totalPatients) * 100 : 0}
                    className={cn("h-1.5", `[&>div]:${item.color}`)}
                  />
                  <p className="text-[10px] text-muted-foreground font-medium">{item.label}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </FadeCard>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <FadeCard delay={0.1}>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Lowest-quality Sources</CardTitle>
              <CardDescription>Quality score per input file (0–100), worst first</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricBarChart
                data={worst.map((q) => ({ file: q.source_file.replace(/\.(csv|xlsx|pdf)$/, ""), score: q.score }))}
                xKey="file"
                layout="vertical"
                height={260}
                series={[{ key: "score", label: "Score", color: "hsl(210, 100%, 60%)" }]}
              />
            </CardContent>
          </Card>
        </FadeCard>

        <FadeCard delay={0.15}>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Issue Types</CardTitle>
              <CardDescription>Most frequent problems found while cleaning, by severity</CardDescription>
            </CardHeader>
            <CardContent>
              {!categoriesApi.data ? (
                <LoadingState />
              ) : (
                <MetricBarChart
                  data={categoriesApi.data.slice(0, 8).map((c) => ({
                    type: c.error_type.replace(/_/g, " ").toLowerCase(),
                    critical: c.by_severity.CRITICAL ?? 0,
                    high: c.by_severity.HIGH ?? 0,
                    medium: c.by_severity.MEDIUM ?? 0,
                    low: c.by_severity.LOW ?? 0,
                  }))}
                  xKey="type"
                  layout="vertical"
                  height={260}
                  series={[
                    { key: "critical", label: "Critical", color: "hsl(0, 84%, 60%)", stackId: "a" },
                    { key: "high", label: "High", color: "hsl(24, 95%, 58%)", stackId: "a" },
                    { key: "medium", label: "Medium", color: "hsl(38, 92%, 50%)", stackId: "a" },
                    { key: "low", label: "Low", color: "hsl(210, 100%, 60%)", stackId: "a" },
                  ]}
                />
              )}
            </CardContent>
          </Card>
        </FadeCard>

        <FadeCard delay={0.2}>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Rows Imported vs Quarantined</CardTitle>
              <CardDescription>Per data origin — central export and the four clinics</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricBarChart
                data={groupData}
                xKey="group"
                layout="vertical"
                height={240}
                series={[
                  { key: "imported", label: "Imported", color: "hsl(210, 100%, 60%)", stackId: "s" },
                  { key: "quarantined", label: "Quarantined", color: "hsl(0, 84%, 60%)", stackId: "s" },
                ]}
              />
            </CardContent>
          </Card>
        </FadeCard>

        {/* Data Quality + Pie */}
        <FadeCard delay={0.25}>
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Data Quality Report</CardTitle>
                  <CardDescription>What happened to the imported rows</CardDescription>
                </div>
                <Badge variant={totals.quarantined / Math.max(1, pieTotal) > 0.05 ? "warning" : "success"}>
                  {Math.round((1 - totals.quarantined / Math.max(1, pieTotal)) * 100)}% Usable
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-start gap-6">
                <div className="flex-1">
                  <MetricPieChart data={qualityPie} height={200} />
                </div>
                <div className="space-y-3 py-2 shrink-0">
                  {qualityPie.map((p) => ({ label: p.name, count: p.value, color: p.fill })).concat([
                  ]).map((item) => (
                    <div key={item.label} className="flex items-center gap-2 text-xs">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: item.color }} />
                      <span className="text-muted-foreground w-28">{item.label}</span>
                      <span className="font-semibold tabular-nums">{nf.format(item.count)}</span>
                    </div>
                  ))}
                  <div className="pt-2 border-t border-border">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="w-2.5 h-2.5" />
                      <span className="text-muted-foreground w-28">Total</span>
                      <span className="font-bold tabular-nums">{nf.format(pieTotal)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </FadeCard>
      </div>

      {/* Missing data detail table */}
      <FadeCard delay={0.3}>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Data Quality by Source File</CardTitle>
            <CardDescription>Every input file, from the worst score to the best</CardDescription>
          </CardHeader>
          <CardContent>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left pb-3 text-muted-foreground font-semibold uppercase tracking-wider">Source</th>
                  <th className="text-left pb-3 text-muted-foreground font-semibold uppercase tracking-wider">Origin</th>
                  <th className="text-left pb-3 text-muted-foreground font-semibold uppercase tracking-wider">Score</th>
                  <th className="text-right pb-3 text-muted-foreground font-semibold uppercase tracking-wider">Imported</th>
                  <th className="text-right pb-3 text-muted-foreground font-semibold uppercase tracking-wider">Quarantined</th>
                  <th className="text-left pb-3 pl-6 text-muted-foreground font-semibold uppercase tracking-wider">Main issue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {[...scores].sort((a, b) => a.score - b.score).map((q) => {
                  const top = Object.entries(q.errors_by_category).sort((a, b) => b[1] - a[1])[0];
                  return (
                    <tr key={q.source_file} className="hover:bg-muted/20">
                      <td className="py-2.5 font-mono">{q.source_file}</td>
                      <td className="py-2.5 text-muted-foreground">{sourceGroup(q.source_file)}</td>
                      <td className="py-2.5">
                        <Badge variant={q.score >= 90 ? "success" : q.score >= 70 ? "warning" : "destructive"}>{q.score}</Badge>
                      </td>
                      <td className="py-2.5 text-right tabular-nums">{nf.format(q.rows_imported)}</td>
                      <td className="py-2.5 text-right tabular-nums">{nf.format(q.rows_quarantined)}</td>
                      <td className="py-2.5 pl-6 text-muted-foreground">
                        {top ? `${top[0].replace(/_/g, " ").toLowerCase()} (${nf.format(top[1])})` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </FadeCard>
    </div>
  );
}
