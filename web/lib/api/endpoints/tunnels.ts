import { z } from 'zod'
import { validatedApi } from '../client'
import { TunnelStatusResponseSchema } from '../schemas'

export interface TunnelSettings {
  provider: string
  watchdog_interval: number
}

export interface TunnelWatchdogStatus {
  running: boolean
  url: string | null
  provider: string
  last_check: string | null
  error: string | null
}

export interface TunnelStatusResponse {
  settings: TunnelSettings
  watchdog: TunnelWatchdogStatus
}

export function getTunnelSettings(): Promise<TunnelStatusResponse> {
  return validatedApi('tunnel_settings_get', TunnelStatusResponseSchema)
}

const SaveTunnelResponseSchema = z.object({ success: z.boolean() }).passthrough()

export function saveTunnelSettings(settings: Partial<TunnelSettings>): Promise<{ success: boolean }> {
  return validatedApi('tunnel_settings_set', SaveTunnelResponseSchema, { body: { settings } })
}
