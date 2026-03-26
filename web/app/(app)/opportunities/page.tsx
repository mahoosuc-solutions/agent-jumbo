'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  BriefcaseBusiness,
  CheckCircle2,
  Compass,
  FileCheck2,
  Import,
  Clock3,
  MapPinned,
  Plus,
  Sparkles,
} from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import { useToast } from '@/components/ui/Toast'
import {
  useApproveOpportunity,
  useCreateOpportunity,
  useHandoffOpportunity,
  useOpportunities,
  useOpportunitiesDashboard,
  useQualifyOpportunity,
  useRunCollectors,
  useSaveOpportunityEstimate,
  useScheduleCollectors,
  useSetTerritoryStatus,
  useTerritories,
  useUnscheduleCollectors,
} from '@/hooks/useOpportunities'

const stageVariant: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  discovered: 'neutral',
  normalized: 'info',
  qualified: 'info',
  estimated: 'warning',
  approved_for_solutioning: 'success',
  solutioning: 'warning',
  proposal_ready: 'success',
  submitted: 'info',
  won: 'success',
  lost: 'danger',
  archived: 'neutral',
}

const laneVariant: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  discovery: 'neutral',
  qualification: 'info',
  estimation: 'warning',
  solutioning: 'success',
}

const EMPTY_REQUIREMENTS = 'Security, reporting, integration requirements'

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2)
}

