import type { Metadata } from 'next'
import DemoChatWidget from './DemoChatWidget'

export const metadata: Metadata = {
  title: 'Live AI Chat Demo',
  description: 'Chat with a hosted Mahoosuc OS agent — 5 free messages, no account needed.',
}

export default function DemoChatPage() {
  return (
    <div className="py-16 px-4 sm:px-6 lg:px-8 max-w-3xl mx-auto">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-white mb-2">Live AI Chat</h1>
        <p className="text-slate-400">
          Talk to a hosted agent powered by the Mahoosuc OS LLM router.
          Routes across 18 providers — cloud and local.
        </p>
        <p className="mt-2 text-xs font-mono text-slate-500">5 free messages · no account · no credit card</p>
      </div>
      <DemoChatWidget />
    </div>
  )
}
