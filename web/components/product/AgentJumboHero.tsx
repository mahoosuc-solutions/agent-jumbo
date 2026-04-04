import Link from 'next/link'
import { getManifest } from '@/lib/manifest'

export default function AgentJumboHero() {
  const m = getManifest()
  const commandCount = m.platform.commands.total
  const instrumentCount = m.platform.instruments.active
  const integrationCount = m.platform.integrations.length

  return (
    <section className="relative py-24 px-4 sm:px-6 lg:px-8 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-mahoosuc-blue-900 via-mahoosuc-blue-800 to-slate-900" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-copper-500/20 via-transparent to-transparent" />

      <div className="relative max-w-7xl mx-auto">
        <div className="max-w-3xl">
          <p className="text-copper-400 font-mono text-sm tracking-widest uppercase mb-4">
            Agent Jumbo
          </p>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white mb-6 leading-[1.1]">
            Your Personal AI Operating System
          </h1>
          <p className="text-xl text-slate-300 mb-4 leading-relaxed">
            Real estate, finances, wellness, relationships, calendar — orchestrated by specialized agents. Built on {commandCount}+ commands and {instrumentCount} active instruments. You talk. It runs. You approve what matters.
          </p>
          <p className="text-sm text-slate-400 font-mono mb-8">
            Every metric is generated from the codebase. Updated every build.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              href="/install"
              className="px-8 py-3 bg-copper-500 text-white rounded-lg font-semibold hover:bg-copper-400 transition text-center"
            >
              Download &amp; Install
            </Link>
            <Link
              href="https://mahoosuc.ai/agent-jumbo"
              className="px-8 py-3 border border-copper-500/40 text-copper-300 rounded-lg font-semibold hover:bg-copper-500/10 transition text-center"
              target="_blank"
              rel="noopener noreferrer"
            >
              Learn the Vision →
            </Link>
          </div>
        </div>

        <div className="mt-16 grid grid-cols-3 gap-6 max-w-xl">
          <div className="text-center">
            <div className="text-3xl font-bold text-copper-400 font-mono">{commandCount}+</div>
            <div className="text-sm text-slate-400 mt-1">Commands</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-copper-400 font-mono">{instrumentCount}</div>
            <div className="text-sm text-slate-400 mt-1">Instruments</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-copper-400 font-mono">{integrationCount}</div>
            <div className="text-sm text-slate-400 mt-1">Integrations</div>
          </div>
        </div>
      </div>
    </section>
  )
}
