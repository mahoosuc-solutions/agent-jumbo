import type { Metadata } from 'next'
import { WbmOnboardingWorkspace } from '@/components/billing/WbmOnboardingWorkspace'

export const metadata: Metadata = { title: 'WBM Onboarding' }

export default function WbmOnboardingPage() {
  return <WbmOnboardingWorkspace />
}
