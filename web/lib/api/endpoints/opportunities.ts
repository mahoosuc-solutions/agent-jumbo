import { z } from 'zod'
import { validatedApi } from '../client'

export const TerritoryZipSchema = z.object({
  zip_code: z.string(),
  city: z.string(),
  state: z.string(),
}).passthrough()

export const TerritorySchema = z.object({
  id: z.number(),
  state: z.string(),
  metro_name: z.string(),
  cluster_name: z.string(),
  priority_tier: z.number(),
  status: z.string(),
  zips: z.array(TerritoryZipSchema),
  opportunity_total: z.number().optional(),
  by_stage: z.record(z.string(), z.number()).optional(),
  coverage_complete: z.boolean().optional(),
  next_action: z.string().optional(),
}).passthrough()

export const OpportunityEstimateSchema = z.object({
  opportunity_id: z.number(),
  total_hours: z.number(),
  timeline_weeks: z.number(),
  estimated_cost: z.number(),
  pricing_notes: z.string(),
  roles: z.array(z.record(z.string(), z.unknown())),
  milestones: z.array(z.record(z.string(), z.unknown())),
  assumptions: z.array(z.unknown()),
  risks: z.array(z.unknown()),
}).passthrough()

export const OpportunitySchema = z.object({
  id: z.number(),
  territory_id: z.number(),
  title: z.string(),
  buyer_name: z.string(),
  source_type: z.string(),
  source_url: z.string().nullable().optional(),
  external_id: z.string().nullable().optional(),
  zip_code: z.string(),
  city: z.string(),
  state: z.string(),
  stage: z.string(),
  lane: z.string(),
  recommendation: z.string(),
  approval_status: z.string(),
  raw_requirements: z.string(),
  normalized_summary: z.string(),
  must_have_requirements: z.array(z.string()),
  due_date: z.string().nullable().optional(),
  strategic_fit_score: z.number(),
  delivery_risk_score: z.number(),
  estimated_contract_value: z.number(),
  confidence_score: z.number(),
  cluster_name: z.string(),
  metro_name: z.string(),
  linked_idea_id: z.number().nullable().optional(),
  linked_project_name: z.string().nullable().optional(),
  linked_workflow_name: z.string().nullable().optional(),
  linked_proposal_id: z.number().nullable().optional(),
  estimate: OpportunityEstimateSchema.nullable().optional(),
}).passthrough()

const DashboardResponseSchema = z.object({
  success: z.boolean(),
  territories: z.array(TerritorySchema),
  stats: z.object({
    total_territories: z.number(),
    active_territories: z.number(),
    covered_territories: z.number(),
    total_opportunities: z.number(),
    approved_opportunities: z.number(),
  }),
  lane_counts: z.record(z.string(), z.number()),
  lane_board: z.record(
    z.string(),
    z.object({
      count: z.number(),
      items: z.array(OpportunitySchema),
    }),
  ),
  collector_schedule: z.object({
    enabled: z.boolean(),
    cron: z.string(),
    task_uuid: z.string(),
    collectors: z.array(z.record(z.string(), z.unknown())),
  }),
  recent: z.array(OpportunitySchema),
}).passthrough()

const TerritoriesResponseSchema = z.object({
  success: z.boolean(),
  territories: z.array(TerritorySchema),
}).passthrough()

const OpportunitiesResponseSchema = z.object({
  success: z.boolean(),
  opportunities: z.array(OpportunitySchema),
}).passthrough()

const OpportunityResponseSchema = z.object({
  success: z.boolean(),
  opportunity: OpportunitySchema,
  estimate: OpportunityEstimateSchema.optional(),
}).passthrough()

const HandoffResponseSchema = z.object({
  success: z.boolean(),
  opportunity: OpportunitySchema,
  idea: z.record(z.string(), z.unknown()),
  project: z.record(z.string(), z.unknown()),
  workflow: z.record(z.string(), z.unknown()),
  proposal: z.record(z.string(), z.unknown()),
  work_items_created: z.number(),
}).passthrough()

const IngestResponseSchema = z.object({
  success: z.boolean(),
  created: z.number(),
  updated: z.number(),
  qualified: z.number(),
  opportunities: z.array(OpportunitySchema),
}).passthrough()

