import Link from 'next/link'

export default function ProductCTA() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-copper-500/10 via-mahoosuc-blue-500/10 to-copper-500/10">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-4xl font-bold text-white mb-6">Ready to orchestrate your world?</h2>
        <p className="text-xl text-slate-300 mb-8">
          See the Mahoosuc Operating System in action. Get a demo tailored to your use case, or self-host and start building today.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/demo" className="px-8 py-3 bg-copper-500 text-white rounded-lg font-semibold hover:bg-copper-400 transition">Get Demo</Link>
          <Link href="/documentation" className="px-8 py-3 border border-slate-700 text-slate-200 rounded-lg font-semibold hover:bg-slate-800 transition">Self-Host Guide</Link>
        </div>
      </div>
    </section>
  )
}
