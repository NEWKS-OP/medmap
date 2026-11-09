"use client";

import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { AnomalyLevel } from "@/types";
import type { ClinicalAlert } from "@/types/medmap";

const LEVEL_COLORS: Record<AnomalyLevel, string> = {
  none: "text-muted-foreground",
  low: "text-blue-400",
  medium: "text-yellow-400",
  high: "text-orange-400",
  critical: "text-anomaly",
};

const LEVEL_BG: Record<AnomalyLevel, string> = {
  none: "bg-muted/30",
  low: "bg-blue-500/10 border-blue-500/20",
  medium: "bg-yellow-500/10 border-yellow-500/20",
  high: "bg-orange-500/10 border-orange-500/20",
  critical: "bg-anomaly/10 border-anomaly/30",
};

function levelOf(severity: string): AnomalyLevel {
  const s = severity.toLowerCase();
  return (["critical", "high", "medium", "low"].includes(s) ? s : "none") as AnomalyLevel;
}

interface AnomalyAlertsProps {
  alerts: (ClinicalAlert & { level?: AnomalyLevel })[];
  total?: number;
}

export function AnomalyAlerts({ alerts: raw, total }: AnomalyAlertsProps) {
  const alerts = raw.map((a) => ({ ...a, level: levelOf(a.severity) }));
  const active = alerts.filter((a) => !a.is_treated);
  const resolved = alerts.filter((a) => a.is_treated);

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-anomaly" />
            Active Alerts
          </CardTitle>
          <Badge variant="critical" className="text-[10px]">
            {total ?? active.length} active
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
        {active.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <CheckCircle className="w-8 h-8 text-success mb-2" />
            <p className="text-sm font-medium">All clear</p>
            <p className="text-xs text-muted-foreground">No active anomalies detected</p>
          </div>
        ) : (
          active.map((alert, i) => (
            <motion.div
              key={`${alert.case_id}-${alert.rule_name}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              className={cn(
                "flex items-start gap-3 rounded-lg border p-3 transition-all",
                LEVEL_BG[alert.level]
              )}
            >
              <div
                className={cn(
                  "mt-0.5 w-2 h-2 rounded-full shrink-0",
                  alert.level === "critical" && "bg-anomaly anomaly-pulse",
                  alert.level === "high" && "bg-orange-400",
                  alert.level === "medium" && "bg-yellow-400",
                  alert.level === "low" && "bg-blue-400",
                )}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <Link href={`/patients/${encodeURIComponent(alert.case_id)}`} className="text-xs font-semibold truncate hover:text-primary">
                    {alert.case_label}
                    {alert.age != null && (
                      <span className="font-normal text-muted-foreground"> · {alert.age}y {alert.gender ?? ""}</span>
                    )}
                  </Link>
                  <span className="text-[10px] text-muted-foreground shrink-0">{alert.sources_involved.join(" + ")}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  <span className={cn("font-medium", LEVEL_COLORS[alert.level])}>{alert.rule_label}</span>
                  {" "}— {alert.message}
                </p>
              </div>
            </motion.div>
          ))
        )}

        {resolved.length > 0 && (
          <>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground pt-2 pb-1">
              Resolved
            </p>
            {resolved.map((alert) => (
              <div
                key={`${alert.case_id}-${alert.rule_name}`}
                className="flex items-start gap-3 rounded-lg border border-border/50 bg-muted/20 p-3 opacity-60"
              >
                <CheckCircle className="w-3 h-3 mt-0.5 text-success shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{alert.case_label}</p>
                  <p className="text-[10px] text-muted-foreground">{alert.rule_label} — resolved</p>
                </div>
              </div>
            ))}
          </>
        )}
      </CardContent>
    </Card>
  );
}
