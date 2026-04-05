'use client'

type WorkflowCheckpoint = {
  checkpoint_id: string
  phase: string
  title: string
  checkpoint_type: string
  created_at: string
}

type RecoveryPayload = {
  status: string
  resume_recommendation?: string
  pending_human_gate?: {
    title?: string
    instructions?: string
  }
  last_safe_checkpoint?: WorkflowCheckpoint | null
}

export function WorkflowRecoveryPanel({
  recovery,
  checkpoints,
  busy,
  onRecover,
  onRestart,
}: {
  recovery: RecoveryPayload | null
  checkpoints: WorkflowCheckpoint[]
  busy: string | null
  onRecover: () => void
  onRestart: (checkpointId: string) => void
}) {
  if (!recovery) return null

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Recovery</h2>
          <p className="mt-1 text-sm text-slate-400">
            Resume in place when possible, or restart from the nearest safe checkpoint when exact recovery is no longer safe.
          </p>
        </div>
        <span className="rounded-full bg-slate-950 px-3 py-1 text-xs uppercase tracking-wide text-slate-300">
          {recovery.status.replace(/_/g, ' ')}
        </span>
      </div>

      {recovery.resume_recommendation && (
        <p className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
          {recovery.resume_recommendation}
        </p>
      )}

      {recovery.pending_human_gate?.instructions && (
        <div className="mt-4 rounded-xl border border-amber-800 bg-amber-900/10 p-4">
          <div className="text-sm font-medium text-amber-200">
            {recovery.pending_human_gate.title || 'Human action required'}
          </div>
          <p className="mt-2 text-sm text-amber-100/90">{recovery.pending_human_gate.instructions}</p>
        </div>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          onClick={onRecover}
          disabled={busy !== null || recovery.status === 'completed' || recovery.status === 'not_recoverable'}
          className="rounded-lg bg-copper-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-copper-500 disabled:opacity-50"
        >
          {busy === 'recover_workflow' ? 'Recovering…' : 'Recover Workflow'}
        </button>
        {recovery.last_safe_checkpoint && (
          <button
            onClick={() => onRestart(recovery.last_safe_checkpoint!.checkpoint_id)}
            disabled={busy !== null}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:opacity-50"
          >
            Restart From Last Checkpoint
          </button>
        )}
      </div>

      <div className="mt-5 space-y-3">
        {checkpoints.length > 0 ? (
          checkpoints
            .slice()
            .reverse()
            .map((checkpoint) => (
              <div key={checkpoint.checkpoint_id} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-white">{checkpoint.title}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {checkpoint.phase || 'workflow'} · {checkpoint.created_at}
                    </div>
                  </div>
                  <button
                    onClick={() => onRestart(checkpoint.checkpoint_id)}
                    disabled={busy !== null}
                    className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-slate-800 disabled:opacity-50"
                  >
                    Restart Here
                  </button>
                </div>
              </div>
            ))
        ) : (
          <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
            Safe checkpoints will appear here as the workflow advances.
          </div>
        )}
      </div>
    </section>
  )
}
