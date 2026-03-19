'use client'

import { useState, useCallback } from 'react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { StatusDot } from '@/components/ui/StatusDot'
import { Button } from '@/components/ui/Button'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import {
  ClipboardList,
  Play,
  X,
  CheckCircle,
  ArrowUpDown,
  RefreshCw,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Clock,
  Power,
} from 'lucide-react'
import {
  useWorkQueueDashboard,
  useWorkQueueItems,
  useScanWorkQueue,
  useUpdateItemStatus,
  useExecuteItem,
  useBulkUpdate,
  useWorkQueueSchedule,
  useSetSchedule,
  useRemoveSchedule,
} from '@/hooks/useWorkQueue'
import type { WorkItem } from '@/lib/api/endpoints/work-queue'

const statusVariant: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  discovered: 'neutral',
  queued: 'info',
  in_progress: 'warning',
  review: 'info',
  done: 'success',
  dismissed: 'neutral',
}

const sourceVariant: Record<string, 'info' | 'warning' | 'neutral'> = {
  scanner: 'warning',
  linear: 'info',
}

const typeLabels: Record<string, string> = {
  todo: 'TODO',
  fixme: 'FIXME',
  failing_test: 'Failing Test',
  skipped_test: 'Skipped Test',
  stale_dep: 'Stale Dep',
  coverage: 'Coverage',
  linear_issue: 'Linear Issue',
}

function priorityColor(score: number): string {
  if (score >= 70) return 'bg-red-500'
  if (score >= 40) return 'bg-amber-500'
  if (score >= 20) return 'bg-blue-500'
  return 'bg-[var(--surface-tertiary)]'
}

