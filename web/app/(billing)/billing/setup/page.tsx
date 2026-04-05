import type { Metadata } from 'next'
import { StripeSetupWorkspace } from '@/components/billing/StripeSetupWorkspace'

export const metadata: Metadata = { title: 'Setup Assistant' }

export default function BillingSetupPage() {
  return <StripeSetupWorkspace />
}
