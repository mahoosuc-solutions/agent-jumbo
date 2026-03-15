/**
 * MOS Dashboard Store - Alpine.js store for MOS (Linear/Motion/Notion) Dashboard
 * Fetches data from /mos_dashboard and /mos_sync_status API endpoints
 */

const mosDashboardModel = {
    // State
    loading: false,
    error: null,
    errors: {},          // per-integration errors: { linear: { message, category }, ... }
    dismissedErrors: {}, // track dismissed error banners per integration

    // Auto-refresh
    refreshInterval: 60,    // seconds
    lastRefreshed: null,     // Date timestamp
    lastRefreshedAgo: '',    // human-readable "Xs ago"
    _refreshTimer: null,
    _agoTimer: null,

    // Sync history
    syncHistory: [],
    syncHistoryTotal: 0,
    syncHistoryOffset: 0,
    showHistory: false,
    loadingHistory: false,

    // Data
    linear: {},
    motion: {},
    pipeline: {},
    syncs: {},

    // Connection test results: { linear: { status, message }, ... }
    connectionTests: {},

    // Computed stats
    get totalLinearIssues() {
        const data = this.linear?.dashboard_data || this.linear;
        return data?.total_issues || data?.issue_count || 0;
    },

    get motionTaskCount() {
        return this.motion?.task_count || 0;
    },

    get pipelineLeads() {
        const p = this.pipeline;
        return p?.total_leads || p?.lead_count || 0;
    },

    get issuesByState() {
        const data = this.linear?.dashboard_data || this.linear;
        return data?.by_state || data?.issues_by_state || {};
    },

    get issuesByPriority() {
        const data = this.linear?.dashboard_data || this.linear;
        return data?.by_priority || data?.issues_by_priority || {};
    },

    // Lifecycle
    async init() {
        await Promise.all([this.loadDashboard(), this.loadSyncStatus()]);
        this.lastRefreshed = Date.now();
        this._updateAgoText();
        this.startAutoRefresh();
    },

    // ── Auto-refresh ──────────────────────────────────────────────

    startAutoRefresh() {
        this.stopAutoRefresh();
        if (this.refreshInterval <= 0) return;

        this._refreshTimer = setInterval(async () => {
            await Promise.all([this.loadDashboard(), this.loadSyncStatus()]);
            this.lastRefreshed = Date.now();
        }, this.refreshInterval * 1000);

        // Update the "Xs ago" label every second
        this._agoTimer = setInterval(() => this._updateAgoText(), 1000);
    },

    stopAutoRefresh() {
        if (this._refreshTimer) { clearInterval(this._refreshTimer); this._refreshTimer = null; }
        if (this._agoTimer) { clearInterval(this._agoTimer); this._agoTimer = null; }
    },

    setRefreshInterval(seconds) {
        this.refreshInterval = Math.max(0, seconds);
        // Restart with new interval
        this.startAutoRefresh();
    },

    _updateAgoText() {
        if (!this.lastRefreshed) { this.lastRefreshedAgo = 'never'; return; }
        const delta = Math.floor((Date.now() - this.lastRefreshed) / 1000);
        if (delta < 5) this.lastRefreshedAgo = 'just now';
        else if (delta < 60) this.lastRefreshedAgo = delta + 's ago';
        else if (delta < 3600) this.lastRefreshedAgo = Math.floor(delta / 60) + 'm ago';
        else this.lastRefreshedAgo = Math.floor(delta / 3600) + 'h ago';
    },

    // ── API methods ───────────────────────────────────────────────

    async loadDashboard() {
        this.loading = true;
        this.error = null;
        try {
            const token = Alpine.store('csrfStore')?.token || '';
            const resp = await fetch('/mos_dashboard', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token
                },
                body: JSON.stringify({
                    include_linear: true,
                    include_motion: true,
                    include_pipeline: true
                })
            });
            const data = await resp.json();
            if (data.success) {
                this.linear = data.linear || {};
                this.motion = data.motion || {};
                this.pipeline = data.pipeline || {};
                // Populate per-integration errors from response
                this._processIntegrationErrors(data);
            } else {
                this.error = data.error || 'Failed to load MOS dashboard';
            }
        } catch (e) {
            console.error('Error loading MOS dashboard:', e);
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    },

    async loadSyncStatus() {
        try {
            const token = Alpine.store('csrfStore')?.token || '';
            const resp = await fetch('/mos_sync_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token
                },
                body: JSON.stringify({})
            });
            const data = await resp.json();
            if (data.success) {
                this.syncs = data.syncs || {};
            }
        } catch (e) {
            console.error('Error loading sync status:', e);
        }
    },

    // ── Sync with progress polling ────────────────────────────────

    async triggerSync(integration) {
        // Mark this integration as actively syncing
        if (!this.syncs[integration]) this.syncs[integration] = {};
        this.syncs[integration].syncing = true;

        try {
            const token = Alpine.store('csrfStore')?.token || '';
            const resp = await fetch('/mos_sync_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token
                },
                body: JSON.stringify({ trigger_sync: integration })
            });
            const data = await resp.json();
            if (data.success) {
                // Start polling for completion
                this._pollSyncCompletion(integration);
            } else {
                this.syncs[integration].syncing = false;
                this._setIntegrationError(integration, data.error || 'Sync trigger failed', 'api');
            }
        } catch (e) {
            console.error('Error triggering sync:', e);
            this.syncs[integration].syncing = false;
            this._setIntegrationError(integration, `Sync failed: ${e.message}`, 'network');
        }
    },

    _pollSyncCompletion(integration) {
        const pollId = setInterval(async () => {
            try {
                const token = Alpine.store('csrfStore')?.token || '';
                const resp = await fetch('/mos_sync_status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': token
                    },
                    body: JSON.stringify({})
                });
                const data = await resp.json();
                if (data.success) {
                    this.syncs = { ...this.syncs, ...data.syncs };
                    const syncInfo = data.syncs?.[integration];
                    const status = syncInfo?.last_sync?.status;
                    // Stop polling when status is no longer 'running'
                    if (status !== 'running') {
                        clearInterval(pollId);
                        if (this.syncs[integration]) this.syncs[integration].syncing = false;

                        if (status === 'success') {
                            this._showToast(`${integration} sync completed successfully`, 'success');
                            this._clearIntegrationError(integration);
                        } else {
                            const errMsg = syncInfo?.last_sync?.error || 'Sync ended with errors';
                            this._showToast(`${integration} sync failed: ${errMsg}`, 'error');
                            this._setIntegrationError(integration, errMsg, 'api');
                        }
                        // Reload dashboard data
                        await this.loadDashboard();
                        this.lastRefreshed = Date.now();
                    }
                }
            } catch (e) {
                clearInterval(pollId);
                if (this.syncs[integration]) this.syncs[integration].syncing = false;
                this._showToast(`Error polling ${integration} sync status`, 'error');
            }
        }, 3000);
    },

    // ── Sync History ──────────────────────────────────────────────

    async loadSyncHistory(integration = null, append = false) {
        this.loadingHistory = true;
        try {
            const token = Alpine.store('csrfStore')?.token || '';
            const offset = append ? this.syncHistoryOffset : 0;
            const resp = await fetch('/mos_sync_history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token
                },
                body: JSON.stringify({
                    integration: integration,
                    limit: 20,
                    offset: offset
                })
            });
            const data = await resp.json();
            if (data.success) {
                const rows = data.history || [];
                if (append) {
                    this.syncHistory = [...this.syncHistory, ...rows];
                } else {
                    this.syncHistory = rows;
                }
                this.syncHistoryTotal = data.total || rows.length;
                this.syncHistoryOffset = this.syncHistory.length;
            }
        } catch (e) {
            console.error('Error loading sync history:', e);
        } finally {
            this.loadingHistory = false;
        }
    },

    toggleHistory() {
        this.showHistory = !this.showHistory;
        if (this.showHistory && this.syncHistory.length === 0) {
            this.loadSyncHistory();
        }
    },

    get hasMoreHistory() {
        return this.syncHistoryOffset < this.syncHistoryTotal;
    },

    // ── Error handling ────────────────────────────────────────────

    _processIntegrationErrors(data) {
        const integrations = ['linear', 'motion', 'notion'];
        for (const name of integrations) {
            const section = data[name];
            if (section?.error) {
                this._setIntegrationError(name, section.error, this._categorizeError(section.error));
            }
        }
    },

    _categorizeError(message) {
        if (!message) return 'api';
        const lower = message.toLowerCase();
        if (lower.includes('api key') || lower.includes('credential') || lower.includes('unauthorized') || lower.includes('401') || lower.includes('not configured')) {
            return 'config';
        }
        if (lower.includes('timeout') || lower.includes('network') || lower.includes('econnrefused') || lower.includes('fetch')) {
            return 'network';
        }
        return 'api';
    },

    _setIntegrationError(integration, message, category) {
        this.errors[integration] = { message, category };
    },

    _clearIntegrationError(integration) {
        const updated = { ...this.errors };
        delete updated[integration];
        this.errors = updated;
    },

    dismissError(integration) {
        this.dismissedErrors[integration] = true;
    },

    getErrorClass(integration) {
        const err = this.errors[integration];
        if (!err) return '';
        return 'sync-error-' + (err.category || 'api');
    },

    isConfigError(integration) {
        return this.errors[integration]?.category === 'config';
    },

    // ── Connection indicator helpers ──────────────────────────────

    getConnectionDot(integration) {
        const sync = this.syncs?.[integration];
        if (!sync) return 'connection-red';
        if (sync.error) return 'connection-red';
        const last = sync.last_sync;
        if (!last) return 'connection-red';
        if (last.status !== 'success') return 'connection-red';
        // Check if last sync was >24h ago
        if (last.started_at) {
            const elapsed = Date.now() - new Date(last.started_at).getTime();
            if (elapsed > 24 * 60 * 60 * 1000) return 'connection-yellow';
        }
        return 'connection-green';
    },

    // ── Toast notifications ───────────────────────────────────────

    _showToast(message, type = 'info') {
        // Create a toast element
        const toast = document.createElement('div');
        toast.className = 'mos-toast mos-toast-' + type;
        toast.textContent = message;
        // Find or create container
        let container = document.querySelector('.mos-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'mos-toast-container';
            document.body.appendChild(container);
        }
        container.appendChild(toast);
        // Animate in
        requestAnimationFrame(() => toast.classList.add('mos-toast-visible'));
        // Remove after 5s
        setTimeout(() => {
            toast.classList.remove('mos-toast-visible');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    },

    // ── Connection test (for settings page) ───────────────────────

    async testConnection(integration) {
        this.connectionTests[integration] = { status: 'testing', message: '' };
        try {
            const token = Alpine.store('csrfStore')?.token || '';
            const settings = Alpine.store('settingsStore')?.currentSettings || {};
            const keyField = integration + '_api_key';
            const resp = await fetch('/mos_test_connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token
                },
                body: JSON.stringify({
                    integration: integration,
                    api_key: settings[keyField] || ''
                })
            });
            const data = await resp.json();
            this.connectionTests[integration] = {
                status: data.success ? 'ok' : 'error',
                message: data.message || (data.success ? 'Connected' : 'Connection failed')
            };
        } catch (e) {
            this.connectionTests[integration] = { status: 'error', message: e.message };
        }
    },

    // ── Existing helpers ──────────────────────────────────────────

    formatDate(dateStr) {
        if (!dateStr) return 'Never';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    },

    formatDuration(seconds) {
        if (!seconds && seconds !== 0) return '-';
        if (seconds < 60) return seconds + 's';
        return Math.floor(seconds / 60) + 'm ' + (seconds % 60) + 's';
    },

    getSyncStatusClass(sync) {
        if (!sync || sync.error) return 'sync-error';
        const last = sync.last_sync;
        if (!last) return 'sync-none';
        if (last.status === 'running') return 'sync-running';
        return last.status === 'success' ? 'sync-ok' : 'sync-error';
    },

    getSyncStatusText(sync) {
        if (!sync) return 'Not configured';
        if (sync.syncing) return 'Syncing...';
        if (sync.error) return 'Error';
        const last = sync.last_sync;
        if (!last) return 'No syncs yet';
        if (last.status === 'running') return 'Running';
        return last.status === 'success' ? 'OK' : 'Failed';
    },

    getHistoryStatusClass(status) {
        if (!status) return 'sync-none';
        switch (status.toLowerCase()) {
            case 'success':
            case 'completed': return 'sync-ok';
            case 'running': return 'sync-running';
            case 'error':
            case 'failed': return 'sync-error';
            default: return 'sync-none';
        }
    },

    getStateColor(state) {
        const colors = {
            'backlog': '#718096',
            'todo': '#4299e1',
            'in_progress': '#ed8936',
            'in_review': '#805ad5',
            'done': '#48bb78',
            'cancelled': '#e53e3e',
            'triage': '#a0aec0'
        };
        return colors[state?.toLowerCase()] || '#718096';
    },

    getPriorityColor(priority) {
        const colors = {
            'urgent': '#e53e3e',
            'high': '#ed8936',
            'medium': '#ecc94b',
            'low': '#48bb78',
            'no_priority': '#718096'
        };
        return colors[priority?.toLowerCase()] || '#718096';
    }
};

// Register the store when Alpine is ready
const registerMosStore = () => {
    Alpine.store('mosDashboard', mosDashboardModel);
};

if (globalThis.Alpine) {
    registerMosStore();
} else {
    document.addEventListener('alpine:init', registerMosStore);
}
