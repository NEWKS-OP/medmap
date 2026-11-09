"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getSession, clearSession, DemoUser } from "@/lib/auth";

export function useAuth() {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const session = getSession();
    setUser(session);
    setLoading(false);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    router.push("/login");
  }, [router]);

  const refresh = useCallback(() => {
    setUser(getSession());
  }, []);

  return { user, loading, logout, refresh };
}
