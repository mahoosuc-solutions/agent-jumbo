import Link from 'next/link'

export default function AgentJumboCTA() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-copper-500/10 via-mahoosuc-blue-500/10 to-copper-500/10">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-4xl font-bold text-white mb-6">
          Ready to run your life with AI?
        </h2>
        <p className="text-xl text-slate-300 mb-8">
          Download Agent Jumbo, self-host in minutes, and connect to Mahoosuc OS when you&apos;re ready. No cloud lock-in. No subscriptions. Your data stays on your infrastructure.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/install"
            className="px-8 py-3 bg-copper-500 text-white rounded-lg font-semibold hover:bg-copper-400 transition"
          >
            Download &amp; Install
          </Link>
          <Link
            href="https://mahoosuc.ai/agent-jumbo"
            className="px-8 py-3 border border-slate-700 text-slate-200 rounded-lg font-semibold hover:bg-slate-800 transition"
            target="_blank"
            rel="noopener noreferrer"
          >
            See the Full Vision →
          </Link>
        </div>
        <p className="mt-6 text-sm text-slate-500">
          Open source under the Mahoosuc OS platform.{' '}
          <Link
            href="https://github.com/mahoosuc-solutions/agent-jumbo"
            className="text-copper-400 hover:text-copper-300 underline underline-offset-2"
            target="_blank"
            rel="noopener noreferrer"
          >
            View on GitHub
          </Link>
        </p>
      </div>
    </section>
  )
}
