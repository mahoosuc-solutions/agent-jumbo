import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const ARTIFACT_ORDER = [
  "inventory.json",
  "research_report.json",
  "definition_of_done.json",
  "execution_plan.json",
  "linear_plan.json",
];

function linesToArray(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function arrayToLines(value) {
  return Array.isArray(value) ? value.join("\n") : "";
}

function taskSlicesToLines(value) {
  if (!Array.isArray(value)) return "";
  return value
    .map((slice) => {
      if (!slice || typeof slice !== "object") return "";
      const title = slice.title || "Execution slice";
      const owner = slice.owner || "unassigned";
      const acceptance = Array.isArray(slice.acceptance_criteria) ? slice.acceptance_criteria.join(", ") : "";
      return `${title} | ${owner} | ${acceptance}`;
    })
    .filter(Boolean)
    .join("\n");
}

function linesToTaskSlices(value) {
  return linesToArray(value).map((line) => {
    const [title, owner, acceptance] = line.split("|").map((part) => part.trim());
    return {
      title: title || "Execution slice",
      owner: owner || "unassigned",
      acceptance_criteria: acceptance
        ? acceptance
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean)
        : [],
      write_scope: [],
    };
  });
}

function childIssuesToLines(value) {
  if (!Array.isArray(value)) return "";
  return value
    .map((issue) => {
      if (!issue || typeof issue !== "object") return "";
      return `${issue.title || "Child issue"} | ${issue.description || ""}`;
    })
    .filter(Boolean)
    .join("\n");
}

function linesToChildIssues(value) {
  return linesToArray(value).map((line) => {
    const [title, description] = line.split("|").map((part) => part.trim());
    return { title: title || "Child issue", description: description || "" };
  });
}

function artifactForm(artifactName, payload) {
  const data = payload || {};
  if (artifactName === "inventory.json") {
    return {
      current_state_summary: data.current_state_summary || "",
      top_level_entries: arrayToLines(data.top_level_entries),
      risks: arrayToLines(data.risks),
    };
  }
  if (artifactName === "research_report.json") {
    return {
      implemented_now: arrayToLines(data.implemented_now),
      gaps: arrayToLines(data.gaps),
      recommended_references: arrayToLines(data.recommended_references),
    };
  }
  if (artifactName === "definition_of_done.json") {
    return {
      functional_requirements: arrayToLines(data.functional_requirements),
      tests_required: arrayToLines(data.tests_required),
      quality_gates: arrayToLines(data.quality_gates),
      security_requirements: arrayToLines(data.security_requirements),
      observability_requirements: arrayToLines(data.observability_requirements),
      rollback_requirements: arrayToLines(data.rollback_requirements),
      release_evidence: arrayToLines(data.release_evidence),
    };
  }
  if (artifactName === "execution_plan.json") {
    return {
      task_slices: taskSlicesToLines(data.task_slices),
      integrator: data.integrator || "",
      approvals_required: arrayToLines(data.approvals_required),
    };
  }
  if (artifactName === "linear_plan.json") {
    return {
      parent_title: data.parent_issue?.title || "",
      parent_description: data.parent_issue?.description || "",
      child_issues: childIssuesToLines(data.child_issues),
    };
  }
  return {};
}

