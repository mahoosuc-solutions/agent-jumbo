import { z } from 'zod'
import { validatedApi } from '../client'
import { ChannelStatusSchema, ChannelConfigSchema, OkResponseSchema } from '../schemas'

export interface ChannelStatus {
  channel: string
  connected: boolean
  enabled: boolean
  error: string | null
  last_activity: number | null
  message_count: number
}

export interface ChannelConfig {
  channel: string
  config: Record<string, string>
}

const GatewayStatusResponseSchema = z.object({ channels: z.array(ChannelStatusSchema) }).passthrough()

export function getGatewayStatus(): Promise<{ channels: ChannelStatus[] }> {
  return validatedApi('gateway_status', GatewayStatusResponseSchema)
}

export function connectChannel(channel: string): Promise<{ ok: boolean }> {
  return validatedApi('gateway_connect', OkResponseSchema, { body: { channel } })
}

export function disconnectChannel(channel: string): Promise<{ ok: boolean }> {
  return validatedApi('gateway_disconnect', OkResponseSchema, { body: { channel } })
}

export function getChannelConfig(channel: string): Promise<ChannelConfig> {
  return validatedApi('gateway_channel_config', ChannelConfigSchema, { method: 'GET', params: { channel } }) as Promise<ChannelConfig>
}

export function updateChannelConfig(channel: string, config: Record<string, string>): Promise<{ ok: boolean }> {
  return validatedApi('gateway_channel_config', OkResponseSchema, { body: { channel, config } })
}
