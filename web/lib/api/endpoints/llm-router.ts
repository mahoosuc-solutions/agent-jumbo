import { z } from 'zod'
import { validatedApi } from '../client'
import { LlmModelSchema, LlmUsageSchema } from '../schemas'

export interface LlmModel {
  id: string
  provider: string
  name: string
  enabled: boolean
}

export interface LlmUsage {
  model: string
  tokens: number
  cost: number
  requests: number
}

const LlmRouterDashboardResponseSchema = z.object({ models: z.array(LlmModelSchema), usage: z.array(LlmUsageSchema) }).passthrough()

export function getLlmRouterDashboard(): Promise<{ models: LlmModel[]; usage: LlmUsage[] }> {
  return validatedApi('llm_router_dashboard', LlmRouterDashboardResponseSchema)
}

const LlmUsageResponseSchema = z.object({ usage: z.array(LlmUsageSchema) }).passthrough()

export function getLlmUsage(): Promise<{ usage: LlmUsage[] }> {
  return validatedApi('llm_router_usage', LlmUsageResponseSchema)
}

const LlmRulesResponseSchema = z.object({ rules: z.array(z.record(z.string(), z.unknown())) }).passthrough()

export function getLlmRules(): Promise<{ rules: Array<Record<string, unknown>> }> {
  return validatedApi('llm_router_rules', LlmRulesResponseSchema)
}

const LlmDiscoverResponseSchema = z.object({ models: z.array(LlmModelSchema) }).passthrough()

export function discoverModels(): Promise<{ models: LlmModel[] }> {
  return validatedApi('llm_router_discover', LlmDiscoverResponseSchema)
}
