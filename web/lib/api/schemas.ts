import { z } from 'zod'

// ── Chat ──────────────────────────────────────
export const ChatLogSchema = z.object({
  id: z.union([z.string(), z.number()]),
  no: z.number(),
  type: z.string(),
  heading: z.string().optional(),
  content: z.string(),
  temp: z.boolean().optional(),
  kvps: z.record(z.string(), z.unknown()).optional(),
}).passthrough()

export const ChatContextSchema = z.object({
  id: z.string(),
  name: z.string(),
  log_length: z.number(),
}).passthrough()

export const PollResponseSchema = z.object({
  ok: z.boolean(),
  context: z.string().nullable(),
  log_guid: z.string(),
  log_version: z.number(),
  logs: z.array(ChatLogSchema),
  log_progress: z.string(),
  log_progress_active: z.boolean(),
  contexts: z.array(ChatContextSchema),
  tasks: z.array(z.object({ id: z.string(), status: z.string(), description: z.string() }).passthrough()),
  notifications: z.array(z.object({ type: z.string(), message: z.string() }).passthrough()),
  paused: z.boolean(),
  deselect_chat: z.boolean().optional(),
}).passthrough()

export const OkResponseSchema = z.object({
  ok: z.boolean(),
}).passthrough()

export const CreateChatResponseSchema = z.object({
  context: z.string(),
}).passthrough()

// ── Health ────────────────────────────────────
export const HealthCheckSubSchema = z.object({
  ok: z.boolean(),
}).passthrough()

export const HealthResponseSchema = z.object({
  ok: z.boolean(),
  status: z.enum(['healthy', 'degraded']),
  checks: z.object({
    git: z.object({ ok: z.boolean() }).passthrough(),
    disk: z.object({ ok: z.boolean(), free_gb: z.number() }).passthrough(),
    memory: z.object({ ok: z.boolean() }).passthrough(),
    uptime_seconds: z.number(),
    runtime_metrics: z.record(z.string(), z.unknown()),
  }).passthrough(),
}).passthrough()

// ── Backups ───────────────────────────────────
export const BackupSchema = z.object({
  id: z.string(),
  name: z.string(),
  size: z.number(),
  created_at: z.string(),
}).passthrough()

export const BackupListResponseSchema = z.object({
  backups: z.array(BackupSchema),
}).passthrough()

export const CreateBackupResponseSchema = z.object({
  ok: z.boolean(),
  id: z.string(),
}).passthrough()

// ── Files ─────────────────────────────────────
export const FileEntrySchema = z.object({
  name: z.string(),
  path: z.string(),
  type: z.enum(['file', 'directory']),
  size: z.number().optional(),
  modified: z.string().optional(),
}).passthrough()

export const FileBrowserResultSchema = z.object({
  data: z.object({
    files: z.array(FileEntrySchema),
    current_path: z.string(),
    parent_path: z.string().nullable(),
  }).passthrough(),
}).passthrough()

// ── Heartbeat ─────────────────────────────────
export const HeartbeatConfigDataSchema = z.object({
  enabled: z.boolean(),
  interval_seconds: z.number(),
  heartbeat_path: z.string(),
  last_run: z.string(),
  run_count: z.number(),
  running: z.boolean(),
}).passthrough()

export const HeartbeatRunItemSchema = z.object({
  text: z.string(),
  completed: z.boolean(),
  result: z.string(),
  started_at: z.string(),
  finished_at: z.string(),
}).passthrough()

export const HeartbeatRunSchema = z.object({
  run_id: z.string(),
  started_at: z.string(),
  finished_at: z.string(),
  items: z.array(HeartbeatRunItemSchema),
  status: z.string(),
  error: z.string(),
}).passthrough()

export const HeartbeatTriggerSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.enum(['CRON', 'EVENT', 'WEBHOOK', 'CONDITION', 'MESSAGE']),
  enabled: z.boolean(),
  config: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  updated_at: z.string(),
  last_fired: z.string().nullable(),
  fire_count: z.number(),
}).passthrough()

// ── LLM Router ────────────────────────────────
export const LlmModelSchema = z.object({
  id: z.string(),
  provider: z.string(),
  name: z.string(),
  enabled: z.boolean(),
}).passthrough()

