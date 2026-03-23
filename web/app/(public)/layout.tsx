import type { Metadata } from 'next'
import Header from '@/components/Header'
import Footer from '@/components/Footer'

export const metadata: Metadata = {
  title: {
    default: 'Mahoosuc OS | The AI Operating System',
    template: '%s | Mahoosuc OS',
  },
  description: 'The event-driven AI operating system for your life and business. Orchestrate agents across properties, finances, workflows, and teams.',
  openGraph: {
    title: 'Mahoosuc OS',
    description: 'The AI Operating System for Your Life and Business',
    type: 'website',
    siteName: 'Mahoosuc OS',
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
