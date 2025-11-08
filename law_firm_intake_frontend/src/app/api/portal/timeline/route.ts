import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url);
    const qs = url.search ? url.search : "";
    const cookieHeader = req.headers.get("cookie") || undefined;
    const res = await fetch(`${FLASK_BASE}/api/portal/timeline${qs}`, {
      method: "GET",
      headers: {
        ...(cookieHeader ? { cookie: cookieHeader } : {}),
      },
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
