import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

function remapCookie(cookieHeader?: string): string | undefined {
  if (!cookieHeader) return undefined;
  const m = /(?:^|; )flask_portal_session=([^;]+)/.exec(cookieHeader);
  if (m && m[1]) return `session=${m[1]}`;
  return cookieHeader;
}

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const cookieHeader = req.headers.get("cookie") || undefined;
    const res = await fetch(`${FLASK_BASE}/api/portal/transcripts/${params.id}`, {
      method: "GET",
      headers: {
        ...(remapCookie(cookieHeader) ? { cookie: remapCookie(cookieHeader)! } : {}),
      },
      cache: "no-store",
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
