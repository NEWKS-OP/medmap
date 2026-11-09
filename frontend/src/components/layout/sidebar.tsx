"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  BarChart3,
  Activity,
  LogOut,
  Heart,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Settings,
  Bell,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useApi } from "@/hooks/use-api";
import type { DashboardOverview } from "@/types/medmap";

const NAV_ITEMS = [
  {
    href: "/overview",
    label: "Overview",
    icon: LayoutDashboard,
    description: "Dashboard summary",
  },
  {
    href: "/patients",
    label: "Patients",
    icon: Users,
    description: "Patient monitoring",
    badgeVariant: "critical" as const,
  },
  {
    href: "/analytics",
    label: "Data Quality",
    icon: BarChart3,
    description: "Sources and issues",
  },
  {
    href: "/activity",
    label: "Audit Trail",
    icon: Activity,
    description: "Changes and corrections",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const initials = user?.name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) ?? "U";

  const overview = useApi<DashboardOverview>("/api/dashboard/overview");
  const activeAlerts = overview.data?.kpis.clinical_alerts ?? 0;

  return (
    <aside
      className={cn(
        "relative flex flex-col h-screen border-r border-sidebar-border bg-sidebar transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-sidebar-border shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/20 border border-primary/30 shrink-0">
          <Heart className="w-4 h-4 text-primary" />
        </div>
        {!collapsed && (
          <div>
            <p className="text-sm font-bold tracking-tight text-foreground">MediFlow</p>
            <p className="text-[10px] text-muted-foreground tracking-widest uppercase">Analytics</p>
          </div>
        )}
      </div>

      {/* Alerts banner */}
      {!collapsed && activeAlerts > 0 && (
        <div className="mx-3 mt-3 flex items-center gap-2 rounded-lg border border-anomaly/30 bg-anomaly/10 px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5 text-anomaly shrink-0 anomaly-pulse" />
          <p className="text-xs text-anomaly font-medium">
            {activeAlerts} clinical alert{activeAlerts > 1 ? "s" : ""}
          </p>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {!collapsed && (
          <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            Navigation
          </p>
        )}
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150",
                isActive
                  ? "bg-primary/15 text-primary border border-primary/20"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <Icon
                className={cn(
                  "shrink-0 transition-colors",
                  collapsed ? "w-5 h-5" : "w-4 h-4",
                  isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              {!collapsed && (
                <>
                  <span className="flex-1 font-medium">{item.label}</span>
                  {item.href === "/patients" && activeAlerts > 0 && (
                    <Badge variant={item.badgeVariant ?? "default"} className="text-[10px] px-1.5 py-0">
                      {activeAlerts}
                    </Badge>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      <Separator className="bg-sidebar-border" />

      {/* User section */}
      <div className={cn("p-3", collapsed ? "flex justify-center" : "")}>
        {!collapsed ? (
          <div className="flex items-center gap-3 rounded-lg p-2 hover:bg-secondary transition-colors">
            <Avatar className="w-8 h-8 shrink-0">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold truncate">{user?.name ?? "User"}</p>
              <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="p-1 rounded hover:text-destructive text-muted-foreground transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={logout}
            title="Sign out"
            className="p-2 rounded-lg hover:bg-secondary hover:text-destructive text-muted-foreground transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="absolute -right-3 top-20 z-10 flex items-center justify-center w-6 h-6 rounded-full bg-secondary border border-border text-muted-foreground hover:text-foreground transition-colors"
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3" />
        ) : (
          <ChevronLeft className="w-3 h-3" />
        )}
      </button>
    </aside>
  );
}
