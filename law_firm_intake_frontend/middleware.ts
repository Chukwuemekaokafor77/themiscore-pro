import { NextResponse, NextRequest } from "next/server";

export async function middleware(req: NextRequest) {
  const url = new URL(req.nextUrl);
  // Protect staff routes under /(auth)
  const isProtected = url.pathname.startsWith("/(") || url.pathname.startsWith("/%28auth%29");
  // In app router, the segment name is literal: /(auth)/...
  if (url.pathname.startsWith("/(auth)")) {
    try {
      const probe = await fetch(`${url.origin}/api/session`, {
        headers: { cookie: req.headers.get("cookie") || "" },
        cache: "no-store",
      });
      if (probe.status === 204) {
        return NextResponse.next();
      }
      return NextResponse.redirect(new URL("/login", url));
    } catch {
      return NextResponse.redirect(new URL("/login", url));
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/(auth)/(.*)",
  ],
};
