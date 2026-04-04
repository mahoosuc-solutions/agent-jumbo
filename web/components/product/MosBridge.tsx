import Link from 'next/link'

const BRIDGE_EVENTS = [
  'task.created',
  'task.completed',
  'approval.requested',
  'approval.granted',
  'context.shared',
  'alert.triggered',
]

const DOMAINS = [
  { label: 'Real Estate & Property', color: 'text-amber-400', dot: 'bg-amber-400' },
  { label: 'Finance & Investments', color: 'text-emerald-400', dot: 'bg-emerald-400' },
  { label: 'Wellness & Health', color: 'text-cyan-400', dot: 'bg-cyan-400' },
  { label: 'Relationships', color: 'text-rose-400', dot: 'bg-rose-400' },
  { label: 'Calendar & Time', color: 'text-indigo-400', dot: 'bg-indigo-400' },
  { label: 'Projects & Goals', color: 'text-violet-400', dot: 'bg-violet-400' },
]

export default function MosBridge() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-slate-800">
      <div className="max-w-7xl mx-auto">

        {/* Section header */}
        <div className="max-w-2xl mb-16">
          <p className="text-copper-400 font-mono text-sm tracking-widest uppercase mb-3">
            Part of Mahoosuc OS
          </p>
          <h2 className="text-3xl font-bold text-white mb-4">
            Personal OS meets Business OS
          </h2>
          <p className="text-slate-400 text-lg leading-relaxed">
            Agent Jumbo connects to{' '}
            <Link
              href="https://mahoosuc.ai"
              className="text-copper-400 hover:text-copper-300 underline underline-offset-2"
              target="_blank"
              rel="noopener noreferrer"
            >
              Mahoosuc OS
            </Link>{' '}
            through the Agent Mesh Bridge — a Redis Streams architecture for bi-directional task routing. Business decisions flow to Mahoosuc OS governance. Personal decisions stay in Agent Jumbo. Both share the same approval architecture.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">

          {/* Left: domains */}
          <div>
            <h3 className="text-sm font-mono text-slate-400 uppercase tracking-widest mb-6">
              Six Domains Agent Jumbo Manages
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {DOMAINS.map((d) => (
                <div key={d.label} className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${d.dot}`} />
                  <span className={`text-sm font-medium ${d.color}`}>{d.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: bridge visual + events */}
          <div>
            <h3 className="text-sm font-mono text-slate-400 uppercase tracking-widest mb-6">
              Agent Mesh Bridge
            </h3>

            {/* Bridge diagram */}
            <div className="flex items-center justify-between gap-4 mb-8 p-6 rounded-xl bg-slate-800/50 border border-slate-700/50">
              <div className="text-center">
                <div className="w-16 h-16 rounded-full border-2 border-copper-500/60 bg-copper-500/10 flex items-center justify-center mx-auto mb-2">
                  <span className="text-copper-400 font-bold text-xs">AJ</span>
                </div>
                <div className="text-white text-xs font-semibold">Agent Jumbo</div>
                <div className="text-slate-500 text-xs">Personal OS</div>
              </div>

              <div className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full h-px bg-gradient-to-r from-copper-500/40 via-mahoosuc-blue-400/60 to-copper-500/40 relative">
                  <div className="absolute inset-0 overflow-hidden">
                    <div className="h-px bg-copper-400/60 animate-pulse w-1/3" style={{ marginLeft: '33%' }} />
                  </div>
                </div>
                <div className="text-slate-500 text-xs font-mono">agentmesh:events</div>
                <div className="w-full h-px bg-gradient-to-r from-mahoosuc-blue-400/40 via-copper-500/60 to-mahoosuc-blue-400/40" />
              </div>

              <div className="text-center">
                <div className="w-16 h-16 rounded-full border-2 border-mahoosuc-blue-500/60 bg-mahoosuc-blue-500/10 flex items-center justify-center mx-auto mb-2">
                  <span className="text-mahoosuc-blue-300 font-bold text-xs">MOS</span>
                </div>
                <div className="text-white text-xs font-semibold">Mahoosuc OS</div>
                <div className="text-slate-500 text-xs">Business OS</div>
              </div>
            </div>

            {/* Event types */}
            <div>
              <p className="text-xs text-slate-500 font-mono mb-3">Event types crossing the bridge:</p>
              <div className="flex flex-wrap gap-2">
                {BRIDGE_EVENTS.map((event) => (
                  <span
                    key={event}
                    className="px-2 py-1 rounded bg-mahoosuc-blue-900/60 border border-mahoosuc-blue-700/40 text-mahoosuc-blue-300 text-xs font-mono"
                  >
                    {event}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 pt-10 border-t border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-white font-semibold">See the full Mahoosuc OS platform</p>
            <p className="text-slate-400 text-sm">20 products. 121 agents. One operating system.</p>
          </div>
          <Link
            href="https://mahoosuc.ai"
            className="px-6 py-2.5 border border-copper-500/40 text-copper-300 rounded-lg font-semibold hover:bg-copper-500/10 transition text-sm whitespace-nowrap"
            target="_blank"
            rel="noopener noreferrer"
          >
            Visit mahoosuc.ai →
          </Link>
        </div>
      </div>
    </section>
  )
}
