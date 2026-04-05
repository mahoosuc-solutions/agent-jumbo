'use client'

import { useState } from 'react'
import { getTiers } from '@/lib/pricing'

interface Subscription {
  stripe_price_id?: string
  status?: string
}

interface Props {
  currentSubscription: Subscription | null
}

export function PlanSelector({ currentSubscription }: Props) {
  const tiers = getTiers()
  const [selectedPriceId, setSelectedPriceId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const paidTiers = tiers.filter((t) => t.price_cents && t.price_cents > 0 && t.stripe_price_id)

  async function handleUpgrade() {
    if (!selectedPriceId) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/backend/billing/upgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price_id: selectedPriceId }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? 'Upgrade failed')
      }
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upgrade failed')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="rounded-xl border border-green-800 bg-green-900/20 p-6">
        <p className="text-green-400 font-medium">Plan updated successfully.</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 text-sm text-slate-400 hover:text-white transition"
        >
          Refresh page →
        </button>
      </div>
    )
  }

  if (paidTiers.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <p className="text-slate-400 text-sm">
          No plans available for upgrade. Visit{' '}
          <a href="/pricing" className="text-copper-400 hover:underline">pricing page</a>.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {paidTiers.map((tier) => {
          const isCurrent = tier.stripe_price_id === currentSubscription?.stripe_price_id
          const isSelected = tier.stripe_price_id === selectedPriceId
          return (
            <button
              key={tier.name}
              onClick={() => setSelectedPriceId(tier.stripe_price_id ?? null)}
              disabled={isCurrent}
              className={`text-left p-5 rounded-xl border transition ${
                isCurrent
                  ? 'border-slate-700 bg-slate-900/50 opacity-60 cursor-not-allowed'
                  : isSelected
                  ? 'border-copper-500 bg-copper-900/20'
                  : 'border-slate-800 bg-slate-900 hover:border-slate-600'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-white">{tier.name}</span>
                {isCurrent && (
                  <span className="text-xs text-slate-500 font-medium">Current</span>
                )}
              </div>
              <p className="text-copper-400 font-bold text-lg">
                ${((tier.price_cents ?? 0) / 100).toFixed(0)}/mo
              </p>
              {tier.description && (
                <p className="text-slate-400 text-xs mt-2 line-clamp-2">{tier.description}</p>
              )}
            </button>
          )
        })}
      </div>

      {error && (
        <p className="text-red-400 text-sm p-3 bg-red-900/20 rounded-lg border border-red-800">
          {error}
        </p>
      )}

      <button
        onClick={handleUpgrade}
        disabled={!selectedPriceId || loading}
        className="px-6 py-2.5 bg-copper-600 text-white rounded-lg font-medium hover:bg-copper-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Updating…' : 'Confirm Plan Change'}
      </button>
    </div>
  )
}
