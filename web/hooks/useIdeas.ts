'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createIdea, getIdeas, getIdeasDashboard, promoteIdeaToProject, updateIdea } from '@/lib/api/endpoints/ideas'

const KEYS = {
  dashboard: ['ideas', 'dashboard'] as const,
  list: (params: Record<string, unknown>) => ['ideas', 'list', params] as const,
}

export function useIdeasDashboard() {
  return useQuery({
    queryKey: KEYS.dashboard,
    queryFn: getIdeasDashboard,
  })
}

export function useIdeas(params: { status?: string; priority?: string; query?: string } = {}) {
  return useQuery({
    queryKey: KEYS.list(params),
    queryFn: () => getIdeas(params),
  })
}

export function useCreateIdea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createIdea,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ideas'] })
    },
  })
}

export function useUpdateIdea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ideaId, updates }: { ideaId: number; updates: Record<string, unknown> }) =>
      updateIdea(ideaId, updates),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ideas'] })
    },
  })
}

export function usePromoteIdea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ideaId: number) => promoteIdeaToProject(ideaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ideas'] })
    },
  })
}
