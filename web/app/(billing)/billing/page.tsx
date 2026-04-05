import type { Metadata } from 'next'
import { SubscriptionCard } from '@/components/billing/SubscriptionCard'
import { InvoiceTable } from '@/components/billing/InvoiceTable'

export const metadata: Metadata = { title: 'Billing' }

async function getBillingSummary() {
  const backendUrl = process.env.FLASK_BACKEND_URL || 'http://localhost:50001'
  try {
    const res = await fetch(`${backendUrl}/billing/summary`, {
      cache: 'no-store',
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function BillingPage() {
  const data = await getBillingSummary()

  if (!data) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 text-lg">Unable to load billing information.</p>
        <p className="text-slate-500 text-sm mt-2">Make sure you are signed in.</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Billing</h1>
        <p className="text-slate-400 text-sm mt-1">
          Manage your subscription, invoices, and payment method.
        </p>
      </div>

      {/* Subscription card */}
      <SubscriptionCard
        subscription={data.subscription}
        customer={data.customer}
      />

      {/* Recent invoices */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Recent Invoices</h2>
          <a href="/billing/invoices" className="text-sm text-copper-400 hover:text-copper-300 transition">
            View all →
          </a>
        </div>
        <InvoiceTable invoices={data.recent_invoices ?? []} />
      </div>
    </div>
  )
}
