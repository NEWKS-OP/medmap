"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Activity, AlertTriangle, Database, GitBranch, LayoutDashboard, Users, Wrench } from "lucide-react";

const ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/sources", label: "Sources & quality", icon: Database },
  { href: "/lineage", label: "Data lineage", icon: GitBranch },
  { href: "/patients", label: "Patients", icon: Users },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/corrections", label: "Corrections", icon: Wrench },
];

export function Nav() {
  const path = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-56 shrink-0 border-r border-slate-800 bg-slate-950 p-4 md:block">
      <div className="mb-6 flex items-center gap-2">
        <Activity className="h-5 w-5 text-sky-400" />
        <div>
          <div className="text-sm font-semibold tracking-wide">MEDMAP</div>
          <div className="text-[11px] text-slate-500">Smart health data mapping</div>
        </div>
      </div>
      <nav className="space-y-1">
        {ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm",
                active ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function MobileNav() {
  return (
    <div className="flex gap-3 overflow-x-auto border-b border-slate-800 px-4 py-2 text-sm md:hidden">
      {ITEMS.map(({ href, label }) => (
        <Link key={href} href={href} className="whitespace-nowrap text-slate-300">
          {label}
        </Link>
      ))}
    </div>
  );
}
