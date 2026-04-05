import type { Metadata } from 'next'
import { PaymentMethodManager } from '@/components/billing/PaymentMethodManager'

export const metadata: Metadata = { title: 'Payment Method' }

async function getPaymentData() {
  const backendUrl = process.env.FLASK_BACKEND_URL || 'http://localhost:50001'
  try {
    const res = await fetch(`${backendUrl}/billing/summary`, { cache: 'no-store' })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function PaymentMethodPage() {
  const data = await getPaymentData()
  const provider = data?.customer?.provider ?? 'stripe'
  const paymentMethods = data?.payment_methods ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Payment Method</h1>
        <p className="text-slate-400 text-sm mt-1">
          Update the card or payment account on file.
        </p>
      </div>

      <PaymentMethodManager
        provider={provider}
        paymentMethods={paymentMethods}
        customerId={data?.customer?.id ?? ''}
      />
    </div>
  )
}
