// web/lib/pricing.ts
import manifestData from '../public/platform-manifest.json'

export interface PricingTier {
  name: string
  price_monthly: number
  tagline: string
  includes: string[]
  limits: Record<string, number | string>
  cost_basis: string
  description?: string
  price_cents?: number
  stripe_price_id?: string
}

export interface PricingModel {
  cost_components: Array<{
    name: string
    unit: string
    cost_low: number
    cost_high: number
    notes: string
  }>
  tiers: PricingTier[]
  competitive_reference: Array<{
    competitor: string
    tier: string
    price: number
    comparison_notes: string
  }>
  assumptions: string[]
}

const emptyPricing: PricingModel = {
  tiers: [],
  cost_components: [],
  competitive_reference: [],
  assumptions: [],
}

export function getPricingModel(): PricingModel {
  const data = manifestData as unknown as Record<string, unknown>
  return (data.pricing as PricingModel) || emptyPricing
}

export function getTiers(): PricingTier[] {
  return (getPricingModel().tiers || []).map((tier) => ({
    ...tier,
    description: tier.description ?? tier.cost_basis,
    price_cents: tier.price_cents ?? Math.round((tier.price_monthly || 0) * 100),
  }))
}
