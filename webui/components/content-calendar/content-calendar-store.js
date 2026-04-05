import { createStore } from "/js/AlpineStore.js";
import * as api from "/js/api.js";
import {
  toastFrontendError,
} from "/components/notifications/notification-store.js";

const STATUS_COLORS = {
  discovered: { bg: "rgba(128, 128, 128, 0.15)", label: "Discovered" },
  queued: { bg: "rgba(0, 145, 255, 0.18)", label: "Queued" },
  in_progress: { bg: "rgba(255, 184, 0, 0.22)", label: "In Progress" },
  done: { bg: "rgba(0, 195, 64, 0.18)", label: "Done" },
  blocked: { bg: "rgba(255, 60, 60, 0.18)", label: "Blocked" },
};

const model = {
  initialized: false,
  loading: false,
  items: [],
  total: 0,
  activeTag: "marketing",
  statusFilter: "",
  error: "",

  get filteredItems() {
    return this.items;
  },

  get byStatus() {
    const counts = {};
    for (const item of this.items) {
      const s = item.status || "discovered";
      counts[s] = (counts[s] || 0) + 1;
    }
    return counts;
  },

  statusLabel(status) {
    return STATUS_COLORS[status]?.label || status;
  },

  statusColor(status) {
    return STATUS_COLORS[status]?.bg || "rgba(128,128,128,0.15)";
  },

  init() {
    if (this.initialized) return;
    this.initialized = true;
    this.refresh().catch((err) => {
      console.warn("Content calendar init failed:", err);
    });
  },

  async refresh() {
    this.loading = true;
    this.error = "";
    try {
      const body = { action: "by_tag", tag: this.activeTag };
      if (this.statusFilter) body.status = this.statusFilter;
      const data = await api.callJsonApi("/work_queue_dashboard", body);
      if (data.success) {
        this.items = data.items || [];
        this.total = data.total || 0;
      } else {
        this.error = data.error || "Unknown error";
      }
    } catch (err) {
      this.error = err?.message || String(err);
      toastFrontendError(
        `Calendar load failed: ${this.error}`,
        "Content Calendar",
        5,
        "content-calendar",
      );
    } finally {
      this.loading = false;
    }
  },

  async setTag(tag) {
    this.activeTag = tag;
    await this.refresh();
  },

  async setStatusFilter(status) {
    this.statusFilter = status === this.statusFilter ? "" : status;
    await this.refresh();
  },

  formatDate(dateStr) {
    if (!dateStr) return "—";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  },
};

export const store = createStore("contentCalendar", model);
