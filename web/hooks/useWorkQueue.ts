'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getWorkQueueDashboard,
  getWorkQueueItems,
  getWorkQueueItem,
  updateWorkQueueItemStatus,
  executeWorkQueueItem,
  bulkUpdateWorkQueueItems,
  scanWorkQueue,
  getWorkQueueProjects,
  registerWorkQueueProject,
  removeWorkQueueProject,
} from '@/lib/api/endpoints/work-queue'

const KEYS = {
  dashboard: (projectPath?: string) => ['work-queue', 'dashboard', projectPath] as const,
  items: (params: Record<string, unknown>) => ['work-queue', 'items', params] as const,
  item: (id: number) => ['work-queue', 'item', id] as const,
  projects: ['work-queue', 'projects'] as const,
}

export function useWorkQueueDashboard(projectPath?: string) {
  return useQuery({
    queryKey: KEYS.dashboard(projectPath),
    queryFn: () => getWorkQueueDashboard(projectPath),
  })
}

export function useWorkQueueItems(params: {
  status?: string
  source?: string
  sourceType?: string
  projectPath?: string
  sortBy?: string
  sortDir?: string
  page?: number
  pageSize?: number
}) {
  return useQuery({
    queryKey: KEYS.items(params),
    queryFn: () => getWorkQueueItems(params),
  })
}

export function useWorkQueueItem(itemId: number) {
  return useQuery({
    queryKey: KEYS.item(itemId),
    queryFn: () => getWorkQueueItem(itemId),
    enabled: itemId > 0,
  })
}

export function useWorkQueueProjects() {
  return useQuery({
    queryKey: KEYS.projects,
    queryFn: getWorkQueueProjects,
  })
}

export function useUpdateItemStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, status }: { itemId: number; status: string }) =>
      updateWorkQueueItemStatus(itemId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-queue'] })
    },
  })
}

export function useExecuteItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: number) => executeWorkQueueItem(itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-queue'] })
    },
  })
}

export function useBulkUpdate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ itemIds, action }: { itemIds: number[]; action: 'queue' | 'dismiss' | 'archive' }) =>
      bulkUpdateWorkQueueItems(itemIds, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-queue'] })
    },
  })
}

export function useScanWorkQueue() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: {
      action: 'scan_codebase' | 'sync_linear' | 'full_scan'
      projectPath?: string
      scanTypes?: string[]
    }) => scanWorkQueue(params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-queue'] })
    },
  })
}

export function useRegisterProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ path, name }: { path: string; name?: string }) =>
      registerWorkQueueProject(path, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-queue'] })
    },
  })
}

export function useRemoveProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (path: string) => removeWorkQueueProject(path),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-queue'] })
    },
  })
}
