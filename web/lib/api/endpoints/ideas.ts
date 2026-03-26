import { z } from 'zod'
import { validatedApi } from '../client'

export const IdeaSchema = z.object({
  id: z.number(),
  title: z.string(),
  raw_note: z.string(),
  summary: z.string(),
  status: z.string(),
  priority: z.string(),
  theme: z.string(),
  source: z.string(),
  conversation_context_id: z.string().nullable().optional(),
  project_name: z.string().nullable().optional(),
  workflow_name: z.string().nullable().optional(),
  clarified_summary: z.string().nullable().optional(),
  first_slice: z.string().nullable().optional(),
  promotion_readiness: z.string().nullable().optional(),
  promoted_at: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
}).passthrough()

export type Idea = z.infer<typeof IdeaSchema>

const IdeasDashboardResponseSchema = z.object({
  success: z.boolean(),
  total: z.number(),
  active: z.number(),
  promoted: z.number(),
  by_status: z.record(z.string(), z.number()),
  by_priority: z.record(z.string(), z.number()),
  recent: z.array(IdeaSchema),
}).passthrough()

const IdeasListResponseSchema = z.object({
  success: z.boolean(),
  ideas: z.array(IdeaSchema),
  total: z.number(),
}).passthrough()

const IdeasMutationResponseSchema = z.object({
  success: z.boolean(),
  idea: IdeaSchema,
  project: z.record(z.string(), z.unknown()).optional(),
  workflow: z.object({
    id: z.number(),
    name: z.string(),
    status: z.string(),
  }).optional(),
  work_items_created: z.number().optional(),
}).passthrough()

export function getIdeasDashboard() {
  return validatedApi('ideas_dashboard', IdeasDashboardResponseSchema, {
    body: { action: 'dashboard' },
  })
}

export function getIdeas(params: { status?: string; priority?: string; query?: string } = {}) {
  return validatedApi('ideas_dashboard', IdeasListResponseSchema, {
    body: {
      action: 'list',
      status: params.status,
      priority: params.priority,
      query: params.query,
    },
  })
}

export function createIdea(idea: {
  title: string
  raw_note: string
  summary?: string
  status?: string
  priority?: string
  theme?: string
  source?: string
  conversation_context_id?: string | null
}) {
  return validatedApi('ideas_update', IdeasMutationResponseSchema, {
    body: { action: 'create', idea },
  })
}

export function updateIdea(ideaId: number, updates: Record<string, unknown>) {
  return validatedApi('ideas_update', IdeasMutationResponseSchema, {
    body: { action: 'update', idea_id: ideaId, updates },
  })
}

export function promoteIdeaToProject(ideaId: number) {
  return validatedApi('ideas_update', IdeasMutationResponseSchema, {
    body: { action: 'promote_to_project', idea_id: ideaId },
  })
}
