import Link from 'next/link'
import { getManifest } from '@/lib/manifest'

export default function PathFork() {
  const m = getManifest()

  const paths = [
    {
      title: "I'm Building AI Products",
      description: `Platform architecture, DevFlow, ArchitectFlow, ${m.platform.api_endpoints.total} API endpoints, ${m.ag_mesh.agent_profiles} agent profiles, and AG Mesh event orchestration.`,
      href: '/solutions?audience=builder',
      accent: 'copper' as const,
      features: ['Agent Orchestration', 'Multi-Cloud Deploy', 'Tool Calling', 'MCP Protocol'],
    },
    {
      title: 'I Want AI Running My Business',
      description: 'Property management, financial automation, customer lifecycle, scheduling, and team coordination -- all event-driven.',
      href: '/solutions?audience=business',
      accent: 'blue' as const,
      features: ['Property Management', 'Finance & Billing', 'Customer Lifecycle', 'Scheduling'],
    },
  ]

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-white text-center mb-4">What brings you here?</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">The Mahoosuc OS serves two worlds. Choose your path.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {paths.map((path) => (
            <Link key={path.title} href={path.href}
              className={`group block p-8 rounded-xl border transition-all duration-200 ${
                path.accent === 'copper'
                  ? 'border-copper-500/30 hover:border-copper-500/60 hover:bg-copper-500/5'
                  : 'border-mahoosuc-blue-400/30 hover:border-mahoosuc-blue-400/60 hover:bg-mahoosuc-blue-500/5'
              }`}>
              <h3 className={`text-2xl font-bold mb-3 ${path.accent === 'copper' ? 'text-copper-400' : 'text-mahoosuc-blue-300'}`}>
                {path.title}
              </h3>
              <p className="text-slate-300 mb-6">{path.description}</p>
              <div className="flex flex-wrap gap-2">
                {path.features.map((f) => (
                  <span key={f} className={`text-xs font-mono px-2 py-1 rounded ${
                    path.accent === 'copper' ? 'bg-copper-500/10 text-copper-300' : 'bg-mahoosuc-blue-500/10 text-mahoosuc-blue-300'
                  }`}>{f}</span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
