import { validatedApi } from '../client'
import { HealthResponseSchema } from '../schemas'

export interface HealthCheck {
  ok: boolean
  free_gb?: number
  rss_mb?: number
  info?: Record<string, unknown>
  error?: string
  note?: string
}

export interface HealthResponse {
  ok: boolean
  status: 'healthy' | 'degraded'
  checks: {
    git: HealthCheck
    disk: HealthCheck & { free_gb: number }
    memory: HealthCheck
    uptime_seconds: number
    runtime_metrics: Record<string, unknown>
  }
}

export function healthCheck(): Promise<HealthResponse> {
  return validatedApi('health_check', HealthResponseSchema)
}
