"use client";
import React, { useRef, useState } from "react";

export default function VoiceIntake() {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [transcriptId, setTranscriptId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function uploadFile(file: File) {
    const form = new FormData();
    form.append('audio_file', file);
    const res = await fetch('/api/portal/transcribe', { method: 'POST', body: form });
    if (!res.ok) throw new Error('upload failed');
    const json = await res.json();
    return json.transcript_id as string;
  }

  async function pollTranscript(id: string) {
    for (let i = 0; i < 30; i++) {
      const r = await fetch(`/api/portal/transcripts/${encodeURIComponent(id)}`);
      if (!r.ok) throw new Error('poll failed');
      const j = await r.json();
      setStatus(j.status);
      if (j.status === 'completed' && j.text) {
        setTranscript(j.text);
        return j.text as string;
      }
      await new Promise(res => setTimeout(res, 2000));
    }
    throw new Error('timeout');
  }

  async function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      setUploading(true); setStatus('uploading'); setTranscript(null); setTranscriptId(null);
      const id = await uploadFile(f);
      setTranscriptId(id);
      setStatus('processing');
      await pollTranscript(id);
    } catch (e) {
      setStatus('error');
    } finally {
      setUploading(false);
    }
  }

  async function createCase() {
    if (!transcript) return;
    try {
      setCreating(true);
      const res = await fetch('/api/portal/intake/auto', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: transcript, title: 'Client Voice Intake' }) });
      if (!res.ok) throw new Error('create failed');
      const j = await res.json();
      window.location.href = `/portal/cases/${j.case_id}`;
    } catch (e) {
      // no-op minimal
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="rounded border bg-white">
      <div className="px-4 py-3 border-b font-medium">Voice Intake</div>
      <div className="p-4 space-y-3 text-sm">
        <input ref={fileRef} type="file" accept="audio/*,video/*" onChange={onSelect} />
        {status && <div className="text-gray-600">Status: {status}</div>}
        {transcript && (
          <div className="space-y-2">
            <div className="font-medium">Transcript Preview</div>
            <pre className="whitespace-pre-wrap text-xs bg-gray-50 p-2 rounded border max-h-64 overflow-auto">{transcript}</pre>
            <button disabled={creating} onClick={createCase} className="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50">Create Case</button>
          </div>
        )}
      </div>
    </div>
  );
}
