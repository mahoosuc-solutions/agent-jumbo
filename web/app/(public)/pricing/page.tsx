import type { Metadata } from 'next'
import PricingTierCard from '@/components/product/PricingTier'
import { getTiers } from '@/lib/pricing'
import { getSolutionPackages } from '@/lib/solution-packages'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Mahoosuc OS pricing tiers -- grounded in real cost modeling, not guesswork.',
}

export default function PricingPage() {
  const tiers = getTiers()
  const packages = getSolutionPackages()

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

      {packages.length > 0 && (
        <div className="mt-20 max-w-6xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-white mb-3">Solution Packages</h2>
            <p className="text-slate-400 max-w-3xl mx-auto">
              Named AI packages are sold separately from the core platform tiers. Each package includes a one-time setup fee and an ongoing monthly operating fee.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {packages.map((pkg) => (
              <div key={pkg.slug} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-white">{pkg.name}</h3>
                    <p className="text-copper-300 text-sm mt-1">{pkg.tagline}</p>
                  </div>
                  <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300">
                    {pkg.status}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 mb-5">
                  <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4">
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Setup</p>
                    <p className="text-2xl font-bold text-white">${pkg.one_time_setup.toLocaleString()}</p>
                  </div>
                  <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4">
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Monthly</p>
                    <p className="text-2xl font-bold text-white">${pkg.monthly.toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-mono text-slate-400 mb-5">
                  <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800">{pkg.category}</span>
                  <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800">{pkg.tier}</span>
                  <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800">{pkg.annual_discount_pct}% annual discount</span>
                </div>
                <Link href={`/solutions/${pkg.slug}`} className="text-copper-300 hover:text-copper-200 transition">
                  View package details
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

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
