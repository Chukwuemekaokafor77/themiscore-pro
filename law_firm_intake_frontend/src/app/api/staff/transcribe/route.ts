import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("audio_file");
    if (!file || !(file instanceof Blob)) {
      return NextResponse.json({ error: "Missing audio_file" }, { status: 400 });
    }
    const staffBase = process.env.FLASK_BASE_URL || "http://localhost:5000";
    const basic = `Basic ${Buffer.from(`${process.env.FLASK_BASIC_USER ?? 'demo'}:${process.env.FLASK_BASIC_PASS ?? 'themiscore123'}`).toString('base64')}`;
    const fd = new FormData();
    fd.append("audio_file", file, (file as any).name || "recording.webm");
    const res = await fetch(`${staffBase}/api/transcribe`, {
      method: "POST",
      headers: { Authorization: basic },
      body: fd as any,
    });
    const text = await res.text();
    return new NextResponse(text, { status: res.status, headers: { "content-type": res.headers.get("content-type") || "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: "Proxy error" }, { status: 500 });
  }
}
