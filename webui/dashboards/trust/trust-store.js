import { createStore } from "/js/AlpineStore.js";
import { loadSettings, saveSettings } from "/js/api.js";

/**
 * Tool risk levels — mirrors Python TOOL_RISK_REGISTRY from trust_system.py
 */
const RISK = { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 };

const TOOL_RISK_REGISTRY = {
  // LOW: read-only, information retrieval
  response: RISK.LOW,
  input: RISK.LOW,
  memory_load: RISK.LOW,
  search_engine: RISK.LOW,
  document_query: RISK.LOW,
  vision_load: RISK.LOW,
  observability_usage_estimator: RISK.LOW,
  unknown: RISK.LOW,
  diagram_tool: RISK.LOW,
  diagram_architect: RISK.LOW,
  // MEDIUM: writes/modifies data but no external effects
  memory_save: RISK.MEDIUM,
  knowledge_ingest: RISK.MEDIUM,
  research_organize: RISK.MEDIUM,
  portfolio_manager: RISK.MEDIUM,
  portfolio_manager_tool: RISK.MEDIUM,
  project_lifecycle: RISK.MEDIUM,
  project_scaffold: RISK.MEDIUM,
  workflow_engine: RISK.MEDIUM,
  workflow_training: RISK.MEDIUM,
  linear_integration: RISK.MEDIUM,
  motion_integration: RISK.MEDIUM,
  notion_integration: RISK.MEDIUM,
  customer_lifecycle: RISK.MEDIUM,
  sales_generator: RISK.MEDIUM,
  brand_voice: RISK.MEDIUM,
  analytics_roi_calculator: RISK.MEDIUM,
  business_xray_tool: RISK.MEDIUM,
  property_manager_tool: RISK.MEDIUM,
  calendar_hub: RISK.MEDIUM,
  life_os: RISK.MEDIUM,
  skill_importer: RISK.MEDIUM,
  solution_catalog: RISK.MEDIUM,
  behaviour_adjustment: RISK.MEDIUM,
  wait: RISK.MEDIUM,
  scheduler: RISK.MEDIUM,
  coordinator: RISK.MEDIUM,
  digest_builder: RISK.MEDIUM,
  ralph_loop: RISK.MEDIUM,
  ai_migration: RISK.MEDIUM,
  demo_request_create: RISK.MEDIUM,
  demo_request_list: RISK.MEDIUM,
  auth_test: RISK.MEDIUM,
  api_design: RISK.MEDIUM,
  security_audit: RISK.MEDIUM,
  // HIGH: external communication, code execution
  email: RISK.HIGH,
  email_advanced: RISK.HIGH,
  telegram_send: RISK.HIGH,
  google_voice_sms: RISK.HIGH,
  twilio_voice_call: RISK.HIGH,
  notify_user: RISK.HIGH,
  a2a_chat: RISK.HIGH,
  code_execution_tool: RISK.HIGH,
  browser_agent: RISK.HIGH,
  visual_validation: RISK.HIGH,
  call_subordinate: RISK.HIGH,
  virtual_team: RISK.HIGH,
  swarm_batch: RISK.HIGH,
  claude_sdk_bridge: RISK.HIGH,
  opencode_bridge: RISK.HIGH,
  pms_hub_tool: RISK.HIGH,
  finance_manager: RISK.HIGH,
  mahoosuc_finance_report: RISK.HIGH,
  code_review: RISK.HIGH,
  // CRITICAL: deploys, deletes, processes payments
  memory_delete: RISK.CRITICAL,
  memory_forget: RISK.CRITICAL,
  deployment_orchestrator: RISK.CRITICAL,
  deployment_execute: RISK.CRITICAL,
  deployment_config: RISK.CRITICAL,
  deployment_run_checks: RISK.CRITICAL,
  deployment_validate_env: RISK.CRITICAL,
  deployment_record_result: RISK.CRITICAL,
  devops_deploy: RISK.CRITICAL,
  devops_monitor: RISK.CRITICAL,
  stripe_payments: RISK.CRITICAL,
  plugin_marketplace: RISK.CRITICAL,
};

const RISK_LABELS = {
  [RISK.LOW]: 'LOW',
  [RISK.MEDIUM]: 'MEDIUM',
  [RISK.HIGH]: 'HIGH',
  [RISK.CRITICAL]: 'CRITICAL',
};

