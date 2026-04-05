import type { Metadata } from 'next'
import { InvoiceTable } from '@/components/billing/InvoiceTable'

export const metadata: Metadata = { title: 'Invoices' }

async function getAllInvoices() {
  const backendUrl = process.env.FLASK_BACKEND_URL || 'http://localhost:50001'
  try {
    const res = await fetch(`${backendUrl}/billing/summary`, { cache: 'no-store' })
    if (!res.ok) return []
    const data = await res.json()
    return data.all_subscriptions ? data.recent_invoices ?? [] : []
  } catch {
    return []
  }
}

export default async function InvoicesPage() {
  const invoices = await getAllInvoices()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Invoices</h1>
        <p className="text-slate-400 text-sm mt-1">Full invoice history for your account.</p>
      </div>
      <InvoiceTable invoices={invoices} showAll />
    </div>
  )
}
