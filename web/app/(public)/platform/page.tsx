import type { Metadata } from 'next'
import PlatformMap from '@/components/product/PlatformMap'
import ProofPoints from '@/components/product/ProofPoints'
import { getManifest } from '@/lib/manifest'

export const metadata: Metadata = {
  title: 'Platform Architecture',
  description: 'Explore the Mahoosuc OS platform -- AG Mesh event bus, integrated solutions, and agent orchestration.',
}

export default function PlatformPage() {
  const m = getManifest()
  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold text-white mb-4">Platform Architecture</h1>
      <p className="text-xl text-slate-400 mb-12">
        The Mahoosuc OS connects {m.platform.instruments.active} integrated solutions through the AG Mesh event bus. Every component communicates via typed events with risk-based approval workflows.
      </p>
      <PlatformMap />
      <div className="mt-16"><ProofPoints /></div>
    </div>
  )
}
