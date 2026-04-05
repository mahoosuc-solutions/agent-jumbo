'use client'

import { useCallback, useEffect, useState } from 'react'

type Check = {
  id: string
  ok: boolean
  detail: string
}

type ActionItem = {
  id: string
  title: string
  detail: string
}

type SetupStep = {
  step_id: string
  title: string
  description?: string
  automation_type: string
  human_instructions?: string
}

type SetupSession = {
  session_id: string
  status: string
  current_step: number
  total_steps: number
  business_name?: string
  email?: string
  steps?: SetupStep[]
}

type CatalogOffer = {
  slug: string
  name: string
  catalog_family: string
  billing_mode: string
  monthly_price_usd: number
  setup_price_usd: number
  recommended_action?: string
  product_exists?: boolean
  monthly_price_id?: string | null
  setup_price_id?: string | null
}

type StatusPayload = {
  provider: string
  tenant_id: string
  summary: {
    ready: boolean
    passed: number
    failed: number
    message: string
  }
  credentials: Record<string, string | null>
  checks: Check[]
  next_actions: ActionItem[]
  journey: {
    current_stage: string
    operator_note: string
    stages: Array<{
      id: string
      title: string
      status: string
      goal: string
      exit_criteria: string
    }>
  }
  process_playbooks: Array<{
    id: string
    title: string
    trigger: string
    steps: string[]
  }>
  active_session: SetupSession | null
  guidance_sections: Array<{
    id: string
    title: string
    summary: string
  }>
}

type CatalogPayload = {
  offers: CatalogOffer[]
}

const DEFAULT_TENANT_ID = 'default'

async function parseJson(res: Response) {
  return res.json().catch(() => ({}))
}

