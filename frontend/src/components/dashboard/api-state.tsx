"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { API_URL } from "@/lib/api";

export function LoadingState({ label = "Loading data…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function ApiError({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <Card className="border-anomaly/30">
      <CardContent className="flex items-start gap-3 p-5">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-anomaly" />
        <div className="space-y-1 text-sm">
          <p className="font-semibold">Can&apos;t reach the MEDMAP API at {API_URL}</p>
          <p className="text-muted-foreground">
            Start the backend: <code className="rounded bg-muted px-1">cd medmap &amp;&amp; uvicorn api.main:app --port 8000</code>
          </p>
          <p className="break-all text-xs text-muted-foreground/70">{error}</p>
          {onRetry && (
            <button onClick={onRetry} className="text-xs text-primary underline">
              Retry
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
