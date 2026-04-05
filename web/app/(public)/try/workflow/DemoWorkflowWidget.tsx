'use client'

import { useState } from 'react'
import Link from 'next/link'

const MAX_USES = 3

const EXAMPLE_GOALS = [
  'Onboard a new B2B customer and set up their subscription',
  "Follow up with leads who haven't responded in 7 days",
  'Generate and send monthly invoices to all active customers',
  'Process a refund request and update the customer record',
]

interface WorkflowStep {
  id: number
  title: string
  agent_role: string
  instrument: string
  inputs: string[]
  outputs: string[]
  human_review: boolean
}

interface WorkflowPlan {
  goal: string
  steps: WorkflowStep[]
  estimated_runtime: string
  requires_human_review: boolean
  _note?: string
}

export default function DemoWorkflowWidget() {
  const [goal, setGoal] = useState('')
  const [plan, setPlan] = useState<WorkflowPlan | null>(null)
  const [usesRemaining, setUsesRemaining] = useState(MAX_USES)
  const [loading, setLoading] = useState(false)
  const [limitReached, setLimitReached] = useState(false)
  const [error, setError] = useState('')

  async function generate() {
    if (!goal.trim() || loading || limitReached) return
    setLoading(true)
    setError('')
    setPlan(null)

    try {
      const res = await fetch('/api/backend/demo_workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      })
      const data = await res.json()

      if (data.error === 'demo_limit_reached') {
        setLimitReached(true)
        setError(data.message)
      } else {
        setPlan(data.plan)
        setUsesRemaining(data.uses_remaining ?? 0)
        if (data.uses_remaining === 0) setLimitReached(true)
      }
    } catch {
      setError('Something went wrong — please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Example goals */}
      <div>
        <p className="text-xs text-slate-500 font-mono mb-2 uppercase tracking-widest">Example goals</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_GOALS.map((eg) => (
            <button
              key={eg}
              onClick={() => setGoal(eg)}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:border-copper-500/50 hover:text-white transition"
            >
              {eg}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 rounded-xl bg-slate-900 border border-slate-700 px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-copper-500/60"
          placeholder="Describe your business goal…"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && generate()}
          disabled={loading || limitReached}
        />
        {!limitReached ? (
          <button
            onClick={generate}
            disabled={loading || !goal.trim()}
            className="px-5 py-3 rounded-xl bg-copper-500 text-white text-sm font-semibold hover:bg-copper-400 disabled:opacity-40 disabled:cursor-not-allowed transition whitespace-nowrap"
          >
            {loading ? 'Planning…' : 'Generate Plan'}
          </button>
        ) : (
          <Link
            href="/signup"
            className="px-5 py-3 rounded-xl bg-copper-500 text-white text-sm font-semibold hover:bg-copper-400 transition whitespace-nowrap"
          >
            Start Free →
          </Link>
        )}
      </div>

      {!limitReached && usesRemaining < MAX_USES && (
        <p className="text-xs text-slate-600 font-mono text-right">
          {usesRemaining} plan{usesRemaining !== 1 ? 's' : ''} remaining
        </p>
      )}

      {error && (
        <div className="rounded-xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {error}
          {limitReached && (
            <div className="mt-3">
              <Link href="/signup" className="text-copper-300 underline hover:text-copper-200">
                Start Free Cloud →
              </Link>
            </div>
          )}
        </div>
      )}

      {plan && (
        <div className="rounded-2xl border border-slate-700 bg-slate-900/60 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-mono uppercase tracking-widest text-slate-500 mb-1">Goal</p>
              <p className="text-white font-medium">{plan.goal}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-xs text-slate-500 font-mono">{plan.estimated_runtime}</p>
              {plan.requires_human_review && (
                <span className="text-xs text-amber-400 font-mono">requires review</span>
              )}
            </div>
          </div>

          <div className="divide-y divide-slate-800">
            {plan.steps.map((step, i) => (
              <div key={step.id} className="px-6 py-4 flex gap-4">
                <div className="shrink-0 w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-mono text-slate-400">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-sm font-semibold text-white">{step.title}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-copper-500/10 border border-copper-500/20 text-copper-300">
                      {step.instrument}
                    </span>
                    {step.human_review && (
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300">
                        human review
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mb-2">{step.agent_role}</p>
                  <div className="flex gap-4 text-xs text-slate-500 font-mono">
                    <span>In: {step.inputs.join(', ')}</span>
                    <span>→</span>
                    <span>Out: {step.outputs.join(', ')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {plan._note && (
            <div className="px-6 py-3 bg-slate-950/60 text-xs text-slate-500 font-mono border-t border-slate-800">
              {plan._note}
            </div>
          )}

          <div className="px-6 py-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Powered by Mahoosuc OS Workflow Engine
            </span>
            <Link href="/signup" className="text-xs text-copper-300 hover:text-copper-200">
              Run this workflow for real →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