export function StripeSetupWorkspace() {
  const [tenantId] = useState(DEFAULT_TENANT_ID)
  const [status, setStatus] = useState<StatusPayload | null>(null)
  const [catalog, setCatalog] = useState<CatalogPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [businessName, setBusinessName] = useState('Mahoosuc tenant')
  const [email, setEmail] = useState('billing@example.com')
  const [country, setCountry] = useState('US')
  const [secretKey, setSecretKey] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statusRes, catalogRes] = await Promise.all([
        fetch(`/api/backend/billing_setup_status?tenant_id=${encodeURIComponent(tenantId)}&provider=stripe`),
        fetch(`/api/backend/billing_catalog?tenant_id=${encodeURIComponent(tenantId)}&provider=stripe`),
      ])
      const statusData = await parseJson(statusRes)
      const catalogData = await parseJson(catalogRes)
      if (!statusRes.ok) throw new Error(statusData.error ?? 'Failed to load setup status')
      if (!catalogRes.ok) throw new Error(catalogData.error ?? 'Failed to load catalog')
      setStatus(statusData)
      setCatalog(catalogData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load billing setup')
    } finally {
      setLoading(false)
    }
  }, [tenantId])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  async function runAction<T>(label: string, request: Promise<Response>, successMessage: string) {
    setBusy(label)
    setError(null)
    setMessage(null)
    try {
      const res = await request
      const data = await parseJson(res)
      if (!res.ok) throw new Error(data.error ?? `${label} failed`)
      setMessage(successMessage || data.message || `${label} complete`)
      await loadAll()
      return data as T
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed`)
      return null
    } finally {
      setBusy(null)
    }
  }

  async function startSetup() {
    await runAction(
      'start_setup',
      fetch('/api/backend/billing_setup_session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: tenantId,
          provider: 'stripe',
          business_name: businessName,
          email,
          country,
        }),
      }),
      'Guided setup session started.',
    )
  }

  async function continueSetup(humanConfirmed: boolean) {
    const sessionId = status?.active_session?.session_id
    if (!sessionId) return
    await runAction(
      'advance_setup',
      fetch('/api/backend/billing_setup_session_advance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          human_confirmed: humanConfirmed,
          step_result: {},
        }),
      }),
      humanConfirmed ? 'Marked the current human step complete.' : 'Moved to the next setup step.',
    )
  }

  async function saveCredentials() {
    const credentials: Record<string, string> = {}
    if (secretKey.trim()) credentials.stripe_secret_key = secretKey.trim()
    if (webhookSecret.trim()) credentials.stripe_webhook_secret = webhookSecret.trim()
    if (Object.keys(credentials).length === 0) {
      setError('Add at least one credential before saving.')
      return
    }
    const result = await runAction(
      'store_credentials',
      fetch('/api/backend/billing_setup_store_credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: tenantId,
          provider: 'stripe',
          credentials,
        }),
      }),
      'Tenant Stripe credentials stored.',
    )
    if (result) {
      setSecretKey('')
      setWebhookSecret('')
    }
  }

  async function verifySetup() {
    await runAction(
      'verify_setup',
      fetch('/api/backend/billing_setup_verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, provider: 'stripe' }),
      }),
      'Stripe readiness checks refreshed.',
    )
  }

  async function syncCatalog(apply: boolean) {
    await runAction(
      apply ? 'sync_catalog' : 'catalog_diff',
      fetch('/api/backend/billing_catalog_sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, provider: 'stripe', apply }),
      }),
      apply ? 'Catalog synced to Stripe.' : 'Catalog dry-run refreshed.',
    )
  }

  if (loading && !status) {
    return <div className="text-slate-400">Loading Stripe billing admin…</div>
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Stripe Setup Assistant</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              Guide tenants through Stripe Dashboard setup, capture billing readiness, and keep the product catalog in sync without making Mahoosuc the billing intermediary.
            </p>
          </div>
          <div className={`rounded-xl border px-4 py-3 text-sm ${status?.summary.ready ? 'border-green-800 bg-green-900/20 text-green-300' : 'border-amber-800 bg-amber-900/20 text-amber-200'}`}>
            <div className="font-medium">{status?.summary.ready ? 'Ready' : 'Needs attention'}</div>
            <div>{status?.summary.message}</div>
            <div className="mt-1 text-xs text-slate-300">
              Passed {status?.summary.passed ?? 0} · Failed {status?.summary.failed ?? 0}
            </div>
          </div>
        </div>
        {error && <p className="mt-4 rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-300">{error}</p>}
        {message && <p className="mt-4 rounded-lg border border-green-800 bg-green-900/20 p-3 text-sm text-green-300">{message}</p>}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Connection</h2>
              <p className="mt-1 text-sm text-slate-400">
                Store tenant-owned Stripe credentials and connect the billing admin workspace.
              </p>
            </div>
            <button
              onClick={verifySetup}
              disabled={busy !== null}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {busy === 'verify_setup' ? 'Checking…' : 'Run Health Check'}
            </button>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Stripe secret key</span>
              <input
                value={secretKey}
                onChange={(event) => setSecretKey(event.target.value)}
                placeholder="sk_test_..."
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-0"
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Webhook secret</span>
              <input
                value={webhookSecret}
                onChange={(event) => setWebhookSecret(event.target.value)}
                placeholder="whsec_..."
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-0"
              />
            </label>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={saveCredentials}
              disabled={busy !== null}
              className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
            >
              {busy === 'store_credentials' ? 'Saving…' : 'Save Tenant Credentials'}
            </button>
            <div className="text-xs text-slate-500">
              Stored values are redacted in the UI. Current capture: {Object.entries(status?.credentials ?? {}).filter(([, value]) => value).length} secrets.
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Next Actions</h2>
          <div className="mt-4 space-y-3">
            {(status?.next_actions ?? []).slice(0, 4).map((action) => (
              <div key={action.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <div className="text-sm font-medium text-white">{action.title}</div>
                <div className="mt-1 text-sm text-slate-400">{action.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Customer Journey</h2>
            <p className="mt-1 text-sm text-slate-400">
              The billing assistant manages a defined journey from discovery through ongoing operations so operators know what to do next.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-300">
            Current stage: <span className="font-medium text-white">{status?.journey.current_stage ?? 'discover'}</span>
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-400">{status?.journey.operator_note}</p>
        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {(status?.journey.stages ?? []).map((stage) => (
            <div key={stage.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-white">{stage.title}</div>
                <span className={`rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wide ${
                  stage.status === 'complete'
                    ? 'bg-green-900/30 text-green-300'
                    : stage.status === 'in_progress'
                    ? 'bg-copper-900/30 text-copper-300'
                    : 'bg-slate-800 text-slate-400'
                }`}>
                  {stage.status.replace('_', ' ')}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-400">{stage.goal}</p>
              <p className="mt-3 text-xs text-slate-500">Exit criteria: {stage.exit_criteria}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Guided Setup</h2>
              <p className="mt-1 text-sm text-slate-400">
                Launch or resume a structured Stripe setup session with human checkpoints for KYC, verification, and dashboard approvals.
              </p>
            </div>
            <button
              onClick={startSetup}
              disabled={busy !== null}
              className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
            >
              {busy === 'start_setup' ? 'Starting…' : 'Start Guided Setup'}
            </button>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Business name</span>
              <input value={businessName} onChange={(event) => setBusinessName(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Billing email</span>
              <input value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Country</span>
              <input value={country} onChange={(event) => setCountry(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
            </label>
          </div>

          {status?.active_session ? (
            <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-white">{status.active_session.session_id}</div>
                  <div className="text-sm text-slate-400">
                    Step {status.active_session.current_step + 1} of {status.active_session.total_steps} · {status.active_session.status}
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => continueSetup(false)}
                    disabled={busy !== null}
                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
                  >
                    {busy === 'advance_setup' ? 'Advancing…' : 'Advance Step'}
                  </button>
                  <button
                    onClick={() => continueSetup(true)}
                    disabled={busy !== null}
                    className="rounded-lg border border-copper-700 px-4 py-2 text-sm font-medium text-copper-300 transition hover:bg-copper-900/20 disabled:opacity-50"
                  >
                    Mark Human Step Done
                  </button>
                </div>
              </div>
              <div className="mt-4 space-y-3">
                {(status.active_session.steps ?? [])
                  .slice(status.active_session.current_step, status.active_session.current_step + 3)
                  .map((step) => (
                    <div key={step.step_id} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-400">
                          {step.automation_type}
                        </span>
                        <span className="text-sm font-medium text-white">{step.title}</span>
                      </div>
                      {step.description && <p className="mt-2 text-sm text-slate-400">{step.description}</p>}
                      {step.human_instructions && <p className="mt-2 rounded-lg border border-amber-800 bg-amber-900/10 p-3 text-sm text-amber-200">{step.human_instructions}</p>}
                    </div>
                  ))}
              </div>
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-dashed border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">
              No active setup session. Start one to walk through Stripe Dashboard, KYC checkpoints, API keys, and webhook setup.
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Health</h2>
              <p className="mt-1 text-sm text-slate-400">
                Stripe readiness is tracked as capabilities so tenants can return later for payouts, webhook recovery, or product changes.
              </p>
            </div>
          </div>
          <div className="mt-4 grid gap-3">
            {(status?.checks ?? []).map((check) => (
              <div
                key={check.id}
                className={`rounded-xl border p-4 ${
                  check.ok ? 'border-green-900 bg-green-900/10' : 'border-amber-900 bg-amber-900/10'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-white">{check.id.replace(/_/g, ' ')}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wide ${check.ok ? 'bg-green-900/40 text-green-300' : 'bg-amber-900/40 text-amber-200'}`}>
                    {check.ok ? 'pass' : 'action needed'}
                  </span>
                </div>
                <div className="mt-1 text-sm text-slate-400">{check.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Catalog</h2>
            <p className="mt-1 text-sm text-slate-400">
              Start from Mahoosuc templates, then sync only the offers that belong in this tenant’s Stripe account.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => syncCatalog(false)}
              disabled={busy !== null}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {busy === 'catalog_diff' ? 'Refreshing…' : 'Refresh Diff'}
            </button>
            <button
              onClick={() => syncCatalog(true)}
              disabled={busy !== null}
              className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
            >
              {busy === 'sync_catalog' ? 'Syncing…' : 'Sync Catalog'}
            </button>
          </div>
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-800 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-3 pr-4">Offer</th>
                <th className="pb-3 pr-4">Type</th>
                <th className="pb-3 pr-4">Monthly</th>
                <th className="pb-3 pr-4">Setup</th>
                <th className="pb-3 pr-4">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {(catalog?.offers ?? []).map((offer) => (
                <tr key={offer.slug}>
                  <td className="py-4 pr-4">
                    <div className="font-medium text-white">{offer.name}</div>
                    <div className="text-xs text-slate-500">{offer.slug}</div>
                  </td>
                  <td className="py-4 pr-4 text-slate-300">{offer.catalog_family.replace('_', ' ')}</td>
                  <td className="py-4 pr-4 text-slate-300">{offer.monthly_price_usd ? `$${offer.monthly_price_usd}/mo` : '—'}</td>
                  <td className="py-4 pr-4 text-slate-300">{offer.setup_price_usd ? `$${offer.setup_price_usd}` : '—'}</td>
                  <td className="py-4 pr-4">
                    <span className={`rounded-full px-2 py-1 text-[11px] uppercase tracking-wide ${
                      offer.recommended_action && offer.recommended_action !== 'ready'
                        ? 'bg-amber-900/30 text-amber-200'
                        : 'bg-green-900/30 text-green-300'
                    }`}>
                      {offer.recommended_action ?? 'pending'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {(status?.guidance_sections ?? []).map((section) => (
          <div key={section.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="text-sm font-medium text-white">{section.title}</div>
            <div className="mt-2 text-sm text-slate-400">{section.summary}</div>
          </div>
        ))}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-lg font-semibold text-white">Defined Processes</h2>
        <p className="mt-1 text-sm text-slate-400">
          These operator playbooks define how to manage onboarding, catalog changes, and recovery without guessing.
        </p>
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {(status?.process_playbooks ?? []).map((playbook) => (
            <div key={playbook.id} className="rounded-xl border border-slate-800 bg-slate-950 p-5">
              <div className="text-sm font-medium text-white">{playbook.title}</div>
              <p className="mt-2 text-sm text-slate-400">{playbook.trigger}</p>
              <ol className="mt-4 space-y-2 text-sm text-slate-300">
                {playbook.steps.map((step, index) => (
                  <li key={`${playbook.id}-${index}`} className="flex gap-2">
                    <span className="text-slate-500">{index + 1}.</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
