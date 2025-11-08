"use client";
import React, { useEffect, useMemo, useState } from "react";

type TimelineItem = {
  type: "status_change" | "message" | "document" | "invoice" | "payment";
  case_id: number | null;
  at: string | null;
  data: any;
};

export default function PortalTimelinePage() {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [caseIdFilter, setCaseIdFilter] = useState<string>("");
  const [cases, setCases] = useState<Array<{ id:number; title:string }>>([]);

  const filtered = useMemo(() => {
    if (!caseIdFilter) return items;
    const cid = Number(caseIdFilter);
    return items.filter(i => i.case_id === cid);
  }, [items, caseIdFilter]);

  async function load(reset = true) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (caseIdFilter) params.set('case_id', caseIdFilter);
      params.set('page', String(reset ? 1 : page + 1));
      params.set('per_page', '25');
      const qs = `?${params.toString()}`;
      const res = await fetch(`/api/portal/timeline${qs}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      const newItems = Array.isArray(data?.items) ? data.items : [];
      if (reset) {
        setItems(newItems);
        setPage(1);
      } else {
        setItems(prev => [...prev, ...newItems]);
        setPage(p => p + 1);
      }
      setHasMore(!!data?.has_more);
    } catch (e:any) {
      setError(e?.message || "Failed to load timeline");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(true); /* eslint-disable-next-line */ }, [caseIdFilter]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/portal/cases', { cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          const mapped = Array.isArray(data) ? data.map((c:any) => ({ id: c.id, title: c.title as string })) : [];
          setCases(mapped);
        }
      } catch {}
    })();
  }, []);

  function groupByDate(arr: TimelineItem[]) {
    const groups: Record<string, TimelineItem[]> = {};
    for (const it of arr) {
      const d = it.at ? new Date(it.at) : null;
      const key = d ? d.toDateString() : 'Unknown date';
      groups[key] = groups[key] || [];
      groups[key].push(it);
    }
    return groups;
  }

  const grouped = useMemo(() => groupByDate(filtered), [filtered]);
  const orderedDates = useMemo(() => Object.keys(grouped).sort((a,b) => new Date(b).getTime() - new Date(a).getTime()), [grouped]);

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-semibold mb-4">Case Timeline</h1>

      <div className="mb-3 flex items-center gap-2">
        <label className="text-sm">Filter by Case:</label>
        <select
          className="border rounded px-2 py-1 w-64"
          value={caseIdFilter}
          onChange={(e) => setCaseIdFilter(e.target.value)}
        >
          <option value="">All cases</option>
          {cases.map(c => (
            <option key={c.id} value={String(c.id)}>{`#${c.id} — ${c.title}`}</option>
          ))}
        </select>
        <button onClick={() => setCaseIdFilter("")} className="text-sm text-gray-600 underline">Clear</button>
      </div>

      {error && <div className="text-sm text-red-600 mb-3">{error}</div>}
      {loading && items.length === 0 ? (
        <div>Loading...</div>
      ) : (
        <div className="space-y-6">
          {orderedDates.map(dateKey => (
            <div key={dateKey}>
              <div className="text-xs uppercase tracking-wide text-gray-600 mb-2">{dateKey}</div>
              <ul className="space-y-3">
                {grouped[dateKey].map((it, idx) => (
                  <li key={idx} className="border rounded p-3">
                    <div className="text-xs text-gray-500 flex justify-between">
                      <span>
                        Case {it.case_id ? (
                          <a className="text-blue-600 hover:underline" href={`/portal/cases/${it.case_id}`}>#{it.case_id}</a>
                        ) : '—'}
                        {` • ${it.type.replace('_',' ')}`}
                      </span>
                      <span>{it.at ? new Date(it.at).toLocaleTimeString() : ""}</span>
                    </div>
                    <div className="mt-1 text-sm">
                      {it.type === 'status_change' && (
                        <div>Case status changed from <strong>{it.data?.from ?? '—'}</strong> to <strong>{it.data?.to ?? '—'}</strong></div>
                      )}
                      {it.type === 'message' && (
                        <div>
                          <div className="text-gray-700">{it.data?.from_client ? 'Client' : 'Firm'} wrote:</div>
                          <div className="font-medium">{it.data?.subject || '(no subject)'}</div>
                          <div className="whitespace-pre-wrap">{it.data?.message}</div>
                        </div>
                      )}
                      {it.type === 'document' && (
                        <div>Document shared: <strong>{it.data?.name ?? '—'}</strong></div>
                      )}
                      {it.type === 'invoice' && (
                        <div>Invoice {it.data?.invoice_number ?? '—'} created • Amount: {typeof it.data?.total_amount === 'number' ? it.data.total_amount.toFixed(2) : it.data?.total_amount ?? '—'} • Status: {it.data?.status ?? '—'}</div>
                      )}
                      {it.type === 'payment' && (
                        <div>Payment recorded • Amount: {typeof it.data?.amount === 'number' ? it.data.amount.toFixed(2) : it.data?.amount ?? '—'} • Status: {it.data?.status ?? '—'}</div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {!filtered.length && (
            <div className="text-sm text-gray-500">No timeline items yet.</div>
          )}
          {hasMore && (
            <div className="pt-2">
              <button
                disabled={loading}
                onClick={() => load(false)}
                className="px-3 py-1 rounded border bg-white hover:bg-gray-50"
              >
                {loading ? 'Loading...' : 'Load more'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
