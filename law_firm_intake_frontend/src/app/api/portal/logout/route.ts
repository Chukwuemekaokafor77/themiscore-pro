import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function POST(_req: NextRequest) {
  try {
    // Call Flask logout to clear server-side session
    await fetch(`${FLASK_BASE}/portal/logout`, { method: "GET", redirect: "manual" });
    const res = NextResponse.json({ ok: true });
    // Clear mirrored cookie
    res.cookies.set("flask_portal_session", "", { httpOnly: true, sameSite: "lax", secure: true, path: "/", maxAge: 0 });
    return res;
  } catch {
    // Still clear client cookie
    const res = NextResponse.json({ ok: false }, { status: 500 });
    res.cookies.set("flask_portal_session", "", { httpOnly: true, sameSite: "lax", secure: true, path: "/", maxAge: 0 });
    return res;
  }
}
