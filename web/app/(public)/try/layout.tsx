import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: {
    default: 'Try Mahoosuc OS',
    template: '%s | Try Mahoosuc OS',
  },
  description: 'Interactive demos — no install, no account required.',
}

export default function TryLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
