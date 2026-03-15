import { validatedApi } from '../client'
import { PollResponseSchema, OkResponseSchema, CreateChatResponseSchema } from '../schemas'

export interface ChatLog {
  id: string | number
  no: number
  type: string
  heading?: string
  content: string
  temp?: boolean
  kvps?: Record<string, unknown>
}

export interface ChatContext {
  id: string
  name: string
  log_length: number
}

export interface PollResponse {
  ok: boolean
  context: string | null
  log_guid: string
  log_version: number
  logs: ChatLog[]
  log_progress: string
  log_progress_active: boolean
  contexts: ChatContext[]
  tasks: Array<{ id: string; status: string; description: string }>
  notifications: Array<{ type: string; message: string }>
  paused: boolean
  deselect_chat?: boolean
}

export function pollChat(
  contextId: string | null,
  logFrom = 0,
  notificationsFrom = 0,
): Promise<PollResponse> {
  return validatedApi('poll', PollResponseSchema, {
    body: {
      context: contextId,
      log_from: logFrom,
      notifications_from: notificationsFrom,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    },
  })
}

export function sendMessage(
  text: string,
  contextId: string,
  attachments: string[] = [],
): Promise<{ ok: boolean }> {
  return validatedApi('message_async', OkResponseSchema, { body: { text, context: contextId, attachments } })
}

export function createChat(): Promise<{ context: string }> {
  return validatedApi('chat_create', CreateChatResponseSchema)
}

export function resetChat(contextId: string): Promise<{ ok: boolean }> {
  return validatedApi('chat_reset', OkResponseSchema, { body: { context: contextId } })
}

export function deleteChat(contextId: string): Promise<{ ok: boolean }> {
  return validatedApi('chat_delete', OkResponseSchema, { body: { context: contextId } })
}
