// web/lib/manifest.ts
import manifestData from '../public/platform-manifest.json'

export interface PlatformManifest {
  generated_at: string
  platform: {
    commands: { total: number; categories: number }
    instruments: { total: number; active: number }
    tools: { total: number }
    api_endpoints: { total: number }
    integrations: string[]
    helper_modules: number
  }
  github: {
    repos: number
    verticals: string[]
  }
  ag_mesh: {
    event_types: string[]
    risk_levels: string[]
    agent_profiles: number
  }
  products: Product[]
  pricing?: {
    tiers: Array<{
      name: string
      price_monthly: number
      tagline: string
      includes: string[]
      limits: Record<string, number | string>
      cost_basis: string
    }>
    cost_components: Array<{
      name: string
      unit: string
      cost_low: number
      cost_high: number
      notes: string
    }>
    competitive_reference: Array<{
      competitor: string
      tier: string
      price: number
      comparison_notes: string
    }>
    assumptions: string[]
  }
}

export interface Product {
  slug: string
  name: string
  tagline: string
  description: string
  audience: 'builder' | 'business' | 'both'
  instruments: string[]
  tools: string[]
  repos: string[]
  integrations: string[]
  ag_mesh_events: string[]
  icon_suggestion: string
}

export function getManifest(): PlatformManifest {
  return manifestData as unknown as PlatformManifest
}

export function getProducts(): Product[] {
  return (manifestData as unknown as PlatformManifest).products || []
}

export function getProductBySlug(slug: string): Product | undefined {
  return getProducts().find((p) => p.slug === slug)
}