export const LlmUsageSchema = z.object({
  model: z.string(),
  tokens: z.number(),
  cost: z.number(),
  requests: z.number(),
}).passthrough()

// ── Memory ────────────────────────────────────
export const MemoryDashboardResponseSchema = z.object({
  memories: z.array(z.record(z.string(), z.unknown())),
}).passthrough()

// ── Messaging ─────────────────────────────────
export const ChannelStatusSchema = z.object({
  channel: z.string(),
  connected: z.boolean(),
  enabled: z.boolean(),
  error: z.string().nullable(),
  last_activity: z.number().nullable(),
  message_count: z.number(),
}).passthrough()

export const ChannelConfigSchema = z.object({
  channel: z.string(),
  config: z.record(z.string(), z.string()),
}).passthrough()

// ── Notifications ─────────────────────────────
export const NotificationSchema = z.object({
  id: z.string(),
  type: z.string(),
  message: z.string(),
  read: z.boolean(),
  timestamp: z.string(),
}).passthrough()

// ── OAuth ─────────────────────────────────────
export const GmailAccountSchema = z.object({
  email: z.string(),
  authenticated: z.boolean(),
  scopes: z.array(z.string()),
  added_date: z.string(),
}).passthrough()

export const GmailAccountsResponseSchema = z.object({
  accounts: z.record(z.string(), GmailAccountSchema),
}).passthrough()

// ── Scheduler ─────────────────────────────────
export const SchedulerTaskSchema = z.object({
  id: z.string(),
  name: z.string(),
  cron: z.string(),
  enabled: z.boolean(),
  last_run: z.string().optional(),
  last_result: z.string().optional(),
  next_run: z.string().optional(),
}).passthrough()

// ── Settings ──────────────────────────────────
export const FieldOptionSchema = z.object({
  value: z.string(),
  label: z.string(),
}).passthrough()

export const SettingsFieldSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  type: z.enum(['text', 'number', 'select', 'range', 'textarea', 'password', 'switch', 'button', 'html']),
  value: z.unknown(),
  min: z.number().optional(),
  max: z.number().optional(),
  step: z.number().optional(),
  hidden: z.boolean().optional(),
  options: z.array(FieldOptionSchema).optional(),
  style: z.string().optional(),
}).passthrough()

export const SettingsSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  tab: z.string(),
  fields: z.array(SettingsFieldSchema),
}).passthrough()

export const SettingsOutputSchema = z.object({
  settings: z.object({
    sections: z.array(SettingsSectionSchema),
  }).passthrough(),
}).passthrough()

// ── Skills ────────────────────────────────────
export const ScanIssueSchema = z.object({
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  message: z.string(),
  file: z.string(),
  line: z.number(),
}).passthrough()

export const ScanResultSchema = z.object({
  name: z.string(),
  safe: z.boolean(),
  issues: z.array(ScanIssueSchema),
  scanned_at: z.string(),
}).passthrough()

export const SkillSchema = z.object({
  name: z.string(),
  version: z.string(),
  author: z.string(),
  description: z.string(),
  category: z.string(),
  tier: z.enum(['markdown', 'python']),
  trust_level: z.enum(['builtin', 'verified', 'community', 'local']),
  enabled: z.boolean(),
  installed: z.boolean(),
  source: z.enum(['tool', 'instrument']),
  capabilities: z.array(z.string()),
}).passthrough()

// ── Telemetry ─────────────────────────────────
export const TelemetryEventSchema = z.object({
  timestamp: z.string(),
  type: z.string(),
  data: z.record(z.string(), z.unknown()),
}).passthrough()

// ── Tunnels ───────────────────────────────────
export const TunnelSettingsSchema = z.object({
  provider: z.string(),
  watchdog_interval: z.number(),
}).passthrough()

export const TunnelWatchdogStatusSchema = z.object({
  running: z.boolean(),
  url: z.string().nullable(),
  provider: z.string(),
  last_check: z.string().nullable(),
  error: z.string().nullable(),
}).passthrough()

export const TunnelStatusResponseSchema = z.object({
  settings: TunnelSettingsSchema,
  watchdog: TunnelWatchdogStatusSchema,
}).passthrough()

// ── Workflows ─────────────────────────────────
export const WorkflowSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  steps: z.array(z.object({ name: z.string(), status: z.string() }).passthrough()),
  created_at: z.string().optional(),
}).passthrough()
