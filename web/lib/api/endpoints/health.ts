import { validatedApi } from '../client'
import { HealthResponseSchema } from '../schemas'

export interface HealthResponse {
  ok: boolean
  status: string
  version?: string
  uptime?: number
}

export function healthCheck(): Promise<HealthResponse> {
  return validatedApi('health_check', HealthResponseSchema)
}
