"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Search, Filter, AlertTriangle, CheckCircle2,
  AlertCircle, Info, ChevronUp, ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ApiError, LoadingState } from "@/components/dashboard/api-state";
import { useApi } from "@/hooks/use-api";
import { AnomalyLevel } from "@/types";
import type { MonitorPatient, MonitorResponse } from "@/types/medmap";

const ANOMALY_VARIANTS: Record<AnomalyLevel, "critical" | "high" | "medium" | "low" | "none"> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  none: "none",
};

const STATUS_COLORS: Record<MonitorPatient["status"], string> = {
  critical: "text-anomaly bg-anomaly/10 border-anomaly/30",
  monitoring: "text-warning bg-warning/10 border-warning/30",
  stable: "text-success bg-success/10 border-success/30",
  discharged: "text-muted-foreground bg-muted/30 border-border",
};

const DATA_QUALITY_ICONS: Record<string, React.ElementType> = {
  complete: CheckCircle2,
  missing: AlertCircle,
  inconsistent: AlertTriangle,
  outdated: Info,
};

const DATA_QUALITY_COLORS: Record<string, string> = {
  complete: "text-success",
  missing: "text-warning",
  inconsistent: "text-anomaly",
  outdated: "text-muted-foreground",
};

// Lab flags from the source systems: H/L = outside reference range, HH/LL = critical
function flagClass(flag: string | null | undefined): string {
  const f = (flag || "").toUpperCase();
  if (f === "HH" || f === "LL") return "text-anomaly font-bold";
  if (f === "H" || f === "L") return "text-warning font-semibold";
  return "text-foreground";
}

function LabCell({ lab }: { lab?: { value: string | null; flag: string | null } }) {
  if (!lab || lab.value == null) return <span className="text-muted-foreground/50">—</span>;
  return (
    <span className={flagClass(lab.flag)}>
      {lab.value}
      {lab.flag && <sup className="ml-0.5 text-[9px]">{lab.flag}</sup>}
    </span>
  );
}

