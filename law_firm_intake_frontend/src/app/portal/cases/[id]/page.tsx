"use client";
import React, { useEffect, useState } from "react";

export default function PortalCaseDetailPage({ params }: { params: { id: string } }) {
  const caseId = params.id;
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [checklist, setChecklist] = useState<{items:any[]; doc_hints:any[]} | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/portal/cases/${encodeURIComponent(caseId)}`, { cache: 'no-store' });
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        const json = await res.json();
        setData(json);
        const cl = await fetch(`/api/portal/cases/${encodeURIComponent(caseId)}/checklist`, { cache: 'no-store' });
        if (cl.ok) {
          setChecklist(await cl.json());
        } else {
          setChecklist({ items: [], doc_hints: [] });
        }
      } catch (e:any) {
        setError(e?.message || 'Failed to load case');
      } finally {
        setLoading(false);
      }
    })();
  }, [caseId]);

  async function completeItem(id: number) {
    try {
      setSavingId(id);
      const res = await fetch(`/api/portal/cases/${encodeURIComponent(caseId)}/checklist/${id}/complete`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to complete');
      setChecklist((prev) => prev ? { ...prev, items: prev.items.filter(i => i.action_id !== id) } : prev);
    } catch (e) {
      // no-op minimal error surfacing
    } finally {
      setSavingId(null);
    }
  }

  if (loading) return <div className="p-4">Loading...</div>;
  if (error) return <div className="p-4 text-red-600 text-sm">{error}</div>;
  if (!data) return <div className="p-4">No data.</div>;

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{data.title}</h1>
        <div className="text-sm text-gray-600">Case #{data.id} • Status: <span className="font-medium">{data.status}</span></div>
      </div>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Key Dates</div>
        <div className="p-4">
          {Array.isArray(data.deadlines) && data.deadlines.length > 0 ? (
            <ul className="text-sm space-y-2">
              {data.deadlines.map((d:any) => (
                <li key={d.id} className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{d.name}</div>
                    <div className="text-gray-600 text-xs">{d.source || ''}</div>
                  </div>
                  <div>{d.due_date ? new Date(d.due_date).toLocaleDateString() : '—'}</div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No deadlines yet.</div>
          )}
        </div>
      </section>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Your Checklist</div>
        <div className="p-4 space-y-4">
          {checklist && checklist.items && checklist.items.length > 0 ? (
            <ul className="text-sm space-y-2">
              {checklist.items.map((it:any) => (
                <li key={it.action_id} className="flex items-center justify-between gap-3 border rounded p-3">
                  <div>
                    <div className="font-medium">{it.title}</div>
                    {it.description && <div className="text-xs text-gray-600">{it.description}</div>}
                    {it.due_date && <div className="text-xs text-gray-600">Due: {new Date(it.due_date).toLocaleString()}</div>}
                  </div>
                  <button
                    onClick={() => completeItem(it.action_id)}
                    disabled={savingId === it.action_id}
                    className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
                  >Mark Done</button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No pending items assigned to you.</div>
          )}

          {checklist && checklist.doc_hints && checklist.doc_hints.length > 0 && (
            <div className="text-sm">
              <div className="font-medium mb-2">Documents that may be needed</div>
              <ul className="list-disc ml-5 space-y-1">
                {checklist.doc_hints.map((d:any) => (
                  <li key={d.deadline_id}>
                    {d.name} {d.due_date ? `• Due ${new Date(d.due_date).toLocaleDateString()}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Documents</div>
        <div className="p-4">
          {Array.isArray(data.documents) && data.documents.length > 0 ? (
            <ul className="text-sm space-y-2">
              {data.documents.map((a:any) => (
                <li key={a.id} className="flex items-center justify-between">
                  <div>{a.document?.name ?? '—'}</div>
                  <div className="text-xs text-gray-600">{a.granted_at ? new Date(a.granted_at).toLocaleString() : ''}</div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No documents for this case.</div>
          )}
        </div>
      </section>

      <section className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Messages</div>
        <div className="p-4">
          {Array.isArray(data.messages) && data.messages.length > 0 ? (
            <ul className="text-sm space-y-3">
              {data.messages.map((m:any) => (
                <li key={m.id} className="border rounded p-3">
                  <div className="text-xs text-gray-500 flex justify-between">
                    <span>{m.from_client ? 'You' : 'Firm'}</span>
                    <span>{m.created_at ? new Date(m.created_at).toLocaleString() : ''}</span>
                  </div>
                  <div className="font-medium">{m.subject || '(no subject)'}</div>
                  <div className="whitespace-pre-wrap">{m.message}</div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No messages yet.</div>
          )}
        </div>
      </section>
    </div>
  );
}
