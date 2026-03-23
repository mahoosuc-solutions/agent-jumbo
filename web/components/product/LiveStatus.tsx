'use client'

import { useEffect, useState } from 'react'

interface Status {
  live: boolean
  status?: string
}

export default function LiveStatus() {
  const [status, setStatus] = useState<Status | null>(null)

  useEffect(() => {
    fetch('/api/platform-status')
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus({ live: false }))
  }, [])

  if (!status) return null

  return (
    <div className="flex items-center gap-2 text-xs font-mono">
      <span className={`w-2 h-2 rounded-full ${status.live ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`} />
      <span className="text-slate-500">{status.live ? 'Platform Online' : 'Metrics as of build'}</span>
    </div>
  )
}
