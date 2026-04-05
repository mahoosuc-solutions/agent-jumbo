'use client'

import { useState } from 'react'

interface PaymentMethod {
  id: string
  type: string
  card?: {
    brand?: string
    last4?: string
    exp_month?: number
    exp_year?: number
  }
}

interface Props {
  provider: string
  paymentMethods: PaymentMethod[]
  customerId: string
}

export function PaymentMethodManager({ provider, paymentMethods, customerId }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function openBillingPortal() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/backend/billing/portal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ return_url: window.location.href }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? 'Could not open billing portal')
      }
      const data = await res.json()
      if (data.portal_url) {
        window.location.href = data.portal_url
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open portal')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Current payment methods */}
      {paymentMethods.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 divide-y divide-slate-800">
          {paymentMethods.map((pm) => (
            <div key={pm.id} className="flex items-center gap-4 px-5 py-4">
              <div className="w-10 h-7 rounded bg-slate-800 flex items-center justify-center text-slate-400 text-xs font-bold uppercase">
                {pm.card?.brand?.slice(0, 4) ?? pm.type.slice(0, 4)}
              </div>
              <div>
                {pm.card ? (
                  <>
                    <p className="text-white text-sm font-medium">
                      {pm.card.brand
                        ? `${pm.card.brand.charAt(0).toUpperCase()}${pm.card.brand.slice(1)} `
                        : ''}
                      •••• {pm.card.last4}
                    </p>
                    {pm.card.exp_month && pm.card.exp_year && (
                      <p className="text-slate-400 text-xs">
                        Expires {pm.card.exp_month}/{pm.card.exp_year}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-white text-sm font-medium capitalize">{pm.type}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Provider portal button or instructions */}
      {provider === 'stripe' ? (
        <div>
          <p className="text-slate-400 text-sm mb-4">
            To update your payment method, you will be redirected to our secure billing portal.
          </p>
          {error && (
            <p className="text-red-400 text-sm mb-3 p-3 bg-red-900/20 rounded-lg border border-red-800">
              {error}
            </p>
          )}
          <button
            onClick={openBillingPortal}
            disabled={loading}
            className="px-5 py-2.5 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-700 transition disabled:opacity-50"
          >
            {loading ? 'Opening portal…' : 'Manage Payment Method →'}
          </button>
        </div>
      ) : provider === 'square' ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-slate-400 text-sm mb-4">
            To update your Square payment method, visit your Square account settings.
          </p>
          <a
            href={`https://squareup.com/dashboard/customers/${customerId}`}
            target="_blank"
            rel="noreferrer"
            className="px-5 py-2.5 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-700 transition inline-block"
          >
            Open Square Dashboard ↗
          </a>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-slate-400 text-sm mb-4">
            To update your PayPal payment method, visit your PayPal account.
          </p>
          <a
            href="https://www.paypal.com/myaccount/autopay/"
            target="_blank"
            rel="noreferrer"
            className="px-5 py-2.5 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-700 transition inline-block"
          >
            Open PayPal Account ↗
          </a>
        </div>
      )}
    </div>
  )
}
