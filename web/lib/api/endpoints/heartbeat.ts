import { z } from 'zod'
import { validatedApi } from '../client'
import { HeartbeatConfigDataSchema, HeartbeatRunSchema, HeartbeatTriggerSchema, OkResponseSchema } from '../schemas'

export interface HeartbeatConfigData {
  enabled: boolean
  interval_seconds: number
  heartbeat_path: string
  last_run: string
  run_count: number
  running: boolean
}

export interface HeartbeatRunItem {
  text: string
  completed: boolean
  result: string
  started_at: string
  finished_at: string
}

export interface HeartbeatRun {
  run_id: string
  started_at: string
  finished_at: string
  items: HeartbeatRunItem[]
  status: string
  error: string
}

export function getHeartbeatConfig(): Promise<HeartbeatConfigData> {
  return validatedApi('heartbeat_config', HeartbeatConfigDataSchema, { method: 'GET' })
}

export function updateHeartbeatConfig(
  updates: Partial<Pick<HeartbeatConfigData, 'enabled' | 'interval_seconds' | 'heartbeat_path'>>
): Promise<HeartbeatConfigData> {
  return validatedApi('heartbeat_config', HeartbeatConfigDataSchema, { body: updates })
}

const TriggerResponseSchema = z.object({ status: z.string(), run: HeartbeatRunSchema }).passthrough()

export function triggerHeartbeat(): Promise<{ status: string; run: HeartbeatRun }> {
  return validatedApi('heartbeat_config', TriggerResponseSchema, { body: { action: 'trigger' } })
}

const HeartbeatLogResponseSchema = z.object({ log: z.array(HeartbeatRunSchema), count: z.number() }).passthrough()

export function getHeartbeatLog(limit = 50): Promise<{ log: HeartbeatRun[]; count: number }> {
  return validatedApi(`heartbeat_log?limit=${limit}`, HeartbeatLogResponseSchema, { method: 'GET' })
}

// --- Heartbeat Triggers ---

export type TriggerType = 'CRON' | 'EVENT' | 'WEBHOOK' | 'CONDITION' | 'MESSAGE'

export interface HeartbeatTrigger {
  id: string
  name: string
  type: TriggerType
  enabled: boolean
  config: TriggerConfig
  created_at: string
  updated_at: string
  last_fired: string | null
  fire_count: number
}

export interface CronConfig {
  expression: string
  timezone: string
}

export interface EventConfig {
  event_type: string
  filter: Record<string, string>
}

export interface WebhookConfig {
  url: string
  method: string
  secret: string
}

export interface ConditionConfig {
  metric: string
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte'
  threshold: number
  cooldown_seconds: number
}

export interface MessageConfig {
  channel: string
  pattern: string
}

export type TriggerConfig = CronConfig | EventConfig | WebhookConfig | ConditionConfig | MessageConfig

export interface CreateTriggerInput {
  name: string
  type: TriggerType
  enabled: boolean
  config: TriggerConfig
}

export interface UpdateTriggerInput extends Partial<CreateTriggerInput> {
  id: string
}

const TriggersListResponseSchema = z.object({ triggers: z.array(HeartbeatTriggerSchema) }).passthrough()

export function listHeartbeatTriggers(): Promise<{ triggers: HeartbeatTrigger[] }> {
  return validatedApi('heartbeat_triggers_list', TriggersListResponseSchema, { method: 'GET' }) as unknown as Promise<{ triggers: HeartbeatTrigger[] }>
}

const TriggerCreateResponseSchema = z.object({ ok: z.boolean(), trigger: HeartbeatTriggerSchema }).passthrough()

export function createHeartbeatTrigger(input: CreateTriggerInput): Promise<{ ok: boolean; trigger: HeartbeatTrigger }> {
  return validatedApi('heartbeat_trigger_create', TriggerCreateResponseSchema, { body: input }) as unknown as Promise<{ ok: boolean; trigger: HeartbeatTrigger }>
}

export function updateHeartbeatTrigger(input: UpdateTriggerInput): Promise<{ ok: boolean; trigger: HeartbeatTrigger }> {
  return validatedApi('heartbeat_trigger_update', TriggerCreateResponseSchema, { body: input }) as unknown as Promise<{ ok: boolean; trigger: HeartbeatTrigger }>
}

export function deleteHeartbeatTrigger(id: string): Promise<{ ok: boolean }> {
  return validatedApi('heartbeat_trigger_delete', OkResponseSchema, { body: { id } })
}

export function emitHeartbeatEvent(eventType: string, payload: Record<string, unknown>): Promise<{ ok: boolean }> {
  return validatedApi('heartbeat_event_emit', OkResponseSchema, { body: { event_type: eventType, payload } })
}
