import { NextRequest, NextResponse } from 'next/server';

const FLASK_BASE = process.env.FLASK_BASE_URL || 'http://localhost:5000';

export async function POST(req: NextRequest) {
  try {
    const { username, password } = await req.json();
    if (!username || !password) {
      return NextResponse.json({ error: 'username and password required' }, { status: 400 });
    }
    const basicToken = Buffer.from(`${username}:${password}`).toString('base64');
    // Probe Flask to verify credentials
    const probe = await fetch(`${FLASK_BASE}/api/dashboard`, {
      headers: { Authorization: `Basic ${basicToken}` },
      cache: 'no-store',
    });
    if (!probe.ok) {
      const status = probe.status;
      return NextResponse.json({ error: status === 401 ? 'unauthorized' : 'failed' }, { status });
    }
    const res = NextResponse.json({ ok: true });
    // Store only the base64 token (without the "Basic " prefix)
    res.cookies.set('team_auth', basicToken, {
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      path: '/',
      // No explicit maxAge -> session cookie; adjust if persistence desired
    });
    return res;
  } catch (e) {
    return NextResponse.json({ error: 'failed' }, { status: 500 });
  }
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set('team_auth', '', { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 0 });
  return res;
}
