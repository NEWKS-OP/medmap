import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({
  title,
  action,
  children,
  className,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("rounded-xl border border-slate-800 bg-slate-900/60 p-4", className)}>
      {(title || action) && (
        <div className="mb-3 flex items-center justify-between gap-2">
          {title && <h2 className="text-sm font-semibold text-slate-200">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-50">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

const TONES: Record<string, string> = {
  neutral: "bg-slate-800 text-slate-300",
  good: "bg-emerald-500/15 text-emerald-300",
  warn: "bg-amber-500/15 text-amber-300",
  bad: "bg-rose-500/15 text-rose-300",
  info: "bg-sky-500/15 text-sky-300",
};

export function Badge({ tone = "neutral", children }: { tone?: keyof typeof TONES | string; children: ReactNode }) {
  return (
    <span className={clsx("inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium", TONES[tone] ?? TONES.neutral)}>
      {children}
    </span>
  );
}

export function severityTone(sev?: string | null) {
  const s = (sev || "").toUpperCase();
  if (s === "CRITICAL" || s === "HH" || s === "LL") return "bad";
  if (s === "HIGH" || s === "H" || s === "L") return "warn";
  if (s === "MEDIUM") return "info";
  return "neutral";
}

export function scoreTone(score?: number | null) {
  if (score == null) return "neutral";
  if (score >= 90) return "good";
  if (score >= 70) return "warn";
  return "bad";
}

export function Button({
  children,
  onClick,
  disabled,
  variant = "primary",
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "ghost" | "danger";
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "rounded-md px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-sky-600 text-white hover:bg-sky-500",
        variant === "ghost" && "border border-slate-700 text-slate-200 hover:bg-slate-800",
        variant === "danger" && "bg-rose-600 text-white hover:bg-rose-500",
      )}
    >
      {children}
    </button>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="py-6 text-sm text-slate-400">{label}</div>;
}

export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-200">
      <div className="font-medium">Could not reach the API.</div>
      <div className="mt-1 break-all text-rose-300/80">{error}</div>
      <div className="mt-2 text-rose-300/80">
        Is the backend running? <code>cd medmap &amp;&amp; uvicorn api.main:app --port 8000</code>
      </div>
      {onRetry && (
        <button className="mt-2 underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-6 text-center text-sm text-slate-500">{children}</div>;
}

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            {head.map((h, i) => (
              <th key={i} className="px-2 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/70">{children}</tbody>
      </table>
    </div>
  );
}

export function fmt(n: unknown, digits = 0): string {
  if (n === null || n === undefined || n === "") return "—";
  const v = typeof n === "number" ? n : Number(n);
  if (Number.isNaN(v)) return String(n);
  return v.toLocaleString("en-US", { maximumFractionDigits: digits });
}
