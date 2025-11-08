import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const id = Number(params.id);
    if (!Number.isFinite(id) || id <= 0) return NextResponse.json({ error: "bad id" }, { status: 400 });
    const teamAuth = req.cookies.get("team_auth")?.value;
    const auth = teamAuth ? `Basic ${teamAuth}` : undefined;
    const body = await req.text();
    const res = await fetch(`${FLASK_BASE}/api/cases/${id}/apply_intent`, {
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
