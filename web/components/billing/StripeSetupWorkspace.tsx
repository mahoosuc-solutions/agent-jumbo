'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { WorkflowRecoveryPanel } from '@/components/billing/WorkflowRecoveryPanel'

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
  active: boolean
  monthly_price_usd: number
  setup_price_usd: number
  source_kind?: string
  sync_status?: string
  recommended_action?: string
  product_exists?: boolean
  monthly_price_id?: string | null
  setup_price_id?: string | null
}

type EmbeddedStatus = {
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
  catalog?: {
    offers: CatalogOffer[]
  }
}

type WorkflowRun = {
  run_id: string
  workflow_type: string
  status: string
  current_phase: string
  target_offer_slug: string
  selected_slugs: string[]
  validation_report: {
    checkout?: {
      checkout_url?: string
      detail?: string
      status?: string
      offer_slug?: string
    }
  }
  current_step: SetupStep | null
  checkout_state?: {
    status: string
    checkout_url?: string
    offer_slug?: string
    detail?: string
  }
}

type EvidenceItem = {
  id: number
  phase: string
  evidence_type: string
  title: string
  status: string
  created_at: string
  payload: Record<string, unknown>
}

type WorkflowPayload = {
  provider: string
  tenant_id: string
  workflow: WorkflowRun | null
  status: EmbeddedStatus
  evidence: EvidenceItem[]
  checkpoints: Array<{
    checkpoint_id: string
    phase: string
    title: string
    checkpoint_type: string
    created_at: string
  }>
  recovery: {
    status: string
    resume_recommendation?: string
    pending_human_gate?: {
      title?: string
      instructions?: string
    }
    last_safe_checkpoint?: {
      checkpoint_id: string
      phase: string
      title: string
      checkpoint_type: string
      created_at: string
    } | null
  }
}

const DEFAULT_TENANT_ID = 'default'

async function parseJson(res: Response) {
  return res.json().catch(() => ({}))
}

