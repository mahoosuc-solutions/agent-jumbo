'use client'

import { useState } from 'react'

interface Props {
  periodEnd: string
  onClose: () => void
}

export function CancelModal({ periodEnd, onClose }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function handleConfirm() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/backend/billing/cancel', { method: 'POST' })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? 'Cancellation failed')
      }
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancellation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 max-w-md w-full shadow-2xl">
        {done ? (
          <>
            <h2 className="text-xl font-bold text-white mb-3">Cancellation Scheduled</h2>
            <p className="text-slate-400 text-sm mb-6">
              Your subscription will remain active until <strong className="text-white">{periodEnd}</strong>.
              You will not be charged again.
            </p>
            <button
              onClick={() => { onClose(); window.location.reload() }}
              className="w-full px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition"
            >
              Close
            </button>
          </>
        ) : (
          <>
            <h2 className="text-xl font-bold text-white mb-3">Cancel Subscription?</h2>
            <p className="text-slate-400 text-sm mb-2">
              Your subscription will stay active until the end of your current billing period
              (<strong className="text-white">{periodEnd}</strong>), then be cancelled.
            </p>
            <p className="text-slate-500 text-sm mb-6">
              You can resubscribe at any time.
            </p>

            {error && (
              <p className="text-red-400 text-sm mb-4 p-3 bg-red-900/20 rounded-lg border border-red-800">
                {error}
              </p>
            )}

            <div className="flex gap-3">
              <button
                onClick={onClose}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-slate-800 text-slate-200 rounded-lg hover:bg-slate-700 transition disabled:opacity-50"
              >
                Keep Subscription
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-red-700 text-white rounded-lg hover:bg-red-600 transition disabled:opacity-50"
              >
                {loading ? 'Cancelling…' : 'Yes, Cancel'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
