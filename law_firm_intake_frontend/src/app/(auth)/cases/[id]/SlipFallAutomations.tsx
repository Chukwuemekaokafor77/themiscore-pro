"use client";
import React, { useState } from "react";

export default function SlipFallAutomations({ caseId, enabled }: { caseId: number; enabled: boolean }) {
  const [loading, setLoading] = useState<"preview" | "apply" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<any | null>(null);

  async function onPreview() {
    try {
      setLoading("preview"); setError(null);
      const res = await fetch("/api/staff/automations/slip_fall/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(j?.error || "Preview failed");
      setPreview(j);
    } catch (e: any) {
      setError(e?.message || "Preview failed");
    } finally {
      setLoading(null);
    }
  }

  async function onApply() {
    try {
      setLoading("apply"); setError(null);
      const res = await fetch("/api/staff/automations/slip_fall/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId, preview }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(j?.error || "Apply failed");
      // Basic success UX: reload page to reflect new tasks/docs/events counts
      window.location.reload();
    } catch (e: any) {
      setError(e?.message || "Apply failed");
    } finally {
      setLoading(null);
    }
  }

  if (!enabled) return null;

  return (
    <section className="rounded border bg-white p-4 text-sm grid gap-3">
      <h2 className="font-medium">Slip &amp; Fall Automations</h2>
      {error && <div className="text-red-600">{error}</div>}
      <div className="flex gap-2">
        <button disabled={loading !== null} onClick={onPreview} className="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50">
          {loading === "preview" ? "Previewing..." : "Preview"}
        </button>
        <button disabled={loading !== null || !preview} onClick={onApply} className="px-3 py-1.5 rounded bg-green-600 text-white disabled:opacity-50">
          {loading === "apply" ? "Applying..." : "Apply"}
        </button>
      </div>
      {preview && (
        <div className="grid gap-3">
          <div className="text-xs text-gray-500">Preview</div>
          <pre className="whitespace-pre-wrap text-xs bg-gray-50 p-2 rounded border max-h-72 overflow-auto">{JSON.stringify(preview, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}
