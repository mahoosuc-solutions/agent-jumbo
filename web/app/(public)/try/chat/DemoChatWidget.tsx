'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const MAX_TURNS = 5

export default function DemoChatWidget() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "Hi! I'm a demo agent running on Mahoosuc OS. Ask me anything — about the platform, AI workflows, or just say hello. You have 5 free messages.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [turnsUsed, setTurnsUsed] = useState(0)
  const [limitReached, setLimitReached] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send() {
    const text = input.trim()
    if (!text || loading || limitReached) return

    const history = messages.slice(1) // exclude the greeting
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/backend/demo_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      })
      const data = await res.json()

      if (data.error === 'demo_limit_reached') {
        setLimitReached(true)
        setMessages((m) => [
          ...m,
          { role: 'assistant', content: data.message },
        ])
      } else {
        setTurnsUsed(data.turns_used ?? turnsUsed + 1)
        if (data.turns_remaining === 0) setLimitReached(true)
        setMessages((m) => [...m, { role: 'assistant', content: data.reply }])
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: 'Something went wrong — please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const remaining = Math.max(0, MAX_TURNS - turnsUsed)

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 overflow-hidden flex flex-col" style={{ minHeight: '480px' }}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ maxHeight: '360px' }}>
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-copper-500/20 text-white border border-copper-500/30'
                  : 'bg-slate-800 text-slate-200'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 rounded-xl px-4 py-3 text-slate-400 text-sm">
              <span className="animate-pulse">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-slate-800 p-4">
        {limitReached ? (
          <div className="text-center py-2">
            <p className="text-slate-400 text-sm mb-3">You&apos;ve used all 5 demo messages.</p>
            <Link
              href="/signup"
              className="inline-block px-6 py-2.5 rounded-lg bg-copper-500 text-white text-sm font-semibold hover:bg-copper-400 transition"
            >
              Start Free — no credit card
            </Link>
          </div>
        ) : (
          <div className="flex gap-2">
            <input
              className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-copper-500/60"
              placeholder="Type a message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
              disabled={loading}
              autoFocus
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 rounded-lg bg-copper-500 text-white text-sm font-semibold hover:bg-copper-400 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Send
            </button>
          </div>
        )}
        {!limitReached && (
          <p className="text-xs text-slate-600 font-mono mt-2 text-right">
            {remaining} message{remaining !== 1 ? 's' : ''} remaining
          </p>
        )}
      </div>
    </div>
  )
}
