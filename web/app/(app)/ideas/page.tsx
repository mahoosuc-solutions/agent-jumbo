'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { Lightbulb, Plus, ArrowRight, Sparkles, FolderPlus, MessageSquare } from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { ChatInput } from '@/components/chat/ChatInput'
import { ChatMessageList } from '@/components/chat/ChatMessageList'
import { ChatProgress } from '@/components/chat/ChatProgress'
import { sendMessage } from '@/lib/api/endpoints/chat'
import { useCreateChat, useSendMessage } from '@/hooks/useChat'
import { useCreateIdea, useIdeas, useIdeasDashboard, usePromoteIdea, useUpdateIdea } from '@/hooks/useIdeas'
import { useProject } from '@/hooks/useProjects'
import { useWorkQueueDashboard, useWorkQueueItems } from '@/hooks/useWorkQueue'
import { useWorkflows } from '@/hooks/useWorkflows'
import type { Idea } from '@/lib/api/endpoints/ideas'
import { useRealtime } from '@/hooks/useRealtime'

const statusVariant: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  captured: 'neutral',
  clarifying: 'info',
  proposed: 'warning',
  promoted: 'success',
  archived: 'neutral',
}

const priorityVariant: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  low: 'neutral',
  medium: 'info',
  high: 'warning',
}

const EMPTY_IDEAS: Idea[] = []

function extractStructuredBrief(content: string) {
  const lines = content.split('\n')
  const sections: Record<string, string[]> = {
    summary: [],
    first_slice: [],
    readiness: [],
  }
  let current: keyof typeof sections | null = null

  for (const rawLine of lines) {
    const line = rawLine.trim()
    const normalized = line.toUpperCase().replace(/\*/g, '')
    if (normalized.startsWith('SUMMARY:')) {
      current = 'summary'
      const remainder = rawLine.split(':').slice(1).join(':').trim()
      if (remainder) sections.summary.push(remainder)
      continue
    }
    if (normalized.startsWith('FIRST_SLICE:')) {
      current = 'first_slice'
      const remainder = rawLine.split(':').slice(1).join(':').trim()
      if (remainder) sections.first_slice.push(remainder)
      continue
    }
    if (normalized.startsWith('READINESS:')) {
      current = 'readiness'
      const remainder = rawLine.split(':').slice(1).join(':').trim()
      if (remainder) sections.readiness.push(remainder)
      continue
    }
    if (current) {
      sections[current].push(rawLine)
    }
  }

  const readinessRaw = sections.readiness.join(' ').toLowerCase()
  let promotionReadiness = ''
  if (readinessRaw.includes('ready')) promotionReadiness = 'ready'
  else if (readinessRaw.includes('high')) promotionReadiness = 'high'
  else if (readinessRaw.includes('medium')) promotionReadiness = 'medium'
  else if (readinessRaw.includes('low')) promotionReadiness = 'low'

  return {
    clarified_summary: sections.summary.join('\n').trim(),
    first_slice: sections.first_slice.join('\n').trim(),
    promotion_readiness: promotionReadiness,
  }
}

