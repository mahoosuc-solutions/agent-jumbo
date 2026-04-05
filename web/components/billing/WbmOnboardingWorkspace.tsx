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

type WorkflowPayload = {
  provider: string
  tenant_id: string
  workflow: {
    run_id: string
    workflow_type: string
    status: string
    current_phase: string
    current_step: SetupStep | null
  } | null
  status: {
    provider: string
    summary: {
      ready: boolean
      passed: number
      failed: number
      message: string
    }
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
  }
  evidence: Array<{
    id: number
    phase: string
    title: string
    created_at: string
    payload: Record<string, unknown>
  }>
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
    pending_human_gate?: { title?: string; instructions?: string }
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

export function WbmOnboardingWorkspace() {
  const [tenantId] = useState(DEFAULT_TENANT_ID)
  const [workflowPayload, setWorkflowPayload] = useState<WorkflowPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [businessName, setBusinessName] = useState('West Bethel Motel')
  const [email, setEmail] = useState('ops@example.com')

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        `/api/backend/billing_setup_workflow_status?tenant_id=${encodeURIComponent(tenantId)}&provider=wbm`,
      )
      const data = await parseJson(response)
      if (!response.ok) throw new Error(data.error ?? 'Failed to load WBM workflow')
      setWorkflowPayload(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load WBM workflow')
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
      if (!res.ok || data.error) throw new Error(data.error ?? `${label} failed`)
      setMessage(successMessage)
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
          provider: 'wbm',
          business_name: businessName,
          email,
          country: 'US',
        }),
      }),
      'WBM onboarding workflow started.',
    )
  }

  async function advanceWorkflow(humanConfirmed: boolean) {
    if (!workflowPayload?.workflow?.run_id) return
    await runAction(
      'advance_workflow',
      fetch('/api/backend/billing_setup_workflow_advance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: workflowPayload.workflow.run_id, human_confirmed: humanConfirmed, step_result: {} }),
      }),
      humanConfirmed ? 'Phase confirmed.' : 'Workflow advanced.',
    )
  }

  async function verifyWorkflow() {
    if (!workflowPayload?.workflow?.run_id) {
      setError('Start the workflow before validating it.')
      return
    }
    await runAction(
      'validate_workflow',
      fetch('/api/backend/billing_setup_workflow_validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: workflowPayload.workflow.run_id }),
      }),
      'WBM validation refreshed.',
    )
  }

  async function recoverWorkflow() {
    if (!workflowPayload?.workflow?.run_id) return
    await runAction(
      'recover_workflow',
      fetch('/api/backend/billing_setup_workflow_recover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: workflowPayload.workflow.run_id }),
      }),
      'Workflow recovery attempted.',
    )
  }

  async function restartFromCheckpoint(checkpointId: string) {
    if (!workflowPayload?.workflow?.run_id) return
    await runAction(
      'restart_workflow',
      fetch('/api/backend/billing_setup_workflow_restart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: workflowPayload.workflow.run_id, checkpoint_id: checkpointId }),
      }),
      'Workflow restarted from checkpoint.',
    )
  }

  const recentEvidence = useMemo(() => (workflowPayload?.evidence ?? []).slice(-6).reverse(), [workflowPayload?.evidence])

  if (loading && !workflowPayload) {
    return <div className="text-slate-400">Loading WBM onboarding workflow…</div>
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">WBM Embedded Onboarding</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              Run West Bethel Motel onboarding from an authenticated workspace with durable evidence, recovery, and safe checkpoints.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-300">
            <div className="font-medium text-white">
              {workflowPayload?.status.summary.ready ? 'Ready' : 'Needs attention'}
            </div>
            <div>{workflowPayload?.status.summary.message}</div>
          </div>
        </div>
        {error && <p className="mt-4 rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-300">{error}</p>}
        {message && <p className="mt-4 rounded-lg border border-green-800 bg-green-900/20 p-3 text-sm text-green-300">{message}</p>}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Workflow Run</h2>
              <p className="mt-1 text-sm text-slate-400">
                Start or resume the embedded WBM onboarding workflow from this workspace.
              </p>
            </div>
            <button
              onClick={startWorkflow}
              disabled={busy !== null}
              className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
            >
              {busy === 'start_workflow' ? 'Starting…' : workflowPayload?.workflow ? 'Start New Workflow' : 'Start Workflow'}
            </button>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Property</span>
              <input
                value={businessName}
                onChange={(event) => setBusinessName(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-slate-500">Operator email</span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
          </div>

          {workflowPayload?.workflow ? (
            <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-white">{workflowPayload.workflow.run_id}</div>
                  <div className="text-sm text-slate-400">
                    Phase {workflowPayload.workflow.current_phase} · {workflowPayload.workflow.status.replace(/_/g, ' ')}
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => advanceWorkflow(false)}
                    disabled={busy !== null}
                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
                  >
                    Advance Workflow
                  </button>
                  <button
                    onClick={() => advanceWorkflow(true)}
                    disabled={busy !== null}
                    className="rounded-lg border border-copper-700 px-4 py-2 text-sm font-medium text-copper-300 transition hover:bg-copper-900/20 disabled:opacity-50"
                  >
                    Confirm Phase
                  </button>
                  <button
                    onClick={verifyWorkflow}
                    disabled={busy !== null}
                    className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:opacity-50"
                  >
                    Validate
                  </button>
                </div>
              </div>

              {workflowPayload.workflow.current_step ? (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-sm font-medium text-white">{workflowPayload.workflow.current_step.title}</div>
                  {workflowPayload.workflow.current_step.description && (
                    <p className="mt-2 text-sm text-slate-400">{workflowPayload.workflow.current_step.description}</p>
                  )}
                  {workflowPayload.workflow.current_step.human_instructions && (
                    <p className="mt-3 rounded-lg border border-amber-800 bg-amber-900/10 p-3 text-sm text-amber-200">
                      {workflowPayload.workflow.current_step.human_instructions}
                    </p>
                  )}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-dashed border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">
              No active workflow yet. Start one to move WBM onboarding into the embedded, recoverable workspace.
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Health Checks</h2>
          <div className="mt-4 space-y-3">
            {(workflowPayload?.status.checks ?? []).map((check) => (
              <div key={check.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-white">{check.id.replace(/_/g, ' ')}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wide ${check.ok ? 'bg-green-900/30 text-green-300' : 'bg-amber-900/30 text-amber-300'}`}>
                    {check.ok ? 'ok' : 'attention'}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-400">{check.detail}</p>
              </div>
            ))}
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

      <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Journey Stages</h2>
          <p className="mt-1 text-sm text-slate-400">{workflowPayload?.status.journey.operator_note}</p>
          <div className="mt-5 grid gap-4">
            {(workflowPayload?.status.journey.stages ?? []).map((stage) => (
              <div key={stage.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-white">{stage.title}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] uppercase tracking-wide ${stage.status === 'complete' ? 'bg-green-900/30 text-green-300' : stage.status === 'in_progress' ? 'bg-copper-900/30 text-copper-300' : 'bg-slate-800 text-slate-400'}`}>
                    {stage.status.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-400">{stage.goal}</p>
                <p className="mt-3 text-xs text-slate-500">Exit criteria: {stage.exit_criteria}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Recent Evidence</h2>
          <div className="mt-4 space-y-3">
            {recentEvidence.length > 0 ? (
              recentEvidence.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <div className="text-sm font-medium text-white">{item.title}</div>
                  <div className="mt-1 text-xs text-slate-500">{item.phase || 'workflow'} · {item.created_at}</div>
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                Evidence appears here as the workflow advances.
              </div>
            )}
          </div>

          <h3 className="mt-6 text-sm font-semibold uppercase tracking-wide text-slate-400">Playbooks</h3>
          <div className="mt-3 space-y-3">
            {(workflowPayload?.status.process_playbooks ?? []).map((playbook) => (
              <div key={playbook.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <div className="text-sm font-medium text-white">{playbook.title}</div>
                <p className="mt-1 text-sm text-slate-400">{playbook.trigger}</p>
                <div className="mt-3 space-y-2">
                  {playbook.steps.map((step) => (
                    <div key={step} className="text-sm text-slate-300">
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
