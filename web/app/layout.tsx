import type { Metadata } from 'next'
import './globals.css'
import AnalyticsClient from '@/components/AnalyticsClient'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'Agent Mahoo — Your Personal AI Operating System',
  description: 'Real estate, finances, wellness, relationships, calendar — orchestrated by specialized agents. Self-hosted. Part of the Mahoosuc OS platform.',
  icons: {
    icon: '/favicon.svg',
  },
  openGraph: {
    title: 'Agent Mahoo',
    description: 'Your Personal AI Operating System. Part of Mahoosuc OS.',
    type: 'website',
    url: 'https://agent-mahoo.com',
    siteName: 'Agent Mahoo',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Agent Mahoo — Your Personal AI Operating System',
    description: 'Self-hosted personal OS for real estate, finances, wellness, and more. Part of Mahoosuc OS.',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-[var(--surface-primary)] text-[var(--text-primary)]">
        <Providers>
          <AnalyticsClient />
          {children}
        </Providers>
      </body>
    </html>
  )
}