export default function PatientsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [filterAnomaly, setFilterAnomaly] = useState<AnomalyLevel | "all">("all");

  useEffect(() => {
    const t = setTimeout(() => setQuery(search.trim()), 250);
    return () => clearTimeout(t);
  }, [search]);

  const params = new URLSearchParams({ limit: "60" });
  if (query) params.set("q", query);
  if (filterAnomaly !== "all") params.set("level", filterAnomaly);
  const monitor = useApi<MonitorResponse>(`/api/dashboard/patients?${params}`);

  if (monitor.error) return <ApiError error={monitor.error} onRetry={monitor.reload} />;
  const counts = monitor.data?.counts ?? {};
  const filtered = monitor.data?.patients ?? [];

  return (
    <div className="space-y-4 pb-8">
      {/* Summary row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(["critical", "high", "medium", "stable"] as const).map((level) => {
          const count = level === "stable" ? counts.none ?? 0 : counts[level] ?? 0;
          return (
            <motion.div key={level} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              <Card
                className={cn(
                  "cursor-pointer transition-all hover:border-primary/30",
                  filterAnomaly === level ? "border-primary/50 bg-primary/5" : ""
                )}
                onClick={() =>
                  setFilterAnomaly((f) => (f === (level === "stable" ? "none" : level) ? "all" : (level === "stable" ? "none" : level)))
                }
              >
                <CardContent className="p-4">
                  <p className="text-2xl font-bold tabular-nums">{count}</p>
                  <p className="text-xs text-muted-foreground capitalize mt-0.5">
                    {level === "stable" ? "No clinical alert" : `${level} alert`}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Table */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <CardTitle className="flex-1">Patient Monitor</CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <Input
                  placeholder="Case, ward, diagnosis…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 h-8 w-48 text-xs"
                />
              </div>
              {filterAnomaly !== "all" && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => setFilterAnomaly("all")}
                >
                  Clear filter
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Case</th>
                  <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Patient</th>
                  <th className="text-left px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Ward</th>
                  <th className="text-right px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider" title="Creatinine mg/dL">Creat</th>
                  <th className="text-right px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider" title="C-reactive protein mg/L">CRP</th>
                  <th className="text-right px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider" title="Hemoglobin g/dL">Hb</th>
                  <th className="text-right px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider" title="Potassium mmol/L">K</th>
                  <th className="text-right px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider" title="Falls detected by motion sensor">Falls</th>
                  <th className="text-center px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Alerts</th>
                  <th className="text-center px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Quality</th>
                  <th className="text-center px-4 py-3 text-muted-foreground font-semibold uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((patient, i) => {
                  const QIcon = DATA_QUALITY_ICONS[patient.data_quality];
                  return (
                    <motion.tr
                      key={patient.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: Math.min(i, 20) * 0.02 }}
                      onClick={() => router.push(`/patients/${encodeURIComponent(patient.id)}`)}
                      className={cn(
                        "border-b border-border/50 hover:bg-muted/20 transition-colors cursor-pointer",
                        patient.anomaly_level === "critical" && "bg-anomaly/5"
                      )}
                    >
                      <td className="px-4 py-3 font-mono text-muted-foreground">
                        <Link href={`/patients/${encodeURIComponent(patient.id)}`} className="hover:text-primary" onClick={(e) => e.stopPropagation()}>
                          {patient.case_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-semibold">
                            {patient.age ?? "?"}y · {patient.gender ?? "?"}
                            {patient.diagnosis_code && <span className="ml-1.5 font-mono font-normal text-muted-foreground">{patient.diagnosis_code}</span>}
                          </p>
                          <p className="text-muted-foreground text-[10px] max-w-[220px] truncate">{patient.diagnosis ?? "No diagnosis record"}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{patient.ward ?? "—"}</td>
                      <td className="px-4 py-3 text-right tabular-nums"><LabCell lab={patient.labs.creatinine} /></td>
                      <td className="px-4 py-3 text-right tabular-nums"><LabCell lab={patient.labs.crp} /></td>
                      <td className="px-4 py-3 text-right tabular-nums"><LabCell lab={patient.labs.hemoglobin} /></td>
                      <td className="px-4 py-3 text-right tabular-nums"><LabCell lab={patient.labs.potassium} /></td>
                      <td className={cn("px-4 py-3 text-right tabular-nums", patient.falls > 0 ? "text-anomaly font-semibold" : "text-muted-foreground")}>
                        {patient.motion_records ? patient.falls : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1 justify-center">
                          {patient.anomaly_level === "none" ? (
                            <Badge variant="none">None</Badge>
                          ) : (
                            <>
                              <Badge variant={ANOMALY_VARIANTS[patient.anomaly_level]} className="capitalize">
                                {patient.anomaly_level}
                              </Badge>
                              {patient.anomaly_flags.slice(0, 1).map((f) => (
                                <Badge key={f} variant="outline" className="text-[9px]">{f}</Badge>
                              ))}
                            </>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col items-center gap-1">
                          <div className={cn("flex items-center gap-1", DATA_QUALITY_COLORS[patient.data_quality])}>
                            <QIcon className="w-3 h-3" />
                            <span className="capitalize text-[10px]">{{ complete: "clean", missing: "to review", inconsistent: "many issues" }[patient.data_quality]}</span>
                          </div>
                          {patient.issues > 0 && (
                            <span className="text-[9px] text-muted-foreground">{patient.issues} flagged</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-center">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded-full border text-[10px] font-semibold capitalize",
                              STATUS_COLORS[patient.status]
                            )}
                          >
                            {patient.status}
                          </span>
                        </div>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
            {!monitor.data && <LoadingState label="Loading patients…" />}
            {monitor.data && filtered.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Search className="w-8 h-8 text-muted-foreground mb-3" />
                <p className="text-sm font-medium">No patients found</p>
                <p className="text-xs text-muted-foreground">Try a different search or filter</p>
              </div>
            )}
          </div>
          <div className="px-4 py-3 border-t border-border text-xs text-muted-foreground">
            Showing {filtered.length} of {monitor.data?.matched ?? 0} matching cases ({monitor.data?.total ?? 0} total) · sorted by alert severity, then data coverage · click a row for the patient trajectory
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
