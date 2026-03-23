import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const model = {
  // State
  tasks: [],
  loading: false,
  error: null,
  filter: 'all',
  stats: { total: 0, running: 0, scheduled: 0, adhoc: 0 },

  // Polling
  pollingInterval: null,

  // ── Lifecycle ──
  async onOpen() {
    await this.refresh();
    this.startPolling();
  },

  cleanup() {
    this.stopPolling();
  },

  startPolling() {
    if (this.pollingInterval) return;
    this.pollingInterval = setInterval(() => this.refreshSilent(), 5000);
  },

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  },

  // ── API ──
  async refresh() {
    this.loading = true;
    this.error = null;
    try {
      const resp = await callJsonApi("/scheduler_tasks_list", {});
      this.tasks = resp.tasks || [];
      this.computeStats();
    } catch (err) {
      console.error("Tasks dashboard error:", err);
      this.error = err?.message || "Failed to load tasks";
    } finally {
      this.loading = false;
    }
  },

  async refreshSilent() {
    try {
      const resp = await callJsonApi("/scheduler_tasks_list", {});
      this.tasks = resp.tasks || [];
      this.computeStats();
    } catch (err) {
      console.error("Silent refresh error:", err);
    }
  },

  computeStats() {
    this.stats = {
      total: this.tasks.length,
      running: this.tasks.filter(t => t.state === 'running').length,
      scheduled: this.tasks.filter(t => t.type === 'scheduled').length,
      adhoc: this.tasks.filter(t => t.type === 'adhoc').length
    };
  },

  // ── Filtered Tasks ──
  get filteredTasks() {
    if (this.filter === 'all') return this.tasks;
    if (this.filter === 'scheduled') return this.tasks.filter(t => t.type === 'scheduled');
    if (this.filter === 'adhoc') return this.tasks.filter(t => t.type === 'adhoc');
    // running, idle, error, paused, disabled match state
    return this.tasks.filter(t => t.state === this.filter);
  },

  setFilter(f) {
    this.filter = f;
  },

  // ── Actions ──
  async runTask(name) {
    try {
      await callJsonApi("/scheduler_task_run", { name });
      await this.refresh();
    } catch (err) {
      console.error("Error running task:", err);
      this.error = err?.message || "Failed to run task";
    }
  },

  async toggleTask(task) {
    try {
      const newState = (task.state === 'paused' || task.state === 'disabled') ? 'active' : 'paused';
      await callJsonApi("/scheduler_task_update", { name: task.name, state: newState });
      await this.refresh();
    } catch (err) {
      console.error("Error toggling task:", err);
      this.error = err?.message || "Failed to toggle task";
    }
  },

  // ── Helpers ──
  formatCron(task) {
    if (task.type === 'adhoc') return 'Run manually';
    if (task.type === 'planned' && task.planned_times) {
      return task.planned_times.length + ' planned run(s)';
    }

    const cron = task.cron || '';
    if (!cron) return 'No schedule';

    const parts = cron.trim().split(/\s+/);
    if (parts.length < 5) return cron;

    const [minute, hour, dom, month, dow] = parts;

    if (minute === '*' && hour === '*') return 'Every minute';
    if (hour === '*' && minute.startsWith('*/')) return `Every ${minute.slice(2)} minutes`;
    if (minute === '0' && hour.startsWith('*/')) return `Every ${hour.slice(2)} hours`;
    if (minute === '0' && hour === '*') return 'Every hour';
    if (minute === '0' && hour === '0' && dom === '*' && month === '*' && dow === '*') return 'Daily at midnight';
    if (dom === '*' && month === '*' && dow === '*') {
      const h = parseInt(hour);
      const m = parseInt(minute);
      const period = h >= 12 ? 'pm' : 'am';
      const displayH = h === 0 ? 12 : h > 12 ? h - 12 : h;
      if (m === 0) return `Daily at ${displayH}${period}`;
      return `Daily at ${displayH}:${String(m).padStart(2, '0')}${period}`;
    }
    if (dow !== '*' && dom === '*' && month === '*') {
      const days = { '0': 'Sun', '1': 'Mon', '2': 'Tue', '3': 'Wed', '4': 'Thu', '5': 'Fri', '6': 'Sat' };
      const dayName = days[dow] || dow;
      return `Weekly on ${dayName}`;
    }

    return cron;
  },

  formatLastRun(dateStr) {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.round(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.round(diff / 3600000) + 'h ago';
    if (diff < 604800000) return Math.round(diff / 86400000) + 'd ago';
    return date.toLocaleDateString();
  },

  openSettings(tab) {
    Alpine.store('dashboardRouter')?.closeDashboard();
    Alpine.store('settingsStore')?.setTab(tab);
    document.getElementById('settings')?.click();
  },

  openChat() {
    Alpine.store('dashboardRouter')?.closeDashboard();
  }
};

export const store = createStore("tasksDashboard", model);
