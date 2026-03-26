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
    startup?: {
      run_mode?: string
      critical_subsystems?: string[]
      optional_subsystems?: string[]
      chat_restore?: {
        status?: string
        active?: boolean
        started_at?: number | null
        finished_at?: number | null
        error?: string | null
      }
      mos_scheduler?: {
        status?: string
        reason?: string
        registered?: string[]
        count?: number
      }
    }
  }
}

export function healthCheck(): Promise<HealthResponse> {
  return validatedApi('health_check', HealthResponseSchema)
}
