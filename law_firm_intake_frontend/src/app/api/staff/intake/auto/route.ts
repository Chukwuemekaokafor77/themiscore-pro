import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const staffBase = process.env.FLASK_BASE_URL || "http://localhost:5000";
    const basic = `Basic ${Buffer.from(`${process.env.FLASK_BASIC_USER ?? 'demo'}:${process.env.FLASK_BASIC_PASS ?? 'themiscore123'}`).toString('base64')}`;
    const res = await fetch(`${staffBase}/api/intake/auto/staff`, {
      method: "POST",
      headers: { Authorization: basic, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") || "application/json" },
    });
  } catch (e) {
    return NextResponse.json({ error: "Proxy error" }, { status: 500 });
  }
}