export default function WorkQueuePage() {
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterSource, setFilterSource] = useState<string>('')
  const [projectPath, setProjectPath] = useState<string>('')
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [detailItem, setDetailItem] = useState<WorkItem | null>(null)

  const { data: dashboard, isLoading: dashLoading } = useWorkQueueDashboard(projectPath || undefined)
  const { data: itemsData, isLoading: itemsLoading } = useWorkQueueItems({
    status: filterStatus || undefined,
    source: filterSource || undefined,
    projectPath: projectPath || undefined,
    page,
    pageSize: 50,
  })

  const scan = useScanWorkQueue()
  const updateStatus = useUpdateItemStatus()
  const executeItem = useExecuteItem()
  const bulkUpdate = useBulkUpdate()

  // Schedule
  const { data: scheduleData } = useWorkQueueSchedule()
  const setSchedule = useSetSchedule()
  const removeSchedule = useRemoveSchedule()
  const [cronInput, setCronInput] = useState('')
  const schedule = scheduleData?.schedule

  const handleToggleSchedule = useCallback(() => {
    if (schedule?.enabled) {
      removeSchedule.mutate()
    } else {
      const cron = cronInput.trim() || '0 */6 * * *'
      setSchedule.mutate({ cron, projectPath: projectPath || undefined })
    }
  }, [schedule?.enabled, cronInput, projectPath, removeSchedule, setSchedule])

  const items = itemsData?.items ?? []
  const totalItems = itemsData?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / 50))

  const projects = dashboard?.projects ?? []

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(items.map((i) => i.id)))
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Work Queue</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Discover, prioritize, and execute work across projects
          </p>
        </div>
        <div className="flex items-center gap-2">
          {projects.length > 0 && (
            <select
              aria-label="Select project"
              className="text-sm rounded-md border border-[var(--border-primary)] bg-[var(--surface-primary)] text-[var(--text-primary)] px-2 py-1.5"
              value={projectPath}
              onChange={(e) => { setProjectPath(e.target.value); setPage(1) }}
            >
              <option value="">All Projects</option>
              {projects.map((p) => (
                <option key={p.path} value={p.path}>{p.name}</option>
              ))}
            </select>
          )}
          <Button
            size="sm"
            onClick={() => scan.mutate({ action: 'full_scan', projectPath: projectPath || undefined })}
            disabled={scan.isPending}
          >
            <RefreshCw className={`h-4 w-4 ${scan.isPending ? 'animate-spin' : ''}`} />
            {scan.isPending ? 'Scanning...' : 'Scan Now'}
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Items', value: dashboard?.total },
          { label: 'Queued', value: dashboard?.by_status?.queued ?? 0 },
          { label: 'In Progress', value: dashboard?.by_status?.in_progress ?? 0 },
          { label: 'Done This Week', value: dashboard?.done_this_week },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardBody>
              <p className="text-xs text-[var(--text-secondary)]">{label}</p>
              {dashLoading ? (
                <Skeleton className="h-7 w-12 mt-1" />
              ) : (
                <p className="text-2xl font-semibold text-[var(--text-primary)]">{value ?? 0}</p>
              )}
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Schedule Bar */}
      <Card>
        <CardBody>
          <div className="flex items-center gap-3 flex-wrap">
            <Clock className="h-4 w-4 text-[var(--text-secondary)]" />
            <span className="text-sm font-medium text-[var(--text-primary)]">Scheduled Scan</span>
            {schedule?.enabled ? (
              <Badge variant="success">Active</Badge>
            ) : (
              <Badge variant="neutral">Off</Badge>
            )}
            <input
              type="text"
              aria-label="Cron expression"
              placeholder={schedule?.cron || '0 */6 * * *'}
              value={cronInput}
              onChange={(e) => setCronInput(e.target.value)}
              className="text-sm rounded-md border border-[var(--border-primary)] bg-[var(--surface-primary)] text-[var(--text-primary)] px-2 py-1 w-40 font-mono"
            />
            <span className="text-xs text-[var(--text-tertiary)]">
              {schedule?.enabled ? `cron: ${schedule.cron}` : 'e.g. 0 */6 * * * (every 6h)'}
            </span>
            <Button
              size="sm"
              variant={schedule?.enabled ? 'secondary' : 'primary'}
              onClick={handleToggleSchedule}
              disabled={setSchedule.isPending || removeSchedule.isPending}
            >
              <Power className="h-3.5 w-3.5" />
              {schedule?.enabled ? 'Disable' : 'Enable'}
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <select
          aria-label="Filter by status"
          className="text-sm rounded-md border border-[var(--border-primary)] bg-[var(--surface-primary)] text-[var(--text-primary)] px-2 py-1.5"
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPage(1) }}
        >
          <option value="">All Statuses</option>
          <option value="discovered">Discovered</option>
          <option value="queued">Queued</option>
          <option value="in_progress">In Progress</option>
          <option value="review">Review</option>
          <option value="done">Done</option>
          <option value="dismissed">Dismissed</option>
        </select>

        <select
          aria-label="Filter by source"
          className="text-sm rounded-md border border-[var(--border-primary)] bg-[var(--surface-primary)] text-[var(--text-primary)] px-2 py-1.5"
          value={filterSource}
          onChange={(e) => { setFilterSource(e.target.value); setPage(1) }}
        >
          <option value="">All Sources</option>
          <option value="scanner">Codebase Scanner</option>
          <option value="linear">Linear</option>
        </select>

        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-[var(--text-secondary)]">{selectedIds.size} selected</span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => bulkUpdate.mutate({ itemIds: Array.from(selectedIds), action: 'queue' })}
              disabled={bulkUpdate.isPending}
            >
              Queue Selected
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => bulkUpdate.mutate({ itemIds: Array.from(selectedIds), action: 'dismiss' })}
              disabled={bulkUpdate.isPending}
            >
              Dismiss Selected
            </Button>
          </div>
        )}
      </div>

      {/* Item Table */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--text-primary)]">
            Work Items {totalItems > 0 && <span className="text-[var(--text-tertiary)] font-normal">({totalItems})</span>}
          </h2>
        </CardHeader>
        <CardBody className="p-0">
          {itemsLoading ? (
            <div className="p-4 space-y-2">
              {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : items.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === items.length && items.length > 0}
                        onChange={toggleAll}
                        aria-label="Select all items"
                      />
                    </TableHead>
                    <TableHead className="w-12">Priority</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>File</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <TableRow
                      key={item.id}
                      className="cursor-pointer hover:bg-[var(--surface-secondary)]"
                      onClick={() => setDetailItem(item)}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(item.id)}
                          onChange={() => toggleSelect(item.id)}
                          aria-label={`Select ${item.title}`}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className={`w-1.5 h-6 rounded-full ${priorityColor(item.priority_score)}`} />
                          <span className="text-xs font-mono text-[var(--text-secondary)]">{item.priority_score}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="font-medium text-sm">{item.title}</span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={sourceVariant[item.source] ?? 'neutral'}>{item.source}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-[var(--text-secondary)]">
                          {typeLabels[item.source_type] ?? item.source_type}
                        </span>
                      </TableCell>
                      <TableCell>
                        {item.file_path ? (
                          <span className="text-xs font-mono text-[var(--text-tertiary)] max-w-[200px] truncate block">
                            {item.file_path}{item.line_number ? `:${item.line_number}` : ''}
                          </span>
                        ) : item.url ? (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-brand-500 hover:underline flex items-center gap-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Link <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : (
                          <span className="text-xs text-[var(--text-tertiary)]">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <StatusDot status={statusVariant[item.status] ?? 'neutral'} />
                          <Badge variant={statusVariant[item.status] ?? 'neutral'}>{item.status}</Badge>
                        </div>
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-1">
                          {item.status === 'discovered' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Queue"
                              onClick={() => updateStatus.mutate({ itemId: item.id, status: 'queued' })}
                            >
                              <ArrowUpDown className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          {(item.status === 'queued' || item.status === 'discovered') && (
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Execute"
                              onClick={() => executeItem.mutate(item.id)}
                            >
                              <Play className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          {item.status !== 'done' && item.status !== 'dismissed' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Dismiss"
                              onClick={() => updateStatus.mutate({ itemId: item.id, status: 'dismissed' })}
                            >
                              <X className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border-primary)]">
                  <span className="text-xs text-[var(--text-secondary)]">
                    Page {page} of {totalPages}
                  </span>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState
              icon={<ClipboardList className="h-10 w-10" />}
              title="No work items found"
              description={
                filterStatus || filterSource
                  ? 'Try adjusting your filters.'
                  : 'Click "Scan Now" to discover work items from your codebase.'
              }
              className="py-8"
            />
          )}
        </CardBody>
      </Card>

      {/* Detail Slide-Over */}
      {detailItem && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setDetailItem(null)}
          />
          <div className="relative w-full max-w-lg bg-[var(--surface-primary)] border-l border-[var(--border-primary)] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[var(--text-primary)]">Item Detail</h2>
              <Button size="sm" variant="ghost" onClick={() => setDetailItem(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Title</p>
                <p className="text-sm font-medium text-[var(--text-primary)]">{detailItem.title}</p>
              </div>

              <div className="flex items-center gap-3">
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">Priority</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className={`w-2 h-6 rounded-full ${priorityColor(detailItem.priority_score)}`} />
                    <span className="text-lg font-mono font-semibold">{detailItem.priority_score}</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">Status</p>
                  <Badge variant={statusVariant[detailItem.status] ?? 'neutral'} className="mt-1">
                    {detailItem.status}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">Source</p>
                  <Badge variant={sourceVariant[detailItem.source] ?? 'neutral'} className="mt-1">
                    {detailItem.source}
                  </Badge>
                </div>
              </div>

              {detailItem.description && (
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">Description</p>
                  <pre className="text-xs text-[var(--text-primary)] mt-1 whitespace-pre-wrap bg-[var(--surface-secondary)] rounded p-3 overflow-x-auto">
                    {detailItem.description}
                  </pre>
                </div>
              )}

              {detailItem.file_path && (
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">File</p>
                  <p className="text-sm font-mono text-[var(--text-primary)]">
                    {detailItem.file_path}{detailItem.line_number ? `:${detailItem.line_number}` : ''}
                  </p>
                </div>
              )}

              {detailItem.url && (
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">URL</p>
                  <a
                    href={detailItem.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-brand-500 hover:underline flex items-center gap-1"
                  >
                    {detailItem.url} <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}

              {detailItem.execution_id && (
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">Execution</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm font-mono">#{detailItem.execution_id}</span>
                    <Badge variant={statusVariant[detailItem.execution_status ?? ''] ?? 'neutral'}>
                      {detailItem.execution_status ?? 'unknown'}
                    </Badge>
                  </div>
                </div>
              )}

              <div className="text-xs text-[var(--text-tertiary)] space-y-1">
                {detailItem.discovered_at && <p>Discovered: {detailItem.discovered_at}</p>}
                {detailItem.updated_at && <p>Updated: {detailItem.updated_at}</p>}
              </div>

              <div className="flex items-center gap-2 pt-4 border-t border-[var(--border-primary)]">
                {detailItem.status !== 'done' && detailItem.status !== 'dismissed' && (
                  <>
                    <Button
                      size="sm"
                      onClick={() => {
                        executeItem.mutate(detailItem.id)
                        setDetailItem(null)
                      }}
                    >
                      <Play className="h-3.5 w-3.5" /> Execute
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        updateStatus.mutate({ itemId: detailItem.id, status: 'queued' })
                        setDetailItem(null)
                      }}
                    >
                      Queue
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        updateStatus.mutate({ itemId: detailItem.id, status: 'dismissed' })
                        setDetailItem(null)
                      }}
                    >
                      Dismiss
                    </Button>
                  </>
                )}
                {detailItem.status === 'done' && (
                  <div className="flex items-center gap-2 text-green-500">
                    <CheckCircle className="h-4 w-4" />
                    <span className="text-sm">Completed</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
