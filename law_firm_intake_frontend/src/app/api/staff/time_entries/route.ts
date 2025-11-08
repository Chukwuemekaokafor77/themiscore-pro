import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url);
    const qs = url.search;
    const teamAuth = req.cookies.get("team_auth")?.value;
    const auth = teamAuth ? `Basic ${teamAuth}` : undefined;
    const res = await fetch(`${FLASK_BASE}/api/time_entries${qs}`, {
      headers: { ...(auth ? { Authorization: auth } : {}) },
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const teamAuth = req.cookies.get("team_auth")?.value;
    const auth = teamAuth ? `Basic ${teamAuth}` : undefined;
    const body = await req.text();
    const res = await fetch(`${FLASK_BASE}/api/time_entries`, {
      method: "POST",
      headers: { ...(auth ? { Authorization: auth } : {}), "Content-Type": "application/json" },
      body,
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
