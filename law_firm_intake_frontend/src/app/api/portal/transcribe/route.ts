import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

function remapCookie(cookieHeader?: string): string | undefined {
  if (!cookieHeader) return undefined;
  const m = /(?:^|; )flask_portal_session=([^;]+)/.exec(cookieHeader);
  if (m && m[1]) return `session=${m[1]}`;
  return cookieHeader;
}

export async function POST(req: NextRequest) {
  try {
    const cookieHeader = req.headers.get("cookie") || undefined;
    const contentType = req.headers.get("content-type") || undefined;
    const body = await req.arrayBuffer();
    const res = await fetch(`${FLASK_BASE}/api/portal/transcribe`, {
      method: "POST",
      headers: {
        ...(contentType ? { "content-type": contentType } : {}),
        ...(remapCookie(cookieHeader) ? { cookie: remapCookie(cookieHeader)! } : {}),
      },
      body: Buffer.from(body),
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
