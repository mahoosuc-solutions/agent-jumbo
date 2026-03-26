'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  approveOpportunity,
  createOpportunity,
  getOpportunities,
  getOpportunitiesDashboard,
  getOpportunity,
  getTerritories,
  handoffOpportunity,
  ingestOpportunities,
  qualifyOpportunity,
  runCollectors,
  saveOpportunityEstimate,
  scheduleCollectors,
  setTerritoryStatus,
  unscheduleCollectors,
  updateOpportunity,
} from '@/lib/api/endpoints/opportunities'

const KEYS = {
  dashboard: ['opportunities', 'dashboard'] as const,
  territories: (status?: string) => ['opportunities', 'territories', status] as const,
  list: (params: Record<string, unknown>) => ['opportunities', 'list', params] as const,
  detail: (id: number) => ['opportunities', 'detail', id] as const,
}

export function useOpportunitiesDashboard() {
  return useQuery({
    queryKey: KEYS.dashboard,
    queryFn: getOpportunitiesDashboard,
  })
}

export function useTerritories(status?: string) {
  return useQuery({
    queryKey: KEYS.territories(status),
    queryFn: () => getTerritories(status),
  })
}

export function useOpportunities(params: {
  territoryId?: number
  stage?: string
  lane?: string
  search?: string
}) {
  return useQuery({
    queryKey: KEYS.list(params),
    queryFn: () => getOpportunities(params),
  })
}

export function useOpportunity(opportunityId: number) {
  return useQuery({
    queryKey: KEYS.detail(opportunityId),
    queryFn: () => getOpportunity(opportunityId),
    enabled: opportunityId > 0,
  })
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['opportunities'] })
  qc.invalidateQueries({ queryKey: ['ideas'] })
  qc.invalidateQueries({ queryKey: ['projects'] })
  qc.invalidateQueries({ queryKey: ['workflows'] })
  qc.invalidateQueries({ queryKey: ['work-queue'] })
}

export function useCreateOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createOpportunity,
    onSuccess: () => invalidateAll(qc),
  })
}

export function useIngestOpportunities() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ opportunities, autoQualify = true }: { opportunities: Record<string, unknown>[]; autoQualify?: boolean }) =>
      ingestOpportunities(opportunities, autoQualify),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useRunCollectors() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ collectors, autoQualify = true }: { collectors: Record<string, unknown>[]; autoQualify?: boolean }) =>
      runCollectors(collectors, autoQualify),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useUpdateOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ opportunityId, updates }: { opportunityId: number; updates: Record<string, unknown> }) =>
      updateOpportunity(opportunityId, updates),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useSaveOpportunityEstimate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ opportunityId, estimate }: { opportunityId: number; estimate: Record<string, unknown> }) =>
      saveOpportunityEstimate(opportunityId, estimate),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useApproveOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (opportunityId: number) => approveOpportunity(opportunityId),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useQualifyOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (opportunityId: number) => qualifyOpportunity(opportunityId),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useHandoffOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (opportunityId: number) => handoffOpportunity(opportunityId),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useSetTerritoryStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ territoryId, status }: { territoryId: number; status: string }) =>
      setTerritoryStatus(territoryId, status),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useScheduleCollectors() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ cron, collectors }: { cron: string; collectors: Record<string, unknown>[] }) =>
      scheduleCollectors(cron, collectors),
    onSuccess: () => invalidateAll(qc),
  })
}

export function useUnscheduleCollectors() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => unscheduleCollectors(),
    onSuccess: () => invalidateAll(qc),
  })
}
