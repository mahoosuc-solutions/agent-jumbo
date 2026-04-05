import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: {
    default: 'Billing',
    template: '%s | Billing | Agent Jumbo',
  },
}

export default function BillingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="border-b border-slate-800 bg-slate-900">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-1">
              <Link
                href="/billing"
                className="px-3 py-2 text-sm text-slate-300 hover:text-white rounded-md hover:bg-slate-800 transition"
              >
                Overview
              </Link>
              <Link
                href="/billing/invoices"
                className="px-3 py-2 text-sm text-slate-300 hover:text-white rounded-md hover:bg-slate-800 transition"
              >
                Invoices
              </Link>
              <Link
                href="/billing/subscription"
                className="px-3 py-2 text-sm text-slate-300 hover:text-white rounded-md hover:bg-slate-800 transition"
              >
                Subscription
              </Link>
              <Link
                href="/billing/payment-method"
                className="px-3 py-2 text-sm text-slate-300 hover:text-white rounded-md hover:bg-slate-800 transition"
              >
                Payment Method
              </Link>
              <Link
                href="/billing/setup"
                className="px-3 py-2 text-sm text-slate-300 hover:text-white rounded-md hover:bg-slate-800 transition"
              >
                Setup Assistant
              </Link>
            </div>
            <Link href="/" className="text-xs text-slate-500 hover:text-slate-300 transition">
              ← Back to Agent Jumbo
            </Link>
          </div>
        </div>
      </nav>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {children}
      </main>
    </div>
  )
}
