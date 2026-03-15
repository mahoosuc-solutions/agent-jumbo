import { z } from 'zod'
import { validatedApi } from '../client'
import { SchedulerTaskSchema, OkResponseSchema } from '../schemas'

export interface SchedulerTask {
  id: string
  name: string
  cron: string
  enabled: boolean
  last_run?: string
  last_result?: string
  next_run?: string
}

const SchedulerTasksResponseSchema = z.object({ tasks: z.array(SchedulerTaskSchema) }).passthrough()

export function listSchedulerTasks(): Promise<{ tasks: SchedulerTask[] }> {
  return validatedApi('scheduler_tasks_list', SchedulerTasksResponseSchema)
}

const CreateTaskResponseSchema = z.object({ ok: z.boolean(), id: z.string() }).passthrough()

export function createSchedulerTask(task: Partial<SchedulerTask>): Promise<{ ok: boolean; id: string }> {
  return validatedApi('scheduler_task_create', CreateTaskResponseSchema, { body: task })
}

export function updateSchedulerTask(task: Partial<SchedulerTask>): Promise<{ ok: boolean }> {
  return validatedApi('scheduler_task_update', OkResponseSchema, { body: task })
}

export function deleteSchedulerTask(id: string): Promise<{ ok: boolean }> {
  return validatedApi('scheduler_task_delete', OkResponseSchema, { body: { id } })
}
