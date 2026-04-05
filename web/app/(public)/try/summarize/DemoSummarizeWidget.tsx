'use client'

import { useState } from 'react'
import Link from 'next/link'

const MAX_USES = 3
const PLACEHOLDER = `Paste any text here — an email thread, contract, meeting notes, article, or report.

Example: "Q3 earnings call transcript..."

The AI will return:
• A one-sentence TL;DR
• 3–5 key points
• Action items or decisions (if any)`

export default function DemoSummarizeWidget() {
  const [text, setText] = useState('')
  const [summary, setSummary] = useState('')
  const [usesRemaining, setUsesRemaining] = useState(MAX_USES)
  const [loading, setLoading] = useState(false)
  const [limitReached, setLimitReached] = useState(false)
  const [error, setError] = useState('')

  async function summarize() {
    if (!text.trim() || loading || limitReached) return
    setLoading(true)
    setError('')
    setSummary('')

    try {
      const res = await fetch('/api/backend/demo_summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      const data = await res.json()

      if (data.error === 'demo_limit_reached') {
        setLimitReached(true)
        setError(data.message)
      } else {
        setSummary(data.summary)
        setUsesRemaining(data.uses_remaining ?? 0)
        if (data.uses_remaining === 0) setLimitReached(true)
      }
    } catch {
      setError('Something went wrong — please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <textarea
        className="w-full rounded-xl bg-slate-900 border border-slate-700 px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-copper-500/60 resize-none font-mono"
        rows={10}
        placeholder={PLACEHOLDER}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={loading || limitReached}
      />

      <div className="flex items-center justify-between gap-4">
        <span className="text-xs text-slate-500 font-mono">
          {text.length.toLocaleString()} chars
          {text.length > 8000 && (
            <span className="text-amber-400 ml-2">(will be truncated to 8,000 for demo)</span>
          )}
        </span>
        {!limitReached ? (
          <button
            onClick={summarize}
            disabled={loading || !text.trim()}
            className="px-6 py-2.5 rounded-lg bg-copper-500 text-white text-sm font-semibold hover:bg-copper-400 disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            {loading ? 'Summarizing…' : 'Summarize'}
          </button>
        ) : (
          <Link
            href="/signup"
            className="px-6 py-2.5 rounded-lg bg-copper-500 text-white text-sm font-semibold hover:bg-copper-400 transition"
          >
            Start Free — no credit card
          </Link>
        )}
      </div>

      {!limitReached && usesRemaining < MAX_USES && (
        <p className="text-xs text-slate-600 font-mono text-right">
          {usesRemaining} summar{usesRemaining !== 1 ? 'ies' : 'y'} remaining
        </p>
      )}

      {error && !summary && (
        <div className="rounded-xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {error}
          {limitReached && (
            <div className="mt-3">
              <Link href="/signup" className="text-copper-300 underline hover:text-copper-200">
                Start Free Cloud →
              </Link>
            </div>
          )}
        </div>
      )}

      {summary && (
        <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs font-mono uppercase tracking-widest text-slate-500">Summary</span>
            <span className="flex-1 border-t border-slate-800" />
          </div>
          <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">{summary}</p>
          <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Powered by Mahoosuc OS AI Document Processing instrument
            </span>
            <Link href="/solutions/ai-document-processing" className="text-xs text-copper-300 hover:text-copper-200">
              See full pipeline →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
