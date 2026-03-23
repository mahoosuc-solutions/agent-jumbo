import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080'

export async function GET() {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)
    const res = await fetch(`${BACKEND_URL}/health`, { signal: controller.signal, cache: 'no-store' })
    clearTimeout(timeout)
    if (!res.ok) return NextResponse.json({ live: false })
    const data = await res.json()
    return NextResponse.json({ live: true, status: data.status || 'ok' })
  } catch {
    return NextResponse.json({ live: false })
  }
}
