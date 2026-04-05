import type { Metadata } from 'next'
import DemoSummarizeWidget from './DemoSummarizeWidget'

export const metadata: Metadata = {
  title: 'Document Summarizer Demo',
  description: 'Paste any text and get a structured AI summary — key points, TL;DR, action items.',
}

export default function DemoSummarizePage() {
  return (
    <div className="py-16 px-4 sm:px-6 lg:px-8 max-w-3xl mx-auto">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-white mb-2">Document Summarizer</h1>
        <p className="text-slate-400">
          Paste an email, contract, report, or any text. The AI Document Processing instrument
          returns a structured summary with TL;DR, key points, and action items.
        </p>
        <p className="mt-2 text-xs font-mono text-slate-500">3 free summaries · no account · no credit card</p>
      </div>
      <DemoSummarizeWidget />
    </div>
  )
}
