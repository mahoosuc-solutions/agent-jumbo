import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--surface-primary)]">
      <div className="max-w-md text-center">
        <h2 className="mb-4 text-2xl font-semibold text-[var(--text-primary)]">
          Page not found
        </h2>
        <p className="mb-6 text-[var(--text-secondary)]">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link
          href="/"
          className="inline-block rounded-lg bg-[var(--accent-primary)] px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-primary-hover)]"
        >
          Go home
        </Link>
      </div>
    </div>
  )
}
