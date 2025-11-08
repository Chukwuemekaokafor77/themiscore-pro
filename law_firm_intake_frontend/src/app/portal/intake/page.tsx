"use client";
import React, { useRef, useState } from "react";

export default function IntakeStartPage() {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function uploadFile(file: File) {
    const form = new FormData();
    form.append("audio_file", file);
    const res = await fetch("/api/portal/transcribe", { method: "POST", body: form });
    if (!res.ok) throw new Error("upload failed");
    const json = await res.json();
    return json.transcript_id as string;
  }

  async function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      setUploading(true);
      setStatus("uploading");
      const id = await uploadFile(f);
      // Go to review page to poll and analyze
      window.location.href = `/portal/intake/review?id=${encodeURIComponent(id)}`;
    } catch (e) {
      setStatus("error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Start Intake</h1>
      <div className="rounded border bg-white p-4 space-y-3">
        <div className="text-sm text-gray-700">Record or upload audio to begin.</div>
        <input ref={fileRef} type="file" accept="audio/*,video/*" onChange={onSelect} />
        {status && <div className="text-gray-600 text-sm">Status: {status}</div>}
        <div className="text-xs text-gray-500">After upload, you'll be taken to review to analyze the transcript.</div>
      </div>
    </div>
  );
}
