# Work Queue Alpine.js Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the work queue dashboard from React/Next.js to Alpine.js so it loads in the Flask-served SPA, unblocking 3 skipped E2E browser tests.

**Architecture:** New dashboard following existing pattern (workflow-dashboard, portfolio-dashboard): an Alpine store (`work-queue-store.js`) manages state and API calls via `callJsonApi()`, an HTML template (`work-queue-dashboard.html`) renders stats cards + filters + item table + detail slide-over, and the dashboard router gains a `workQueue` entry with URL-based auto-open for `/work-queue`.

**Tech Stack:** Alpine.js 3.x, `createStore()` from `/js/AlpineStore.js`, `callJsonApi()` from `/js/api.js`, existing Flask `work_queue_*` API endpoints.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `webui/dashboards/work-queue/work-queue-store.js` | Alpine store: state, API calls, filtering, pagination, bulk ops |
| Create | `webui/dashboards/work-queue/work-queue-dashboard.html` | HTML template with stats, filters, table, detail panel |
| Modify | `webui/dashboards/dashboard-router.js` | Add `workQueue` entry + URL auto-open on page load |
| Modify | `webui/components/sidebar/bottom/dashboard-nav/dashboard-nav.html` | Add Work Queue nav button |
| Modify | `tests/e2e/test_work_queue_e2e.py` | Remove 3 `@pytest.mark.skip` decorators |

---

### Task 1: Create the Alpine Store

**Files:**

- Create: `webui/dashboards/work-queue/work-queue-store.js`

- [ ] **Step 1: Create the store file**

```javascript
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
    if (!filePath) return "—";
    const parts = filePath.split("/");
    return parts.length > 3 ? ".../" + parts.slice(-3).join("/") : filePath;
  },
};

export const store = createStore("workQueueStore", model);
```

- [ ] **Step 2: Verify file loads without errors**

Run: Open browser console at the app URL, check no JS errors from the store import.

- [ ] **Step 3: Commit**

```bash
git add webui/dashboards/work-queue/work-queue-store.js
git commit -m "feat(work-queue): add Alpine.js store for work queue dashboard"
```

---

### Task 2: Create the Dashboard HTML Template

**Files:**

- Create: `webui/dashboards/work-queue/work-queue-dashboard.html`

- [ ] **Step 1: Create the HTML template**

The template must include these `data-testid` attributes for E2E tests:

- `data-testid="work-queue-dashboard"` on the root container
- `data-testid="stats-cards"` on the stats cards container
- `data-testid="status-filter"` on the status filter `<select>`

The template uses the same `<html><head><script type="module">` + `<body>` pattern as `workflow-dashboard.html`.

Key sections:

1. **Header** — Back button, "Work Queue" title, Schedule/Scan Now/Refresh buttons
2. **Schedule bar** — Toggle + cron input (collapsible)
3. **Stats cards** — Total, Queued, In Progress, Done This Week (4-column grid)
4. **Toolbar** — Status filter `<select>`, Source filter `<select>`, Search input, Bulk actions
5. **Item table** — Checkbox, Priority (bar + score), Title, Source, Type, File, Status pill, Action button
6. **Pagination** — "Showing X-Y of Z" + Prev/Next
7. **Detail slide-over** — Overlay with item details, priority breakdown, actions

Text content must include the words "Work Queue", "Total", "Queued", "In Progress", "Done" (checked by E2E tests).

The full HTML is based on the approved mockup at `docs/mockups/work-queue-mockup.html`, adapted to use Alpine.js bindings (`x-data`, `x-show`, `x-for`, `$store.workQueueStore`, `@click`) and scoped `<style>` tags.

- [ ] **Step 2: Verify HTML renders correctly by loading it directly**

Open `webui/dashboards/work-queue/work-queue-dashboard.html` in browser to check for syntax errors.

- [ ] **Step 3: Commit**

```bash
git add webui/dashboards/work-queue/work-queue-dashboard.html
git commit -m "feat(work-queue): add Alpine.js dashboard HTML template"
```

---

### Task 3: Register Dashboard in Router + Add Sidebar Nav

**Files:**

- Modify: `webui/dashboards/dashboard-router.js` (~3 changes)
- Modify: `webui/components/sidebar/bottom/dashboard-nav/dashboard-nav.html` (~1 button addition)

- [ ] **Step 1: Add `workQueue` entry to the `dashboards` object in dashboard-router.js**

After the `mos` entry (line 31), add:

```javascript
workQueue: {
    id: 'workQueue',
    label: 'Work Queue',
    icon: 'workQueue',
    component: 'dashboards/work-queue/work-queue-dashboard.html'
}
```

- [ ] **Step 2: Add store loader in the `showDashboard` method**

In the `storeLoader` object (around line 53), add:

```javascript
workQueue: () => import('/dashboards/work-queue/work-queue-store.js'),
```

- [ ] **Step 3: Add icon SVG for workQueue**

In `getIconSvg` icons object, add:

