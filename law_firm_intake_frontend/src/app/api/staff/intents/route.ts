import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function GET(req: NextRequest) {
  try {
    const teamAuth = req.cookies.get("team_auth")?.value;
    const auth = teamAuth ? `Basic ${teamAuth}` : undefined;
    const res = await fetch(`${FLASK_BASE}/api/intents`, {
      headers: { ...(auth ? { Authorization: auth } : {}) },
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
