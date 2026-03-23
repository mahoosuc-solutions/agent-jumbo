import { getManifest } from '@/lib/manifest'

export default function PlatformMap() {
  const m = getManifest()
  const products = m.products

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[600px] p-8">
        <div className="flex flex-col items-center mb-12">
          <div className="w-32 h-32 rounded-full border-2 border-copper-500/60 bg-copper-500/10 flex items-center justify-center">
            <div className="text-center">
              <div className="text-copper-400 font-mono text-xs uppercase tracking-widest">AG Mesh</div>
              <div className="text-white font-bold text-sm mt-1">Event Bus</div>
              <div className="text-slate-400 font-mono text-xs mt-1">{m.ag_mesh.event_types.length} events</div>
            </div>
          </div>
        </div>
        {products.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {products.map((product) => (
              <a key={product.slug} href={`/solutions/${product.slug}`}
                className="block p-4 rounded-lg border border-slate-800 hover:border-copper-500/40 transition text-center">
                <div className="text-white font-bold text-sm">{product.name}</div>
                <div className="text-slate-400 text-xs mt-1">{product.instruments.length} instruments</div>
                <div className="text-copper-500/60 text-xs font-mono mt-2">{product.ag_mesh_events.length} events</div>
              </a>
            ))}
          </div>
        ) : (
          <p className="text-center text-slate-500 font-mono text-sm">Product catalog loading...</p>
        )}
        <div className="mt-12 flex justify-center gap-8 text-xs font-mono text-slate-500">
          <span>{m.ag_mesh.risk_levels.length} risk levels</span>
          <span>{m.ag_mesh.agent_profiles} agent profiles</span>
          <span>{m.platform.helper_modules} helper modules</span>
        </div>
      </div>
    </div>
  )
}
