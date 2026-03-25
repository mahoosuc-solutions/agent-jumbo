'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { activateProject, getProject, getProjectFileStructure, getProjects } from '@/lib/api/endpoints/projects'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  })
}

export function useProject(name: string | null) {
  return useQuery({
    queryKey: ['projects', 'detail', name],
    queryFn: () => getProject(name || ''),
    enabled: Boolean(name),
  })
}

export function useProjectFileStructure(name: string | null) {
  return useQuery({
    queryKey: ['projects', 'file-structure', name],
    queryFn: () => getProjectFileStructure(name || ''),
    enabled: Boolean(name),
  })
}

export function useActivateProject() {
  return useMutation({
    mutationFn: ({ contextId, name }: { contextId: string; name: string }) => activateProject(contextId, name),
  })
}
