"use client";

import { motion } from "framer-motion";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { AnomalyAlerts } from "@/components/dashboard/anomaly-alerts";
import { WardCapacity } from "@/components/dashboard/ward-capacity";
import { MetricLineChart } from "@/components/charts/line-chart";
import { MetricBarChart } from "@/components/charts/bar-chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ApiError, LoadingState } from "@/components/dashboard/api-state";
import { useApi } from "@/hooks/use-api";
import type { KpiMetric } from "@/types";
import type { ClinicalAlert, DashboardOverview } from "@/types/medmap";

const nf = new Intl.NumberFormat("en-US");

function toKpis(k: DashboardOverview["kpis"]): KpiMetric[] {
  return [
    { label: "Cases", value: nf.format(k.cases), trend: "flat", status: "good", icon: "Users", hint: `${k.sources} source files` },
    {
      label: "Clinical Alerts",
      value: k.clinical_alerts,
      trend: "flat",
      status: k.clinical_alerts > 0 ? "critical" : "good",
      icon: "AlertTriangle",
      hint: `${k.patients_with_alerts} patients`,
    },
    {
      label: "Data Quality",
      value: k.data_quality_pct,
      unit: "%",
      trend: "flat",
      status: k.data_quality_pct >= 90 ? "good" : "warning",
      icon: "Database",
      hint: "weighted source score",
    },
    { label: "Rows Imported", value: nf.format(k.rows_imported), trend: "flat", status: "good", icon: "Files" },
    { label: "Auto-corrected", value: nf.format(k.auto_corrected), trend: "flat", status: "good", icon: "Zap", hint: "values fixed by the pipeline" },
    {
      label: "Awaiting Review",
      value: nf.format(k.pending_review),
      trend: "flat",
      status: "warning",
      icon: "ClipboardCheck",
      hint: "flagged values",
    },
  ];
}

export default function OverviewPage() {
  const overview = useApi<DashboardOverview>("/api/dashboard/overview");
  const alerts = useApi<ClinicalAlert[]>("/api/dashboard/alerts?limit=25");

  if (overview.error) return <ApiError error={overview.error} onRetry={overview.reload} />;
  if (!overview.data) return <LoadingState label="Loading overview…" />;
  const o = overview.data;

  return (
    <div className="space-y-6 pb-8">
      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {toKpis(o.kpis).map((metric, i) => (
          <KpiCard key={metric.label} metric={metric} index={i} />
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Heart Rate chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Patient Movement by Hour</CardTitle>
              <CardDescription>Average movement index (0–100) from bedside motion sensors — all patients</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricLineChart
                data={o.movement_by_hour}
                series={[{ key: "avg_movement", label: "Avg movement index", color: "hsl(210, 100%, 60%)" }]}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* SpO2 chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.28 }}
        >
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Falls &amp; Bed Exits by Hour</CardTitle>
              <CardDescription>Events detected by motion sensors, summed over all patients</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricLineChart
                data={o.movement_by_hour}
                series={[
                  { key: "bed_exits", label: "Bed exits", color: "hsl(38, 92%, 50%)" },
                  { key: "falls", label: "Falls", color: "hsl(0, 84%, 60%)" },
                ]}
              />
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Anomaly by day */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.35 }}
        >
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Data Issues by Source</CardTitle>
              <CardDescription>Problems detected while cleaning, by origin and severity</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricBarChart
                data={o.issues_by_group}
                xKey="group"
                series={[
                  { key: "critical", label: "Critical", color: "hsl(0, 84%, 60%)", stackId: "a" },
                  { key: "high", label: "High", color: "hsl(24, 95%, 58%)", stackId: "a" },
                  { key: "medium", label: "Medium", color: "hsl(38, 92%, 50%)", stackId: "a" },
                  { key: "low", label: "Low", color: "hsl(210, 100%, 60%)", stackId: "a" },
                ]}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Active alerts */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.42 }}
        >
          {alerts.data ? (
            <AnomalyAlerts alerts={alerts.data} total={o.kpis.clinical_alerts} />
          ) : (
            <Card className="h-full">
              <LoadingState label="Loading alerts…" />
            </Card>
          )}
        </motion.div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Admission trend */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.48 }}
        >
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Admission Flow (14 days)</CardTitle>
              <CardDescription>Daily admissions vs discharges from the diagnosis records</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricBarChart
                data={o.admissions_by_day}
                xKey="date"
                series={[
                  { key: "admissions", label: "Admissions", color: "hsl(210, 100%, 60%)" },
                  { key: "discharges", label: "Discharges", color: "hsl(142, 71%, 45%)" },
                ]}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Ward capacity */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.54 }}
        >
          <WardCapacity wards={o.wards} />
        </motion.div>
      </div>
    </div>
  );
}
