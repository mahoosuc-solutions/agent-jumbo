import type { Metadata } from 'next'
import { getProductBySlug, getProducts } from '@/lib/manifest'
import { getSolutionPackageBySlug, getSolutionPackages } from '@/lib/solution-packages'
import { notFound } from 'next/navigation'

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const product = getProductBySlug(params.slug)
  const solutionPackage = getSolutionPackageBySlug(params.slug)
  if (!product && !solutionPackage) return { title: 'Not Found' }
  const resolved = solutionPackage ?? product!
  return { title: resolved.name, description: resolved.description }
}

export function generateStaticParams() {
  return [
    ...getProducts().map((p) => ({ slug: p.slug })),
    ...getSolutionPackages().map((solution) => ({ slug: solution.slug })),
  ]
}

export default function SolutionDetailPage({ params }: { params: { slug: string } }) {
  const product = getProductBySlug(params.slug)
  const solutionPackage = getSolutionPackageBySlug(params.slug)
  if (!product && !solutionPackage) notFound()

  if (solutionPackage && !product) {
    return (
      <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
        <a href="/pricing" className="text-sm text-copper-400 hover:text-copper-300 mb-6 inline-block">Pricing</a>
        <h1 className="text-4xl font-bold text-white mb-2">{solutionPackage.name}</h1>
        <p className="text-copper-400 font-mono text-sm mb-6">{solutionPackage.tagline}</p>
        <p className="text-lg text-slate-300 mb-10">{solutionPackage.description}</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-5">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Setup</p>
            <p className="text-3xl font-bold text-white">${solutionPackage.one_time_setup.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-5">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Monthly</p>
            <p className="text-3xl font-bold text-white">${solutionPackage.monthly.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-5">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Annual Discount</p>
            <p className="text-3xl font-bold text-white">{solutionPackage.annual_discount_pct}%</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">{solutionPackage.category}</span>
          <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">{solutionPackage.tier}</span>
          <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">{solutionPackage.status}</span>
        </div>
      </div>
    )
  }

  const resolvedProduct = product!

  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
      <a href="/solutions" className="text-sm text-copper-400 hover:text-copper-300 mb-6 inline-block">All Solutions</a>
      <h1 className="text-4xl font-bold text-white mb-2">{resolvedProduct.name}</h1>
      <p className="text-copper-400 font-mono text-sm mb-6">{resolvedProduct.tagline}</p>
      <p className="text-lg text-slate-300 mb-12">{resolvedProduct.description}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Instruments</h2>
          <ul className="space-y-2">
            {resolvedProduct.instruments.map((i) => (
              <li key={i} className="text-sm font-mono text-slate-400 flex items-center gap-2">
                <span className="text-copper-500">+</span> {i}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Tools</h2>
          <ul className="space-y-2">
            {resolvedProduct.tools.map((t) => (
              <li key={t} className="text-sm font-mono text-slate-400 flex items-center gap-2">
                <span className="text-copper-500">+</span> {t}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Integrations</h2>
          <div className="flex flex-wrap gap-2">
            {resolvedProduct.integrations.map((i) => (
              <span key={i} className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">{i}</span>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-lg font-bold text-white mb-4">AG Mesh Events</h2>
          <div className="flex flex-wrap gap-2">
            {resolvedProduct.ag_mesh_events.map((e) => (
              <span key={e} className="text-xs font-mono px-2 py-1 rounded bg-copper-500/10 text-copper-300">{e}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
