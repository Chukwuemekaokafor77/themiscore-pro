'use client'

import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'

export default function TranscribePage() {
  const router = useRouter()
  const [transcriptId, setTranscriptId] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [caseTitle, setCaseTitle] = useState('Client Intake')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [creating, setCreating] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [analysis, setAnalysis] = useState<any | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)

  const uploadMutation = useMutation({
    mutationFn: async (input: File) => {
      if (input.size > 16 * 1024 * 1024) throw new Error('File too large')
      const ct = input.type || ''
      if (!(ct.startsWith('audio/') || ct.startsWith('video/'))) throw new Error('Unsupported file type')
      const fd = new FormData()
      fd.append('audio_file', input)
      // Option A: use /flask rewrite to post directly to Flask (bypass Next body limits)
      const res = await fetch('/flask/transcribe', {
        method: 'POST',
        body: fd,
      })
      if (!res.ok) throw new Error('Upload failed')
      return res.json() as Promise<{ status: string; transcript_id: string }>
    },
    onSuccess: (data) => setTranscriptId(data.transcript_id),
  })

  const statusQuery = useQuery({
    queryKey: ['transcribe-status', transcriptId],
    queryFn: async () => {
      // Option A: use /flask rewrite for status polling
      const res = await fetch(`/flask/transcribe/status/${transcriptId}`)
      if (!res.ok) throw new Error('Status failed')
      return res.json() as Promise<any>
    },
    enabled: !!transcriptId,
    refetchInterval: (q) => {
      const status = q.state.data as any
      if (!status || status.status === 'processing' || status.status === 'queued') return 1500
      return false
    },
  })

  useEffect(() => {
    const text = (statusQuery.data as any)?.text
    if (text && !analysis) {
      ;(async () => {
        try {
          const res = await fetch('/flask/intake/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
          if (res.ok) {
            const a = await res.json()
            setAnalysis(a)
          }
        } catch {}
      })()
    }
  }, [statusQuery.data, analysis])

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current)
      mediaRecorderRef.current?.stream.getTracks().forEach(t => t.stop())
    }
  }, [])

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      chunksRef.current = []
      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const file = new File([blob], `recording_${Date.now()}.webm`, { type: 'audio/webm' })
        uploadMutation.mutate(file)
        mr.stream.getTracks().forEach(t => t.stop())
      }
      mediaRecorderRef.current = mr
      mr.start(1000)
      setIsRecording(true)
      setElapsed(0)
      timerRef.current = window.setInterval(() => {
        setElapsed((s) => {
          const ns = s + 1
          if (ns >= 15 * 60) {
            try { mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive' && mediaRecorderRef.current.stop() } catch {}
          }
          return ns
        })
      }, 1000)
    } catch (e) {
      // no-op minimal error handling
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
    setIsRecording(false)
  }

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Transcribe Audio</h1>
      <div className="mb-4 flex items-center gap-3">
        {!isRecording ? (
          <button onClick={startRecording} className="px-4 py-2 bg-primary text-primary-foreground rounded">
            Start Recording
          </button>
        ) : (
          <button onClick={stopRecording} className="px-4 py-2 bg-destructive text-white rounded">
            Stop ({String(Math.floor(elapsed / 60)).padStart(2,'0')}:{String(elapsed % 60).padStart(2,'0')})
          </button>
        )}
        <div className="text-sm text-gray-600">Or upload a file:</div>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (file) uploadMutation.mutate(file)
        }}
        className="space-y-3"
      >
        <input
          type="file"
          accept="audio/*,video/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full"
        />
        <button
          type="submit"
          disabled={!file || uploadMutation.isPending}
          className="px-4 py-2 bg-primary text-primary-foreground rounded disabled:opacity-50"
        >
          {uploadMutation.isPending ? 'Uploading…' : 'Upload & Transcribe'}
        </button>
      </form>

      {transcriptId && (
        <div className="mt-6">
          <div className="text-sm text-gray-600 mb-2">Transcript ID: {transcriptId}</div>
          {statusQuery.isLoading && <div>Checking status…</div>}
          {statusQuery.data && (
            <div className="space-y-2">
              <div className="font-medium">Status: {statusQuery.data.status}</div>
              {statusQuery.data.status === 'completed' && (
                <>
                  <div className="text-sm whitespace-pre-wrap border rounded p-3 bg-gray-50">
                    {statusQuery.data.text || ''}
                  </div>
                  {analysis && (
                    <div className="border rounded p-3 bg-gray-50 space-y-1">
                      <div className="font-medium">Analysis</div>
                      <div>Category: {analysis.category}</div>
                      <div>Urgency: {analysis.urgency}</div>
                      {Array.isArray(analysis.dates) && analysis.dates.length > 0 && (
                        <div>Dates: {analysis.dates.slice(0,2).join(', ')}</div>
                      )}
                      {analysis.key_facts && Object.keys(analysis.key_facts).length > 0 && (
                        <div className="text-sm">Key facts: {Object.entries(analysis.key_facts).filter(([_,v]) => v).map(([k,v]) => `${k}: ${v}`).slice(0,5).join('; ')}</div>
                      )}
                      <div className="flex gap-3 pt-2">
                        <button
                          className="px-3 py-2 rounded bg-primary text-primary-foreground"
                          onClick={async () => {
                            setCreating(true)
                            try {
                              const res = await fetch('/api/staff/intake/auto', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                  text: statusQuery.data?.text || '',
                                  title: caseTitle || 'Client Intake',
                                  client: { first_name: firstName, last_name: lastName, email, phone, address },
                                }),
                              })
                              if (!res.ok) throw new Error('Create failed')
                              const data = await res.json()
                              if (data && data.case_id) {
                                router.push(`/cases/${data.case_id}`)
                              }
                            } catch {}
                            setCreating(false)
                          }}
                          disabled={creating}
                        >
                          {creating ? 'Creating…' : 'Create Case + Automation'}
                        </button>
                      </div>
                    </div>
                  )}
                  <div className="flex gap-3">
                    <button
                      className="px-3 py-2 rounded bg-primary text-primary-foreground"
                      onClick={() => setShowModal(true)}
                    >
                      Create Case from Transcript
                    </button>
                    <button
                      className="px-3 py-2 rounded border"
                      onClick={() => router.push(`/cases/new?title=${encodeURIComponent(caseTitle)}&text=${encodeURIComponent(statusQuery.data.text || '')}`)}
                    >
                      Open /cases/new
                    </button>
                  </div>
                </>
              )}
              {statusQuery.data.status === 'error' && (
                <div className="text-red-600">{statusQuery.data.error || 'Error'}</div>
              )}
            </div>
          )}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded shadow-lg w-full max-w-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-medium">Create Case</h2>
              <button className="text-gray-500" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form
              onSubmit={async (e) => {
                e.preventDefault()
                setCreating(true)
                try {
                  const res = await fetch('/api/staff/intake/auto', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      text: statusQuery.data?.text || '',
                      title: caseTitle || 'Client Intake',
                      client: { first_name: firstName, last_name: lastName, email, phone, address },
                    }),
                  })
                  if (!res.ok) throw new Error('Create failed')
                  const data = await res.json()
                  if (data && data.case_id) {
                    router.push(`/cases/${data.case_id}`)
                  }
                } catch (e) {
                  // no-op minimal error handling
                } finally {
                  setCreating(false)
                }
              }}
              className="space-y-3"
            >
              <div className="grid gap-2">
                <label className="text-sm text-gray-600">Case title</label>
                <input className="border rounded px-3 py-2" value={caseTitle} onChange={(e) => setCaseTitle(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <label className="text-sm text-gray-600">First name</label>
                  <input className="border rounded px-3 py-2" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm text-gray-600">Last name</label>
                  <input className="border rounded px-3 py-2" value={lastName} onChange={(e) => setLastName(e.target.value)} />
                </div>
              </div>
              <div className="grid gap-2">
                <label className="text-sm text-gray-600">Email</label>
                <input className="border rounded px-3 py-2" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <label className="text-sm text-gray-600">Phone</label>
                  <input className="border rounded px-3 py-2" value={phone} onChange={(e) => setPhone(e.target.value)} />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm text-gray-600">Address</label>
                  <input className="border rounded px-3 py-2" value={address} onChange={(e) => setAddress(e.target.value)} />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" className="px-3 py-2 border rounded" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="px-3 py-2 bg-primary text-primary-foreground rounded" disabled={creating}>
                  {creating ? 'Creating…' : 'Create Case'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

