import { validatedApi } from '../client'
import { MemoryDashboardResponseSchema } from '../schemas'

export function getMemoryDashboard(): Promise<{ memories: Array<Record<string, unknown>> }> {
  return validatedApi('memory_dashboard', MemoryDashboardResponseSchema)
}
