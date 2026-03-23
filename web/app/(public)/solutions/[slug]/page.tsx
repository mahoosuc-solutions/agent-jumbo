import type { Metadata } from 'next'
import { getProductBySlug, getProducts } from '@/lib/manifest'
import { notFound } from 'next/navigation'

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const product = getProductBySlug(params.slug)
  if (!product) return { title: 'Not Found' }
  return { title: product.name, description: product.description }
}

export function generateStaticParams() {
  return getProducts().map((p) => ({ slug: p.slug }))
}

export default function SolutionDetailPage({ params }: { params: { slug: string } }) {
  const product = getProductBySlug(params.slug)
  if (!product) notFound()

  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
      <a href="/solutions" className="text-sm text-copper-400 hover:text-copper-300 mb-6 inline-block">All Solutions</a>
      <h1 className="text-4xl font-bold text-white mb-2">{product.name}</h1>
      <p className="text-copper-400 font-mono text-sm mb-6">{product.tagline}</p>
      <p className="text-lg text-slate-300 mb-12">{product.description}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Instruments</h2>
          <ul className="space-y-2">
            {product.instruments.map((i) => (
              <li key={i} className="text-sm font-mono text-slate-400 flex items-center gap-2">
                <span className="text-copper-500">+</span> {i}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Tools</h2>
          <ul className="space-y-2">
            {product.tools.map((t) => (
              <li key={t} className="text-sm font-mono text-slate-400 flex items-center gap-2">
                <span className="text-copper-500">+</span> {t}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Integrations</h2>
          <div className="flex flex-wrap gap-2">
            {product.integrations.map((i) => (
              <span key={i} className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">{i}</span>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-lg font-bold text-white mb-4">AG Mesh Events</h2>
          <div className="flex flex-wrap gap-2">
            {product.ag_mesh_events.map((e) => (
              <span key={e} className="text-xs font-mono px-2 py-1 rounded bg-copper-500/10 text-copper-300">{e}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