function serializeArtifact(artifactName, form, workspace) {
  const targetPath = workspace?.unit?.target_path || "";
  if (artifactName === "inventory.json") {
    return {
      target_path: targetPath,
      current_state_summary: form.current_state_summary || "",
      top_level_entries: linesToArray(form.top_level_entries),
      risks: linesToArray(form.risks),
    };
  }
  if (artifactName === "research_report.json") {
    return {
      implemented_now: linesToArray(form.implemented_now),
      gaps: linesToArray(form.gaps),
      recommended_references: linesToArray(form.recommended_references),
    };
  }
  if (artifactName === "definition_of_done.json") {
    return {
      functional_requirements: linesToArray(form.functional_requirements),
      tests_required: linesToArray(form.tests_required),
      quality_gates: linesToArray(form.quality_gates),
      security_requirements: linesToArray(form.security_requirements),
      observability_requirements: linesToArray(form.observability_requirements),
      rollback_requirements: linesToArray(form.rollback_requirements),
      release_evidence: linesToArray(form.release_evidence),
    };
  }
  if (artifactName === "execution_plan.json") {
    return {
      task_slices: linesToTaskSlices(form.task_slices),
      integrator: form.integrator || "",
      approvals_required: linesToArray(form.approvals_required),
    };
  }
  if (artifactName === "linear_plan.json") {
    return {
      parent_issue: {
        title: form.parent_title || "",
        description: form.parent_description || "",
      },
      child_issues: linesToChildIssues(form.child_issues),
    };
  }
  return {};
}

