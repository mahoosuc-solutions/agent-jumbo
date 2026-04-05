'use client'

import { useState } from 'react'
import { CancelModal } from './CancelModal'

interface Subscription {
  stripe_subscription_id: string
  status: string
  current_period_end?: string
  cancel_at_period_end?: number
  amount_cents?: number
  recurring_interval?: string
  stripe_price_id?: string
}

interface Customer {
  email?: string
  name?: string
  provider?: string
}

interface Props {
  subscription: Subscription | null
  customer: Customer | null
  showActions?: boolean
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    active: 'bg-green-900/50 text-green-400 border-green-700',
    trialing: 'bg-blue-900/50 text-blue-400 border-blue-700',
    past_due: 'bg-yellow-900/50 text-yellow-400 border-yellow-700',
    canceled: 'bg-slate-800 text-slate-400 border-slate-700',
    incomplete: 'bg-orange-900/50 text-orange-400 border-orange-700',
  }
  return map[status] ?? 'bg-slate-800 text-slate-400 border-slate-700'
}

export function SubscriptionCard({ subscription, customer, showActions = false }: Props) {
  const [showCancel, setShowCancel] = useState(false)

  if (!subscription) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <p className="text-slate-400">No active subscription.</p>
        <a
          href="/pricing"
          className="mt-4 inline-block px-4 py-2 bg-copper-600 text-white rounded-lg text-sm font-medium hover:bg-copper-500 transition"
        >
          View Plans
        </a>
      </div>
    )
  }

  const amount = subscription.amount_cents
    ? `$${(subscription.amount_cents / 100).toFixed(2)} / ${subscription.recurring_interval ?? 'mo'}`
    : 'Custom pricing'

  const periodEnd = subscription.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString()
    : '—'

  const cancelScheduled = subscription.cancel_at_period_end === 1

  return (
    <>
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-white font-semibold text-lg">Current Plan</span>
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${statusBadge(subscription.status)}`}>
                {subscription.status}
              </span>
              {cancelScheduled && (
                <span className="text-xs px-2 py-0.5 rounded-full border bg-orange-900/50 text-orange-400 border-orange-700">
                  Cancels {periodEnd}
                </span>
              )}
            </div>
            <p className="text-2xl font-bold text-white">{amount}</p>
            {customer?.email && (
              <p className="text-slate-400 text-sm mt-1">{customer.email}</p>
            )}
          </div>
          <div className="text-right">
            <p className="text-slate-500 text-xs">Next billing</p>
            <p className="text-slate-300 text-sm font-medium">{periodEnd}</p>
          </div>
        </div>

        {showActions && !cancelScheduled && subscription.status !== 'canceled' && (
          <div className="mt-6 flex gap-3">
            <a
              href="/billing/subscription"
              className="px-4 py-2 bg-slate-800 text-slate-200 rounded-lg text-sm hover:bg-slate-700 transition"
            >
              Change Plan
            </a>
            <button
              onClick={() => setShowCancel(true)}
              className="px-4 py-2 text-red-400 border border-red-800 rounded-lg text-sm hover:bg-red-900/30 transition"
            >
              Cancel Subscription
            </button>
          </div>
        )}
      </div>

      {showCancel && (
        <CancelModal
          periodEnd={periodEnd}
          onClose={() => setShowCancel(false)}
        />
      )}
    </>
  )
}
