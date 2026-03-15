import { z } from 'zod'
import { validatedApi } from '../client'
import { TelemetryEventSchema } from '../schemas'

export interface TelemetryEvent {
  timestamp: string
  type: string
  data: Record<string, unknown>
}

const TelemetryResponseSchema = z.object({ events: z.array(TelemetryEventSchema) }).passthrough()

export function getTelemetry(): Promise<{ events: TelemetryEvent[] }> {
  return validatedApi('telemetry_get', TelemetryResponseSchema)
}
