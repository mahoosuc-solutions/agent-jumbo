'use client'

import { useState } from 'react'
import Link from 'next/link'

const PLANS = [
  {
    id: 'free_cloud',
    label: 'Free Cloud',
    price: '$0/mo',
    description: 'Hosted trial — $2 token budget, 30-day solution trial, no credit card.',
  },
  {
    id: 'pro',
    label: 'Pro',
    price: '$39/mo',
    description: 'Managed routing, $10 token budget, usage analytics, email support.',
  },
  {
    id: 'enterprise',
    label: 'Enterprise',
    price: '$149/mo',
    description: 'Multi-instance, $50 token budget, governance controls, 12-hour SLA.',
  },
  {
    id: 'community',
    label: 'Community (Self-hosted)',
    price: 'Free forever',
    description: 'Full platform, your hardware, your API keys. No account needed.',
  },
]

interface NextStep {
  headline: string
  body: string
  actions: { label: string; href: string }[]
}

interface SignupResult {
  ok: boolean
  plan: string
  email: string
  next_steps: NextStep
}

export default function SignupWidget({ initialPlan }: { initialPlan: string }) {
  const validPlan = PLANS.find((p) => p.id === initialPlan) ? initialPlan : 'free_cloud'
  const [plan, setPlan] = useState(validPlan)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SignupResult | null>(null)
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    // Community plan needs no backend — send straight to install guide
    if (plan === 'community') {
      window.location.href = '/install'
      return
    }
    if (!email.trim() || loading) return
    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/backend/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          email,
          company,
          plan,
          source: 'signup_page',
          referrer: typeof window !== 'undefined' ? document.referrer : '',
        }),
      })
      const data = await res.json()
      if (!res.ok || data.error) {
        setError(data.error || 'Something went wrong — please try again.')
      } else {
        setResult(data as SignupResult)
      }
    } catch {
      setError('Network error — please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (result) {
    const ns = result.next_steps
    return (
      <div className="rounded-2xl border border-green-800/40 bg-green-950/20 p-8 text-center">
        <div className="text-4xl mb-4">✓</div>
        <h2 className="text-2xl font-bold text-white mb-3">{ns.headline}</h2>
        <p className="text-slate-300 leading-relaxed mb-6">{ns.body}</p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {ns.actions.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className="px-6 py-2.5 rounded-lg bg-copper-500 text-white font-semibold hover:bg-copper-400 transition text-sm"
            >
              {action.label}
            </Link>
          ))}
        </div>
        <p className="mt-6 text-xs text-slate-500">
          Confirmation sent to <span className="text-slate-300">{result.email}</span>
        </p>
      </div>
    )
  }

  const selectedPlan = PLANS.find((p) => p.id === plan)!

  return (
    <form onSubmit={submit} className="space-y-5">
      {/* Plan selector */}
      <div>
        <label className="block text-xs font-mono uppercase tracking-widest text-slate-500 mb-2">
          Plan
        </label>
        <div className="grid grid-cols-2 gap-2">
          {PLANS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPlan(p.id)}
              className={`rounded-xl border p-3 text-left transition ${
                plan === p.id
                  ? 'border-copper-500/60 bg-copper-500/10 text-white'
                  : 'border-slate-700 bg-slate-900/50 text-slate-400 hover:border-slate-600'
              }`}
            >
              <div className="text-sm font-semibold">{p.label}</div>
              <div className="text-xs font-mono mt-0.5 text-copper-300">{p.price}</div>
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500 leading-relaxed">{selectedPlan.description}</p>
      </div>

      {/* Fields */}
      <div>
        <label className="block text-xs font-mono uppercase tracking-widest text-slate-500 mb-1.5">
          Name
        </label>
        <input
          type="text"
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-copper-500/60"
          placeholder="Your name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoComplete="name"
        />
      </div>

      <div>
        <label className="block text-xs font-mono uppercase tracking-widest text-slate-500 mb-1.5">
          Email <span className="text-copper-400">*</span>
        </label>
        <input
          type="email"
          required
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-copper-500/60"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-xs font-mono uppercase tracking-widest text-slate-500 mb-1.5">
          Company
        </label>
        <input
          type="text"
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-copper-500/60"
          placeholder="Company name (optional)"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          autoComplete="organization"
        />
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-950/20 border border-red-900/40 rounded-lg px-4 py-2.5">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading || !email.trim()}
        className="w-full py-3 rounded-lg bg-copper-500 text-white font-semibold hover:bg-copper-400 disabled:opacity-40 disabled:cursor-not-allowed transition"
      >
        {loading ? 'Submitting…' : plan === 'community' ? 'Go to Install Guide' : 'Get Started'}
      </button>

      <p className="text-center text-xs text-slate-600">
        By signing up you agree to our{' '}
        <Link href="/documentation/TERMS_OF_USE" className="text-slate-400 hover:text-white underline">
          Terms
        </Link>{' '}
        and{' '}
        <Link href="/documentation/PRIVACY_POLICY" className="text-slate-400 hover:text-white underline">
          Privacy Policy
        </Link>
        .
      </p>
    </form>
  )
}