const CollectorRunResponseSchema = z.object({
  success: z.boolean(),
  created: z.number(),
  updated: z.number(),
  qualified: z.number(),
  runs: z.array(
    z.object({
      adapter: z.string(),
      items_received: z.number(),
      created: z.number(),
      updated: z.number(),
    }),
  ),
  opportunities: z.array(OpportunitySchema),
}).passthrough()

export function getOpportunitiesDashboard() {
  return validatedApi('opportunities_dashboard', DashboardResponseSchema, {
    body: { action: 'dashboard' },
  })
}

export function getTerritories(status?: string) {
  return validatedApi('opportunities_dashboard', TerritoriesResponseSchema, {
    body: { action: 'territories', status },
  })
}

export function getOpportunities(params: {
  territoryId?: number
  stage?: string
  lane?: string
  search?: string
}) {
  return validatedApi('opportunities_dashboard', OpportunitiesResponseSchema, {
    body: {
      action: 'list',
      territory_id: params.territoryId,
      stage: params.stage,
      lane: params.lane,
      search: params.search,
    },
  })
}

export function getOpportunity(opportunityId: number) {
  return validatedApi('opportunities_dashboard', OpportunityResponseSchema, {
    body: { action: 'get', opportunity_id: opportunityId },
  })
}

export function createOpportunity(opportunity: Record<string, unknown>) {
  return validatedApi('opportunities_update', OpportunityResponseSchema, {
    body: { action: 'create', opportunity },
  })
}

export function ingestOpportunities(opportunities: Record<string, unknown>[], autoQualify = true) {
  return validatedApi('opportunities_update', IngestResponseSchema, {
    body: { action: 'ingest', opportunities, auto_qualify: autoQualify },
  })
}

export function runCollectors(collectors: Record<string, unknown>[], autoQualify = true) {
  return validatedApi('opportunities_update', CollectorRunResponseSchema, {
    body: { action: 'run_collectors', collectors, auto_qualify: autoQualify },
  })
}

export function updateOpportunity(opportunityId: number, updates: Record<string, unknown>) {
  return validatedApi('opportunities_update', OpportunityResponseSchema, {
    body: { action: 'update', opportunity_id: opportunityId, updates },
  })
}

export function saveOpportunityEstimate(opportunityId: number, estimate: Record<string, unknown>) {
  return validatedApi('opportunities_update', OpportunityResponseSchema, {
    body: { action: 'estimate', opportunity_id: opportunityId, estimate },
  })
}

export function approveOpportunity(opportunityId: number) {
  return validatedApi('opportunities_update', OpportunityResponseSchema, {
    body: { action: 'approve', opportunity_id: opportunityId },
  })
}

export function qualifyOpportunity(opportunityId: number) {
  return validatedApi('opportunities_update', OpportunityResponseSchema, {
    body: { action: 'qualify', opportunity_id: opportunityId },
  })
}

export function handoffOpportunity(opportunityId: number) {
  return validatedApi('opportunities_update', HandoffResponseSchema, {
    body: { action: 'handoff', opportunity_id: opportunityId },
  })
}

export function setTerritoryStatus(territoryId: number, status: string) {
  return validatedApi(
    'opportunities_update',
    z.object({ success: z.boolean(), updated: z.boolean() }).passthrough(),
    { body: { action: 'set_territory_status', territory_id: territoryId, status } },
  )
}

export function scheduleCollectors(cron: string, collectors: Record<string, unknown>[]) {
  return validatedApi(
    'opportunities_update',
    z.object({
      success: z.boolean(),
      cron: z.string().optional(),
      task_uuid: z.string().optional(),
      collectors: z.array(z.record(z.string(), z.unknown())).optional(),
      error: z.string().optional(),
    }).passthrough(),
    { body: { action: 'schedule_collectors', cron, collectors } },
  )
}

export function unscheduleCollectors() {
  return validatedApi(
    'opportunities_update',
    z.object({ success: z.boolean(), error: z.string().optional() }).passthrough(),
    { body: { action: 'unschedule_collectors' } },
  )
}
