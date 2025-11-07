'use client'

import { useState } from 'react'
import { api } from '@/lib/api'

export default function IntakePage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<null | {
    category?: string
    urgency?: string
    key_facts: string[]
    dates: Record<string, string>
    parties: Record<string, unknown>
    suggested_actions: string[]
  }>(null)

  const onAnalyze = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.staff.intakeAnalyze(text)
      setResult(res)
    } catch (e: any) {
      setError(e?.message || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Intake Analysis</h1>

      <section className="rounded border bg-white p-4 space-y-3">
        <label className="block text-sm text-gray-600">Paste client narrative</label>
        <textarea
          className="w-full min-h-[160px] border rounded px-3 py-2"
          placeholder="Paste transcript or notes..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          onClick={onAnalyze}
          disabled={loading || !text.trim()}
          className="px-4 py-2 bg-black text-white rounded disabled:opacity-50"
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
        {error && <div className="text-sm text-red-600">{error}</div>}
      </section>

      {result && (
        <section className="rounded border bg-white p-4 grid gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-gray-500">Category</div>
              <div>{result.category ?? '—'}</div>
            </div>
            <div>
              <div className="text-gray-500">Urgency</div>
              <div>{result.urgency ?? '—'}</div>
            </div>
          </div>

          <div>
            <div className="font-medium mb-2">Key Facts</div>
            <ul className="list-disc ml-5 text-sm space-y-1">
              {(result.key_facts || []).length ? result.key_facts.map((f, i) => (
                <li key={i}>{f}</li>
              )) : <li>—</li>}
            </ul>
          </div>

          <div>
            <div className="font-medium mb-2">Dates</div>
            <div className="text-sm grid gap-1">
              {Object.keys(result.dates || {}).length ? (
                Object.entries(result.dates).map(([k, v]) => (
                  <div key={k}><span className="text-gray-500 mr-2">{k}:</span>{v}</div>
                ))
              ) : (
                <div>—</div>
              )}
            </div>
          </div>

          <div>
            <div className="font-medium mb-2">Parties</div>
            <pre className="text-xs bg-gray-50 border rounded p-3 overflow-auto">{JSON.stringify(result.parties || {}, null, 2)}</pre>
          </div>

          <div>
            <div className="font-medium mb-2">Suggested Actions</div>
            <ul className="list-disc ml-5 text-sm space-y-1">
              {(result.suggested_actions || []).length ? result.suggested_actions.map((a, i) => (
                <li key={i}>{a}</li>
              )) : <li>—</li>}
            </ul>
          </div>
        </section>
      )}
    </div>
  )
}
