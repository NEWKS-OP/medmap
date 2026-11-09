/**
 * DEMO AUTH SYSTEM
 * ----------------
 * Temporary authentication layer for hackathon/demo purposes.
 * To re-enable Clerk: remove this file and restore Clerk provider + middleware.
 *
 * Auth strategy: Cookie-based session with JSON payload.
 */

export interface DemoUser {
  email: string;
  name: string;
  role: "admin" | "analyst" | "viewer";
  avatar?: string;
  loginTime: string;
}

const SESSION_KEY = "mediflow_session";

/** Validate demo email — any non-empty string with "@" is accepted */
export function validateDemoEmail(email: string): boolean {
  return email.length > 0 && email.includes("@");
}

/** Store session in both localStorage and a cookie (for middleware) */
export function setSession(user: DemoUser): void {
  if (typeof window === "undefined") return;
  const payload = JSON.stringify(user);
  localStorage.setItem(SESSION_KEY, payload);
  // Cookie for SSR/middleware access (no httpOnly for demo)
  document.cookie = `${SESSION_KEY}=${encodeURIComponent(payload)}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

/** Get current session */
export function getSession(): DemoUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as DemoUser;
  } catch {
    return null;
  }
}

/** Clear session from localStorage and cookie */
export function clearSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SESSION_KEY);
  document.cookie = `${SESSION_KEY}=; path=/; max-age=0`;
}

/** Parse cookie from a cookie header string (used in middleware) */
export function parseSessionCookie(cookieHeader: string): DemoUser | null {
  try {
    const match = cookieHeader
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith(`${SESSION_KEY}=`));
    if (!match) return null;
    const encoded = match.split("=").slice(1).join("=");
    return JSON.parse(decodeURIComponent(encoded)) as DemoUser;
  } catch {
    return null;
  }
}

/** Login with demo credentials */
export function demoLogin(email: string, name?: string): DemoUser {
  const user: DemoUser = {
    email,
    name: name || email.split("@")[0].replace(/\./g, " "),
    role: "analyst",
    loginTime: new Date().toISOString(),
  };
  setSession(user);
  return user;
}

/** Quick-fill demo credentials */
export const DEMO_CREDENTIALS = {
  email: "demo@mediflow.ai",
  password: "demo",
  name: "Demo User",
};
