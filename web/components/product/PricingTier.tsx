import type { PricingTier as PricingTierType } from '@/lib/pricing'

export default function PricingTier({ tier, featured = false }: { tier: PricingTierType; featured?: boolean }) {
  return (
    <div className={`p-8 rounded-xl border ${featured ? 'border-copper-500/60 bg-copper-500/5' : 'border-slate-800'}`}>
      <h3 className="text-xl font-bold text-white mb-1">{tier.name}</h3>
      <p className="text-sm text-slate-400 mb-4">{tier.tagline}</p>
      <div className="mb-6">
        <span className="text-4xl font-bold font-mono text-white">
          {tier.price_monthly === 0
            ? (tier.name.toLowerCase().includes('custom') ? 'Contact Sales' : 'Free')
            : `$${tier.price_monthly}`}
        </span>
        {tier.price_monthly > 0 && <span className="text-slate-400 text-sm">/month</span>}
      </div>
      <ul className="space-y-2 mb-6">
        {tier.includes.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm text-slate-300">
            <span className="text-copper-500 mt-0.5">+</span>
            {feature}
          </li>
        ))}
      </ul>
      <p className="text-xs text-slate-500 font-mono">{tier.cost_basis}</p>
    </div>
  )
}
