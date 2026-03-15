import { z } from 'zod'
import { validatedApi } from '../client'
import { WorkflowSchema, OkResponseSchema } from '../schemas'

export interface Workflow {
  id: string
  name: string
  status: string
  steps: Array<{ name: string; status: string }>
  created_at?: string
}

const WorkflowDashboardResponseSchema = z.object({ workflows: z.array(WorkflowSchema) }).passthrough()

export function getWorkflowDashboard(): Promise<{ workflows: Workflow[] }> {
  return validatedApi('workflow_dashboard', WorkflowDashboardResponseSchema)
}

export function getWorkflow(id: string): Promise<Workflow> {
  return validatedApi('workflow_get', WorkflowSchema, { body: { id } })
}

export function saveWorkflow(workflow: Partial<Workflow>): Promise<{ ok: boolean }> {
  return validatedApi('workflow_save', OkResponseSchema, { body: workflow })
}

export function deleteWorkflow(id: string): Promise<{ ok: boolean }> {
  return validatedApi('workflow_delete', OkResponseSchema, { body: { id } })
}

export function runWorkflow(id: string): Promise<{ ok: boolean }> {
  return validatedApi('workflow_run', OkResponseSchema, { body: { id } })
}
