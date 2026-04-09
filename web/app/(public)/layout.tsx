import type { Metadata } from 'next'
import Header from '@/components/Header'
import Footer from '@/components/Footer'

export const metadata: Metadata = {
  title: {
    default: 'Agent Mahoo — Your Personal AI Operating System',
    template: '%s | Agent Mahoo',
  },
  description: 'Agent Mahoo orchestrates your life — real estate, finances, wellness, relationships, calendar — with specialized AI agents and human governance. Part of Mahoosuc OS.',
  openGraph: {
    title: 'Agent Mahoo',
    description: 'Your Personal AI Operating System. Part of Mahoosuc OS.',
    type: 'website',
    siteName: 'Agent Mahoo',
  },
}

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      <main className="min-h-screen">{children}</main>
      <Footer />
    </>
  )
}
