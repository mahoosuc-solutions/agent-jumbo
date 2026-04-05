import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Try It Free',
  description: 'Three interactive demos — live AI chat, document summarizer, and workflow planner. No install, no account.',
}

const demos = [
  {
    href: '/try/chat',
    title: 'Live AI Chat',
    description: 'Chat with a hosted agent powered by the Mahoosuc OS LLM router. Up to 5 messages, no signup.',
    badge: '5 free messages',
    icon: '💬',
  },
  {
    href: '/try/summarize',
    title: 'Document Summarizer',
    description: 'Paste any text — email, contract, report — and get a structured summary with key points and action items.',
    badge: '3 free summaries',
    icon: '📄',
  },
  {
    href: '/try/workflow',
    title: 'Workflow Planner',
    description: 'Describe a business goal and get an AI-generated multi-step agent workflow with instrument assignments.',
    badge: '3 free plans',
    icon: '🔀',
  },
]

export default function TryIndexPage() {
  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto">
      <div className="text-center mb-14">
        <h1 className="text-4xl font-bold text-white mb-4">Try Mahoosuc OS</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">
          Three live demos — no install, no account, no credit card.
        </p>
        <p className="mt-3 text-sm text-copper-300">
          Ready for more?{' '}
          <Link href="/signup" className="underline hover:text-copper-200">
            Start the Free Cloud tier
          </Link>{' '}
          and run the full platform in seconds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {demos.map((demo) => (
          <Link
            key={demo.href}
            href={demo.href}
            className="group flex flex-col rounded-2xl border border-slate-800 bg-slate-950/50 p-7 hover:border-copper-500/50 hover:bg-copper-500/5 transition-all"
          >
            <span className="text-4xl mb-4">{demo.icon}</span>
            <h2 className="text-xl font-bold text-white mb-2 group-hover:text-copper-200 transition">
              {demo.title}
            </h2>
            <p className="text-sm text-slate-400 flex-1 leading-relaxed">{demo.description}</p>
            <span className="mt-5 inline-block text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300 w-fit">
              {demo.badge}
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
