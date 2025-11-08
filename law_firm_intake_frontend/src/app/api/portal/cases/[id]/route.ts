import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const id = params.id;
    const res = await fetch(`${FLASK_BASE}/api/portal/cases/${encodeURIComponent(id)}`, {
      method: "GET",
      // portal cookie not required for server-to-server when behind same origin, but include to be safe
      headers: {},
      cache: "no-store",
      credentials: "include",
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
