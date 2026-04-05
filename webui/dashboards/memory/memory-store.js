import { createStore } from "/js/AlpineStore.js";
import * as api from "/js/api.js";
import {
  toastFrontendError,
} from "/components/notifications/notification-store.js";

const model = {
  initialized: false,
  loading: false,
  error: "",
  stats: null,
  subdirs: [],
  selectedSubdir: "default",
  consolidateResult: null,
  consolidating: false,

  init() {
    if (this.initialized) return;
    this.initialized = true;
    this.loadSubdirs().catch(() => {});
    this.loadStats().catch(() => {});
  },

  async loadSubdirs() {
    try {
      const data = await api.callJsonApi("/memory_stats", { action: "list_subdirs" });
      if (data.success) {
        this.subdirs = data.subdirs || [];
      }
    } catch (err) {
      console.warn("Failed to load memory subdirs:", err);
    }
  },

  async loadStats() {
    this.loading = true;
    this.error = "";
    try {
      const data = await api.callJsonApi("/memory_stats", {
        action: "stats",
        memory_subdir: this.selectedSubdir,
      });
      if (data.success) {
        this.stats = data.stats;
      } else {
        this.error = data.error || "Unknown error";
      }
    } catch (err) {
      this.error = err?.message || String(err);
      toastFrontendError(`Memory stats failed: ${this.error}`, "Memory", 5, "memory-stats");
    } finally {
      this.loading = false;
    }
  },

  async selectSubdir(subdir) {
    this.selectedSubdir = subdir;
    this.consolidateResult = null;
    await this.loadStats();
  },

  async consolidateDryRun(area) {
    this.consolidating = true;
    this.consolidateResult = null;
    try {
      const data = await api.callJsonApi("/memory_stats", {
        action: "consolidate",
        memory_subdir: this.selectedSubdir,
        area: area || undefined,
        dry_run: true,
      });
      if (data.success) {
        this.consolidateResult = { ...data, dryRun: true, area: area || "all" };
      } else {
        this.error = data.error || "Consolidation failed";
      }
    } catch (err) {
      this.error = err?.message || String(err);
    } finally {
      this.consolidating = false;
    }
  },

  formatNumber(n) {
    return typeof n === "number" ? n.toLocaleString() : "—";
  },
};

export const store = createStore("memoryDashboard", model);
