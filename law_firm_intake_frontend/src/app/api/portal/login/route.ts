import { NextRequest, NextResponse } from "next/server";

const FLASK_BASE = process.env.FLASK_BASE_URL || "http://localhost:5000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.text();
    const res = await fetch(`${FLASK_BASE}/api/portal/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const text = await res.text();
    const out = new NextResponse(text, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") || "application/json" },
    });
    // Mirror Flask session cookie into a Next cookie for later proxying
    const setCookie = res.headers.get("set-cookie");
    if (setCookie) {
      // Try to extract the session cookie value (format: session=<val>; ...)
      const m = /\bsession=([^;]+)/.exec(setCookie);
      if (m && m[1]) {
        const secure = process.env.NODE_ENV === 'production';
        out.cookies.set("flask_portal_session", m[1], {
          httpOnly: true,
          sameSite: "lax",
          secure,
          path: "/",
        });
      }
    }
    return out;
  } catch (e) {
    return NextResponse.json({ error: "failed" }, { status: 500 });
  }
}