export function StripeSetupWorkspace() {
  const [tenantId] = useState(DEFAULT_TENANT_ID)
  const [workflowPayload, setWorkflowPayload] = useState<WorkflowPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [businessName, setBusinessName] = useState('Mahoosuc tenant')
  const [email, setEmail] = useState('billing@example.com')
  const [country, setCountry] = useState('US')
  const [secretKey, setSecretKey] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [catalogDrafts, setCatalogDrafts] = useState<
    Record<string, { active: boolean; monthly_price_usd: number; setup_price_usd: number }>
  >({})

  const status = workflowPayload?.status ?? null
  const workflow = workflowPayload?.workflow ?? null
  const catalog = status?.catalog ?? { offers: [] }

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        `/api/backend/billing_setup_workflow_status?tenant_id=${encodeURIComponent(tenantId)}&provider=stripe`,
      )
      const data = await parseJson(response)
      if (!response.ok) throw new Error(data.error ?? 'Failed to load Stripe workflow')
      setWorkflowPayload(data)
      setCatalogDrafts(
        Object.fromEntries(
          (data.status.catalog?.offers ?? []).map((offer: CatalogOffer) => [
            offer.slug,
            {
              active: Boolean(offer.active),
              monthly_price_usd: Number(offer.monthly_price_usd ?? 0),
              setup_price_usd: Number(offer.setup_price_usd ?? 0),
            },
          ]),
        ),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Stripe workflow')
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

  async function startWorkflow() {
    await runAction(
      'start_workflow',
      fetch('/api/backend/billing_setup_workflow_start', {
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
      'Stripe onboarding workflow started.',
    )
  }

  async function advanceWorkflow(humanConfirmed: boolean) {
    if (!workflow?.run_id) return
    await runAction(
      'advance_workflow',
      fetch('/api/backend/billing_setup_workflow_advance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: workflow.run_id,
          human_confirmed: humanConfirmed,
          step_result: {},
        }),
      }),
      humanConfirmed ? 'Human-required step confirmed.' : 'Workflow advanced to the next setup step.',
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

  async function saveCatalogOffer(slug: string) {
    const draft = catalogDrafts[slug]
    if (!draft) return
    await runAction(
      `save_offer_${slug}`,
      fetch('/api/backend/billing_catalog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: tenantId,
          provider: 'stripe',
          slug,
          active: draft.active,
          monthly_price_usd: draft.monthly_price_usd,
          setup_price_usd: draft.setup_price_usd,
        }),
      }),
      `Updated ${slug} catalog draft.`,
    )
  }

  async function validateWorkflow(applyCatalogSync: boolean, checkoutCompleted = false) {
    if (!workflow?.run_id) {
      setError('Start the workflow before validating it.')
      return
    }
    const selectedSlugs = catalog.offers.filter((offer) => offer.active).map((offer) => offer.slug)
    const firstPaidOffer = catalog.offers.find(
      (offer) => offer.active && offer.billing_mode !== 'free' && offer.billing_mode !== 'custom_quote',
    )
    await runAction(
      checkoutCompleted ? 'confirm_checkout' : applyCatalogSync ? 'sync_validate' : 'validate_workflow',
      fetch('/api/backend/billing_setup_workflow_validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: workflow.run_id,
          apply_catalog_sync: applyCatalogSync,
          checkout_completed: checkoutCompleted,
          selected_slugs: selectedSlugs,
          target_offer_slug: workflow.target_offer_slug || firstPaidOffer?.slug || '',
        }),
      }),
      checkoutCompleted
        ? 'Hosted checkout marked complete.'
        : applyCatalogSync
          ? 'Catalog synced and hosted checkout prepared.'
          : 'Workflow validation refreshed.',
    )
  }

  async function recoverWorkflow() {
    if (!workflow?.run_id) return
    await runAction(
      'recover_workflow',
      fetch('/api/backend/billing_setup_workflow_recover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: workflow.run_id }),
      }),
      'Workflow recovery attempted.',
    )
  }

  async function restartFromCheckpoint(checkpointId: string) {
    if (!workflow?.run_id) return
    await runAction(
      'restart_workflow',
      fetch('/api/backend/billing_setup_workflow_restart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: workflow.run_id, checkpoint_id: checkpointId }),
      }),
      'Workflow restarted from checkpoint.',
    )
  }

  const recentEvidence = useMemo(
    () => (workflowPayload?.evidence ?? []).slice(-6).reverse(),
    [workflowPayload?.evidence],
  )

  if (loading && !workflowPayload) {
    return <div className="text-slate-400">Loading Stripe billing workflow…</div>
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Stripe Onboarding Workflow</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              Launch a tenant-owned Stripe onboarding run, guide the operator through dashboard steps,
              sync a controlled catalog, and validate readiness with a hosted test checkout.
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-sm">
              <a
                href="/documentation/BILLING_SETUP_JOURNEY" /* pragma: allowlist secret */
                className="text-copper-300 transition hover:text-copper-200 hover:underline"
              >
                Billing journey guide
              </a>
              <a
                href="/documentation/BROWSER_ACCOUNT_SETUP" /* pragma: allowlist secret */
                className="text-copper-300 transition hover:text-copper-200 hover:underline"
              >
                Browser setup reference
              </a>
            </div>
          </div>
          <div
            className={`rounded-xl border px-4 py-3 text-sm ${
              status?.summary.ready
                ? 'border-green-800 bg-green-900/20 text-green-300'
                : 'border-amber-800 bg-amber-900/20 text-amber-200'
            }`}
          >
            <div className="font-medium">{status?.summary.ready ? 'Ready' : 'Needs attention'}</div>
            <div>{status?.summary.message}</div>
            <div className="mt-1 text-xs text-slate-300">
              Passed {status?.summary.passed ?? 0} · Failed {status?.summary.failed ?? 0}
            </div>
            {workflow?.run_id && (
              <div className="mt-2 text-xs text-slate-300">
                Workflow {workflow.run_id} · {workflow.status.replace('_', ' ')}
              </div>
            )}
          </div>
        </div>
        {error && (
          <p className="mt-4 rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-300">
            {error}
          </p>
        )}
        {message && (
          <p className="mt-4 rounded-lg border border-green-800 bg-green-900/20 p-3 text-sm text-green-300">
            {message}
          </p>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Workflow Run</h2>
              <p className="mt-1 text-sm text-slate-400">
                Start or resume the embedded Stripe onboarding workflow from this workspace.
              </p>
            </div>
            <button
              onClick={startWorkflow}
              disabled={busy !== null}
              className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
            >
              {busy === 'start_workflow' ? 'Starting…' : workflow ? 'Start New Workflow' : 'Start Workflow'}
            </button>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Business name</span>
              <input
                value={businessName}
                onChange={(event) => setBusinessName(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Billing email</span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Country</span>
              <input
                value={country}
                onChange={(event) => setCountry(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
          </div>

          {workflow ? (
            <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-white">{workflow.run_id}</div>
                  <div className="text-sm text-slate-400">
                    Phase {workflow.current_phase} · {workflow.status.replace('_', ' ')}
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => advanceWorkflow(false)}
                    disabled={busy !== null}
                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
                  >
                    {busy === 'advance_workflow' ? 'Advancing…' : 'Advance Workflow'}
                  </button>
                  <button
                    onClick={() => advanceWorkflow(true)}
                    disabled={busy !== null}
                    className="rounded-lg border border-copper-700 px-4 py-2 text-sm font-medium text-copper-300 transition hover:bg-copper-900/20 disabled:opacity-50"
                  >
                    Confirm Human Step
                  </button>
                </div>
              </div>

              {workflow.current_step ? (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-400">
                      {workflow.current_step.automation_type}
                    </span>
                    <span className="text-sm font-medium text-white">{workflow.current_step.title}</span>
                  </div>
                  {workflow.current_step.description && (
                    <p className="mt-2 text-sm text-slate-400">{workflow.current_step.description}</p>
                  )}
                  {workflow.current_step.human_instructions && (
                    <p className="mt-3 rounded-lg border border-amber-800 bg-amber-900/10 p-3 text-sm text-amber-200">
                      {workflow.current_step.human_instructions}
                    </p>
                  )}
                </div>
              ) : (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-400">
                  No current setup step is active. Move to catalog sync or checkout validation below.
                </div>
              )}
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-dashed border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">
              No active workflow yet. Start one to create or connect a Stripe test account and capture the full audit trail.
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Recent Evidence</h2>
          <p className="mt-1 text-sm text-slate-400">
            The workflow keeps a structured audit trail of steps, human gates, validation runs, and checkout preparation.
          </p>
          <div className="mt-4 space-y-3">
            {recentEvidence.length > 0 ? (
              recentEvidence.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  {(() => {
                    const detail =
                      typeof item.payload.detail === 'string' ? item.payload.detail : null
                    return (
                      <>
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-white">{item.title}</div>
                    <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-400">
                      {item.phase || item.evidence_type}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{item.created_at}</div>
                  {detail && <div className="mt-2 text-sm text-slate-400">{detail}</div>}
                      </>
                    )
                  })()}
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                Evidence will appear here after you start the workflow.
              </div>
            )}
          </div>
        </div>
      </section>

      <WorkflowRecoveryPanel
        recovery={workflowPayload?.recovery ?? null}
        checkpoints={workflowPayload?.checkpoints ?? []}
        busy={busy}
        onRecover={recoverWorkflow}
        onRestart={restartFromCheckpoint}
      />

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Journey Stages</h2>
            <p className="mt-1 text-sm text-slate-400">
              The workflow tracks progress from discovery through ongoing billing operations.
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
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wide ${
                    stage.status === 'complete'
                      ? 'bg-green-900/30 text-green-300'
                      : stage.status === 'in_progress'
                        ? 'bg-copper-900/30 text-copper-300'
                        : 'bg-slate-800 text-slate-400'
                  }`}
                >
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
              <h2 className="text-lg font-semibold text-white">Connection</h2>
              <p className="mt-1 text-sm text-slate-400">
                Store tenant-owned Stripe credentials and keep them redacted inside the billing workflow.
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
              Stored values are redacted in the UI. Current capture:{' '}
              {Object.entries(status?.credentials ?? {}).filter(([, value]) => value).length} secrets.
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
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Catalog</h2>
            <p className="mt-1 text-sm text-slate-400">
              Start from Mahoosuc templates, then sync only the offers that belong in this tenant’s Stripe account.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => validateWorkflow(false, false)}
              disabled={busy !== null || !workflow}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {busy === 'validate_workflow' ? 'Refreshing…' : 'Refresh Validation'}
            </button>
            <button
              onClick={() => validateWorkflow(true, false)}
              disabled={busy !== null || !workflow}
              className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
            >
              {busy === 'sync_validate' ? 'Syncing…' : 'Sync And Prepare Checkout'}
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
                <th className="pb-3 pr-4">Manage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {(catalog.offers ?? []).map((offer) => (
                <tr key={offer.slug}>
                  <td className="py-4 pr-4">
                    <div className="font-medium text-white">{offer.name}</div>
                    <div className="text-xs text-slate-500">{offer.slug}</div>
                  </td>
                  <td className="py-4 pr-4 text-slate-300">{offer.catalog_family.replace('_', ' ')}</td>
                  <td className="py-4 pr-4 text-slate-300">
                    {offer.monthly_price_usd ? `$${offer.monthly_price_usd}/mo` : '—'}
                  </td>
                  <td className="py-4 pr-4 text-slate-300">
                    {offer.setup_price_usd ? `$${offer.setup_price_usd}` : '—'}
                  </td>
                  <td className="py-4 pr-4">
                    <div className="flex flex-col gap-2">
                      <span
                        className={`w-fit rounded-full px-2 py-1 text-[11px] uppercase tracking-wide ${
                          offer.recommended_action && offer.recommended_action !== 'ready'
                            ? 'bg-amber-900/30 text-amber-200'
                            : 'bg-green-900/30 text-green-300'
                        }`}
                      >
                        {offer.recommended_action ?? 'pending'}
                      </span>
                      <span className="text-xs text-slate-500">
                        {offer.source_kind ?? 'template'} · {offer.sync_status ?? 'pending'}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 pr-4">
                    <div className="grid min-w-[260px] gap-3">
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        <input
                          type="checkbox"
                          checked={catalogDrafts[offer.slug]?.active ?? offer.active}
                          onChange={(event) =>
                            setCatalogDrafts((current) => ({
                              ...current,
                              [offer.slug]: {
                                active: event.target.checked,
                                monthly_price_usd:
                                  current[offer.slug]?.monthly_price_usd ?? offer.monthly_price_usd,
                                setup_price_usd: current[offer.slug]?.setup_price_usd ?? offer.setup_price_usd,
                              },
                            }))
                          }
                        />
                        Offer active for this tenant
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={catalogDrafts[offer.slug]?.monthly_price_usd ?? offer.monthly_price_usd}
                          onChange={(event) =>
                            setCatalogDrafts((current) => ({
                              ...current,
                              [offer.slug]: {
                                active: current[offer.slug]?.active ?? offer.active,
                                monthly_price_usd: Number(event.target.value),
                                setup_price_usd:
                                  current[offer.slug]?.setup_price_usd ?? offer.setup_price_usd,
                              },
                            }))
                          }
                          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white"
                        />
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={catalogDrafts[offer.slug]?.setup_price_usd ?? offer.setup_price_usd}
                          onChange={(event) =>
                            setCatalogDrafts((current) => ({
                              ...current,
                              [offer.slug]: {
                                active: current[offer.slug]?.active ?? offer.active,
                                monthly_price_usd:
                                  current[offer.slug]?.monthly_price_usd ?? offer.monthly_price_usd,
                                setup_price_usd: Number(event.target.value),
                              },
                            }))
                          }
                          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white"
                        />
                      </div>
                      <button
                        onClick={() => saveCatalogOffer(offer.slug)}
                        disabled={busy !== null}
                        className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-medium text-white transition hover:bg-slate-800 disabled:opacity-50"
                      >
                        {busy === `save_offer_${offer.slug}` ? 'Saving…' : 'Save Draft'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Hosted Checkout Validation</h2>
          <p className="mt-1 text-sm text-slate-400">
            After syncing a paid offer, prepare a Stripe-hosted test checkout and confirm it here once you finish the payment flow.
          </p>
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4">
            <div className="text-sm text-slate-300">
              Status: <span className="font-medium text-white">{workflow?.checkout_state?.status ?? 'not_started'}</span>
            </div>
            {workflow?.checkout_state?.detail && (
              <p className="mt-2 text-sm text-slate-400">{workflow.checkout_state.detail}</p>
            )}
            {workflow?.checkout_state?.checkout_url && (
              <a
                href={workflow.checkout_state.checkout_url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex text-sm text-copper-300 transition hover:text-copper-200 hover:underline"
              >
                Open hosted Stripe checkout
              </a>
            )}
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => validateWorkflow(false, true)}
                disabled={busy !== null || !workflow || workflow.checkout_state?.status !== 'awaiting_human_completion'}
                className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
              >
                {busy === 'confirm_checkout' ? 'Confirming…' : 'Mark Test Checkout Complete'}
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Health</h2>
          <p className="mt-1 text-sm text-slate-400">
            Stripe readiness is tracked as capabilities so tenants can return later for payouts, webhook recovery, or product changes.
          </p>
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
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wide ${
                      check.ok ? 'bg-green-900/40 text-green-300' : 'bg-amber-900/40 text-amber-200'
                    }`}
                  >
                    {check.ok ? 'pass' : 'action needed'}
                  </span>
                </div>
                <div className="mt-1 text-sm text-slate-400">{check.detail}</div>
              </div>
            ))}
          </div>
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