const TRUST_LEVELS = {
  1: {
    name: 'Observer',
    icon: 'eye',
    description: 'Maximum oversight. The agent explains every action and asks for your approval before doing anything. Best for learning how AI agents work.',
    auto: 'Nothing',
    asks: 'Everything',
  },
  2: {
    name: 'Guided',
    icon: 'hand',
    description: 'The agent handles simple read-only tasks automatically, but asks before modifying data, sending messages, or executing code.',
    auto: 'Read-only tasks (search, view, query)',
    asks: 'Data modifications, external actions',
  },
  3: {
    name: 'Collaborative',
    icon: 'handshake',
    description: 'The agent works independently on most tasks, only asking for approval on high-risk actions like sending emails, executing code, or making payments.',
    auto: 'Most tasks including data modifications',
    asks: 'Email, code execution, payments, deployments',
  },
  4: {
    name: 'Autonomous',
    icon: 'rocket',
    description: 'Full autonomy. The agent handles everything including high-risk actions, only pausing for critical operations like deployments and payments.',
    auto: 'Everything except critical operations',
    asks: 'Deployments, deletions, payment processing',
  },
};

const model = {
  // State
  trustLevel: 3,
  loading: false,
  saving: false,
  error: null,

  // Constants exposed to templates
  RISK,
  RISK_LABELS,
  TRUST_LEVELS,
  TOOL_RISK_REGISTRY,

  // ── Lifecycle ──
  async init() {
    await this.loadTrustLevel();
  },

  async loadTrustLevel() {
    this.loading = true;
    this.error = null;
    try {
      const settings = await loadSettings();
      this.trustLevel = parseInt(settings.trust_level, 10) || 3;
    } catch (err) {
      console.error('Trust dashboard: failed to load settings', err);
      this.error = err?.message || 'Failed to load settings';
    } finally {
      this.loading = false;
    }
  },

  async setTrustLevel(level) {
    if (level < 1 || level > 4 || level === this.trustLevel) return;
    this.saving = true;
    this.error = null;
    try {
      await saveSettings({ trust_level: level });
      this.trustLevel = level;
    } catch (err) {
      console.error('Trust dashboard: failed to save trust level', err);
      this.error = err?.message || 'Failed to save trust level';
    } finally {
      this.saving = false;
    }
  },

  // ── Tool filtering ──

  /** Returns true if a tool requires approval at the current trust level */
  toolRequiresApproval(toolName) {
    const risk = TOOL_RISK_REGISTRY[toolName] ?? RISK.MEDIUM;
    const level = this.trustLevel;
    if (level === 1) return true;            // Observer: everything
    if (level === 2) return risk >= RISK.MEDIUM;  // Guided: medium+
    if (level === 3) return risk >= RISK.HIGH;     // Collaborative: high+
    if (level === 4) return risk >= RISK.CRITICAL; // Autonomous: critical only
    return false;
  },

  /** All tools sorted by name, with risk info */
  get allTools() {
    return Object.entries(TOOL_RISK_REGISTRY)
      .map(([name, risk]) => ({
        name,
        risk,
        riskLabel: RISK_LABELS[risk],
      }))
      .sort((a, b) => a.risk - b.risk || a.name.localeCompare(b.name));
  },

  /** Tools that auto-execute at current trust level */
  getAutoTools() {
    return this.allTools.filter(t => !this.toolRequiresApproval(t.name));
  },

  /** Tools that require approval at current trust level */
  getGatedTools() {
    return this.allTools.filter(t => this.toolRequiresApproval(t.name));
  },

  /** Count tools at each risk level */
  get riskCounts() {
    const counts = { [RISK.LOW]: 0, [RISK.MEDIUM]: 0, [RISK.HIGH]: 0, [RISK.CRITICAL]: 0 };
    for (const risk of Object.values(TOOL_RISK_REGISTRY)) {
      counts[risk] = (counts[risk] || 0) + 1;
    }
    return counts;
  },

  /** Current level info */
  get currentLevelInfo() {
    return TRUST_LEVELS[this.trustLevel] || TRUST_LEVELS[3];
  },
};

export const store = createStore("trustDashboard", model);
