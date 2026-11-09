import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { parseSessionCookie } from "@/lib/auth";

const PUBLIC_PATHS = ["/login", "/signup"];
const SESSION_KEY = "mediflow_session";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    // If already logged in, redirect to dashboard
    const cookie = request.cookies.get(SESSION_KEY)?.value;
    if (cookie) {
      try {
        const decoded = decodeURIComponent(cookie);
        const session = parseSessionCookie(`${SESSION_KEY}=${decoded}`);
        if (session?.email) {
          return NextResponse.redirect(new URL("/overview", request.url));
        }
      } catch {}
    }
    return NextResponse.next();
  }

  // Protect dashboard routes
  const cookie = request.cookies.get(SESSION_KEY)?.value;
  if (!cookie) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const decoded = decodeURIComponent(cookie);
    const session = parseSessionCookie(`${SESSION_KEY}=${decoded}`);
    if (!session?.email) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  } catch {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|public).*)",
  ],
};
