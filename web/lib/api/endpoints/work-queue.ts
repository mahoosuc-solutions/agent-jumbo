import { z } from 'zod'
import { validatedApi } from '../client'

// ── Schemas ──────────────────────────────────────────

export const WorkItemSchema = z.object({
  id: z.number(),
  external_id: z.string(),
  source: z.string(),
  source_type: z.string(),
  title: z.string(),
  description: z.string().nullable(),
  file_path: z.string().nullable(),
  line_number: z.number().nullable(),
  url: z.string().nullable(),
  status: z.string(),
  priority_score: z.number(),
  priority_raw: z.string().nullable(),
  effort_estimate: z.string().nullable(),
  effort_minutes: z.number().nullable(),
  project_path: z.string(),
  linear_priority: z.number().nullable(),
  linear_state: z.string().nullable(),
  linear_assignee: z.string().nullable(),
  linear_labels: z.string().nullable(),
  execution_id: z.number().nullable(),
  execution_status: z.string().nullable(),
  discovered_at: z.string().nullable(),
  queued_at: z.string().nullable(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  updated_at: z.string().nullable(),
}).passthrough()

export type WorkItem = z.infer<typeof WorkItemSchema>

const ProjectSchema = z.object({
  id: z.number(),
  path: z.string(),
  name: z.string(),
  registered_at: z.string().nullable(),
}).passthrough()

export type Project = z.infer<typeof ProjectSchema>

const DashboardResponseSchema = z.object({
  success: z.boolean(),
  total: z.number(),
  by_status: z.record(z.string(), z.number()),
  by_source: z.record(z.string(), z.number()),
  by_type: z.record(z.string(), z.number()),
  done_this_week: z.number(),
  last_scan: z.record(z.string(), z.unknown()).nullable(),
  projects: z.array(ProjectSchema),
}).passthrough()

const ListResponseSchema = z.object({
  success: z.boolean(),
  items: z.array(WorkItemSchema),
  total: z.number(),
}).passthrough()

const SearchResponseSchema = z.object({
  success: z.boolean(),
  items: z.array(WorkItemSchema),
  total: z.number(),
}).passthrough()

const ItemDetailResponseSchema = z.object({
  success: z.boolean(),
  item: WorkItemSchema.extend({ priority_breakdown: z.record(z.string(), z.unknown()).optional() }),
}).passthrough()

const OkResponseSchema = z.object({ success: z.boolean() }).passthrough()

const ScanResponseSchema = z.object({
  success: z.boolean(),
  scan_id: z.number().optional(),
  items_found: z.number().optional(),
  by_type: z.record(z.string(), z.number()).optional(),
  error: z.string().optional(),
}).passthrough()

const ProjectsResponseSchema = z.object({
  success: z.boolean(),
  projects: z.array(ProjectSchema),
}).passthrough()

const SettingsResponseSchema = z.object({
  success: z.boolean(),
  settings: z.record(z.string(), z.string()),
}).passthrough()

// ── API Functions ────────────────────────────────────

export function getWorkQueueDashboard(projectPath?: string) {
  return validatedApi('work_queue_dashboard', DashboardResponseSchema, {
    body: { action: 'dashboard', project_path: projectPath },
  })
}

export function getWorkQueueItems(params: {
  status?: string
  source?: string
  sourceType?: string
  projectPath?: string
  sortBy?: string
  sortDir?: string
  page?: number
  pageSize?: number
}) {
  return validatedApi('work_queue_dashboard', ListResponseSchema, {
    body: {
      action: 'list',
      status: params.status,
      source: params.source,
      source_type: params.sourceType,
      project_path: params.projectPath,
      sort_by: params.sortBy || 'priority_score',
      sort_dir: params.sortDir || 'DESC',
      page: params.page || 1,
      page_size: params.pageSize || 50,
    },
  })
}

export function searchWorkQueueItems(query: string, projectPath?: string) {
  return validatedApi('work_queue_dashboard', SearchResponseSchema, {
    body: { action: 'search', query, project_path: projectPath },
  })
}

export function getWorkQueueItem(itemId: number) {
  return validatedApi('work_queue_item_get', ItemDetailResponseSchema, {
    body: { item_id: itemId },
  })
}

export function updateWorkQueueItemStatus(itemId: number, status: string) {
  return validatedApi('work_queue_item_update', OkResponseSchema, {
    body: { item_id: itemId, action: 'update_status', status },
  })
}

export function executeWorkQueueItem(itemId: number) {
  return validatedApi('work_queue_item_execute', OkResponseSchema.passthrough(), {
    body: { item_id: itemId },
  })
}

export function bulkUpdateWorkQueueItems(itemIds: number[], action: 'queue' | 'dismiss' | 'archive') {
  return validatedApi('work_queue_item_bulk', OkResponseSchema.passthrough(), {
    body: { item_ids: itemIds, action },
  })
}

export function scanWorkQueue(params: {
  action: 'scan_codebase' | 'sync_linear' | 'full_scan'
  projectPath?: string
  scanTypes?: string[]
}) {
  return validatedApi('work_queue_scan', ScanResponseSchema, {
    body: {
      action: params.action,
      project_path: params.projectPath,
      scan_types: params.scanTypes,
    },
  })
}

export function getWorkQueueProjects() {
  return validatedApi('work_queue_projects', ProjectsResponseSchema, {
    body: { action: 'list' },
  })
}

export function registerWorkQueueProject(path: string, name?: string) {
  return validatedApi('work_queue_projects', OkResponseSchema.passthrough(), {
    body: { action: 'register', path, name },
  })
}

export function removeWorkQueueProject(path: string) {
  return validatedApi('work_queue_projects', OkResponseSchema.passthrough(), {
    body: { action: 'remove', path },
  })
}

export function getWorkQueueSettings() {
  return validatedApi('work_queue_settings', SettingsResponseSchema, {
    body: { action: 'get' },
  })
}

export function setWorkQueueSetting(key: string, value: string) {
  return validatedApi('work_queue_settings', OkResponseSchema, {
    body: { action: 'set', key, value },
  })
}

// ── Schedule ────────────────────────────────────────

const ScheduleSchema = z.object({
  enabled: z.boolean(),
  cron: z.string(),
  scan_types: z.array(z.string()),
  project_path: z.string(),
  task_uuid: z.string(),
})

const ScheduleResponseSchema = z.object({
  success: z.boolean(),
  schedule: ScheduleSchema,
}).passthrough()

export type ScanSchedule = z.infer<typeof ScheduleSchema>

export function getWorkQueueSchedule() {
  return validatedApi('work_queue_settings', ScheduleResponseSchema, {
    body: { action: 'get_schedule' },
  })
}

export function setWorkQueueSchedule(params: {
  cron: string
  projectPath?: string
  scanTypes?: string[]
}) {
  return validatedApi('work_queue_settings', OkResponseSchema.passthrough(), {
    body: {
      action: 'set_schedule',
      cron: params.cron,
      project_path: params.projectPath,
      scan_types: params.scanTypes,
    },
  })
}

export function removeWorkQueueSchedule() {
  return validatedApi('work_queue_settings', OkResponseSchema.passthrough(), {
    body: { action: 'remove_schedule' },
  })
}
