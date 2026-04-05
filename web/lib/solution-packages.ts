import fs from 'fs'
import path from 'path'

export interface SolutionPackage {
  slug: string
  name: string
  tagline: string
  description: string
  category: string
  tier: string
  monthly: number
  one_time_setup: number
  annual_discount_pct: number
  status: string
}

const SOLUTIONS_DIR = path.join(process.cwd(), '..', 'solutions')

export function getSolutionPackages(): SolutionPackage[] {
  if (!fs.existsSync(SOLUTIONS_DIR)) {
    return []
  }

  return fs.readdirSync(SOLUTIONS_DIR)
    .filter((entry) => !entry.startsWith('_'))
    .map((entry) => path.join(SOLUTIONS_DIR, entry, 'solution.json'))
    .filter((file) => fs.existsSync(file))
    .map((file) => JSON.parse(fs.readFileSync(file, 'utf-8')))
    .map((solution) => ({
      slug: solution.slug,
      name: solution.name,
      tagline: solution.tagline,
      description: solution.description ?? '',
      category: solution.category,
      tier: solution.tier,
      monthly: solution.pricing?.monthly ?? 0,
      one_time_setup: solution.pricing?.one_time_setup ?? 0,
      annual_discount_pct: solution.pricing?.annual_discount_pct ?? 0,
      status: solution.status ?? 'draft',
    }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

export function getSolutionPackageBySlug(slug: string): SolutionPackage | undefined {
  return getSolutionPackages().find((solution) => solution.slug === slug)
}
