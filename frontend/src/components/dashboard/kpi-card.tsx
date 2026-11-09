"use client";

import { motion } from "framer-motion";
import {
  Users, AlertTriangle, Activity, Database, Zap, Heart, ClipboardCheck, Files,
  TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { KpiMetric } from "@/types";

const ICON_MAP: Record<string, React.ElementType> = {
  Users,
  AlertTriangle,
  Activity,
  Database,
  Zap,
  Heart,
  ClipboardCheck,
  Files,
};

const STATUS_STYLES = {
  good: "text-success border-success/20 bg-success/10",
  warning: "text-warning border-warning/20 bg-warning/10",
  critical: "text-anomaly border-anomaly/20 bg-anomaly/10 anomaly-pulse",
};

const STATUS_CARD_GLOW = {
  good: "glow-green",
  warning: "",
  critical: "glow-red",
};

const TREND_ICON = {
  up: TrendingUp,
  down: TrendingDown,
  flat: Minus,
};

interface KpiCardProps {
  metric: KpiMetric;
  index: number;
}

export function KpiCard({ metric, index }: KpiCardProps) {
  const Icon = metric.icon ? ICON_MAP[metric.icon] ?? Activity : Activity;
  const TrendIcon = TREND_ICON[metric.trend];

  const deltaPositive =
    (metric.trend === "up" && metric.status === "good") ||
    (metric.trend === "down" && metric.status === "critical");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
    >
      <Card
        className={cn(
          "relative overflow-hidden transition-all duration-300 hover:border-primary/30 hover:-translate-y-0.5",
          STATUS_CARD_GLOW[metric.status]
        )}
      >
        {/* Status accent bar */}
        <div
          className={cn(
            "absolute top-0 left-0 right-0 h-0.5",
            metric.status === "critical" && "bg-anomaly",
            metric.status === "warning" && "bg-warning",
            metric.status === "good" && "bg-success"
          )}
        />

        <CardContent className="p-5">
          <div className="flex items-start justify-between mb-4">
            <div
              className={cn(
                "flex items-center justify-center w-9 h-9 rounded-lg border",
                STATUS_STYLES[metric.status]
              )}
            >
              <Icon className="w-4 h-4" />
            </div>

            {/* Delta badge */}
            {metric.delta !== undefined && (
              <div
                className={cn(
                  "flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border",
                  metric.status === "critical"
                    ? "text-anomaly border-anomaly/30 bg-anomaly/10"
                    : metric.delta > 0
                    ? "text-warning border-warning/30 bg-warning/10"
                    : "text-success border-success/30 bg-success/10"
                )}
              >
                <TrendIcon className="w-3 h-3" />
                {Math.abs(metric.delta).toFixed(1)}%
              </div>
            )}
          </div>

          <p className="text-2xl font-bold tabular-nums text-foreground">
            {metric.value}
            {metric.unit && (
              <span className="text-sm font-normal text-muted-foreground ml-1">
                {metric.unit}
              </span>
            )}
          </p>
          <p className="text-xs text-muted-foreground mt-1 uppercase tracking-wider font-medium">
            {metric.label}
          </p>
          {metric.hint && <p className="text-[10px] text-muted-foreground/70 mt-1">{metric.hint}</p>}
        </CardContent>
      </Card>
    </motion.div>
  );
}