export default function OpportunitiesPage() {
  const { toast } = useToast()
  const dashboard = useOpportunitiesDashboard()
  const territoriesQuery = useTerritories()
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<number | undefined>(undefined)
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('')
  const [laneFilter, setLaneFilter] = useState('')
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false)
  const [estimateModalOpen, setEstimateModalOpen] = useState(false)
  const [autoQualifyImport, setAutoQualifyImport] = useState(true)
  const [collectorCron, setCollectorCron] = useState('0 */6 * * *')
  const [collectorConfigsText, setCollectorConfigsText] = useState(`[
  {
    "adapter": "json_file",
    "name": "metro-json-drop",
    "config": {
      "path": "/tmp/opportunities-feed.json"
    }
  }
]`)
  const [importPayload, setImportPayload] = useState(`[
  {
    "adapter": "inline_json",
    "name": "manual-inline-feed",
    "config": {
      "opportunities": [
        {
          "territory_id": 1,
          "title": "County public health reporting modernization",
          "buyer_name": "County health department",
          "source_type": "public_rfp",
          "external_id": "county-rfp-001",
          "source_url": "https://example.gov/rfps/001",
          "zip_code": "02108",
          "city": "Boston",
          "state": "MA",
          "raw_requirements": "Need secure FHIR reporting, workflow dashboards, analytics, and integration support.",
          "due_date": "2026-04-30"
        }
      ]
    }
  }
]`)
  const [newOpportunity, setNewOpportunity] = useState({
    territory_id: '',
    title: '',
    buyer_name: '',
    zip_code: '',
    city: '',
    state: '',
    source_type: 'manual',
    raw_requirements: '',
    normalized_summary: '',
    recommendation: 'watch',
  })
  const [estimateDraft, setEstimateDraft] = useState({
    total_hours: '240',
    timeline_weeks: '10',
    estimated_cost: '48000',
    roles: 'Solution Architect:120:24000\nEngineer:80:16000\nQA:40:8000',
    milestones: 'Discovery and architecture\nMVP build\nValidation and hardening',
    assumptions: 'Customer supplies subject matter access\nHosted integration APIs available',
    risks: 'Data access delays\nProcurement security review',
    pricing_notes: 'Fixed fee estimate with milestone-based acceptance',
  })

  const territories = territoriesQuery.data?.territories ?? dashboard.data?.territories ?? []

  useEffect(() => {
    if (!selectedTerritoryId && territories.length > 0) {
      const active = territories.find((territory) => territory.status === 'active')
      setSelectedTerritoryId(active?.id ?? territories[0].id)
    }
  }, [selectedTerritoryId, territories])

  const opportunitiesQuery = useOpportunities({
    territoryId: selectedTerritoryId,
    stage: stageFilter || undefined,
    lane: laneFilter || undefined,
    search: search || undefined,
  })
  const opportunities = opportunitiesQuery.data?.opportunities ?? []
  const selectedTerritory = useMemo(
    () => territories.find((territory) => territory.id === selectedTerritoryId) ?? territories[0] ?? null,
    [selectedTerritoryId, territories],
  )
  const selectedOpportunity = useMemo(
    () => opportunities.find((opportunity) => opportunity.id === selectedOpportunityId) ?? opportunities[0] ?? null,
    [opportunities, selectedOpportunityId],
  )

  useEffect(() => {
    if (selectedOpportunity && selectedOpportunityId !== selectedOpportunity.id) {
      setSelectedOpportunityId(selectedOpportunity.id)
    }
    if (!selectedOpportunity && selectedOpportunityId !== null) {
      setSelectedOpportunityId(null)
    }
  }, [selectedOpportunity, selectedOpportunityId])

  const createOpportunity = useCreateOpportunity()
  const runCollectors = useRunCollectors()
  const saveEstimate = useSaveOpportunityEstimate()
  const approveOpportunity = useApproveOpportunity()
  const qualifyOpportunity = useQualifyOpportunity()
  const handoffOpportunity = useHandoffOpportunity()
  const setTerritoryStatus = useSetTerritoryStatus()
  const scheduleCollectors = useScheduleCollectors()
  const unscheduleCollectors = useUnscheduleCollectors()

  function getTerritoryBundle(territoryId?: number | null) {
    const territory = territories.find((item) => item.id === territoryId)
    return territory?.collector_bundle ?? []
  }

  function loadBundleIntoImport(territoryId?: number | null) {
    const bundle = getTerritoryBundle(territoryId)
    if (bundle.length === 0) {
      toast('No predefined collector bundle for this territory', 'warning')
      return
    }
    setImportPayload(prettyJson(bundle))
    setImportModalOpen(true)
  }

  function loadBundleIntoSchedule(territoryId?: number | null) {
    const bundle = getTerritoryBundle(territoryId)
    if (bundle.length === 0) {
      toast('No predefined collector bundle for this territory', 'warning')
      return
    }
    setCollectorConfigsText(prettyJson(bundle))
    setScheduleModalOpen(true)
  }

  useEffect(() => {
    if (createOpportunity.isError) toast(createOpportunity.error?.message || 'Failed to create opportunity', 'danger')
  }, [createOpportunity.isError, createOpportunity.error, toast])
  useEffect(() => {
    if (runCollectors.isError) toast(runCollectors.error?.message || 'Failed to run collectors', 'danger')
  }, [runCollectors.isError, runCollectors.error, toast])
  useEffect(() => {
    if (saveEstimate.isError) toast(saveEstimate.error?.message || 'Failed to save estimate', 'danger')
  }, [saveEstimate.isError, saveEstimate.error, toast])
  useEffect(() => {
    if (approveOpportunity.isError) toast(approveOpportunity.error?.message || 'Failed to approve opportunity', 'danger')
  }, [approveOpportunity.isError, approveOpportunity.error, toast])
  useEffect(() => {
    if (qualifyOpportunity.isError) toast(qualifyOpportunity.error?.message || 'Failed to qualify opportunity', 'danger')
  }, [qualifyOpportunity.isError, qualifyOpportunity.error, toast])
  useEffect(() => {
    if (handoffOpportunity.isError) toast(handoffOpportunity.error?.message || 'Failed to hand off opportunity', 'danger')
  }, [handoffOpportunity.isError, handoffOpportunity.error, toast])
  useEffect(() => {
    if (scheduleCollectors.isError) toast(scheduleCollectors.error?.message || 'Failed to schedule collectors', 'danger')
  }, [scheduleCollectors.isError, scheduleCollectors.error, toast])
  useEffect(() => {
    if (unscheduleCollectors.isError) toast(unscheduleCollectors.error?.message || 'Failed to unschedule collectors', 'danger')
  }, [unscheduleCollectors.isError, unscheduleCollectors.error, toast])

  async function handleCreateOpportunity(e: React.FormEvent) {
    e.preventDefault()
    const territoryId = Number(newOpportunity.territory_id)
    if (!territoryId) return
    const created = await createOpportunity.mutateAsync({
      territory_id: territoryId,
      title: newOpportunity.title.trim(),
      buyer_name: newOpportunity.buyer_name.trim(),
      zip_code: newOpportunity.zip_code.trim(),
      city: newOpportunity.city.trim(),
      state: newOpportunity.state.trim(),
      source_type: newOpportunity.source_type,
      raw_requirements: newOpportunity.raw_requirements.trim(),
      normalized_summary: newOpportunity.normalized_summary.trim(),
      recommendation: newOpportunity.recommendation,
    })
    setCreateModalOpen(false)
    setSelectedTerritoryId(created.opportunity.territory_id)
    setSelectedOpportunityId(created.opportunity.id)
    setNewOpportunity({
      territory_id: String(created.opportunity.territory_id),
      title: '',
      buyer_name: '',
      zip_code: '',
      city: '',
      state: '',
      source_type: 'manual',
      raw_requirements: '',
      normalized_summary: '',
      recommendation: 'watch',
    })
  }

  async function handleRunCollectors(e: React.FormEvent) {
    e.preventDefault()
    let parsed: unknown
    try {
      parsed = JSON.parse(importPayload)
    } catch {
      toast('Import payload must be valid JSON', 'danger')
      return
    }
    if (!Array.isArray(parsed)) {
      toast('Import payload must be a JSON array', 'danger')
      return
    }

    const result = await runCollectors.mutateAsync({
      collectors: parsed as Record<string, unknown>[],
      autoQualify: autoQualifyImport,
    })
    setImportModalOpen(false)
    if (result.opportunities[0]) {
      setSelectedTerritoryId(result.opportunities[0].territory_id)
      setSelectedOpportunityId(result.opportunities[0].id)
    }
    toast(`Collectors created ${result.created} and updated ${result.updated} opportunities`, 'success')
  }

  async function handleScheduleCollectors(e: React.FormEvent) {
    e.preventDefault()
    let parsed: unknown
    try {
      parsed = JSON.parse(collectorConfigsText)
    } catch {
      toast('Collector config must be valid JSON', 'danger')
      return
    }
    if (!Array.isArray(parsed)) {
      toast('Collector config must be a JSON array', 'danger')
      return
    }
    const result = await scheduleCollectors.mutateAsync({
      cron: collectorCron.trim(),
      collectors: parsed as Record<string, unknown>[],
    })
    if (!result.success) {
      toast(result.error || 'Failed to schedule collectors', 'danger')
      return
    }
    setScheduleModalOpen(false)
    toast('Collector schedule saved', 'success')
  }

  async function handleSaveEstimate() {
    if (!selectedOpportunity) return
    const roles = estimateDraft.roles
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [role, hours, cost] = line.split(':')
        return {
          role: role.trim(),
          hours: Number(hours || 0),
          cost: Number(cost || 0),
          description: `${role.trim()} delivery allocation`,
        }
      })
    const milestones = estimateDraft.milestones
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((name, idx) => ({ name, order: idx + 1 }))
    const assumptions = estimateDraft.assumptions.split('\n').map((line) => line.trim()).filter(Boolean)
    const risks = estimateDraft.risks.split('\n').map((line) => line.trim()).filter(Boolean)

    await saveEstimate.mutateAsync({
      opportunityId: selectedOpportunity.id,
      estimate: {
        total_hours: Number(estimateDraft.total_hours),
        timeline_weeks: Number(estimateDraft.timeline_weeks),
        estimated_cost: Number(estimateDraft.estimated_cost),
        roles,
        milestones,
        assumptions,
        risks,
        pricing_notes: estimateDraft.pricing_notes.trim(),
      },
    })
    setEstimateModalOpen(false)
    toast('Detailed estimate saved', 'success')
  }

  async function handleActivateTerritory(territoryId: number) {
    await setTerritoryStatus.mutateAsync({ territoryId, status: 'active' })
    setSelectedTerritoryId(territoryId)
  }

  async function handleMarkCovered(territoryId: number) {
    await setTerritoryStatus.mutateAsync({ territoryId, status: 'covered' })
  }

  async function handleApprove() {
    if (!selectedOpportunity) return
    await approveOpportunity.mutateAsync(selectedOpportunity.id)
    toast('Opportunity approved for solutioning', 'success')
  }

  async function handleQualify() {
    if (!selectedOpportunity) return
    await qualifyOpportunity.mutateAsync(selectedOpportunity.id)
    toast('Opportunity qualified and scored', 'success')
  }

  async function handleHandoff() {
    if (!selectedOpportunity) return
    const result = await handoffOpportunity.mutateAsync(selectedOpportunity.id)
    toast(
      `Created project ${result.project.name}, workflow ${result.workflow.name}, and proposal ${result.proposal.proposal_id}`,
      'success',
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Opportunities</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Territory-based opportunity capture with estimate gating and downstream solutioning handoff.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => loadBundleIntoImport(selectedTerritory?.id)}
            disabled={!selectedTerritory?.collector_bundle?.length}
          >
            <MapPinned className="h-4 w-4" /> Run Territory Bundle
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setImportModalOpen(true)}>
            <Import className="h-4 w-4" /> Import Feed
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setScheduleModalOpen(true)}>
            <Clock3 className="h-4 w-4" /> Schedule
          </Button>
          <Button size="sm" onClick={() => setCreateModalOpen(true)}>
            <Plus className="h-4 w-4" /> New Opportunity
          </Button>
        </div>
      </div>

      <Modal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        title="New Opportunity"
        description="Create an opportunity inside a predefined metro zip cluster."
      >
        <form onSubmit={handleCreateOpportunity} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="territory">
              Territory
            </label>
            <select
              id="territory"
              className="flex h-9 w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 text-sm text-[var(--text-primary)]"
              value={newOpportunity.territory_id}
              onChange={(e) => setNewOpportunity((prev) => ({ ...prev, territory_id: e.target.value }))}
              required
            >
              <option value="">Choose a metro cluster</option>
              {territories.map((territory) => (
                <option key={territory.id} value={territory.id}>
                  {territory.metro_name} — {territory.cluster_name}
                </option>
              ))}
            </select>
          </div>
          <Input
            label="Title"
            placeholder="State public health data modernization support"
            value={newOpportunity.title}
            onChange={(e) => setNewOpportunity((prev) => ({ ...prev, title: e.target.value }))}
            required
          />
          <Input
            label="Buyer"
            placeholder="City public health department"
            value={newOpportunity.buyer_name}
            onChange={(e) => setNewOpportunity((prev) => ({ ...prev, buyer_name: e.target.value }))}
            required
          />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Zip" placeholder="02108" value={newOpportunity.zip_code} onChange={(e) => setNewOpportunity((prev) => ({ ...prev, zip_code: e.target.value }))} />
            <Input label="City" placeholder="Boston" value={newOpportunity.city} onChange={(e) => setNewOpportunity((prev) => ({ ...prev, city: e.target.value }))} />
            <Input label="State" placeholder="MA" value={newOpportunity.state} onChange={(e) => setNewOpportunity((prev) => ({ ...prev, state: e.target.value }))} />
          </div>
          <Input
            label="Summary"
            placeholder="FHIR reporting, dashboards, security, interoperability"
            value={newOpportunity.normalized_summary}
            onChange={(e) => setNewOpportunity((prev) => ({ ...prev, normalized_summary: e.target.value }))}
          />
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="raw-requirements">
              Raw Requirements
            </label>
            <textarea
              id="raw-requirements"
              className="flex min-h-[120px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
              value={newOpportunity.raw_requirements}
              onChange={(e) => setNewOpportunity((prev) => ({ ...prev, raw_requirements: e.target.value }))}
              placeholder={EMPTY_REQUIREMENTS}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="secondary" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" loading={createOpportunity.isPending}>
              Create Opportunity
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={importModalOpen}
        onOpenChange={setImportModalOpen}
        title="Run Collectors"
        description="Paste collector configs or preload the selected territory bundle to ingest normalized opportunities."
      >
        <form onSubmit={handleRunCollectors} className="space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] p-3">
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                {selectedTerritory ? `${selectedTerritory.metro_name} bundle` : 'No territory selected'}
              </p>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {selectedTerritory?.collector_bundle?.length
                  ? `${selectedTerritory.collector_bundle.length} collectors ready to load`
                  : 'Select a territory with a predefined bundle'}
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => loadBundleIntoImport(selectedTerritory?.id)}
              disabled={!selectedTerritory?.collector_bundle?.length}
            >
              Load Bundle
            </Button>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="import-payload">
              Collector Config
            </label>
            <textarea
              id="import-payload"
              className="flex min-h-[260px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
              value={importPayload}
              onChange={(e) => setImportPayload(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[var(--text-primary)]">
            <input
              type="checkbox"
              checked={autoQualifyImport}
              onChange={(e) => setAutoQualifyImport(e.target.checked)}
            />
            Auto-qualify imported opportunities
          </label>
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="secondary" onClick={() => setImportModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" loading={runCollectors.isPending}>
              Run Collectors
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={scheduleModalOpen}
        onOpenChange={setScheduleModalOpen}
        title="Collector Schedule"
        description="Register a scheduled collector run using cron plus one or more source adapters."
      >
        <form onSubmit={handleScheduleCollectors} className="space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] p-3">
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                {selectedTerritory ? `${selectedTerritory.metro_name} schedule bundle` : 'No territory selected'}
              </p>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {selectedTerritory?.collector_bundle?.length
                  ? `${selectedTerritory.collector_bundle.length} collectors ready for scheduling`
                  : 'Select a territory with a predefined bundle'}
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => loadBundleIntoSchedule(selectedTerritory?.id)}
              disabled={!selectedTerritory?.collector_bundle?.length}
            >
              Load Bundle
            </Button>
          </div>
          <Input
            label="Cron"
            value={collectorCron}
            onChange={(e) => setCollectorCron(e.target.value)}
            placeholder="0 */6 * * *"
          />
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="collector-configs">
              Collector Configs
            </label>
            <textarea
              id="collector-configs"
              className="flex min-h-[220px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
              value={collectorConfigsText}
              onChange={(e) => setCollectorConfigsText(e.target.value)}
            />
          </div>
          <div className="flex justify-between gap-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => void unscheduleCollectors.mutateAsync()}
              loading={unscheduleCollectors.isPending}
            >
              Unschedule
            </Button>
            <div className="flex gap-2">
              <Button type="button" size="sm" variant="secondary" onClick={() => setScheduleModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" loading={scheduleCollectors.isPending}>
                Save Schedule
              </Button>
            </div>
          </div>
        </form>
      </Modal>

      <Modal
        open={estimateModalOpen}
        onOpenChange={setEstimateModalOpen}
        title="Detailed Estimate"
        description="Role-based effort and milestone estimate required before solutioning approval."
      >
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Input label="Total Hours" value={estimateDraft.total_hours} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, total_hours: e.target.value }))} />
            <Input label="Timeline Weeks" value={estimateDraft.timeline_weeks} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, timeline_weeks: e.target.value }))} />
            <Input label="Estimated Cost" value={estimateDraft.estimated_cost} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, estimated_cost: e.target.value }))} />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="estimate-roles">Roles</label>
            <textarea id="estimate-roles" className="flex min-h-[110px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]" value={estimateDraft.roles} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, roles: e.target.value }))} />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="estimate-milestones">Milestones</label>
            <textarea id="estimate-milestones" className="flex min-h-[90px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]" value={estimateDraft.milestones} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, milestones: e.target.value }))} />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="estimate-assumptions">Assumptions</label>
              <textarea id="estimate-assumptions" className="flex min-h-[90px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]" value={estimateDraft.assumptions} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, assumptions: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-primary)]" htmlFor="estimate-risks">Risks</label>
              <textarea id="estimate-risks" className="flex min-h-[90px] w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]" value={estimateDraft.risks} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, risks: e.target.value }))} />
            </div>
          </div>
          <Input label="Pricing Notes" value={estimateDraft.pricing_notes} onChange={(e) => setEstimateDraft((prev) => ({ ...prev, pricing_notes: e.target.value }))} />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="secondary" onClick={() => setEstimateModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSaveEstimate} loading={saveEstimate.isPending}>
              Save Estimate
            </Button>
          </div>
        </div>
      </Modal>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Territories', value: dashboard.data?.stats.total_territories, icon: MapPinned },
          { label: 'Active Territories', value: dashboard.data?.stats.active_territories, icon: Compass },
          { label: 'Opportunities', value: dashboard.data?.stats.total_opportunities, icon: BriefcaseBusiness },
          { label: 'Approved', value: dashboard.data?.stats.approved_opportunities, icon: CheckCircle2 },
          { label: 'Solutioning Lane', value: dashboard.data?.lane_counts.solutioning, icon: Sparkles },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardBody>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs text-[var(--text-secondary)]">{label}</p>
                  {dashboard.isLoading ? (
                    <Skeleton className="h-7 w-12 mt-1" />
                  ) : (
                    <p className="text-2xl font-semibold text-[var(--text-primary)]">{value ?? 0}</p>
                  )}
                </div>
                <Icon className="h-5 w-5 text-[var(--text-tertiary)]" />
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <div>
            <h2 className="font-semibold text-[var(--text-primary)]">Assembly-Line Board</h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Functional lane queues for discovery, qualification, estimation, and solutioning.
            </p>
          </div>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {Object.entries(dashboard.data?.lane_board ?? {}).map(([lane, bucket]) => (
              <div key={lane} className="rounded-lg border border-[var(--border-default)] p-4">
                <div className="flex items-center justify-between gap-3">
                  <Badge variant={laneVariant[lane] ?? 'neutral'}>{lane}</Badge>
                  <span className="text-sm font-medium text-[var(--text-primary)]">{bucket.count}</span>
                </div>
                <div className="mt-3 space-y-2">
                  {bucket.items.length > 0 ? (
                    bucket.items.slice(0, 3).map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className="block w-full rounded-md bg-[var(--surface-secondary)] p-3 text-left hover:bg-[var(--surface-tertiary)]"
                        onClick={() => {
                          setSelectedTerritoryId(item.territory_id)
                          setSelectedOpportunityId(item.id)
                        }}
                      >
                        <p className="text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
                        <p className="mt-1 text-xs text-[var(--text-secondary)]">{item.buyer_name}</p>
                      </button>
                    ))
                  ) : (
                    <p className="text-sm text-[var(--text-secondary)]">No items in this lane.</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <div>
            <h2 className="font-semibold text-[var(--text-primary)]">Collector Automation</h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Adapter-based intake automation for normalized feeds and scheduled territory coverage.
            </p>
          </div>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Schedule</p>
              <p className="mt-2 text-sm text-[var(--text-primary)]">
                {dashboard.data?.collector_schedule.enabled ? dashboard.data.collector_schedule.cron : 'disabled'}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Collectors</p>
              <p className="mt-2 text-sm text-[var(--text-primary)]">
                {dashboard.data?.collector_schedule.collectors.length ?? 0}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Task UUID</p>
              <p className="mt-2 text-sm text-[var(--text-primary)] break-all">
                {dashboard.data?.collector_schedule.task_uuid || 'not scheduled'}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Supported Adapters</p>
              <p className="mt-2 text-sm text-[var(--text-primary)]">inline_json, json_file, jsonl_file, csv_file</p>
            </div>
          </div>
          <div className="mt-6">
            <p className="text-sm font-medium text-[var(--text-primary)]">Latest Collector Runs</p>
            {dashboard.data?.collector_runs.length ? (
              <div className="mt-3 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Collector</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Updated</TableHead>
                      <TableHead>Error</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dashboard.data.collector_runs.map((run) => (
                      <TableRow key={`${run.adapter}-${run.id ?? run.started_at ?? run.collector_name ?? 'run'}`}>
                        <TableCell>
                          <div>
                            <p className="font-medium text-[var(--text-primary)]">{run.collector_name || run.adapter}</p>
                            <p className="text-xs text-[var(--text-secondary)] mt-1">{run.adapter}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={run.status === 'ok' ? 'success' : run.status === 'error' ? 'danger' : 'warning'}>
                            {run.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{run.items_received}</TableCell>
                        <TableCell>{run.created_count ?? run.created ?? 0}</TableCell>
                        <TableCell>{run.updated_count ?? run.updated ?? 0}</TableCell>
                        <TableCell className="max-w-[320px] truncate text-xs text-[var(--text-secondary)]">
                          {run.error || 'None'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="mt-2 text-sm text-[var(--text-secondary)]">No collector runs recorded yet.</p>
            )}
          </div>
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-6">
        <Card className="h-fit">
          <CardHeader>
            <div>
              <h2 className="font-semibold text-[var(--text-primary)]">Coverage Planner</h2>
              <p className="text-sm text-[var(--text-secondary)] mt-1">Predefined metro zip clusters with coverage-first progression.</p>
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {territoriesQuery.isLoading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((idx) => <Skeleton key={idx} className="h-24 w-full" />)}
              </div>
            ) : territories.length > 0 ? (
              <div className="divide-y divide-[var(--border-default)]">
                {territories.map((territory) => (
                  <button
                    key={territory.id}
                    type="button"
                    onClick={() => setSelectedTerritoryId(territory.id)}
                    className={`w-full text-left px-4 py-4 transition-colors ${
                      territory.id === selectedTerritoryId ? 'bg-brand-50/60 dark:bg-brand-900/10' : 'hover:bg-[var(--surface-secondary)]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-[var(--text-primary)]">{territory.metro_name}</p>
                        <p className="text-sm text-[var(--text-secondary)] mt-1">{territory.cluster_name}</p>
                        <p className="text-xs text-[var(--text-tertiary)] mt-2">
                          {territory.zips.length} zips · tier {territory.priority_tier}
                        </p>
                        <p className="text-xs text-[var(--text-secondary)] mt-2">{territory.next_action}</p>
                        <div className="mt-2 flex items-center gap-2 flex-wrap">
                          <Badge variant={territory.coverage_evidence?.bundle_ready ? 'success' : 'warning'}>
                            Bundle {territory.coverage_evidence?.successful_collector_count ?? 0}/
                            {territory.coverage_thresholds?.required_successful_collectors ?? territory.collector_bundle?.length ?? 0}
                          </Badge>
                          <Badge variant={territory.coverage_evidence?.backlog_ready ? 'success' : 'warning'}>
                            Backlog {territory.coverage_evidence?.discovered_backlog ?? 0}
                          </Badge>
                        </div>
                      </div>
                      <Badge variant={territory.coverage_complete ? 'success' : territory.status === 'active' ? 'warning' : 'neutral'}>
                        {territory.status}
                      </Badge>
                    </div>
                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                      <Badge variant="neutral">Opps: {territory.opportunity_total ?? 0}</Badge>
                      <Badge variant="info">Qualified: {territory.by_stage?.qualified ?? 0}</Badge>
                      <Badge variant="warning">Estimated: {territory.by_stage?.estimated ?? 0}</Badge>
                    </div>
                    <div className="mt-3">
                      <p className="text-xs text-[var(--text-tertiary)]">Required collectors</p>
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        {territory.collector_bundle?.map((collector) => {
                          const successful = territory.coverage_evidence?.successful_collectors?.includes(String(collector.name))
                          return (
                            <Badge key={String(collector.name)} variant={successful ? 'success' : 'neutral'}>
                              {String(collector.name)}
                            </Badge>
                          )
                        })}
                      </div>
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={(e) => {
                          e.stopPropagation()
                          loadBundleIntoImport(territory.id)
                        }}
                        disabled={!territory.collector_bundle?.length}
                      >
                        Run Bundle
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={(e) => {
                          e.stopPropagation()
                          loadBundleIntoSchedule(territory.id)
                        }}
                        disabled={!territory.collector_bundle?.length}
                      >
                        Schedule Bundle
                      </Button>
                      {territory.status !== 'active' && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleActivateTerritory(territory.id)
                          }}
                          loading={setTerritoryStatus.isPending}
                        >
                          Activate
                        </Button>
                      )}
                      {territory.status !== 'covered' && territory.coverage_complete && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleMarkCovered(territory.id)
                          }}
                          loading={setTerritoryStatus.isPending}
                        >
                          Mark Covered
                        </Button>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState icon={<MapPinned className="h-10 w-10" />} title="No territories" description="Predefined metro clusters will appear here." className="py-10" />
            )}
          </CardBody>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                  <h2 className="font-semibold text-[var(--text-primary)]">Cluster Inbox</h2>
                  <p className="text-sm text-[var(--text-secondary)] mt-1">Lane-based review of opportunities inside the active territory.</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Input placeholder="Search opportunities" value={search} onChange={(e) => setSearch(e.target.value)} />
                  <select className="h-9 rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 text-sm text-[var(--text-primary)]" value={stageFilter} onChange={(e) => setStageFilter(e.target.value)}>
                    <option value="">All stages</option>
                    {['discovered', 'normalized', 'qualified', 'estimated', 'approved_for_solutioning', 'solutioning', 'proposal_ready'].map((stage) => (
                      <option key={stage} value={stage}>{stage}</option>
                    ))}
                  </select>
                  <select className="h-9 rounded-md border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 text-sm text-[var(--text-primary)]" value={laneFilter} onChange={(e) => setLaneFilter(e.target.value)}>
                    <option value="">All lanes</option>
                    {['discovery', 'qualification', 'estimation', 'solutioning'].map((lane) => (
                      <option key={lane} value={lane}>{lane}</option>
                    ))}
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardBody className="p-0">
              {opportunitiesQuery.isLoading ? (
                <div className="p-4 space-y-2">
                  {[1, 2, 3].map((idx) => <Skeleton key={idx} className="h-12 w-full" />)}
                </div>
              ) : opportunities.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Opportunity</TableHead>
                      <TableHead>Lane</TableHead>
                      <TableHead>Stage</TableHead>
                      <TableHead>Fit</TableHead>
                      <TableHead>Approval</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {opportunities.map((opportunity) => (
                      <TableRow key={opportunity.id} className={selectedOpportunity?.id === opportunity.id ? 'bg-brand-50/60 dark:bg-brand-900/10' : ''} onClick={() => setSelectedOpportunityId(opportunity.id)}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{opportunity.title}</p>
                            <p className="text-xs text-[var(--text-secondary)] mt-1">{opportunity.buyer_name}</p>
                          </div>
                        </TableCell>
                        <TableCell><Badge variant={laneVariant[opportunity.lane] ?? 'neutral'}>{opportunity.lane}</Badge></TableCell>
                        <TableCell><Badge variant={stageVariant[opportunity.stage] ?? 'neutral'}>{opportunity.stage}</Badge></TableCell>
                        <TableCell className="text-sm">{Math.round(opportunity.strategic_fit_score)}</TableCell>
                        <TableCell><Badge variant={opportunity.approval_status === 'approved' ? 'success' : 'warning'}>{opportunity.approval_status}</Badge></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <EmptyState icon={<BriefcaseBusiness className="h-10 w-10" />} title="No opportunities yet" description="Start by activating a cluster and adding opportunities into its inbox." className="py-10" />
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="font-semibold text-[var(--text-primary)]">
                {selectedOpportunity ? selectedOpportunity.title : 'Opportunity Detail'}
              </h2>
            </CardHeader>
            <CardBody>
              {!selectedOpportunity ? (
                <EmptyState icon={<FileCheck2 className="h-10 w-10" />} title="Select an opportunity" description="Choose an opportunity from the inbox to review requirements, estimate, and handoff readiness." className="py-10" />
              ) : (
                <div className="space-y-6">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge>{selectedOpportunity.cluster_name}</Badge>
                    <Badge variant={laneVariant[selectedOpportunity.lane] ?? 'neutral'}>{selectedOpportunity.lane}</Badge>
                    <Badge variant={stageVariant[selectedOpportunity.stage] ?? 'neutral'}>{selectedOpportunity.stage}</Badge>
                    <Badge variant={selectedOpportunity.recommendation === 'pursue' ? 'success' : selectedOpportunity.recommendation === 'pass' ? 'danger' : 'warning'}>
                      {selectedOpportunity.recommendation}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                    <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                      <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Buyer</p>
                      <p className="mt-2 text-sm text-[var(--text-primary)]">{selectedOpportunity.buyer_name}</p>
                    </div>
                    <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                      <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Territory</p>
                      <p className="mt-2 text-sm text-[var(--text-primary)]">{selectedOpportunity.metro_name}</p>
                    </div>
                    <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                      <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Estimated Value</p>
                      <p className="mt-2 text-sm text-[var(--text-primary)]">${selectedOpportunity.estimated_contract_value.toLocaleString()}</p>
                    </div>
                    <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                      <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Confidence</p>
                      <p className="mt-2 text-sm text-[var(--text-primary)]">{Math.round(selectedOpportunity.confidence_score)}%</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Normalized Summary</p>
                    <p className="mt-2 text-sm text-[var(--text-primary)] whitespace-pre-wrap">
                      {selectedOpportunity.normalized_summary || 'No normalized summary yet'}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Raw Requirements</p>
                    <pre className="mt-2 text-xs text-[var(--text-primary)] whitespace-pre-wrap rounded-lg bg-[var(--surface-secondary)] p-4 overflow-x-auto">
                      {selectedOpportunity.raw_requirements || 'No raw requirements yet'}
                    </pre>
                  </div>

                  <div className="rounded-lg border border-[var(--border-default)] p-4">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">Detailed Estimate Gate</p>
                        <p className="text-sm text-[var(--text-secondary)] mt-1">
                          Solutioning requires a detailed estimate and explicit approval.
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <Button size="sm" variant="secondary" onClick={handleQualify} loading={qualifyOpportunity.isPending}>
                          Qualify
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setEstimateModalOpen(true)}>
                          Save Estimate
                        </Button>
                        <Button size="sm" variant="secondary" onClick={handleApprove} loading={approveOpportunity.isPending} disabled={!selectedOpportunity.estimate}>
                          Approve
                        </Button>
                        <Button size="sm" onClick={handleHandoff} loading={handoffOpportunity.isPending} disabled={selectedOpportunity.approval_status !== 'approved'}>
                          Handoff
                        </Button>
                      </div>
                    </div>
                    {selectedOpportunity.estimate ? (
                      <div className="mt-4 grid grid-cols-1 lg:grid-cols-4 gap-4">
                        <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                          <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Hours</p>
                          <p className="mt-2 text-sm text-[var(--text-primary)]">{selectedOpportunity.estimate.total_hours}</p>
                        </div>
                        <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                          <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Timeline</p>
                          <p className="mt-2 text-sm text-[var(--text-primary)]">{selectedOpportunity.estimate.timeline_weeks} weeks</p>
                        </div>
                        <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                          <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Estimated Cost</p>
                          <p className="mt-2 text-sm text-[var(--text-primary)]">${selectedOpportunity.estimate.estimated_cost.toLocaleString()}</p>
                        </div>
                        <div className="rounded-lg bg-[var(--surface-secondary)] p-4">
                          <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Roles</p>
                          <p className="mt-2 text-sm text-[var(--text-primary)]">{selectedOpportunity.estimate.roles.length}</p>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-4 text-sm text-[var(--text-secondary)]">No estimate saved yet.</p>
                    )}
                  </div>

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                      Must-Have Requirements
                    </p>
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                      {selectedOpportunity.must_have_requirements.length > 0 ? (
                        selectedOpportunity.must_have_requirements.map((requirement) => (
                          <Badge key={requirement} variant="info">
                            {requirement}
                          </Badge>
                        ))
                      ) : (
                        <p className="text-sm text-[var(--text-secondary)]">Qualification has not extracted must-have requirements yet.</p>
                      )}
                    </div>
                  </div>

                  {(selectedOpportunity.linked_project_name || selectedOpportunity.linked_proposal_id) && (
                    <div className="rounded-lg border border-[var(--border-default)] p-4">
                      <p className="text-sm font-medium text-[var(--text-primary)]">Downstream Artifacts</p>
                      <div className="mt-3 flex items-center gap-2 flex-wrap">
                        {selectedOpportunity.linked_idea_id && <Badge variant="info">Idea #{selectedOpportunity.linked_idea_id}</Badge>}
                        {selectedOpportunity.linked_project_name && <Badge variant="success">Project: {selectedOpportunity.linked_project_name}</Badge>}
                        {selectedOpportunity.linked_workflow_name && <Badge variant="warning">Workflow: {selectedOpportunity.linked_workflow_name}</Badge>}
                        {selectedOpportunity.linked_proposal_id && <Badge variant="neutral">Proposal #{selectedOpportunity.linked_proposal_id}</Badge>}
                      </div>
                      <div className="mt-4 flex items-center gap-2 flex-wrap">
                        <Link href="/ideas"><Button size="sm" variant="secondary">Ideas</Button></Link>
                        <Link href="/projects"><Button size="sm" variant="secondary">Projects</Button></Link>
                        <Link href="/workflows"><Button size="sm" variant="secondary">Workflows</Button></Link>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
