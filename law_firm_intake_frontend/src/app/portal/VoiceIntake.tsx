"use client";
import React, { useRef, useState, useEffect } from "react";

export default function VoiceIntake() {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [transcriptId, setTranscriptId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createdCaseId, setCreatedCaseId] = useState<number | null>(null);
  const [createdSummary, setCreatedSummary] = useState<any | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
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

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      chunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = async () => {
        try {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          const file = new File([blob], `recording_${Date.now()}.webm`, { type: 'audio/webm' });
          setUploading(true);
          setStatus('uploading');
          setTranscript(null);
          setTranscriptId(null);
          const id = await uploadFile(file);
          setTranscriptId(id);
          setStatus('processing');
          await pollTranscript(id);
        } catch (e) {
          setStatus('error');
        } finally {
          setUploading(false);
        }
        mr.stream.getTracks().forEach(t => t.stop());
      };
      mediaRecorderRef.current = mr;
      mr.start(1000);
      setIsRecording(true);
      setElapsed(0);
      timerRef.current = window.setInterval(() => {
        setElapsed((s) => {
          const ns = s + 1;
          if (ns >= 10 * 60) { // 10 minute cap
            try {
              if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                mediaRecorderRef.current.stop();
              }
            } catch {}
          }
          return ns;
        });
      }, 1000);
    } catch (e) {
      // minimal error handling
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
  }

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      mediaRecorderRef.current?.stream.getTracks().forEach(t => t.stop());
    };
  }, []);

  async function createCase() {
    if (!transcript) return;
    try {
      setCreating(true);
      const res = await fetch('/api/portal/intake/auto', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: transcript, title: 'Client Voice Intake' }) });
      const j = await res.json().catch(() => ({} as any));
      if (!res.ok) throw new Error(j.error || 'create failed');
      const caseId = j.case_id ?? j.caseId ?? null;
      setCreatedCaseId(typeof caseId === 'number' ? caseId : Number(caseId) || null);
      setCreatedSummary(j || null);
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
        <div className="flex items-center gap-3 flex-wrap">
          {!isRecording ? (
            <button
              type="button"
              onClick={startRecording}
              className="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50"
              disabled={uploading}
            >
              Start Recording
            </button>
          ) : (
            <button
              type="button"
              onClick={stopRecording}
              className="px-3 py-1.5 rounded bg-red-600 text-white"
            >
              Stop ({String(Math.floor(elapsed / 60)).padStart(2, '0')}:{String(elapsed % 60).padStart(2, '0')})
            </button>
          )}
          <div className="text-xs text-gray-600">or upload a file:</div>
        </div>
        <input ref={fileRef} type="file" accept="audio/*,video/*" onChange={onSelect} />
        {status && <div className="text-gray-600">Status: {status}</div>}
        {transcript && (
          <div className="space-y-2">
            <div className="font-medium">Transcript Preview</div>
            <pre className="whitespace-pre-wrap text-xs bg-gray-50 p-2 rounded border max-h-64 overflow-auto">{transcript}</pre>
            <button disabled={creating} onClick={createCase} className="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50">Create Case</button>
            {createdSummary && (
              <div className="mt-3 border rounded bg-white p-3 space-y-2 text-xs">
                <div className="font-medium text-sm">Automation Summary</div>
                {createdCaseId && (
                  <div>
                    <span className="text-gray-500 mr-1">Case ID:</span>
                    <span className="font-mono">{createdCaseId}</span>
                  </div>
                )}
                {createdSummary.analysis && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <div className="text-gray-500 uppercase">Category</div>
                      <div>{createdSummary.analysis.category ?? '—'}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 uppercase">Department</div>
                      <div>{createdSummary.analysis.department ?? '—'}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 uppercase">Priority / Urgency</div>
                      <div>{createdSummary.analysis.priority || createdSummary.analysis.urgency || '—'}</div>
                    </div>
                  </div>
                )}
                {Array.isArray(createdSummary.actions_created) && createdSummary.actions_created.length > 0 && (
                  <div>
                    <div className="font-medium mb-1">Actions Created ({createdSummary.actions_created.length})</div>
                    <ul className="list-disc ml-5 space-y-1">
                      {createdSummary.actions_created.slice(0, 5).map((a: any, idx: number) => (
                        <li key={idx}>
                          {a.title || a.name || 'Action'}
                          {a.due_date && <span className="text-gray-500 ml-1">(due {String(a.due_date).slice(0, 10)})</span>}
                        </li>
                      ))}
                      {createdSummary.actions_created.length > 5 && (
                        <li className="text-gray-500">…and {createdSummary.actions_created.length - 5} more</li>
                      )}
                    </ul>
                  </div>
                )}
                {createdCaseId && (
                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={() => {
                        window.location.href = `/portal/cases/${createdCaseId}`;
                      }}
                      className="px-3 py-1.5 rounded bg-black text-white"
                    >
                      Open Case
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
