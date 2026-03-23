import Link from 'next/link'
import type { Product } from '@/lib/manifest'

export default function SolutionCard({ product }: { product: Product }) {
  return (
    <Link href={`/solutions/${product.slug}`}
      className="group block p-6 rounded-xl border border-slate-800 hover:border-copper-500/40 transition-all duration-200 hover:bg-slate-800/50">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-bold text-white group-hover:text-copper-400 transition">{product.name}</h3>
        <span className={`text-xs font-mono px-2 py-0.5 rounded ${
          product.audience === 'builder' ? 'bg-copper-500/10 text-copper-400'
            : product.audience === 'business' ? 'bg-mahoosuc-blue-500/10 text-mahoosuc-blue-300'
            : 'bg-slate-700 text-slate-300'
        }`}>{product.audience}</span>
      </div>
      <p className="text-sm text-slate-400 mb-4">{product.tagline}</p>
      <div className="flex flex-wrap gap-1.5">
        {product.integrations.slice(0, 4).map((i) => (
          <span key={i} className="text-xs font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{i}</span>
        ))}
        <span className="text-xs font-mono text-slate-500">{product.instruments.length} instruments</span>
      </div>
    </Link>
  )
}
