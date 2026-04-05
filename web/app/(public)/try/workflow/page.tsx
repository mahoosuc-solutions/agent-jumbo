import type { Metadata } from 'next'
import DemoWorkflowWidget from './DemoWorkflowWidget'

export const metadata: Metadata = {
  title: 'Workflow Planner Demo',
  description: 'Describe a business goal and get an AI-generated multi-step agent workflow with instrument assignments.',
}

export default function DemoWorkflowPage() {
  return (
    <div className="py-16 px-4 sm:px-6 lg:px-8 max-w-3xl mx-auto">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-white mb-2">Workflow Planner</h1>
        <p className="text-slate-400">
          Describe a business goal. The AI maps it to a multi-step agent workflow
          using Mahoosuc OS instruments — customer lifecycle, payments, scheduling, communications, and more.
        </p>
        <p className="mt-2 text-xs font-mono text-slate-500">3 free plans · no account · no credit card</p>
      </div>
      <DemoWorkflowWidget />
    </div>
  )
}
