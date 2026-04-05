import type { Metadata } from 'next'
import { SubscriptionCard } from '@/components/billing/SubscriptionCard'
import { PlanSelector } from '@/components/billing/PlanSelector'

export const metadata: Metadata = { title: 'Subscription' }

async function getSubscriptionData() {
  const backendUrl = process.env.FLASK_BACKEND_URL || 'http://localhost:50001'
  try {
    const res = await fetch(`${backendUrl}/billing/summary`, { cache: 'no-store' })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function SubscriptionPage() {
  const data = await getSubscriptionData()

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Subscription</h1>
        <p className="text-slate-400 text-sm mt-1">Manage your plan and billing cycle.</p>
      </div>

      <SubscriptionCard
        subscription={data?.subscription ?? null}
        customer={data?.customer ?? null}
        showActions
      />

      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Change Plan</h2>
        <PlanSelector currentSubscription={data?.subscription ?? null} />
      </div>
    </div>
  )
}
