"use client";

import { useState } from "react";

type Analysis = {
  category?: string;
  case_type_key?: string | null;
  urgency?: string;
  key_facts?: Record<string, unknown>;
  dates?: Record<string, unknown>;
  parties?: Record<string, unknown>;
  suggested_actions?: string[];
  checklists?: Record<string, unknown>;
  department?: string | null;
  confidence?: number | null;
};

export default function IntakePage() {
  // Client info (minimal for now)
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");

  // Intake text & title
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");

  // Analysis + UI state
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);

  const onAnalyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/staff/intake/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `Analysis failed (${res.status})`);
      }
      const j = (await res.json()) as Analysis;
      setResult(j);
    } catch (e: any) {
      setError(e?.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const onCreateCase = async () => {
    setError(null);
    if (!firstName.trim() || !lastName.trim()) {
      setError("First name and last name are required to create a case.");
      return;
    }
    if (!text.trim()) {
      setError("Please enter intake text first.");
      return;
    }
    setCreating(true);
    try {
      const res = await fetch("/api/staff/intake/auto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          title: title || "New Intake",
          client: {
            first_name: firstName.trim(),
            last_name: lastName.trim(),
            email: email || undefined,
          },
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error || `Create failed (${res.status})`);
      }
      const j = await res.json();
      const caseId = j.case_id;
      if (caseId) {
        window.location.href = `/cases/${caseId}`;
      }
    } catch (e: any) {
      setError(e?.message || "Create failed");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Intake Analysis & Auto Case Creation</h1>

      {error && (
        <div className="text-sm text-red-700 border border-red-200 bg-red-50 px-3 py-2 rounded">
          {error}
        </div>
      )}

      {/* Client + title */}
      <section className="rounded border bg-white p-4 space-y-3">
        <h2 className="font-medium text-sm">Client & Case</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div>
            <label className="block text-xs text-gray-600 mb-1">First name</label>
            <input
              className="w-full border rounded px-2 py-1.5"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Last name</label>
            <input
              className="w-full border rounded px-2 py-1.5"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Email (optional)</label>
            <input
              className="w-full border rounded px-2 py-1.5"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="sm:col-span-3">
            <label className="block text-xs text-gray-600 mb-1">Case title (optional)</label>
            <input
              className="w-full border rounded px-2 py-1.5"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Walmart slip and fall – produce section"
            />
          </div>
        </div>
      </section>

      {/* Narrative + analyze */}
      <section className="rounded border bg-white p-4 space-y-3">
        <label className="block text-sm text-gray-600">Paste client narrative</label>
        <textarea
          className="w-full min-h-[160px] border rounded px-3 py-2 text-sm"
          placeholder="Paste transcript or notes..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          onClick={onAnalyze}
          disabled={loading || !text.trim()}
          className="px-4 py-2 bg-black text-white rounded text-sm disabled:opacity-50"
        >
          {loading ? "Analyzing…" : "Analyze with AI"}
        </button>
      </section>

      {/* Analysis result */}
      {result && (
        <section className="rounded border bg-white p-4 grid gap-4 text-sm">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <div className="text-gray-500 text-xs">Category</div>
              <div>{result.category ?? "—"}</div>
            </div>
            <div>
              <div className="text-gray-500 text-xs">Case Type Key</div>
              <div className="font-mono text-xs break-all">
                {result.case_type_key ?? <span className="text-gray-400">none</span>}
              </div>
            </div>
            <div>
              <div className="text-gray-500 text-xs">Urgency / Confidence</div>
              <div>
                {result.urgency ?? "—"}
                {typeof result.confidence === "number" && (
                  <span className="ml-1 text-xs text-gray-500">
                    ({Math.round(result.confidence * 100)}%)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Key facts */}
          {result.key_facts && Object.keys(result.key_facts).length > 0 && (
            <div>
              <div className="font-medium mb-1">Key Facts</div>
              <ul className="list-disc ml-5 space-y-1">
                {Object.entries(result.key_facts).map(([k, v]) =>
                  v ? (
                    <li key={k}>
                      <span className="font-medium">{k.replace(/_/g, " ")}:</span>{" "}
                      <span className="text-gray-700 text-xs">{String(v)}</span>
                    </li>
                  ) : null,
                )}
              </ul>
            </div>
          )}

          {/* Dates */}
          {result.dates && Object.keys(result.dates).length > 0 && (
            <div>
              <div className="font-medium mb-1">Dates</div>
              <div className="text-xs grid gap-1">
                {Object.entries(result.dates).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-gray-500 mr-2">{k}:</span>
                    {String(v)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested actions */}
          {result.suggested_actions && result.suggested_actions.length > 0 && (
            <div>
              <div className="font-medium mb-1">Suggested Actions</div>
              <ul className="list-disc ml-5 space-y-1">
                {result.suggested_actions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-2 border-t mt-2 flex justify-end">
            <button
              onClick={onCreateCase}
              disabled={creating}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
            >
              {creating ? "Creating case…" : "Create Case from Analysis"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}