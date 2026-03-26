'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { FolderKanban, MessageSquare, GitBranch, ClipboardList, FolderOpen } from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { useCreateChat } from '@/hooks/useChat'
import { useActivateProject, useProject, useProjectFileStructure, useProjects } from '@/hooks/useProjects'
import type { ProjectSummary } from '@/lib/api/endpoints/projects'

const EMPTY_PROJECTS: ProjectSummary[] = []

export default function ProjectsPage() {
  const { toast } = useToast()
  const [query, setQuery] = useState('')
  const [selectedName, setSelectedName] = useState<string | null>(null)

  const projectsQuery = useProjects()
  const createChat = useCreateChat()
  const activateProject = useActivateProject()

  const projects = projectsQuery.data?.data ?? EMPTY_PROJECTS
  const filteredProjects = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return projects
    return projects.filter((project) =>
      [project.name, project.title, project.description].some((value) => value.toLowerCase().includes(q)),
    )
  }, [projects, query])

  useEffect(() => {
    if (!selectedName && filteredProjects.length > 0) {
      setSelectedName(filteredProjects[0].name)
    }
    if (selectedName && !filteredProjects.some((project) => project.name === selectedName)) {
      setSelectedName(filteredProjects[0]?.name ?? null)
    }
  }, [filteredProjects, selectedName])

  const selectedProject = useProject(selectedName)
  const projectFileStructure = useProjectFileStructure(selectedName)

  useEffect(() => {
    if (createChat.isError) {
      toast(createChat.error?.message || 'Failed to create chat', 'danger')
    }
  }, [createChat.isError, createChat.error, toast])

  useEffect(() => {
    if (activateProject.isError) {
      toast(activateProject.error?.message || 'Failed to activate project', 'danger')
    }
  }, [activateProject.isError, activateProject.error, toast])

  async function handleOpenProjectChat() {
    if (!selectedName) return
    const result = await createChat.mutateAsync()
    await activateProject.mutateAsync({ contextId: result.context, name: selectedName })
    toast(`Project chat ready for ${selectedName}`, 'success')
    window.location.href = `/chat/${result.context}`
  }

  const project = selectedProject.data?.data
  const structure = projectFileStructure.data?.data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Projects</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Review active project workspaces and open a project-scoped agent chat.
          </p>
        </div>
        {selectedName && (
          <Button size="sm" onClick={handleOpenProjectChat} loading={createChat.isPending || activateProject.isPending}>
            <MessageSquare className="h-4 w-4" /> Start Project Chat
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-6">
        <Card className="h-fit">
          <CardHeader>
            <div className="space-y-3">
              <div>
                <h2 className="font-semibold text-[var(--text-primary)]">Project List</h2>
                <p className="text-sm text-[var(--text-secondary)] mt-1">Projects created directly or promoted from ideas.</p>
              </div>
              <Input
                placeholder="Search projects"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {projectsQuery.isLoading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3, 4].map((idx) => <Skeleton key={idx} className="h-24 w-full" />)}
              </div>
            ) : filteredProjects.length > 0 ? (
              <div className="divide-y divide-[var(--border-default)]">
                {filteredProjects.map((project) => (
                  <button
                    key={project.name}
                    type="button"
                    onClick={() => setSelectedName(project.name)}
                    className={`w-full text-left px-4 py-4 transition-colors ${
                      selectedName === project.name ? 'bg-brand-50/60 dark:bg-brand-900/10' : 'hover:bg-[var(--surface-secondary)]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-[var(--text-primary)] truncate">
                          {project.title || project.name}
                        </p>
                        <p className="mt-1 text-sm text-[var(--text-secondary)] line-clamp-2">
                          {project.description || 'No description yet'}
                        </p>
                      </div>
                      <Badge>{project.name}</Badge>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<FolderKanban className="h-10 w-10" />}
                title="No projects yet"
                description="Promote an idea into a project or create one through the existing backend API."
                className="py-10"
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-semibold text-[var(--text-primary)]">
              {project ? (project.title || project.name) : 'Project Detail'}
            </h2>
          </CardHeader>
          <CardBody>
            {!selectedName ? (
              <EmptyState
                icon={<FolderKanban className="h-10 w-10" />}
                title="Select a project"
                description="Choose a project from the list to inspect its instructions and file structure."
                className="py-10"
              />
            ) : selectedProject.isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-64 w-full" />
              </div>
            ) : project ? (
              <div className="space-y-6">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge>{project.name}</Badge>
                  <Badge variant="info">Memory: {project.memory}</Badge>
                  <Badge variant="neutral">Knowledge Files: {project.knowledge_files_count}</Badge>
                  <Badge variant="neutral">Instruction Files: {project.instruction_files_count}</Badge>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <Link href="/ideas">
                    <Button variant="secondary" size="sm" className="w-full justify-start">
                      <FolderOpen className="h-4 w-4" /> Back To Ideas
                    </Button>
                  </Link>
                  <Link href="/workflows">
                    <Button variant="secondary" size="sm" className="w-full justify-start">
                      <GitBranch className="h-4 w-4" /> View Workflows
                    </Button>
                  </Link>
                  <Link href="/work-queue">
                    <Button variant="secondary" size="sm" className="w-full justify-start">
                      <ClipboardList className="h-4 w-4" /> View Work Queue
                    </Button>
                  </Link>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Description</p>
                  <p className="mt-2 text-sm text-[var(--text-primary)] whitespace-pre-wrap">
                    {project.description || 'No description yet'}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Instructions</p>
                  <pre className="mt-2 text-xs text-[var(--text-primary)] whitespace-pre-wrap rounded-lg bg-[var(--surface-secondary)] p-4 overflow-x-auto">
                    {project.instructions || 'No instructions yet'}
                  </pre>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">File Structure</p>
                  {projectFileStructure.isLoading ? (
                    <Skeleton className="h-64 w-full mt-2" />
                  ) : (
                    <pre className="mt-2 text-xs text-[var(--text-primary)] whitespace-pre-wrap rounded-lg bg-[var(--surface-secondary)] p-4 overflow-x-auto">
                      {structure || '# Empty'}
                    </pre>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState
                icon={<FolderKanban className="h-10 w-10" />}
                title="Project not found"
                description="The selected project could not be loaded."
                className="py-10"
              />
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
