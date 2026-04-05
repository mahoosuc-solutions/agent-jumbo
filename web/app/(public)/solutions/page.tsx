import type { Metadata } from 'next'
import Link from 'next/link'
import SolutionCard from '@/components/product/SolutionCard'
import { getProducts } from '@/lib/manifest'
import { getSolutionPackages } from '@/lib/solution-packages'

export const metadata: Metadata = {
  title: 'Solutions',
  description: 'Explore the named products within the Mahoosuc OS -- each backed by real instruments, tools, and integrations.',
}

export default async function SolutionsPage({
  searchParams,
}: {
  searchParams: Promise<{ audience?: string }>
}) {
  const { audience } = await searchParams
  const allProducts = getProducts()
  const products = audience
    ? allProducts.filter((p) => p.audience === audience || p.audience === 'both')
    : allProducts

  // Solution packages are not filtered by audience (they're all business-facing)
  const packages = audience && audience !== 'business' ? [] : getSolutionPackages()

  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold text-white mb-4">Solutions</h1>
      <p className="text-xl text-slate-400 mb-8">
        {audience === 'builder'
          ? 'Tools and frameworks for building AI-powered products.'
          : audience === 'business'
            ? 'AI automation for your business operations.'
            : 'Every solution in the Mahoosuc OS ecosystem.'}
      </p>
      {audience && (
        <a href="/solutions" className="text-sm text-copper-400 hover:text-copper-300 mb-8 inline-block">
          View all solutions
        </a>
      )}

      {/* Platform products */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-4">
        {products.map((product) => (
          <SolutionCard key={product.slug} product={product} />
        ))}
      </div>

      {/* Named AI solution packages */}
      {packages.length > 0 && (
        <div className="mt-20">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">AI Solution Packages</h2>
            <p className="text-slate-400">
              Vertical AI packages with a one-time setup and monthly operating fee. Each includes full implementation and ongoing automation.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {packages.map((pkg) => (
              <Link
                key={pkg.slug}
                href={`/solutions/${pkg.slug}`}
                className="group block p-6 rounded-xl border border-slate-800 hover:border-copper-500/40 transition-all duration-200 hover:bg-slate-800/50"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-lg font-bold text-white group-hover:text-copper-400 transition">{pkg.name}</h3>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-700 text-slate-300">{pkg.status}</span>
                </div>
                <p className="text-sm text-slate-400 mb-4">{pkg.tagline}</p>
                <div className="flex flex-wrap gap-2 text-xs font-mono text-slate-500">
                  <span className="px-1.5 py-0.5 rounded bg-slate-800">{pkg.category}</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800">
                    ${pkg.one_time_setup.toLocaleString()} setup · ${pkg.monthly.toLocaleString()}/mo
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
