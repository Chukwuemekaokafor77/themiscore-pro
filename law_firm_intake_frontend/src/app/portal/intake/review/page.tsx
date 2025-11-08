"use client";
import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { normalizeAnalysis, type IntakeAnalysis } from "@/lib/intake";

export default function IntakeReviewPage() {
  const params = useSearchParams();
  const id = params.get("id");
  const [status, setStatus] = useState<string | null>(id ? "processing" : null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<IntakeAnalysis | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Poll transcript by id
  useEffect(() => {
    let stop = false;
    async function poll() {
      if (!id) return;
      for (let i = 0; i < 30 && !stop; i++) {
        const r = await fetch(`/api/portal/transcripts/${encodeURIComponent(id)}`);
        if (!r.ok) {
          setStatus("error");
          return;
        }
        const j = await r.json();
        setStatus(j.status);
        if (j.status === "completed" && j.text) {
          setTranscript(j.text);
          return;
        }
        await new Promise((res) => setTimeout(res, 2000));
      }
      if (!stop) setStatus("timeout");
    }
    poll();
    return () => {
      stop = true;
    };
  }, [id]);

  const canAnalyze = useMemo(() => Boolean(transcript && !analysis), [transcript, analysis]);

  async function onAnalyze() {
    if (!transcript) return;
    try {
      setAnalyzing(true);
      const res = await fetch("/api/portal/intake/auto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: transcript, title: "Client Voice Intake" }),
      });
      const json = await res.json();
      const norm = normalizeAnalysis(json || {});
      setAnalysis(norm);
    } catch (e) {
      // ignore minimal
    } finally {
      setAnalyzing(false);
    }
  }

  async function onConfirm() {
    if (!transcript || !analysis) {
      window.location.href = "/portal";
      return;
    }
    try {
      setSaving(true);
      setError(null);
      const res = await fetch("/api/portal/intake/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, analysis }),
      });
      const j = await res.json().catch(() => ({} as any));
      if (!res.ok) {
        setError(j?.error || "Save failed");
        return;
      }
      const caseId = j?.case_id || j?.caseId;
      if (caseId) {
        window.location.href = `/portal/cases/${caseId}`;
      } else {
        window.location.href = "/portal";
      }
    } catch (_) {
      setError("Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Review Transcript</h1>

      <div className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Transcript</div>
        <div className="p-4 text-sm space-y-3">
          {!id && <div className="text-gray-600">Missing transcript id.</div>}
          {id && !transcript && (
            <div className="text-gray-600">Status: {status ?? "loading"}</div>
          )}
          {transcript && (
            <pre className="whitespace-pre-wrap text-xs bg-gray-50 p-2 rounded border max-h-96 overflow-auto">{transcript}</pre>
          )}
        </div>
      </div>

      <div className="rounded border bg-white">
        <div className="px-4 py-3 border-b font-medium">Analyze</div>
        <div className="p-4 text-sm space-y-3">
          {error && <div className="text-red-600">{error}</div>}
          <button
            disabled={!canAnalyze || analyzing}
            onClick={onAnalyze}
            className="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50"
          >
            {analyzing ? "Analyzing..." : "Analyze"}
          </button>
          {analysis && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs uppercase text-gray-500">Category</div>
                <div className="font-medium">{analysis.category ?? "—"}</div>
              </div>
              <div>
                <div className="text-xs uppercase text-gray-500">Urgency</div>
                <div className="font-medium">{String(analysis.urgency ?? "—")}</div>
              </div>
              <div className="md:col-span-2">
                <div className="text-xs uppercase text-gray-500">Key Facts</div>
                <ul className="list-disc pl-5 space-y-1">
                  {(analysis.key_facts || []).map((f, idx) => (
                    <li key={idx}>{f}</li>
                  ))}
                  {!analysis.key_facts?.length && <li className="text-gray-500">—</li>}
                </ul>
              </div>
              <div>
                <div className="text-xs uppercase text-gray-500">Dates</div>
                <ul className="list-disc pl-5 space-y-1">
                  {(analysis.dates || []).map((d, idx) => (
                    <li key={idx}>{d.label}: {d.value}</li>
                  ))}
                  {!analysis.dates?.length && <li className="text-gray-500">—</li>}
                </ul>
              </div>
              <div>
                <div className="text-xs uppercase text-gray-500">Parties</div>
                <ul className="list-disc pl-5 space-y-1">
                  {(analysis.parties || []).map((p, idx) => (
                    <li key={idx}>{p.role}{p.name ? `: ${p.name}` : ""}</li>
                  ))}
                  {!analysis.parties?.length && <li className="text-gray-500">—</li>}
                </ul>
              </div>
            </div>
          )}
          {analysis && (
            <div>
              <button disabled={saving} onClick={onConfirm} className="mt-2 px-3 py-1.5 rounded bg-green-600 text-white disabled:opacity-50">{saving ? "Saving..." : "Confirm"}</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
