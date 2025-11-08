import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function POST(req: NextRequest) {
  try {
    const teamAuth = req.cookies.get("team_auth")?.value;
    const auth = teamAuth ? `Basic ${teamAuth}` : undefined;
    const res = await fetch(`${FLASK_BASE}/api/admin/seed_intents`, {
      method: "POST",
      headers: { ...(auth ? { Authorization: auth } : {}), "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
