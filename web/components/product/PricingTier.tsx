import Link from 'next/link'
import type { PricingTier as PricingTierType } from '@/lib/pricing'

export default function PricingTier({ tier, featured = false }: { tier: PricingTierType; featured?: boolean }) {
  const isCustom = tier.name.toLowerCase().includes('custom')
  const isFree = tier.price_monthly === 0 && !isCustom

  const priceLabel = isCustom
    ? 'Contact Sales'
    : isFree
      ? 'Free'
      : `$${tier.price_monthly}`

  const ctaLabel = tier.cta_label ?? (isCustom ? 'Contact Sales' : isFree ? 'Get Started' : `Get ${tier.name}`)
  const ctaHref = tier.cta_href ?? (isCustom ? '/demo' : '/signup')

  return (
    <div
      className={`relative flex flex-col p-8 rounded-xl border transition-shadow ${
        featured
          ? 'border-copper-500/60 bg-copper-500/5 shadow-lg shadow-copper-500/10'
          : 'border-slate-800 bg-slate-950/40'
      }`}
    >
      {tier.highlight && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-xs font-semibold bg-copper-500 text-white shadow">
          {tier.highlight}
        </span>
      )}

      <h3 className="text-xl font-bold text-white mb-1">{tier.name}</h3>
      <p className="text-sm text-slate-400 mb-4 leading-snug">{tier.tagline}</p>

      <div className="mb-6">
        <span className="text-4xl font-bold font-mono text-white">{priceLabel}</span>
        {tier.price_monthly > 0 && <span className="text-slate-400 text-sm ml-1">/month</span>}
      </div>

      <ul className="space-y-2 mb-6 flex-1">
        {tier.includes.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm text-slate-300">
            <span className="text-copper-500 mt-0.5 shrink-0">+</span>
            {feature}
          </li>
        ))}
      </ul>

      <Link
        href={ctaHref}
        className={`mt-auto block text-center py-2.5 px-4 rounded-lg text-sm font-semibold transition ${
          featured
            ? 'bg-copper-500 text-white hover:bg-copper-400'
            : 'bg-slate-800 text-slate-200 hover:bg-slate-700'
        }`}
      >
        {ctaLabel}
      </Link>

      <p className="text-xs text-slate-600 font-mono mt-4 leading-relaxed">{tier.cost_basis}</p>
    </div>
  )
}
