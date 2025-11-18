// src/app/api/staff/intake/analyze/route.ts
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const staffBase = process.env.FLASK_BASE_URL || "http://localhost:5000";
const ENV_BASIC = `Basic ${Buffer.from(
  `${process.env.FLASK_BASIC_USER ?? "demo"}:${process.env.FLASK_BASIC_PASS ?? "themiscore123"}`
).toString("base64")}`;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const text = (body?.text ?? "").trim();
    if (!text) {
      return NextResponse.json({ error: "Missing text" }, { status: 400 });
    }

    const store = await cookies();
    const teamAuth = store.get("team_auth")?.value;
    const auth = teamAuth ? `Basic ${teamAuth}` : ENV_BASIC;

    const res = await fetch(`${staffBase}/api/intake/analyze`, {
      method: "POST",
      headers: {
        Authorization: auth,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
    });

    if (res.status === 401 || res.status === 403) {
      return NextResponse.json({ error: "unauthorized" }, { status: res.status });
    }
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json({ error: `Backend error ${res.status}`, detail: text.slice(0, 200) }, { status: 502 });
    }

    const data = await res.json();

    // data already includes category, case_type_key, etc.
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: "Server error", detail: String(e?.message ?? e) }, { status: 500 });
  }
}