```javascript
workQueue: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <path d="M9 7h6M9 11h6M9 15h4"/>
</svg>`
```

- [ ] **Step 4: Add URL-based auto-open on page load**

Add to the `dashboardRouterModel` object, after `getIconSvg`:

```javascript
// Auto-open dashboard based on URL path
initFromUrl() {
    const path = window.location.pathname.replace(/^\//, '');
    const urlMap = {
        'work-queue': 'workQueue',
        'workflows': 'workflows',
        'portfolio': 'portfolio',
        'mos': 'mos'
    };
    const dashboardId = urlMap[path];
    if (dashboardId && this.dashboards[dashboardId]) {
        this.showDashboard(dashboardId);
    }
}
```

Then in the `alpine:init` event handler (line 112), add auto-init:

```javascript
document.addEventListener('alpine:init', () => {
    Alpine.store('dashboardRouter', dashboardRouterModel);
    // Auto-open dashboard if URL matches
    setTimeout(() => {
        Alpine.store('dashboardRouter').initFromUrl();
    }, 100);
});
```

- [ ] **Step 5: Add Work Queue button to sidebar nav**

In `dashboard-nav.html`, after the MOS button block (before `</div>` closing `.dashboard-nav-buttons`), add:

```html
<!-- Work Queue Dashboard Button -->
<button
  class="dashboard-nav-btn"
  :class="{ 'active': $store.dashboardRouter && $store.dashboardRouter.isDashboardActive('workQueue') }"
  @click="$store.dashboardRouter && $store.dashboardRouter.showDashboard('workQueue')"
  title="Work Queue">
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <path d="M9 7h6M9 11h6M9 15h4"/>
  </svg>
  <span>Work Queue</span>
</button>
```

- [ ] **Step 6: Commit**

```bash
git add webui/dashboards/dashboard-router.js webui/components/sidebar/bottom/dashboard-nav/dashboard-nav.html
git commit -m "feat(work-queue): register dashboard in router + add sidebar nav button"
```

---

### Task 4: Remove E2E Test Skip Decorators

**Files:**

- Modify: `tests/e2e/test_work_queue_e2e.py` (lines 197-198, 213-215, 233-235)

- [ ] **Step 1: Remove the 3 `@pytest.mark.skip` decorators**

Remove these exact blocks (the `@pytest.mark.skip(reason=...)` lines only, keep the `@pytest.mark.e2e`):

Line 197-199 (before `test_work_queue_page_loads`):

```python
# REMOVE these 2 lines:
@pytest.mark.skip(
    reason="Work queue UI exists in Next.js frontend (web/) but Flask serves Alpine.js SPA (webui/) — browser tests deferred until frontend integration"
)
```

Line 213-215 (before `test_work_queue_shows_stats_cards`):

```python
# REMOVE these 3 lines (same skip decorator)
```

Line 233-235 (before `test_work_queue_filter_dropdown_present`):

```python
# REMOVE these 3 lines (same skip decorator)
```

- [ ] **Step 2: Verify the browser tests can be collected by pytest**

Run: `cd /mnt/wdblack/dev/projects/agent-jumbo && python -m pytest tests/e2e/test_work_queue_e2e.py --collect-only 2>&1 | grep "test_work_queue"`

Expected: All 11 tests collected (no skips for the 3 browser tests).

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_work_queue_e2e.py
git commit -m "test(work-queue): remove skip decorators from browser tests — Alpine.js UI now available"
```

---

### Task 5: Integration Test — Run Full E2E Suite

- [ ] **Step 1: Run the work queue E2E tests**

Run: `cd /mnt/wdblack/dev/projects/agent-jumbo && python -m pytest tests/e2e/test_work_queue_e2e.py -v --timeout=120`

Expected: All 11 tests pass (8 API + 3 browser).

The 3 browser tests check:

1. `test_work_queue_page_loads` — Navigates to `/work-queue`, expects "Work Queue" in body text
2. `test_work_queue_shows_stats_cards` — Expects at least one of: "total", "discovered", "queued", "in progress", "done" in body text
3. `test_work_queue_filter_dropdown_present` — Expects at least one `<select>` element on the page

- [ ] **Step 2: If any browser test fails, debug and fix**

Common issues:

- Alpine store not loaded before template renders → check `x-create` timing
- `data-testid` attributes missing → verify HTML template
- URL routing not working → check `initFromUrl()` fires and `_SPA_PATHS` includes `work-queue` (already confirmed at `run_ui.py:300`)
- CSRF / auth issues → these are the same as other dashboards, should work

- [ ] **Step 3: Run full E2E suite to check no regressions**

Run: `cd /mnt/wdblack/dev/projects/agent-jumbo && python -m pytest tests/e2e/ -v --timeout=120`

Expected: 49/52 pass (the 3 previously-skipped tests now active, other skips remain for env-limited tests).

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -u
git commit -m "fix(work-queue): address E2E test feedback"
```
