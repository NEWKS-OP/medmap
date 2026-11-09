"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Heart, ArrowRight, Zap, Shield, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { demoLogin, validateDemoEmail, getSession, DEMO_CREDENTIALS } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Auto-login if session exists
  useEffect(() => {
    const session = getSession();
    if (session) router.replace("/overview");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!validateDemoEmail(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800)); // Simulate auth delay
    demoLogin(email);
    router.push("/overview");
  }

  function fillDemo() {
    setEmail(DEMO_CREDENTIALS.email);
    setPassword(DEMO_CREDENTIALS.password);
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left panel — branding */}
      <div className="hidden lg:flex relative flex-col justify-between p-12 bg-sidebar border-r border-border overflow-hidden">
        {/* Grid background */}
        <div className="absolute inset-0 grid-bg opacity-30" />
        {/* Glow */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />

        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/20 border border-primary/30">
              <Heart className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="font-bold text-lg tracking-tight">MediFlow</p>
              <p className="text-xs text-muted-foreground tracking-widest uppercase">Healthcare Analytics</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="text-4xl font-bold leading-tight gradient-text">
              Intelligent Patient<br />Monitoring at Scale
            </h2>
            <p className="mt-4 text-muted-foreground text-sm leading-relaxed max-w-sm">
              Real-time anomaly detection, data quality scoring, and clinical insights for modern healthcare teams.
            </p>
          </div>

          <div className="space-y-3">
            {[
              { icon: Zap, text: "Instant anomaly detection with ML-powered alerts" },
              { icon: Activity, text: "Live vitals monitoring across all wards" },
              { icon: Shield, text: "HIPAA-compliant data pipeline with audit trails" },
            ].map((item) => (
              <div key={item.text} className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 shrink-0">
                  <item.icon className="w-3.5 h-3.5 text-primary" />
                </div>
                {item.text}
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 text-xs text-muted-foreground">
          © 2026 MediFlow · Healthcare AI Platform
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex items-center justify-center p-8 bg-background">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-sm space-y-6"
        >
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-2 mb-8">
            <Heart className="w-5 h-5 text-primary" />
            <span className="font-bold">MediFlow</span>
          </div>

          {/* Demo badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs text-primary font-medium">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Demo Mode — any @email works
          </div>

          <div className="space-y-1.5">
            <h1 className="text-2xl font-bold">Sign in to MediFlow</h1>
            <p className="text-sm text-muted-foreground">
              Enter your credentials to access the dashboard.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@hospital.org"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Any password in demo mode"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>

            {error && (
              <p className="text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          {/* Quick demo login */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">or</span>
            </div>
          </div>

          <Button
            variant="outline"
            className="w-full gap-2 border-primary/30 text-primary hover:bg-primary/10 hover:text-primary"
            onClick={fillDemo}
            type="button"
          >
            <Zap className="h-3.5 w-3.5" />
            Use Demo Credentials
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Don&apos;t have an account?{" "}
            <a href="/signup" className="text-primary hover:underline">
              Sign up
            </a>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