const model = {
  loading: false,
  saving: false,
  error: null,
  activeView: "queue",
  dashboard: {
    initiative_title: "",
    products: [],
    summary: {},
  },
  selectedProductSlug: "",
  workspace: null,
  artifactForms: {},
  artifactOrder: ARTIFACT_ORDER,
  actor: "codex-ui",
  branchRef: "",
  deployEnvironment: "",
  targetPathInput: "",
  linearTeamId: "",
  linearProjectId: "",
  linearStateId: "",
  linearPriority: 1,
  bundleNotes: "",
  acknowledgeRepoDiff: false,
  draftProvider: "codex",
  pollingInterval: null,

  async onOpen() {
    await this.refreshDashboard();
    this.startPolling();
  },

  cleanup() {
    this.stopPolling();
  },

  startPolling() {
    if (this.pollingInterval) return;
    this.pollingInterval = setInterval(() => this.pollWorkspace(), 3000);
  },

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  },

  async refreshDashboard() {
    this.loading = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", { action: "dashboard", actor: this.actor });
      if (!resp.ok) throw new Error(resp.error || "Failed to load rollout dashboard");
      this.dashboard = resp.data || this.dashboard;
      if (this.selectedProductSlug) {
        const stillExists = (this.dashboard.products || []).some((item) => item.slug === this.selectedProductSlug);
        if (stillExists) {
          await this.loadWorkspace(this.selectedProductSlug);
        }
      }
    } catch (err) {
      console.error("Rollout dashboard error:", err);
      this.error = err?.message || "Failed to load rollout dashboard";
    } finally {
      this.loading = false;
    }
  },

  async selectProduct(productSlug) {
    this.selectedProductSlug = productSlug;
    this.activeView = "workspace";
    await this.loadWorkspace(productSlug);
  },

  async loadWorkspace(productSlug = this.selectedProductSlug) {
    if (!productSlug) return;
    this.loading = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "product_workspace",
        product_slug: productSlug,
        actor: this.actor,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to load product workspace");
      this.workspace = resp.data || null;
      this.targetPathInput = this.workspace?.unit?.target_path || "";
      this.bundleNotes = this.workspace?.bundle_approval?.notes || "";
      this.acknowledgeRepoDiff = false;
      this.resetArtifactForms();
    } catch (err) {
      console.error("Workspace load error:", err);
      this.error = err?.message || "Failed to load product workspace";
    } finally {
      this.loading = false;
    }
  },

  async pollWorkspace() {
    if (this.loading || this.saving) return;
    if (!this.selectedProductSlug || !this.workspace?.planning_jobs?.length) return;
    const hasActiveJobs = (this.workspace.planning_jobs || []).some((job) =>
      ["queued", "running"].includes(job.status || ""),
    );
    if (!hasActiveJobs) return;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "product_workspace",
        product_slug: this.selectedProductSlug,
        actor: this.actor,
      });
      if (resp.ok) {
        this.workspace = resp.data || this.workspace;
        this.resetArtifactForms();
      }
    } catch (err) {
      console.error("Rollout poll error:", err);
    }
  },

  resetArtifactForms() {
    const next = {};
    for (const artifactName of this.artifactOrder) {
      next[artifactName] = artifactForm(artifactName, this.workspace?.artifacts?.[artifactName]?.payload || {});
    }
    this.artifactForms = next;
  },

  async resolveTarget() {
    if (!this.selectedProductSlug || !this.targetPathInput.trim()) return;
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "resolve_target",
        product_slug: this.selectedProductSlug,
        target_path: this.targetPathInput.trim(),
        actor: this.actor,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to resolve target");
      this.workspace = resp.data;
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || "Failed to resolve target";
    } finally {
      this.saving = false;
    }
  },

  async startPlanning() {
    if (!this.selectedProductSlug) return;
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "start_planning",
        product_slug: this.selectedProductSlug,
        actor: this.actor,
        branch_ref: this.branchRef,
        deploy_environment: this.deployEnvironment,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to start planning");
      this.workspace = resp.data;
      this.resetArtifactForms();
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || "Failed to start planning";
    } finally {
      this.saving = false;
    }
  },

  canStartPlanning() {
    return !!this.selectedProductSlug && !!this.workspace?.unit?.target_path && !this.saving;
  },

  canDraftArtifact(artifactName) {
    if (!artifactName) return false;
    if (!this.workspace?.unit?.target_path) return false;
    if (this.hasActivePlanningJobs()) return false;
    return !this.saving;
  },

  async draftArtifact(artifactName) {
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "draft_artifact",
        product_slug: this.selectedProductSlug,
        artifact_name: artifactName,
        actor: this.actor,
        agent_provider: this.draftProvider,
      });
      if (!resp.ok) throw new Error(resp.error || `Failed to draft ${artifactName}`);
      this.workspace = resp.data;
      this.resetArtifactForms();
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || `Failed to draft ${artifactName}`;
    } finally {
      this.saving = false;
    }
  },

  async startProductPlanningJob(provider = this.draftProvider) {
    if (!this.selectedProductSlug) return;
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "start_product_planning_job",
        product_slug: this.selectedProductSlug,
        actor: this.actor,
        agent_provider: provider,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to start product planning job");
      this.workspace = resp.data;
      this.resetArtifactForms();
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || "Failed to start product planning job";
    } finally {
      this.saving = false;
    }
  },

  async cancelDraftJob(jobId) {
    return this.cancelPlanningJob(jobId);
  },

  async cancelPlanningJob(jobId) {
    if (!jobId) return;
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "cancel_planning_job",
        product_slug: this.selectedProductSlug,
        job_id: jobId,
        actor: this.actor,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to cancel planning job");
      this.workspace = resp.data;
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || "Failed to cancel planning job";
    } finally {
      this.saving = false;
    }
  },

  async rerunPlanningJob(jobId, provider = this.draftProvider) {
    if (!jobId) return;
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "rerun_planning_job",
        product_slug: this.selectedProductSlug,
        job_id: jobId,
        actor: this.actor,
        agent_provider: provider,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to rerun planning job");
      this.workspace = resp.data;
      this.resetArtifactForms();
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || "Failed to rerun planning job";
    } finally {
      this.saving = false;
    }
  },

  async saveArtifact(artifactName) {
    this.saving = true;
    this.error = null;
    try {
      const payload = serializeArtifact(artifactName, this.artifactForms[artifactName] || {}, this.workspace);
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "save_artifact",
        product_slug: this.selectedProductSlug,
        artifact_name: artifactName,
        payload,
        actor: this.actor,
        producer: "human-ui",
      });
      if (!resp.ok) throw new Error(resp.error || `Failed to save ${artifactName}`);
      this.workspace = resp.data;
      this.resetArtifactForms();
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || `Failed to save ${artifactName}`;
    } finally {
      this.saving = false;
    }
  },

  async approveArtifact(artifactName, approved = true) {
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "approve_artifact",
        product_slug: this.selectedProductSlug,
        artifact_name: artifactName,
        approved,
        actor: this.actor,
      });
      if (!resp.ok) throw new Error(resp.error || `Failed to review ${artifactName}`);
      this.workspace = resp.data;
      this.resetArtifactForms();
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || `Failed to review ${artifactName}`;
    } finally {
      this.saving = false;
    }
  },

  async approveBundle() {
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "approve_bundle",
        product_slug: this.selectedProductSlug,
        approved: true,
        actor: this.actor,
        notes: this.bundleNotes,
        acknowledge_repo_diff: this.acknowledgeRepoDiff,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to approve planning bundle");
      this.workspace = resp.data;
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || "Failed to approve planning bundle";
    } finally {
      this.saving = false;
    }
  },

  async syncLinear() {
    this.saving = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/portfolio_rollout", {
        action: "sync_linear",
        product_slug: this.selectedProductSlug,
        actor: this.actor,
        team_id: this.linearTeamId,
        project_id: this.linearProjectId,
        state_id: this.linearStateId,
        priority: this.linearPriority,
      });
      if (!resp.ok) throw new Error(resp.error || "Failed to sync Linear plan");
      this.workspace = resp.data;
      await this.refreshDashboard();
    } catch (err) {
      this.error = err?.message || "Failed to sync Linear plan";
    } finally {
      this.saving = false;
    }
  },

  productsByStatus(status) {
    return (this.dashboard.products || []).filter((item) => item.status === status);
  },

  isSelected(productSlug) {
    return this.selectedProductSlug === productSlug;
  },

  artifactMeta(artifactName) {
    return this.workspace?.artifacts?.[artifactName] || {};
  },

  latestJobForArtifact(artifactName) {
    return this.artifactMeta(artifactName)?.latest_job || null;
  },

  latestProductJob() {
    return this.workspace?.latest_product_job || null;
  },

  hasActivePlanningJobs() {
    return (this.workspace?.planning_jobs || []).some((job) => ["queued", "running"].includes(job.status || ""));
  },

  artifactCanApprove(artifactName) {
    const meta = this.artifactMeta(artifactName);
    const job = this.latestJobForArtifact(artifactName);
    if (job && ["queued", "running"].includes(job.status || "")) return false;
    return !!meta.complete;
  },

  canStartProductJob() {
    return !!this.workspace?.unit?.target_path && !this.hasActivePlanningJobs();
  },

  canRetryJob(job) {
    return !!job && ["failed", "attention_required", "canceled"].includes(job.status || "");
  },

  diffEvidenceJobs() {
    return (this.workspace?.diff_evidence || []).filter((entry) => entry?.summary);
  },

  bundleCanApprove() {
    if (!this.workspace) return false;
    if ((this.workspace.progress?.active_jobs || 0) > 0) return false;
    if (!this.workspace.unit?.target_path) return false;
    if (this.workspace.bundle_approval?.requires_repo_diff_ack && !this.acknowledgeRepoDiff) return false;
    return this.artifactOrder.every((artifactName) => {
      const meta = this.artifactMeta(artifactName);
      return meta.complete && meta.approved;
    });
  },

  productProgressLabel(product) {
    const progress = product?.planning_progress || {};
    const complete = progress.complete_count || 0;
    const approved = progress.approved_count || 0;
    const total = progress.total || 5;
    return `${complete}/${total} complete · ${approved}/${total} approved`;
  },

  formatDate(value) {
    if (!value) return "Not recorded";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  },

  statusTone(status) {
    const tones = {
      definition_blocked: "danger",
      seeded: "muted",
      discovery: "info",
      planning: "info",
      approval_pending: "warn",
      ready_for_execution: "success",
      executing: "info",
      release_ready: "warn",
      done: "success",
    };
    return tones[status] || "muted";
  },

  jobTone(status) {
    const tones = {
      queued: "muted",
      running: "info",
      completed: "success",
      failed: "danger",
      canceled: "warn",
      attention_required: "warn",
    };
    return tones[status] || "muted";
  },
};

export const store = createStore("rolloutDashboard", model);
