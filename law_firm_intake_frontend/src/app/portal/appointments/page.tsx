"use client";
import React, { useEffect, useState } from "react";

export default function PortalAppointmentsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const res = await fetch(`/api/portal/appointments`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setEvents(await res.json());
    } catch (e:any) {
      setError(e?.message || 'Failed to load');
    }
  }

  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);
      const res = await fetch(`/api/portal/appointments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          start_at: start || undefined,
          end_at: end || undefined,
          location: location || undefined,
        }),
      });
      if (!res.ok) throw new Error('Failed to create');
      setTitle(""); setStart(""); setEnd(""); setLocation("");
      await load();
    } catch (e:any) {
      setError(e?.message || 'Failed to create');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-semibold">Appointments</h1>

      <form onSubmit={create} className="rounded border bg-white p-4 space-y-3">
        <div className="font-medium">Book an appointment</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="border rounded px-3 py-2" placeholder="Title" value={title} onChange={e=>setTitle(e.target.value)} required />
          <input className="border rounded px-3 py-2" placeholder="Location" value={location} onChange={e=>setLocation(e.target.value)} />
          <input className="border rounded px-3 py-2" type="datetime-local" value={start} onChange={e=>setStart(e.target.value)} />
          <input className="border rounded px-3 py-2" type="datetime-local" value={end} onChange={e=>setEnd(e.target.value)} />
        </div>
        <div>
          <button disabled={saving} className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50">Create</button>
        </div>
        {error && <div className="text-sm text-red-600">{error}</div>}
      </form>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Upcoming</div>
        <div className="p-4">
          {events.length > 0 ? (
            <ul className="text-sm space-y-2">
              {events.map(ev => (
                <li key={ev.id} className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{ev.title}</div>
                    <div className="text-xs text-gray-600">{ev.location || '—'}</div>
                  </div>
                  <div className="text-xs text-gray-700">{ev.start_at ? new Date(ev.start_at).toLocaleString() : '—'}{ev.end_at ? ` - ${new Date(ev.end_at).toLocaleString()}` : ''}</div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No appointments yet.</div>
          )}
        </div>
      </section>
    </div>
  );
}