export default function IdeasPage() {
  const { toast } = useToast()
  const [modalOpen, setModalOpen] = useState(false)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPriority, setFilterPriority] = useState('')
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [newIdea, setNewIdea] = useState({
    title: '',
    raw_note: '',
    priority: 'medium',
    theme: '',
  })

  const dashboard = useIdeasDashboard()
  const ideasQuery = useIdeas({
    status: filterStatus || undefined,
    priority: filterPriority || undefined,
    query: query || undefined,
  })
  const createIdea = useCreateIdea()
  const updateIdea = useUpdateIdea()
  const promoteIdea = usePromoteIdea()
  const createChat = useCreateChat()

  const ideas = ideasQuery.data?.ideas ?? EMPTY_IDEAS
  const selectedIdea = useMemo(
    () => ideas.find((idea) => idea.id === selectedId) ?? ideas[0] ?? null,
    [ideas, selectedId],
  )
  const ideaChatContextId = selectedIdea?.conversation_context_id ?? null
  const ideaRealtime = useRealtime(ideaChatContextId, Boolean(ideaChatContextId))
  const sendIdeaMessage = useSendMessage(ideaChatContextId)
  const linkedProject = useProject(selectedIdea?.project_name ?? null)
  const workQueueProjects = useWorkQueueDashboard(undefined, Boolean(selectedIdea?.project_name))
  const matchedQueueProjectPath = useMemo(() => {
    if (!selectedIdea?.project_name) return undefined
    const match = workQueueProjects.data?.projects?.find((project) => project.name === selectedIdea.project_name)
    return match?.path
  }, [selectedIdea?.project_name, workQueueProjects.data?.projects])
  const linkedQueueDashboard = useWorkQueueDashboard(matchedQueueProjectPath, Boolean(matchedQueueProjectPath))
  const linkedQueueItems = useWorkQueueItems({
    projectPath: matchedQueueProjectPath,
    page: 1,
    pageSize: 5,
    enabled: Boolean(matchedQueueProjectPath),
  })
  const workflowsQuery = useWorkflows()
  const linkedWorkflow = useMemo(() => {
    if (!selectedIdea?.workflow_name) return null
    return workflowsQuery.data?.workflows?.find((workflow) => workflow.name === selectedIdea.workflow_name) ?? null
  }, [selectedIdea?.workflow_name, workflowsQuery.data?.workflows])

  useEffect(() => {
    if (selectedIdea && selectedId !== selectedIdea.id) {
      setSelectedId(selectedIdea.id)
    }
    if (!selectedIdea && selectedId !== null) {
      setSelectedId(null)
    }
  }, [selectedIdea, selectedId])

  useEffect(() => {
    if (createIdea.isError) {
      toast(createIdea.error?.message || 'Failed to create idea', 'danger')
    }
  }, [createIdea.isError, createIdea.error, toast])

  useEffect(() => {
    if (updateIdea.isError) {
      toast(updateIdea.error?.message || 'Failed to update idea', 'danger')
    }
  }, [updateIdea.isError, updateIdea.error, toast])

  useEffect(() => {
    if (promoteIdea.isError) {
      toast(promoteIdea.error?.message || 'Failed to promote idea', 'danger')
    }
  }, [promoteIdea.isError, promoteIdea.error, toast])

  useEffect(() => {
    if (sendIdeaMessage.isError) {
      toast(sendIdeaMessage.error?.message || 'Failed to send idea message', 'danger')
    }
  }, [sendIdeaMessage.isError, sendIdeaMessage.error, toast])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    const title = newIdea.title.trim()
    const rawNote = newIdea.raw_note.trim()
    if (!title || !rawNote) return
    const result = await createIdea.mutateAsync({
      title,
      raw_note: rawNote,
      priority: newIdea.priority,
      theme: newIdea.theme.trim(),
    })
    setModalOpen(false)
    setNewIdea({ title: '', raw_note: '', priority: 'medium', theme: '' })
    setSelectedId(result.idea.id)
  }

  async function handleStatusChange(idea: Idea, status: string) {
    await updateIdea.mutateAsync({ ideaId: idea.id, updates: { status } })
  }

  async function handlePromote(idea: Idea) {
    const result = await promoteIdea.mutateAsync(idea.id)
    const projectName = result.idea.project_name || result.project?.name || 'untitled'
    const workflowName = result.workflow?.name || result.idea.workflow_name || 'starter workflow'
    const workItemsCreated = result.work_items_created ?? 0
    toast(`Created project ${projectName}, workflow ${workflowName}, and ${workItemsCreated} queue items`, 'success')
  }

  async function handleCreateIdeaChat(idea: Idea) {
    if (idea.conversation_context_id) return
    const result = await createChat.mutateAsync()
    await updateIdea.mutateAsync({
      ideaId: idea.id,
      updates: { conversation_context_id: result.context, status: idea.status === 'captured' ? 'clarifying' : idea.status },
    })
    await sendMessage(
      [
        `Help me refine this idea into a concrete project candidate.`,
        `Idea title: ${idea.title}`,
        idea.theme ? `Theme: ${idea.theme}` : '',
        `Summary: ${idea.summary || '(none yet)'}`,
        `Raw note:`,
        idea.raw_note,
        '',
        'Please respond using this exact structure:',
        'SUMMARY: <clear restatement of the idea>',
        'QUESTIONS: <important clarification questions>',
        'FIRST_SLICE: <smallest useful first project slice>',
        'READINESS: <low|medium|high|ready>',
      ].filter(Boolean).join('\n'),
      result.context,
    )
    toast('Idea chat created', 'success')
  }

  async function handleGenerateBrief(idea: Idea) {
    if (!idea.conversation_context_id) {
      await handleCreateIdeaChat(idea)
      return
    }
    sendIdeaMessage.mutate([
      'Generate an updated structured brief for this idea.',
      'Use this exact format:',
      'SUMMARY: <clear restatement>',
      'QUESTIONS: <important unresolved questions>',
      'FIRST_SLICE: <smallest useful first slice>',
      'READINESS: <low|medium|high|ready>',
    ].join('\n'))
  }

  async function handleSaveLatestBrief(idea: Idea) {
    const latestAssistantLog = [...ideaRealtime.logs]
      .reverse()
      .find((log) => log.type === 'response' || log.type === 'agent')
    if (!latestAssistantLog) {
      toast('No agent brief available to save yet', 'warning')
      return
    }
    const structured = extractStructuredBrief(latestAssistantLog.content)
    if (!structured.clarified_summary && !structured.first_slice && !structured.promotion_readiness) {
      toast('Latest agent response did not match the structured brief format', 'warning')
      return
    }
    await updateIdea.mutateAsync({
      ideaId: idea.id,
      updates: structured,
    })
    toast('Saved structured brief to idea', 'success')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Ideas</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Capture action-oriented ideas, refine them with the agent, and promote the best ones into projects.
          </p>
        </div>
        <Button size="sm" onClick={() => setModalOpen(true)}>
          <Plus className="h-4 w-4" /> New Idea
        </Button>
      </div>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title="New Idea"
        description="Capture a project seed before it turns into a project."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Title"
            placeholder="Operator dashboard for scattered project intake"
            value={newIdea.title}
            onChange={(e) => setNewIdea((prev) => ({ ...prev, title: e.target.value }))}
            required
          />
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="raw-note">Raw Note</label>
            <textarea
              id="raw-note"
              className="flex min-h-[120px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Dump the messy version here. The agent can help clean it up later."
              value={newIdea.raw_note}
              onChange={(e) => setNewIdea((prev) => ({ ...prev, raw_note: e.target.value }))}
              required
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="priority">Priority</label>
              <select
                id="priority"
                className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={newIdea.priority}
                onChange={(e) => setNewIdea((prev) => ({ ...prev, priority: e.target.value }))}
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <Input
              label="Theme"
              placeholder="Operator OS"
              value={newIdea.theme}
              onChange={(e) => setNewIdea((prev) => ({ ...prev, theme: e.target.value }))}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" loading={createIdea.isPending}>
              Create Idea
            </Button>
          </div>
        </form>
      </Modal>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Ideas', value: dashboard.data?.total },
          { label: 'Active', value: dashboard.data?.active },
          { label: 'Promoted', value: dashboard.data?.promoted },
          { label: 'High Priority', value: dashboard.data?.by_priority?.high ?? 0 },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardBody>
              <p className="text-xs text-[var(--text-secondary)]">{label}</p>
              {dashboard.isLoading ? (
                <Skeleton className="h-7 w-12 mt-1" />
              ) : (
                <p className="text-2xl font-semibold text-[var(--text-primary)]">{value ?? 0}</p>
              )}
            </CardBody>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-6">
        <Card className="h-fit">
          <CardHeader>
            <div className="space-y-3">
              <div>
                <h2 className="font-semibold text-[var(--text-primary)]">Idea Queue</h2>
                <p className="text-sm text-[var(--text-secondary)] mt-1">Capture first, sort second.</p>
              </div>
              <Input
                placeholder="Search ideas"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  aria-label="Filter by status"
                  className="rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-2 py-2 text-sm text-[var(--text-primary)]"
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <option value="">All Statuses</option>
                  <option value="captured">Captured</option>
                  <option value="clarifying">Clarifying</option>
                  <option value="proposed">Proposed</option>
                  <option value="promoted">Promoted</option>
                  <option value="archived">Archived</option>
                </select>
                <select
                  aria-label="Filter by priority"
                  className="rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-2 py-2 text-sm text-[var(--text-primary)]"
                  value={filterPriority}
                  onChange={(e) => setFilterPriority(e.target.value)}
                >
                  <option value="">All Priorities</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {ideasQuery.isLoading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3, 4].map((idx) => <Skeleton key={idx} className="h-24 w-full" />)}
              </div>
            ) : ideas.length > 0 ? (
              <div className="divide-y divide-[var(--border-default)]">
                {ideas.map((idea) => (
                  <button
                    key={idea.id}
                    type="button"
                    onClick={() => setSelectedId(idea.id)}
                    className={`w-full text-left px-4 py-4 transition-colors ${
                      selectedIdea?.id === idea.id ? 'bg-brand-50/60 dark:bg-brand-900/10' : 'hover:bg-[var(--surface-secondary)]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-[var(--text-primary)] truncate">{idea.title}</p>
                        <p className="mt-1 text-sm text-[var(--text-secondary)] line-clamp-2">
                          {idea.summary || idea.raw_note}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <Badge variant={priorityVariant[idea.priority] ?? 'neutral'}>{idea.priority}</Badge>
                        <Badge variant={statusVariant[idea.status] ?? 'neutral'}>{idea.status}</Badge>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-xs text-[var(--text-tertiary)] flex-wrap">
                      {idea.theme && <span>{idea.theme}</span>}
                      {idea.project_name && <span>Project: {idea.project_name}</span>}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Lightbulb className="h-10 w-10" />}
                title="No ideas yet"
                description="Start by capturing the next project seed you want the agent to work on."
                className="py-10"
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            {selectedIdea ? (
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold text-[var(--text-primary)]">{selectedIdea.title}</h2>
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    <Badge variant={priorityVariant[selectedIdea.priority] ?? 'neutral'}>
                      {selectedIdea.priority}
                    </Badge>
                    <Badge variant={statusVariant[selectedIdea.status] ?? 'neutral'}>
                      {selectedIdea.status}
                    </Badge>
                    {selectedIdea.theme && <Badge>{selectedIdea.theme}</Badge>}
                    {selectedIdea.project_name && <Badge variant="success">Project: {selectedIdea.project_name}</Badge>}
                    {selectedIdea.workflow_name && <Badge variant="info">Workflow: {selectedIdea.workflow_name}</Badge>}
                    {selectedIdea.promotion_readiness && (
                      <Badge variant={selectedIdea.promotion_readiness === 'ready' ? 'success' : 'warning'}>
                        Readiness: {selectedIdea.promotion_readiness}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap justify-end">
                  {selectedIdea.conversation_context_id ? (
                    <Link href={`/chat/${selectedIdea.conversation_context_id}`}>
                      <Button size="sm" variant="secondary">
                        <MessageSquare className="h-4 w-4" /> Open Chat
                      </Button>
                    </Link>
                  ) : (
                    <Button size="sm" variant="secondary" onClick={() => handleCreateIdeaChat(selectedIdea)} loading={createChat.isPending}>
                      <MessageSquare className="h-4 w-4" /> Create Chat
                    </Button>
                  )}
                  {!selectedIdea.project_name && selectedIdea.status !== 'promoted' && (
                    <Button size="sm" onClick={() => handlePromote(selectedIdea)} loading={promoteIdea.isPending}>
                      <FolderPlus className="h-4 w-4" /> Promote To Project
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <h2 className="font-semibold text-[var(--text-primary)]">Idea Detail</h2>
            )}
          </CardHeader>
          <CardBody>
            {selectedIdea ? (
              <div className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_220px] gap-6">
                  <div className="space-y-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Summary</p>
                      <p className="mt-2 text-sm text-[var(--text-primary)] whitespace-pre-wrap">
                        {selectedIdea.summary}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Raw Note</p>
                      <p className="mt-2 text-sm text-[var(--text-secondary)] whitespace-pre-wrap">
                        {selectedIdea.raw_note}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Next Move</p>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="w-full justify-start"
                      onClick={() => handleStatusChange(selectedIdea, 'clarifying')}
                      disabled={selectedIdea.status === 'clarifying' || updateIdea.isPending}
                    >
                      <Sparkles className="h-4 w-4" /> Clarify With Agent
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="w-full justify-start"
                      onClick={() => handleStatusChange(selectedIdea, 'proposed')}
                      disabled={selectedIdea.status === 'proposed' || updateIdea.isPending}
                    >
                      <ArrowRight className="h-4 w-4" /> Mark Proposed
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="w-full justify-start"
                      onClick={() => handleStatusChange(selectedIdea, 'archived')}
                      disabled={selectedIdea.status === 'archived' || updateIdea.isPending}
                    >
                      <ArrowRight className="h-4 w-4" /> Archive
                    </Button>
                  </div>
                </div>

                <div className="rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] p-4">
                  <p className="text-sm font-medium text-[var(--text-primary)]">Promotion Path</p>
                  <div className="mt-3 flex items-center gap-3 text-sm text-[var(--text-secondary)] flex-wrap">
                    <span className="inline-flex items-center gap-2 rounded-full bg-[var(--surface-primary)] px-3 py-1.5">
                      <Lightbulb className="h-4 w-4" /> Idea
                    </span>
                    <ArrowRight className="h-4 w-4" />
                    <span className="inline-flex items-center gap-2 rounded-full bg-[var(--surface-primary)] px-3 py-1.5">
                      <FolderPlus className="h-4 w-4" /> Project
                    </span>
                    <ArrowRight className="h-4 w-4" />
                    <span className="inline-flex items-center gap-2 rounded-full bg-[var(--surface-primary)] px-3 py-1.5">
                      <Sparkles className="h-4 w-4" /> Workflow / Queue
                    </span>
                  </div>
                  {selectedIdea.project_name && (
                    <div className="mt-4 space-y-2 text-sm text-[var(--text-secondary)]">
                      <p>Project: <span className="text-[var(--text-primary)]">{selectedIdea.project_name}</span></p>
                      {selectedIdea.workflow_name && (
                        <p>Starter workflow: <span className="text-[var(--text-primary)]">{selectedIdea.workflow_name}</span></p>
                      )}
                      <p>The work queue is seeded automatically for promoted ideas.</p>
                    </div>
                  )}
                </div>

                {selectedIdea.project_name && (
                  <div className="rounded-lg border border-[var(--border-default)] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-[var(--text-primary)]">Downstream Status</p>
                      <div className="flex items-center gap-2">
                        <Link href="/projects">
                          <Button size="sm" variant="secondary">
                            Project
                          </Button>
                        </Link>
                        <Link href="/workflows">
                          <Button size="sm" variant="secondary">
                            Workflow
                          </Button>
                        </Link>
                        <Link href="/work-queue">
                          <Button size="sm" variant="secondary">
                            Queue
                          </Button>
                        </Link>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
                      <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Project</p>
                        {linkedProject.isLoading ? (
                          <Skeleton className="h-20 w-full mt-2" />
                        ) : linkedProject.data?.data ? (
                          <div className="mt-2 space-y-2">
                            <p className="text-sm font-medium text-[var(--text-primary)]">
                              {linkedProject.data.data.title || linkedProject.data.data.name}
                            </p>
                            <p className="text-sm text-[var(--text-secondary)] line-clamp-3">
                              {linkedProject.data.data.description || 'No project description yet.'}
                            </p>
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant="info">Memory: {linkedProject.data.data.memory}</Badge>
                              <Badge variant="neutral">Knowledge: {linkedProject.data.data.knowledge_files_count}</Badge>
                            </div>
                          </div>
                        ) : (
                          <p className="mt-2 text-sm text-[var(--text-secondary)]">Project metadata not available.</p>
                        )}
                      </div>

                      <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Starter Workflow</p>
                        {selectedIdea.workflow_name && linkedWorkflow ? (
                          <div className="mt-2 space-y-2">
                            <p className="text-sm font-medium text-[var(--text-primary)]">{linkedWorkflow.name}</p>
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant={statusVariant[linkedWorkflow.status] ?? 'neutral'}>
                                {linkedWorkflow.status}
                              </Badge>
                              <Badge variant="neutral">{linkedWorkflow.steps.length} steps</Badge>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)]">
                              {linkedWorkflow.steps.filter((step) => step.status === 'completed').length} of {linkedWorkflow.steps.length} steps complete.
                            </p>
                          </div>
                        ) : selectedIdea.workflow_name ? (
                          <div className="mt-2 space-y-2">
                            <p className="text-sm font-medium text-[var(--text-primary)]">{selectedIdea.workflow_name}</p>
                            <p className="text-sm text-[var(--text-secondary)]">Workflow definition exists but current status is not loaded.</p>
                          </div>
                        ) : (
                          <p className="mt-2 text-sm text-[var(--text-secondary)]">No workflow linked yet.</p>
                        )}
                      </div>

                      <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Work Queue</p>
                        {matchedQueueProjectPath ? (
                          linkedQueueDashboard.isLoading ? (
                            <Skeleton className="h-20 w-full mt-2" />
                          ) : (
                            <div className="mt-2 space-y-3">
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge variant="neutral">Total: {linkedQueueDashboard.data?.total ?? 0}</Badge>
                                <Badge variant="info">Queued: {linkedQueueDashboard.data?.by_status?.queued ?? 0}</Badge>
                                <Badge variant="warning">In Progress: {linkedQueueDashboard.data?.by_status?.in_progress ?? 0}</Badge>
                              </div>
                              {(linkedQueueItems.data?.items ?? []).length > 0 ? (
                                <div className="space-y-2">
                                  {(linkedQueueItems.data?.items ?? []).slice(0, 3).map((item) => (
                                    <div key={item.id} className="rounded-md bg-[var(--surface-primary)] px-3 py-2">
                                      <p className="text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
                                      <div className="mt-1 flex items-center gap-2 flex-wrap">
                                        <Badge variant={statusVariant[item.status] ?? 'neutral'}>{item.status}</Badge>
                                        <Badge variant="neutral">{item.priority_score}</Badge>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-sm text-[var(--text-secondary)]">No queue items found for this project.</p>
                              )}
                            </div>
                          )
                        ) : (
                          <p className="mt-2 text-sm text-[var(--text-secondary)]">Queue linkage appears after project registration.</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-[var(--border-default)] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-[var(--text-primary)]">Structured Brief</p>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleGenerateBrief(selectedIdea)}
                          disabled={sendIdeaMessage.isPending || createChat.isPending}
                        >
                          Generate Brief
                        </Button>
                        {selectedIdea.conversation_context_id && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleSaveLatestBrief(selectedIdea)}
                            disabled={updateIdea.isPending}
                          >
                            Save Latest Brief
                          </Button>
                        )}
                      </div>
                    </div>
                    <div className="mt-4 space-y-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Clarified Summary</p>
                        <p className="mt-2 text-sm text-[var(--text-primary)] whitespace-pre-wrap">
                          {selectedIdea.clarified_summary || 'No structured summary saved yet.'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Recommended First Slice</p>
                        <p className="mt-2 text-sm text-[var(--text-primary)] whitespace-pre-wrap">
                          {selectedIdea.first_slice || 'No first slice saved yet.'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Promotion Readiness</p>
                        <p className="mt-2 text-sm text-[var(--text-primary)]">
                          {selectedIdea.promotion_readiness || 'Not assessed yet.'}
                        </p>
                      </div>
                    </div>
                  </div>

                <div className="rounded-lg border border-[var(--border-default)] overflow-hidden">
                  <div className="flex items-center justify-between border-b border-[var(--border-default)] px-4 py-3 bg-[var(--surface-secondary)]">
                    <div>
                      <p className="text-sm font-medium text-[var(--text-primary)]">Idea Refinement</p>
                      <p className="text-xs text-[var(--text-secondary)] mt-1">
                        Work with the agent here before promoting the idea into a project.
                      </p>
                    </div>
                    {selectedIdea.conversation_context_id ? (
                      <Link href={`/chat/${selectedIdea.conversation_context_id}`}>
                        <Button size="sm" variant="secondary">
                          <MessageSquare className="h-4 w-4" /> Full Chat
                        </Button>
                      </Link>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleCreateIdeaChat(selectedIdea)}
                        loading={createChat.isPending}
                      >
                        <MessageSquare className="h-4 w-4" /> Start Refinement
                      </Button>
                    )}
                  </div>

                  {selectedIdea.conversation_context_id ? (
                    <div className="flex flex-col h-[520px]">
                      {ideaRealtime.logs.length > 0 ? (
                        <ChatMessageList logs={ideaRealtime.logs} />
                      ) : (
                        <div className="flex-1 flex items-center justify-center px-6 text-center">
                          <div>
                            <p className="text-sm font-medium text-[var(--text-primary)]">Refinement thread is ready</p>
                            <p className="text-sm text-[var(--text-secondary)] mt-2">
                              Ask the agent to sharpen scope, find risks, or propose the first shippable slice.
                            </p>
                          </div>
                        </div>
                      )}
                      <ChatProgress message={ideaRealtime.progress} active={ideaRealtime.progressActive} />
                      <ChatInput
                        onSend={(text) => sendIdeaMessage.mutate(text)}
                        disabled={sendIdeaMessage.isPending}
                        placeholder="Ask the agent to refine this idea..."
                      />
                    </div>
                  ) : (
                    <div className="px-4 py-8 text-sm text-[var(--text-secondary)]">
                      Create an idea chat to refine this concept in place.
                    </div>
                  )}
                </div>
                </div>
              </div>
            ) : (
              <EmptyState
                icon={<Lightbulb className="h-10 w-10" />}
                title="Select an idea"
                description="Choose an idea from the queue to review its detail and promote it into a project."
                className="py-10"
              />
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
