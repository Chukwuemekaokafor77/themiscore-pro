"use client";
import React, { useEffect, useMemo, useState } from "react";

type MessageItem = {
  id: number;
  case_id: number;
  from_client: boolean;
  subject: string | null;
  message: string;
  read: boolean;
  created_at: string | null;
};

export default function PortalMessagesPage() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<MessageItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [caseIdFilter, setCaseIdFilter] = useState<string>("");
  const [cases, setCases] = useState<Array<{ id:number; title:string }>>([]);

  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [caseId, setCaseId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const filtered = useMemo(() => {
    if (!caseIdFilter) return items;
    const cid = Number(caseIdFilter);
    return items.filter(i => i.case_id === cid);
  }, [items, caseIdFilter]);

  async function loadMessages() {
    setLoading(true);
    setError(null);
    try {
      const qs = caseIdFilter ? `?case_id=${encodeURIComponent(caseIdFilter)}` : "";
      const res = await fetch(`/api/portal/messages${qs}`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`Failed to load: ${res.status}`);
      }
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(e?.message || "Failed to load messages");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseIdFilter]);

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

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const body: any = { message: message.trim() };
      if (subject.trim()) body.subject = subject.trim();
      if (caseId) body.case_id = Number(caseId);
      const res = await fetch(`/api/portal/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Failed to send: ${res.status}`);
      }
      setSubject("");
      setMessage("");
      // keep selected caseId
      await loadMessages();
    } catch (e: any) {
      setError(e?.message || "Failed to send message");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-semibold mb-4">Messages</h1>

      <div className="mb-6 border rounded p-3">
        <h2 className="font-medium mb-2">Compose</h2>
        <form onSubmit={onSend} className="space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Subject (optional)"
              className="flex-1 border rounded px-2 py-1"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
            <select
              className="w-64 border rounded px-2 py-1"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              required
            >
              <option value="">Select case...</option>
              {cases.map(c => (
                <option key={c.id} value={String(c.id)}>{`#${c.id} — ${c.title}`}</option>
              ))}
            </select>
          </div>
          <textarea
            placeholder="Write your message..."
            className="w-full border rounded px-2 py-1 h-28"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
          />
          <button
            type="submit"
            disabled={submitting || !message.trim() || !caseId}
            className="bg-blue-600 text-white px-3 py-1 rounded disabled:opacity-60"
          >
            {submitting ? "Sending..." : "Send"}
          </button>
        </form>
      </div>

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
        <button
          onClick={() => setCaseIdFilter("")}
          className="text-sm text-gray-600 underline"
        >
          Clear
        </button>
      </div>

      {error && (
        <div className="mb-3 text-red-600 text-sm">{error}</div>
      )}

      {loading ? (
        <div>Loading...</div>
      ) : (
        <ul className="space-y-3">
          {filtered.map((m) => (
            <li key={m.id} className="border rounded p-3">
              <div className="text-xs text-gray-500 flex justify-between">
                <span>
                  Case #{m.case_id} • {m.from_client ? "You" : "Firm"}
                </span>
                <span>{m.created_at ? new Date(m.created_at).toLocaleString() : ""}</span>
              </div>
              <div className="font-medium mt-1">{m.subject || "(no subject)"}</div>
              <div className="whitespace-pre-wrap text-sm mt-1">{m.message}</div>
            </li>
          ))}
          {!filtered.length && (
            <li className="text-sm text-gray-500">No messages yet.</li>
          )}
        </ul>
      )}
    </div>
  );
}
