"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type Entry = { id:number; date:string|null; duration_minutes:number; hourly_rate:number; amount:number; description:string|null; created_at:string|null };

export default function AddTimeEntryForm({ caseId }: { caseId: number }) {
  const [date, setDate] = useState<string>(new Date().toISOString().slice(0,10));
  const [hours, setHours] = useState<string>("1.0");
  const [rate, setRate] = useState<string>("150");
  const [desc, setDesc] = useState<string>("");
  const [pending, startTransition] = useTransition();
  const [msg, setMsg] = useState<string | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const router = useRouter();

  async function loadEntries() {
    try {
      const res = await fetch(`/api/staff/time_entries?case_id=${caseId}`, { cache: 'no-store' });
      if (!res.ok) return;
      const items = await res.json();
      setEntries(items.slice(0, 5));
    } catch {}
  }

  useEffect(() => { loadEntries(); }, [caseId]);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    startTransition(async () => {
      try {
        const res = await fetch('/api/staff/time_entries', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ case_id: caseId, hours: Number(hours), rate: Number(rate), description: desc, date }),
        });
        if (!res.ok) { setMsg(`Failed (${res.status})`); return; }
        setMsg('Time entry added.');
        setDesc('');
        await loadEntries();
        router.refresh();
      } catch {
        setMsg('Request failed');
      }
    });
  }

  return (
    <div className="rounded border bg-white p-4">
      <div className="text-sm font-medium mb-3">Add Time Entry</div>
      <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600">Date</label>
          <input type="date" className="border rounded px-2 py-1" value={date} onChange={e=>setDate(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600">Hours</label>
          <input type="number" min="0" step="0.1" className="border rounded px-2 py-1" value={hours} onChange={e=>setHours(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600">Rate</label>
          <input type="number" min="0" step="0.01" className="border rounded px-2 py-1" value={rate} onChange={e=>setRate(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2">
          <label className="text-xs text-gray-600">Description</label>
          <textarea className="border rounded px-2 py-1" rows={3} value={desc} onChange={e=>setDesc(e.target.value)} />
        </div>
        <div className="sm:col-span-2 flex items-center gap-2">
          <button className="border rounded px-3 py-1 bg-black text-white text-sm" disabled={pending}>
            {pending ? 'Saving...' : 'Add Time'}
          </button>
          {msg && <span className="text-xs text-gray-600">{msg}</span>}
        </div>
      </form>
      {entries.length > 0 && (
        <div className="mt-4">
          <div className="text-sm font-medium mb-2">Recent Entries</div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-left"><tr><th className="px-2 py-1">Date</th><th className="px-2 py-1">Hours</th><th className="px-2 py-1">Rate</th><th className="px-2 py-1">Amount</th><th className="px-2 py-1">Description</th></tr></thead>
              <tbody>
                {entries.map(e => (
                  <tr key={e.id} className="border-t">
                    <td className="px-2 py-1">{e.date ? new Date(e.date).toLocaleDateString() : '—'}</td>
                    <td className="px-2 py-1">{(e.duration_minutes/60).toFixed(2)}</td>
                    <td className="px-2 py-1">${e.hourly_rate.toFixed(2)}</td>
                    <td className="px-2 py-1">${e.amount.toFixed(2)}</td>
                    <td className="px-2 py-1">{e.description ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
