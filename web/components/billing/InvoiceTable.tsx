'use client'

interface Invoice {
  stripe_invoice_id: string
  status: string
  amount_due?: number
  amount_paid?: number
  currency?: string
  created_at?: string
  hosted_url?: string
  pdf_url?: string
}

interface Props {
  invoices: Invoice[]
  showAll?: boolean
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    paid: 'bg-green-900/50 text-green-400',
    open: 'bg-blue-900/50 text-blue-400',
    draft: 'bg-slate-800 text-slate-400',
    void: 'bg-slate-800 text-slate-500',
    uncollectible: 'bg-red-900/50 text-red-400',
    past_due: 'bg-yellow-900/50 text-yellow-400',
  }
  return map[status] ?? 'bg-slate-800 text-slate-400'
}

function formatAmount(cents: number, currency = 'usd') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
  }).format(cents / 100)
}

export function InvoiceTable({ invoices, showAll = false }: Props) {
  if (invoices.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-center">
        <p className="text-slate-400 text-sm">No invoices yet.</p>
      </div>
    )
  }

  const displayed = showAll ? invoices : invoices.slice(0, 5)

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Invoice</th>
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Date</th>
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Amount</th>
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Status</th>
            <th className="text-right px-5 py-3 text-slate-500 font-medium">Download</th>
          </tr>
        </thead>
        <tbody>
          {displayed.map((inv) => (
            <tr key={inv.stripe_invoice_id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition">
              <td className="px-5 py-3 text-slate-300 font-mono text-xs">
                {inv.stripe_invoice_id.slice(0, 18)}…
              </td>
              <td className="px-5 py-3 text-slate-400">
                {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : '—'}
              </td>
              <td className="px-5 py-3 text-white font-medium">
                {inv.amount_due != null ? formatAmount(inv.amount_due, inv.currency) : '—'}
              </td>
              <td className="px-5 py-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(inv.status)}`}>
                  {inv.status}
                </span>
              </td>
              <td className="px-5 py-3 text-right">
                {inv.pdf_url ? (
                  <a
                    href={inv.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-copper-400 hover:text-copper-300 transition text-xs"
                  >
                    PDF ↗
                  </a>
                ) : inv.hosted_url ? (
                  <a
                    href={inv.hosted_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-copper-400 hover:text-copper-300 transition text-xs"
                  >
                    View ↗
                  </a>
                ) : (
                  <span className="text-slate-600 text-xs">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
