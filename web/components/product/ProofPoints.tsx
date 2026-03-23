import { getManifest } from '@/lib/manifest'

export default function ProofPoints() {
  const m = getManifest()
  const metrics = [
    { value: m.platform.commands.total, label: 'Commands & SOPs', suffix: '+' },
    { value: m.platform.instruments.active, label: 'Integrated Solutions', suffix: '' },
    { value: m.platform.tools.total, label: 'Native Tools', suffix: '+' },
    { value: m.platform.api_endpoints.total, label: 'API Endpoints', suffix: '' },
    { value: m.platform.integrations.length, label: 'Live Integrations', suffix: '' },
    { value: m.ag_mesh.agent_profiles, label: 'Agent Profiles', suffix: '' },
  ]

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 border-y border-slate-800">
      <div className="max-w-7xl mx-auto">
        <p className="text-center text-xs font-mono text-slate-500 mb-8 tracking-widest uppercase">
          Code-Validated Metrics
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8">
          {metrics.map((metric) => (
            <div key={metric.label} className="text-center">
              <div className="text-3xl font-bold font-mono text-copper-400">{metric.value}{metric.suffix}</div>
              <div className="text-sm text-slate-400 mt-1">{metric.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
