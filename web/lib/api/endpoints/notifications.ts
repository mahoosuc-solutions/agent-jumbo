import { z } from 'zod'
import { validatedApi } from '../client'
import { NotificationSchema, OkResponseSchema } from '../schemas'

export interface Notification {
  id: string
  type: string
  message: string
  read: boolean
  timestamp: string
}

const NotificationsResponseSchema = z.object({ notifications: z.array(NotificationSchema) }).passthrough()

export function getNotifications(): Promise<{ notifications: Notification[] }> {
  return validatedApi('notifications_get', NotificationsResponseSchema)
}

export function markNotificationRead(id: string): Promise<{ ok: boolean }> {
  return validatedApi('notification_read', OkResponseSchema, { body: { id } })
}
