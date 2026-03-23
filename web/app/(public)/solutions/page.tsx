import type { Metadata } from 'next'
import SolutionCard from '@/components/product/SolutionCard'
import { getProducts } from '@/lib/manifest'

export const metadata: Metadata = {
  title: 'Solutions',
  description: 'Explore the named products within the Mahoosuc OS -- each backed by real instruments, tools, and integrations.',
}

export default function SolutionsPage({ searchParams }: { searchParams: { audience?: string } }) {
  const allProducts = getProducts()
  const audience = searchParams.audience
  const products = audience
    ? allProducts.filter((p) => p.audience === audience || p.audience === 'both')
    : allProducts

  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold text-white mb-4">Solutions</h1>
      <p className="text-xl text-slate-400 mb-8">
        {audience === 'builder' ? 'Tools and frameworks for building AI-powered products.'
          : audience === 'business' ? 'AI automation for your business operations.'
          : 'Every solution in the Mahoosuc OS ecosystem.'}
      </p>
      {audience && <a href="/solutions" className="text-sm text-copper-400 hover:text-copper-300 mb-8 inline-block">View all solutions</a>}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-4">
        {products.map((product) => (
          <SolutionCard key={product.slug} product={product} />
        ))}
      </div>
    </div>
  )
}
