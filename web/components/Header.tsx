'use client'

import Link from 'next/link'
import { useState } from 'react'
import { PUBLIC_NAVIGATION } from '@/lib/constants'

export default function Header() {
  const [isOpen, setIsOpen] = useState(false)

  const trackNavClick = (label: string) => {
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', 'navigation_click', {
        location: label,
      })
    }
  }

  return (
    <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="font-bold text-xl text-slate-900 dark:text-white" onClick={() => trackNavClick('Home')}>
          Agent Mahoo
        </Link>
        <ul className="hidden md:flex gap-8">
          {PUBLIC_NAVIGATION.map((item) => (
            <li key={item.href}>
              {'external' in item && item.external ? (
                <a
                  href={item.href}
                  className="text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => trackNavClick(item.label)}
                >
                  {item.label}
                </a>
              ) : (
                <Link href={item.href} className="text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white" onClick={() => trackNavClick(item.label)}>
                  {item.label}
                </Link>
              )}
            </li>
          ))}
        </ul>
        <Link
          href="/try"
          className="hidden md:inline-block px-4 py-1.5 rounded-lg bg-copper-500 text-white text-sm font-semibold hover:bg-copper-400 transition"
          onClick={() => trackNavClick('Try Free CTA')}
        >
          Try Free
        </Link>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="md:hidden p-2"
          aria-label="Toggle menu"
        >
          ☰
        </button>
      </nav>
      {isOpen && (
        <nav className="md:hidden border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 space-y-2">
            {PUBLIC_NAVIGATION.map((item) => (
              'external' in item && item.external ? (
                <a key={item.href} href={item.href} className="block px-3 py-2 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded" target="_blank" rel="noopener noreferrer" onClick={() => { trackNavClick(item.label); setIsOpen(false) }}>
                  {item.label}
                </a>
              ) : (
                <Link key={item.href} href={item.href} className="block px-3 py-2 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded" onClick={() => { trackNavClick(item.label); setIsOpen(false) }}>
                  {item.label}
                </Link>
              )
            ))}
          </div>
        </nav>
      )}
    </header>
  )
}
