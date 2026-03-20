import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const model = {
  // State
  loading: false,
  error: null,

  // Dashboard stats
  stats: {
    total: 0,
    by_status: {},
    by_source: {},
    by_type: {},
    done_this_week: 0,
    last_scan: null,
    projects: [],
  },

  // Item list
  items: [],
  totalItems: 0,
  page: 1,
  pageSize: 50,

  // Filters
  statusFilter: "",
  sourceFilter: "",
  searchQuery: "",

  // Selection
  selectedIds: new Set(),
  selectAll: false,

  // Detail panel
  detailItem: null,
  detailOpen: false,

  // Schedule
  schedule: { enabled: false, cron: "", scan_types: [] },
  scheduleOpen: false,

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

  // ── API: Dashboard ──
  async refresh() {
    this.loading = true;
    this.error = null;
    try {
      await Promise.all([this.loadDashboard(), this.loadItems(), this.loadSchedule()]);
    } catch (err) {
      console.error("Work queue dashboard error:", err);
      this.error = err?.message || "Failed to load work queue data";
    } finally {
      this.loading = false;
    }
  },

  async refreshSilent() {
    try {
      await Promise.all([this.loadDashboard(), this.loadItems()]);
    } catch (err) {
      console.error("Silent refresh error:", err);
    }
  },

  async loadDashboard() {
    const resp = await callJsonApi("/work_queue_dashboard", { action: "dashboard" });
    if (resp.success) {
      this.stats = {
        total: resp.total ?? 0,
        by_status: resp.by_status ?? {},
        by_source: resp.by_source ?? {},
        by_type: resp.by_type ?? {},
        done_this_week: resp.done_this_week ?? 0,
        last_scan: resp.last_scan ?? null,
        projects: resp.projects ?? [],
      };
    } else {
      throw new Error(resp.error || "Failed to load dashboard");
    }
  },

  // ── API: Items ──
  async loadItems() {
    const body = {
      action: "list",
      page: this.page,
      page_size: this.pageSize,
    };
    if (this.statusFilter) body.status = this.statusFilter;
    if (this.sourceFilter) body.source = this.sourceFilter;

    const resp = await callJsonApi("/work_queue_dashboard", body);
    if (resp.success) {
      this.items = resp.items ?? [];
      this.totalItems = resp.total ?? 0;
    }
  },

  async searchItems() {
    if (!this.searchQuery.trim()) {
      return this.loadItems();
    }
    this.loading = true;
    try {
      const resp = await callJsonApi("/work_queue_dashboard", {
        action: "search",
        query: this.searchQuery,
      });
      if (resp.success) {
        this.items = resp.items ?? [];
        this.totalItems = resp.total ?? this.items.length;
      }
    } catch (err) {
      this.error = err?.message || "Search failed";
    } finally {
      this.loading = false;
    }
  },

  // ── API: Item Detail ──
  async openDetail(itemId) {
    this.loading = true;
    try {
      const resp = await callJsonApi("/work_queue_item_get", { item_id: itemId });
      if (resp.success) {
        this.detailItem = resp.item ?? resp;
        this.detailOpen = true;
      } else {
        this.error = resp.error || "Failed to load item";
      }
    } catch (err) {
      this.error = err?.message || "Failed to load item";
    } finally {
      this.loading = false;
    }
  },

  closeDetail() {
    this.detailOpen = false;
    this.detailItem = null;
  },

  // ── API: Item Actions ──
  async updateStatus(itemId, status) {
    try {
      await callJsonApi("/work_queue_item_update", {
        item_id: itemId,
        action: "update_status",
        status,
      });
      await this.refreshSilent();
      if (this.detailItem?.id === itemId) {
        this.detailItem.status = status;
      }
    } catch (err) {
      this.error = err?.message || "Failed to update status";
    }
  },

  async executeItem(itemId) {
    try {
      const resp = await callJsonApi("/work_queue_item_execute", { item_id: itemId });
      if (resp.success) {
        await this.refreshSilent();
      } else {
        this.error = resp.error || "Failed to execute item";
      }
    } catch (err) {
      this.error = err?.message || "Execution failed";
    }
  },

  // ── API: Bulk Actions ──
  async bulkAction(action) {
    const ids = Array.from(this.selectedIds);
    if (!ids.length) return;
    try {
      await callJsonApi("/work_queue_item_bulk", { item_ids: ids, action });
      this.selectedIds = new Set();
      this.selectAll = false;
      await this.refreshSilent();
    } catch (err) {
      this.error = err?.message || "Bulk action failed";
    }
  },

  // ── API: Scan ──
  async scanNow() {
    this.loading = true;
    try {
      await callJsonApi("/work_queue_scan", { action: "full_scan" });
      await this.refresh();
    } catch (err) {
      this.error = err?.message || "Scan failed";
    } finally {
      this.loading = false;
    }
  },

  // ── API: Schedule ──
  async loadSchedule() {
    try {
      const resp = await callJsonApi("/work_queue_settings", { action: "get_schedule" });
      if (resp.success) {
        const sched = resp.schedule ?? resp;
        this.schedule = {
          enabled: sched.enabled ?? false,
          cron: sched.cron ?? "",
          scan_types: sched.scan_types ?? [],
        };
      }
    } catch (err) {
      console.warn("Failed to load schedule:", err);
    }
  },

  async saveSchedule() {
    try {
      if (this.schedule.enabled && this.schedule.cron) {
        await callJsonApi("/work_queue_settings", {
          action: "set_schedule",
          cron: this.schedule.cron,
          scan_types: this.schedule.scan_types,
        });
      } else {
        await callJsonApi("/work_queue_settings", { action: "remove_schedule" });
      }
    } catch (err) {
      this.error = err?.message || "Failed to save schedule";
    }
  },

  // ── Pagination ──
  nextPage() {
    if (this.page * this.pageSize < this.totalItems) {
      this.page++;
      this.loadItems();
    }
  },

  prevPage() {
    if (this.page > 1) {
      this.page--;
      this.loadItems();
    }
  },

  // ── Filters ──
  applyFilters() {
    this.page = 1;
    this.loadItems();
  },

  // ── Selection ──
  toggleSelectAll() {
    if (this.selectAll) {
      this.selectedIds = new Set(this.items.map((i) => i.id));
    } else {
      this.selectedIds = new Set();
    }
  },

  toggleItem(id) {
    const s = new Set(this.selectedIds);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    this.selectedIds = s;
    this.selectAll = s.size === this.items.length;
  },

  isSelected(id) {
    return this.selectedIds.has ? this.selectedIds.has(id) : false;
  },

  // ── Helpers ──
  priorityClass(score) {
    if (score >= 70) return "p-critical";
    if (score >= 40) return "p-high";
    if (score >= 20) return "p-medium";
    return "p-low";
  },

  statusClass(status) {
    return "s-" + (status || "discovered");
  },

  formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  },

  truncatePath(filePath) {
    if (!filePath) return "\u2014";
    const parts = filePath.split("/");
    return parts.length > 3 ? ".../" + parts.slice(-3).join("/") : filePath;
  },
};

export const store = createStore("workQueueStore", model);
