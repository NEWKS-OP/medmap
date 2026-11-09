"use client";

import React, { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Moon, Sun, Bell, Search, RefreshCw } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/hooks/use-api";
import type { DashboardOverview } from "@/types/medmap";

const PAGE_TITLES: Record<string, { title: string; description: string }> = {
  "/overview": { title: "Overview", description: "Harmonized data from the central export and four clinics" },
  "/patients": { title: "Patient Monitor", description: "Latest labs, sensor events and cross-source alerts" },
  "/analytics": { title: "Data Quality", description: "Source scores, issue types and quarantined rows" },
  "/activity": { title: "Audit Trail", description: "Every change the pipeline made, with manual corrections" },
};

export function Header() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    setMounted(true);
    const interval = setInterval(() => setLastUpdated(new Date()), 30000);
    return () => clearInterval(interval);
  }, []);

  const pageInfo =
    PAGE_TITLES[pathname] ??
    (pathname.startsWith("/patients/")
      ? { title: "Patient Trajectory", description: "All sources for one case on a single timeline" }
      : { title: "Dashboard", description: "" });
  const overview = useApi<DashboardOverview>("/api/dashboard/overview");
  const activeAlerts = overview.data?.kpis.clinical_alerts ?? 0;

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-background/80 backdrop-blur-sm px-6">
      <div>
        <h1 className="text-lg font-bold tracking-tight">{pageInfo.title}</h1>
        <p className="text-xs text-muted-foreground">{pageInfo.description}</p>
      </div>

      <div className="flex items-center gap-2">
        {/* Data freshness indicator */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground bg-secondary rounded-lg px-3 py-1.5">
          <span className={`inline-block w-1.5 h-1.5 rounded-full animate-pulse ${overview.error ? "bg-anomaly" : "bg-success"}`} />
          <span>{overview.error ? "API offline" : "API connected"}</span>
          <span className="text-border">·</span>
          <span>
            Updated{" "}
            {mounted
              ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : "--:--"}
          </span>
        </div>

        {/* Alerts bell */}
        <div className="relative">
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-4 w-4" />
            {activeAlerts > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-anomaly text-[9px] font-bold text-white anomaly-pulse">
                {activeAlerts > 99 ? "99+" : activeAlerts}
              </span>
            )}
          </Button>
        </div>

        {/* Theme toggle */}
        {mounted && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>
    </header>
  );
}
