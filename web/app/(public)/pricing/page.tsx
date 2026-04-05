import type { Metadata } from 'next'
import PricingTierCard from '@/components/product/PricingTier'
import { getTiers } from '@/lib/pricing'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Mahoosuc OS pricing tiers -- grounded in real cost modeling, not guesswork.',
}

export default function PricingPage() {
  const tiers = getTiers()

  if (tiers.length === 0) {
    return (
      <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-center">
        <h1 className="text-4xl font-bold text-white mb-4">Pricing</h1>
        <p className="text-xl text-slate-400 mb-8">Pricing tiers are being validated against our cost model. Contact us for early access pricing.</p>
        <Link href="/demo" className="px-8 py-3 bg-copper-500 text-white rounded-lg font-semibold hover:bg-copper-400 transition inline-block">Get Demo</Link>
      </div>
    )
  }

  const featuredIndex = Math.min(1, tiers.length - 1)

  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <div className="text-center mb-16">
        <h1 className="text-4xl font-bold text-white mb-4">Pricing</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Every tier is grounded in real cost modeling -- LLM tokens, compute, storage, and integration fees. No hidden costs.</p>
      </div>
      <div className={`grid grid-cols-1 gap-8 max-w-5xl mx-auto ${
        tiers.length >= 3 ? 'md:grid-cols-3' : tiers.length === 2 ? 'md:grid-cols-2' : ''
      }`}>
        {tiers.map((tier, i) => (<PricingTierCard key={tier.name} tier={tier} featured={i === featuredIndex} />))}
      </div>
      <p className="text-center text-xs text-slate-500 font-mono mt-8">Pricing validated by codebase cost analysis.</p>

      <div className="mt-16 max-w-4xl mx-auto rounded-2xl border border-copper-500/20 bg-slate-950/60 p-8">
        <h2 className="text-2xl font-bold text-white mb-4">Support & Compliance</h2>
        <p className="text-slate-300 leading-7">
          Self-serve launch commitments, customer policies, and support escalation paths are published in the documentation surface used at launch.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/documentation/CUSTOMER_SUPPORT" className="px-4 py-2 rounded-lg border border-copper-400/40 text-copper-200 hover:border-copper-300 hover:text-white transition">
            Customer Support
          </Link>
          <Link href="/documentation/PRIVACY_POLICY" className="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 hover:border-slate-500 hover:text-white transition">
            Privacy Policy
          </Link>
          <Link href="/documentation/TERMS_OF_USE" className="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 hover:border-slate-500 hover:text-white transition">
            Terms Of Use
          </Link>
          <Link href="/documentation/DATA_RETENTION_POLICY" className="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 hover:border-slate-500 hover:text-white transition">
            Data Retention
          </Link>
          <Link href="/documentation/DATA_DELETION_POLICY" className="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 hover:border-slate-500 hover:text-white transition">
            Data Deletion
          </Link>
        </div>
      </div>
    </div>
  )
}
