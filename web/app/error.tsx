'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--surface-primary)]">
      <div className="max-w-md text-center">
        <h2 className="mb-4 text-2xl font-semibold text-[var(--text-primary)]">
          Something went wrong
        </h2>
        <p className="mb-6 text-[var(--text-secondary)]">
          An unexpected error occurred. Please try again or contact support if the
          problem persists.
        </p>
        {error.digest && (
          <p className="mb-4 font-mono text-xs text-[var(--text-tertiary)]">
            Error ID: {error.digest}
          </p>
        )}
        <button
          onClick={reset}
          className="rounded-lg bg-[var(--accent-primary)] px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-primary-hover)]"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
