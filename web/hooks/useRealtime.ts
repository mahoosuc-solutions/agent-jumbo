'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { pollChat, type ChatLog, type ChatContext, type PollResponse } from '@/lib/api/endpoints/chat'

interface RealtimeState {
  logs: ChatLog[]
  contexts: ChatContext[]
  progress: string
  progressActive: boolean
  paused: boolean
  connected: boolean
}

/**
 * Real-time chat updates via SSE with automatic polling fallback.
 *
 * Attempts SSE first for lower latency and reduced server load.
 * Falls back to polling (1.5s interval) if SSE connection fails.
 */
export function useRealtime(contextId: string | null, enabled = true) {
  const [state, setState] = useState<RealtimeState>({
    logs: [],
    contexts: [],
    progress: '',
    progressActive: false,
    paused: false,
    connected: false,
  })

  const logVersionRef = useRef(0)
  const logGuidRef = useRef('')
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const useSSERef = useRef(true) // Start with SSE, fallback to polling

  // Handle incoming data (shared between SSE and polling)
  const handleData = useCallback((data: PollResponse) => {
    // Handle log_guid change (context reset)
    if (logGuidRef.current && logGuidRef.current !== data.log_guid) {
      logVersionRef.current = 0
      logGuidRef.current = data.log_guid
      setState((prev) => ({ ...prev, logs: [] }))
      // Will get fresh data on next update
      return
    }

    logGuidRef.current = data.log_guid

    if (data.log_version !== logVersionRef.current) {
      setState((prev) => ({
        ...prev,
        logs: logVersionRef.current === 0 ? data.logs : [...prev.logs, ...data.logs],
        contexts: data.contexts,
        progress: data.log_progress,
        progressActive: data.log_progress_active,
        paused: data.paused,
        connected: true,
      }))
      logVersionRef.current = data.log_version
    } else {
      setState((prev) => ({
        ...prev,
        contexts: data.contexts,
        progress: data.log_progress,
        progressActive: data.log_progress_active,
        paused: data.paused,
        connected: true,
      }))
    }
  }, [])

  // SSE connection
  const connectSSE = useCallback(() => {
    if (!enabled || !useSSERef.current) return

    const params = new URLSearchParams()
    if (contextId) params.set('context', contextId)
    params.set('log_version', String(logVersionRef.current))

    const url = `/api/backend/sse?${params.toString()}`
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.error) {
          console.warn('SSE error:', data.error)
          return
        }
        handleData(data as PollResponse)
      } catch {
        // Ignore parse errors
      }
    }

    es.addEventListener('reset', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        logVersionRef.current = 0
        logGuidRef.current = data.log_guid || ''
        setState((prev) => ({ ...prev, logs: [] }))
      } catch {
        // Ignore
      }
    })

    es.addEventListener('reconnect', () => {
      es.close()
      // Reconnect after a brief delay
      setTimeout(() => connectSSE(), 1000)
    })

    es.onerror = () => {
      es.close()
      eventSourceRef.current = null
      // Fall back to polling
      useSSERef.current = false
      startPolling()
    }
  }, [contextId, enabled, handleData])

  // Polling fallback
  const doPoll = useCallback(async () => {
    if (!enabled) return
    try {
      const data: PollResponse = await pollChat(contextId, logVersionRef.current)
      handleData(data)
    } catch {
      setState((prev) => ({ ...prev, connected: false }))
    }
  }, [contextId, enabled, handleData])

  const startPolling = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    doPoll()
    intervalRef.current = setInterval(doPoll, 1500)
  }, [doPoll])

  // Reset on context change
  useEffect(() => {
    logVersionRef.current = 0
    logGuidRef.current = ''
    setState((prev) => ({ ...prev, logs: [] }))
  }, [contextId])

  // Main connection effect
  useEffect(() => {
    if (!enabled) return

    if (useSSERef.current) {
      connectSSE()
    } else {
      startPolling()
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [connectSSE, startPolling, enabled])

  return state
}
