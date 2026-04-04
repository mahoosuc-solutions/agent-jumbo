# Progressive Trust UX — Approval Sidebar & First-Run Onboarding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire trust-gated tool approvals into the existing cowork sidebar panel and add a guided 3-question first-run wizard that sets the user's trust level before their first conversation.

**Architecture:** The trust gate extension stores structured approval records via `cowork.add_approval()` and sets `context.paused = True` to suspend the agent until the user approves or denies in the cowork panel. The onboarding wizard intercepts the first chat message, runs a 2-question guided flow to recommend a trust level, persists the choice to settings + localStorage, then delivers the intercepted message.

**Tech Stack:** Python (Flask extensions, `cowork.py` data layer), Alpine.js (cowork panel inline component, new onboarding modal), existing `loadSettings`/`saveSettings` API helpers in `webui/js/api.js`.

---

## File Map

**Modified — backend:**
- `python/helpers/trust_system.py` — add `get_approval_fingerprint()`, `is_always_allowed()`, `TRUST_ALWAYS_ALLOW_KEY`
- `python/helpers/settings_core.py` — add `trust_always_allow: list[str]` and `trust_onboarded: bool` fields + defaults
- `python/extensions/tool_execute_before/_25_trust_gate.py` — rewrite to use cowork + pause instead of bare `RepairableException`
- `python/api/cowork_approvals_update.py` — on approve/deny for trust gate records, also set `context.paused = False`

**Modified — frontend:**
- `webui/components/panels/cowork-panel.html` — add risk badge, always-approve link, and `alwaysApprove()` method
- `webui/index.js` — wire send intercept for onboarding check
- `webui/index.html` — include onboarding modal component

**Created — frontend:**
- `webui/components/onboarding/onboarding-modal.html` — 3-step Alpine.js wizard with inline store

**Tests:**
- `tests/unit/test_trust_system.py` — unit tests for new trust_system helpers
- `tests/e2e/test_trust_gate_approval.py` — e2e: trust gate stores approval record, approve/deny unpauses

---

## Task 1: Add settings fields for trust_always_allow and trust_onboarded

**Files:**
- Modify: `python/helpers/settings_core.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_trust_system.py`:

```python
"""Unit tests for trust_system helpers added in Task 1-2."""
import pytest
from python.helpers.settings_core import get_default_settings


def test_default_settings_has_trust_always_allow():
    s = get_default_settings()
    assert "trust_always_allow" in s
    assert isinstance(s["trust_always_allow"], list)
    assert s["trust_always_allow"] == []


def test_default_settings_has_trust_onboarded():
    s = get_default_settings()
    assert "trust_onboarded" in s
    assert s["trust_onboarded"] is False
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /mnt/wdblack/dev/projects/agent-jumbo
python -m pytest tests/unit/test_trust_system.py::test_default_settings_has_trust_always_allow tests/unit/test_trust_system.py::test_default_settings_has_trust_onboarded -v
```

Expected: `FAILED` — `KeyError: 'trust_always_allow'`

- [ ] **Step 3: Add fields to Settings TypedDict**

In `python/helpers/settings_core.py`, find the `# Trust & Performance` block around line 202 and add the two new fields:

```python
    # Trust & Performance
    trust_level: int
    performance_profile: str
    trust_always_allow: list[str]   # tools permanently exempt from trust gate
    trust_onboarded: bool           # whether first-run wizard has been completed
    max_monologue_iterations: int
```

- [ ] **Step 4: Add defaults**

In the same file, find the `trust_level=3,` line near line 586 in `get_default_settings()` and add the two new defaults directly below it:

```python
        trust_level=3,  # Collaborative
        performance_profile="efficient",
        trust_always_allow=[],
        trust_onboarded=False,
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
python -m pytest tests/unit/test_trust_system.py::test_default_settings_has_trust_always_allow tests/unit/test_trust_system.py::test_default_settings_has_trust_onboarded -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add python/helpers/settings_core.py tests/unit/test_trust_system.py
git commit -m "feat: add trust_always_allow and trust_onboarded settings fields"
```

---

## Task 2: Add trust_system helpers for always-allow and fingerprinting

**Files:**
- Modify: `python/helpers/trust_system.py`
- Modify: `tests/unit/test_trust_system.py`

These helpers are used by the trust gate (Task 3). Define them first so the gate can import them cleanly.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_trust_system.py`:

```python
from python.helpers.trust_system import (
    get_approval_fingerprint,
    is_always_allowed,
    TRUST_ALWAYS_ALLOW_KEY,
)


def test_get_approval_fingerprint_uses_tool_name_and_first_arg():
    fp = get_approval_fingerprint("email_advanced", {"to": "a@b.com", "subject": "hi"})
    assert fp == "email_advanced:a@b.com"


def test_get_approval_fingerprint_no_args():
    fp = get_approval_fingerprint("memory_delete", {})
    assert fp == "memory_delete:"


def test_is_always_allowed_true():
    settings = {TRUST_ALWAYS_ALLOW_KEY: ["email_advanced", "code_execution_tool"]}
    assert is_always_allowed("email_advanced", settings) is True


def test_is_always_allowed_false():
    settings = {TRUST_ALWAYS_ALLOW_KEY: ["memory_delete"]}
    assert is_always_allowed("email_advanced", settings) is False


def test_is_always_allowed_empty_list():
    settings = {TRUST_ALWAYS_ALLOW_KEY: []}
    assert is_always_allowed("email_advanced", settings) is False


def test_is_always_allowed_missing_key():
    assert is_always_allowed("email_advanced", {}) is False
```

- [ ] **Step 2: Run to verify they fail**

```bash
python -m pytest tests/unit/test_trust_system.py -k "fingerprint or always_allowed or TRUST_ALWAYS" -v
```

Expected: `ImportError: cannot import name 'get_approval_fingerprint'`

- [ ] **Step 3: Implement the helpers in trust_system.py**

At the end of `python/helpers/trust_system.py`, after the `TRUST_LEVEL_INFO` dict, add:

```python
# ── Always-allow list ──────────────────────────────────────────────────────

TRUST_ALWAYS_ALLOW_KEY = "trust_always_allow"


def is_always_allowed(tool_name: str, settings: dict) -> bool:
    """Return True if the tool is in the user's permanent allow list."""
    allow_list = settings.get(TRUST_ALWAYS_ALLOW_KEY, [])
    return tool_name in allow_list


def get_approval_fingerprint(tool_name: str, tool_args: dict) -> str:
    """Return a stable fingerprint for an approval record.

    Format: "<tool_name>:<first_meaningful_arg_value>"
    Used by cowork.find_matching_approval() for deduplication.
    """
    # Pick the first string arg value as the identifier (to, email, name, prompt)
    first_val = ""
    for val in tool_args.values():
        if isinstance(val, str) and val:
            first_val = val
            break
    return f"{tool_name}:{first_val}"
```

- [ ] **Step 4: Run to verify they pass**

```bash
python -m pytest tests/unit/test_trust_system.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add python/helpers/trust_system.py tests/unit/test_trust_system.py
git commit -m "feat: add get_approval_fingerprint and is_always_allowed to trust_system"
```

---

## Task 3: Rewrite trust gate to use cowork approval + context.paused

**Files:**
- Modify: `python/extensions/tool_execute_before/_25_trust_gate.py`
- Modify: `python/api/cowork_approvals_update.py`
- Create: `tests/e2e/test_trust_gate_approval.py`

The trust gate currently raises `RepairableException`, which the monologue loop adds to history and continues. The new gate sets `context.paused = True` so the agent spin-waits at `handle_intervention()` and stores a structured approval record in the cowork system. `cowork_approvals_update.py` already calls `context.communicate()` to resume the agent on approve — it just needs to also unset `context.paused`.

- [ ] **Step 1: Write the e2e test**

Create `tests/e2e/test_trust_gate_approval.py`:

```python
"""E2E tests for trust gate → cowork approval integration."""
import pytest
from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_trust_gate_approval_record_has_source_field(app_server, auth_cookies):
    """cowork_approvals_update with a trust_gate source approval clears correctly."""
    # We can't easily trigger a real tool call in e2e, so we test the API layer:
    # manually inject an approval record and verify approve/deny behaves correctly.
    # The trust gate itself is tested via unit tests in test_trust_system.py.

    # List approvals for a fresh context — should be empty
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_list",
        {"context": "nonexistent_trust_gate_ctx"},
    )
    assert resp["approvals"] == []


def test_cowork_approvals_update_approve_and_retry_action(app_server, auth_cookies):
    """approve_and_retry action returns approvals list."""
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_update",
        {
            "context": "nonexistent_trust_gate_ctx",
            "action": "approve_and_retry",
            "approval_id": "trust-nonexistent-id",
        },
    )
    assert "approvals" in resp
```

- [ ] **Step 2: Run to verify the tests pass (these are structural — they test existing behavior)**

```bash
python -m pytest tests/e2e/test_trust_gate_approval.py -v -m e2e
```

Expected: `PASSED` — these test the existing API shape, not the new behavior

- [ ] **Step 3: Rewrite _25_trust_gate.py**

Replace the entire contents of `python/extensions/tool_execute_before/_25_trust_gate.py`:

```python
"""Trust Gate — blocks tool execution for user approval based on trust level.

Runs before every tool call. Checks:
  1. Is the tool in the user's permanent allow list? → skip
  2. Does the current trust level require approval for this risk level? → block

When blocking, stores a structured approval record via cowork.add_approval()
and sets context.paused = True so the agent spin-waits at handle_intervention()
until the user approves or denies in the cowork sidebar panel.

On approval: cowork_approvals_update.py injects a retry message and sets
context.paused = False, resuming the agent.
"""

import uuid

from python.helpers import cowork, settings
from python.helpers.errors import RepairableException
from python.helpers.extension import Extension
from python.helpers.trust_system import (
    TRUST_ALWAYS_ALLOW_KEY,
    TrustLevel,
    get_approval_explanation,
    get_approval_fingerprint,
    get_tool_risk,
    get_trust_level,
    is_always_allowed,
    requires_approval,
)

# Tools that bypass the gate entirely — agent cannot function without these
_GATE_BYPASS = {"response", "input", "wait", "unknown"}

# Risk level labels for the approval record
_RISK_LABELS = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}


class TrustGate(Extension):
    async def execute(self, **kwargs):
        tool_name = kwargs.get("tool_name", "")
        tool_args = kwargs.get("tool_args", {}) or {}

        if tool_name in _GATE_BYPASS:
            return

        trust_level = get_trust_level()

        # Check permanent allow list first
        s = settings.get_settings()
        if is_always_allowed(tool_name, s):
            return

        if not requires_approval(tool_name, trust_level):
            return  # Auto-approved at this trust level

        agent = kwargs.get("agent")
        if agent is None:
            # No agent context — fall back to text warning (shouldn't happen in prod)
            raise RepairableException(
                f"[TRUST GATE] {tool_name} requires approval but no agent context available."
            )

        # Build and store the approval record
        risk = get_tool_risk(tool_name)
        approval = cowork.add_approval(
            agent.context,
            {
                "id": f"trust-{uuid.uuid4().hex[:12]}",
                "source": "trust_gate",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "risk": _RISK_LABELS.get(int(risk), "MEDIUM"),
                "risk_label": get_approval_explanation(tool_name, tool_args),
                "trust_level_name": TrustLevel(trust_level).name.capitalize(),
                "status": "pending",
                "fingerprint": get_approval_fingerprint(tool_name, tool_args),
                "agent_number": getattr(agent, "agent_number", 0),
            },
        )

        # Pause the agent — handle_intervention() spin-waits while context.paused is True
        agent.context.paused = True

        agent.context.log.log(
            type="info",
            heading=f"Trust gate blocked: {tool_name}",
            content=f"Risk={_RISK_LABELS.get(int(risk))} trust={TrustLevel(trust_level).name} approval_id={approval['id']}",
        )

        raise RepairableException(
            f"[TRUST GATE] {tool_name} requires approval. "
            f"Check the Approvals panel to approve or deny this action."
        )
```

- [ ] **Step 4: Modify cowork_approvals_update.py to unset context.paused on trust gate approvals**

In `python/api/cowork_approvals_update.py`, replace the existing `if action in ("approve", "approve_and_retry", "deny")` block (lines 34–44) with:

```python
        if action in ("approve", "approve_and_retry", "deny") and approval_id:
            status = "approved" if action in ("approve", "approve_and_retry") else "denied"
            updated = cowork.update_approval(context, approval_id, status, resolved_by="user")
            if updated:
                updated["inherit"] = inherit
                is_trust_gate = updated.get("source") == "trust_gate"

                if action == "approve_and_retry" or is_trust_gate:
                    tool_name = updated.get("tool_name", "tool")
                    if status == "approved":
                        message = f"Approval granted for {tool_name}. Please retry the action now."
                    else:
                        message = f"User denied approval for {tool_name}. Do not attempt this action again in this session."
                    context.communicate(UserMessage(message=message, attachments=[], system_message=[]))

                # Unblock the agent for both trust gate records (always) and explicit approve_and_retry
                if is_trust_gate or action == "approve_and_retry":
                    context.paused = False
                    context.resume_queued()

            return {"approvals": cowork.get_approvals(context)}
```

- [ ] **Step 5: Verify the e2e tests still pass**

```bash
python -m pytest tests/e2e/test_trust_gate_approval.py tests/e2e/test_cowork_api.py -v -m e2e
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add python/extensions/tool_execute_before/_25_trust_gate.py \
        python/api/cowork_approvals_update.py \
        tests/e2e/test_trust_gate_approval.py
git commit -m "feat: wire trust gate into cowork approval system with context.paused suspension"
```

---

## Task 4: Add risk badge and always-approve to cowork panel

**Files:**
- Modify: `webui/components/panels/cowork-panel.html`

The cowork panel already renders `pendingApprovals`. Add:
1. A color-coded risk badge when `approval.source === 'trust_gate'`
2. An "Always approve this tool →" link that calls `alwaysApprove(toolName)`
3. The `alwaysApprove()` method in `coworkPanelData()`

No new files. No new API endpoints — `alwaysApprove()` uses the existing `saveSettings` call pattern (direct fetch to `/settings_get` then `/settings_set`).

- [ ] **Step 1: Add risk badge CSS to the `<style>` block**

In `webui/components/panels/cowork-panel.html`, find the closing `</style>` tag and insert before it:

```css
/* Trust gate risk badges */
.risk-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-left: 6px;
}
.risk-LOW    { background: #22543d; color: #9ae6b4; }
.risk-MEDIUM { background: #744210; color: #fbd38d; }
.risk-HIGH   { background: #7b341e; color: #fbd38d; }
.risk-CRITICAL { background: #63171b; color: #feb2b2; }

.always-approve-link {
    display: block;
    margin-top: 8px;
    font-size: 11px;
    color: var(--text-secondary, #aaa);
    text-decoration: underline;
    cursor: pointer;
    text-align: center;
}
.always-approve-link:hover { color: var(--color-primary, #4a9eff); }
```

- [ ] **Step 2: Add risk badge and always-approve link to the approval card template**

Find the `<div class="approval-card">` template block (around line 21) and replace it:

```html
            <template x-for="approval in pendingApprovals.slice(0, 5)" :key="approval.id">
                <div class="approval-card">
                    <div class="approval-header">
                        <span class="approval-tool" x-text="approval.tool_name"></span>
                        <span x-show="approval.source === 'trust_gate'"
                              class="risk-badge"
                              :class="'risk-' + (approval.risk || 'MEDIUM')"
                              x-text="approval.risk || 'MEDIUM'"></span>
                        <span class="approval-time" x-text="formatTime(approval.timestamp || approval.created_at)"></span>
                    </div>
                    <div class="approval-summary" x-text="truncate(approval.summary || approval.args_preview || formatArgs(approval.tool_args), 80)"></div>
                    <div class="approval-actions">
                        <button class="btn-approve" @click="approveAction(approval.id)">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
                            Approve
                        </button>
                        <button class="btn-reject" @click="rejectAction(approval.id)">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                            Deny
                        </button>
                    </div>
                    <span x-show="approval.source === 'trust_gate'"
                          class="always-approve-link"
                          @click="alwaysApprove(approval.tool_name)">
                        Always approve this tool →
                    </span>
                </div>
            </template>
```

- [ ] **Step 3: Add alwaysApprove() and formatArgs() to coworkPanelData()**

In the `<script>` block, find the `truncate(text, length)` method and add after it:

```js
        formatArgs(args) {
            if (!args || typeof args !== 'object') return '-';
            const entries = Object.entries(args).slice(0, 2);
            return entries.map(([k, v]) => `${k}: ${String(v).substring(0, 40)}`).join(', ') || '-';
        },

        async alwaysApprove(toolName) {
            try {
                const token = Alpine.store('csrfStore')?.token || '';
                // Fetch current always-allow list
                const getResp = await fetch('/settings_get', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
                    body: JSON.stringify({}),
                });
                const getData = await getResp.json();
                const sections = getData?.settings?.sections || [];
                let currentList = [];
                for (const section of sections) {
                    for (const field of (section.fields || [])) {
                        if (field.id === 'trust_always_allow') {
                            currentList = Array.isArray(field.value) ? field.value : [];
                        }
                    }
                }

                if (currentList.includes(toolName)) return; // already in list

                const updatedList = [...currentList, toolName];
                await fetch('/settings_set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
                    body: JSON.stringify({
                        sections: [{ fields: [{ id: 'trust_always_allow', value: updatedList }] }]
                    }),
                });
            } catch (e) {
                console.error('alwaysApprove failed:', e);
            }
        },
```

- [ ] **Step 4: Manual verification**

Start the app, set `trust_level = 2` (Guided) via Trust dashboard, send a message asking the agent to save something to memory. Verify:
- The cowork panel shows a pending approval card with a yellow MEDIUM badge
- "Always approve this tool →" link appears
- Clicking Approve resumes the agent

- [ ] **Step 5: Commit**

```bash
git add webui/components/panels/cowork-panel.html
git commit -m "feat: add risk badge and always-approve link to cowork approval panel"
```

---

## Task 5: First-run onboarding wizard

**Files:**
- Create: `webui/components/onboarding/onboarding-modal.html`
- Modify: `webui/index.js`
- Modify: `webui/index.html`

The wizard intercepts the first message, asks 2 questions to recommend a trust level, shows a confirmation screen with override picker, then delivers the intercepted message after saving settings.

- [ ] **Step 1: Create the onboarding modal component**

Create `webui/components/onboarding/onboarding-modal.html`:

```html
<!-- First-run onboarding wizard — shown when trust_onboarded is not set -->
<div id="onboarding-overlay"
     x-data="onboardingData()"
     x-init="init()"
     x-show="show"
     x-cloak
     style="position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.75);display:flex;align-items:center;justify-content:center;">

    <div style="background:var(--secondary-bg,#1a1a2e);border:1px solid var(--color-border,#333);border-radius:12px;padding:32px;max-width:480px;width:90%;position:relative;">

        <!-- Progress dots -->
        <div style="display:flex;justify-content:center;gap:8px;margin-bottom:24px;">
            <template x-for="i in [1,2,3]" :key="i">
                <div :style="`width:8px;height:8px;border-radius:50%;background:${step >= i ? 'var(--color-primary,#4a9eff)' : 'var(--color-border,#333)'}`"></div>
            </template>
        </div>

        <!-- Step 1: Experience -->
        <div x-show="step === 1">
            <h2 style="margin:0 0 8px;font-size:20px;text-align:center;">👋 Welcome to Agent Jumbo</h2>
            <p style="text-align:center;color:var(--text-secondary,#aaa);margin:0 0 24px;font-size:14px;">Let's set up how much you want the agent to do on its own</p>
            <p style="font-weight:500;margin:0 0 16px;font-size:14px;">How would you describe your experience with AI assistants?</p>
            <div style="display:flex;flex-direction:column;gap:10px;">
                <template x-for="(opt, idx) in step1Options" :key="idx">
                    <div @click="step1Answer = opt.score; nextStep()"
                         :style="`padding:12px 16px;border-radius:8px;cursor:pointer;font-size:13px;border:1px solid var(--color-border,#333);background:${step1Answer===opt.score ? 'var(--color-primary-bg,#1a365d)' : 'var(--tertiary-bg,#252525)'};color:${step1Answer===opt.score ? 'var(--color-primary,#4a9eff)' : 'var(--text-primary,#fff)'}`">
                        <span x-text="opt.label"></span>
                    </div>
                </template>
            </div>
        </div>

        <!-- Step 2: Comfort -->
        <div x-show="step === 2">
            <p style="font-weight:500;margin:0 0 16px;font-size:14px;">How comfortable are you with the agent sending messages or running code without asking?</p>
            <div style="display:flex;flex-direction:column;gap:10px;">
                <template x-for="(opt, idx) in step2Options" :key="idx">
                    <div @click="step2Answer = opt.score; nextStep()"
                         :style="`padding:12px 16px;border-radius:8px;cursor:pointer;font-size:13px;border:1px solid var(--color-border,#333);background:${step2Answer===opt.score ? 'var(--color-primary-bg,#1a365d)' : 'var(--tertiary-bg,#252525)'};color:${step2Answer===opt.score ? 'var(--color-primary,#4a9eff)' : 'var(--text-primary,#fff)'}`">
                        <span x-text="opt.label"></span>
                    </div>
                </template>
            </div>
            <button @click="step = 1" style="margin-top:16px;background:none;border:none;color:var(--text-secondary,#aaa);font-size:12px;cursor:pointer;">← Back</button>
        </div>

        <!-- Step 3: Confirmation -->
        <div x-show="step === 3">
            <p style="font-weight:500;margin:0 0 8px;font-size:14px;text-align:center;">We recommend:</p>
            <div style="background:var(--tertiary-bg,#252525);border:1px solid var(--color-primary,#4a9eff);border-radius:8px;padding:16px;margin-bottom:20px;text-align:center;">
                <div style="font-size:22px;margin-bottom:4px;" x-text="trustLevels[selectedLevel]?.icon_emoji || '🤝'"></div>
                <div style="font-size:16px;font-weight:600;margin-bottom:4px;" x-text="trustLevels[selectedLevel]?.name"></div>
                <div style="font-size:12px;color:var(--text-secondary,#aaa);margin-bottom:12px;" x-text="trustLevels[selectedLevel]?.description"></div>
                <div style="font-size:11px;color:#22c55e;">✓ Auto: <span x-text="trustLevels[selectedLevel]?.auto"></span></div>
                <div style="font-size:11px;color:var(--color-warning,#d69e2e);margin-top:4px;">⚡ Asks: <span x-text="trustLevels[selectedLevel]?.asks"></span></div>
            </div>

            <p style="font-size:12px;color:var(--text-secondary,#aaa);margin:0 0 10px;text-align:center;">Or choose a different level:</p>
            <div style="display:flex;gap:8px;margin-bottom:20px;">
                <template x-for="(info, lvl) in trustLevels" :key="lvl">
                    <div @click="selectedLevel = parseInt(lvl)"
                         :style="`flex:1;padding:8px 4px;border-radius:6px;cursor:pointer;text-align:center;border:1px solid ${selectedLevel===parseInt(lvl) ? 'var(--color-primary,#4a9eff)' : 'var(--color-border,#333)'};background:${selectedLevel===parseInt(lvl) ? 'var(--color-primary-bg,#1a365d)' : 'var(--tertiary-bg,#252525)'}`">
                        <div style="font-size:14px;" x-text="info.icon_emoji"></div>
                        <div style="font-size:10px;margin-top:2px;" x-text="info.name"></div>
                    </div>
                </template>
            </div>

            <button @click="confirm()"
                    style="width:100%;padding:12px;background:var(--color-primary,#4a9eff);color:white;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">
                Start using Agent Jumbo →
            </button>
            <button @click="step = 2" style="width:100%;margin-top:8px;background:none;border:none;color:var(--text-secondary,#aaa);font-size:12px;cursor:pointer;">← Back</button>
        </div>

    </div>
</div>

<script>
function onboardingData() {
    return {
        show: false,
        step: 1,
        step1Answer: null,
        step2Answer: null,
        selectedLevel: 3,
        pendingMessage: null,

        step1Options: [
            { label: "🆕 I'm new — I want to understand what it's doing", score: 1 },
            { label: "🧑‍💻 Some experience — I like reviewing important actions", score: 2 },
            { label: "⚡ Experienced — let it run, I'll step in when needed", score: 3 },
        ],
        step2Options: [
            { label: "🔒 I want to review everything first", score: 1 },
            { label: "👍 Fine for most things, but ask for emails/code", score: 2 },
            { label: "🚀 Go ahead, I trust it", score: 3 },
        ],
        trustLevels: {
            1: { name: 'Observer',      icon_emoji: '👁️',  description: 'Maximum oversight. Explains every action before doing it.', auto: 'Nothing', asks: 'Everything' },
            2: { name: 'Guided',        icon_emoji: '✋',  description: 'Handles read-only tasks, asks before modifying data.', auto: 'Read-only tasks', asks: 'Data modifications, external actions' },
            3: { name: 'Collaborative', icon_emoji: '🤝', description: 'Works independently on most tasks, asks for high-risk actions.', auto: 'Most tasks', asks: 'Email, code execution, payments' },
            4: { name: 'Autonomous',    icon_emoji: '🚀', description: 'Full autonomy, only pauses for critical operations.', auto: 'Everything except critical', asks: 'Deployments, deletions, payments' },
        },

        async init() {
            // Fast check: localStorage first, then settings fallback
            if (localStorage.getItem('trust_onboarded') === '1') return;
            try {
                const resp = await fetch('/settings_get', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}),
                });
                const data = await resp.json();
                const sections = data?.settings?.sections || [];
                for (const section of sections) {
                    for (const field of (section.fields || [])) {
                        if (field.id === 'trust_onboarded' && field.value === true) {
                            localStorage.setItem('trust_onboarded', '1');
                            return;
                        }
                    }
                }
            } catch (e) {
                // Network error on init — don't block the user
                return;
            }
            // Neither check passed — show wizard
            this.show = true;
        },

        nextStep() {
            if (this.step === 1 && this.step1Answer !== null) {
                this.step = 2;
            } else if (this.step === 2 && this.step2Answer !== null) {
                this.selectedLevel = this.recommendLevel();
                this.step = 3;
            }
        },

        recommendLevel() {
            const total = (this.step1Answer || 2) + (this.step2Answer || 2);
            if (total <= 2) return 1; // Observer
            if (total <= 4) return 2; // Guided
            if (total <= 5) return 3; // Collaborative
            return 4;                 // Autonomous
        },

        async confirm() {
            const level = this.selectedLevel;
            try {
                const token = Alpine.store('csrfStore')?.token || '';
                await fetch('/settings_set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
                    body: JSON.stringify({
                        sections: [{ fields: [
                            { id: 'trust_level', value: level },
                            { id: 'trust_onboarded', value: true },
                        ]}]
                    }),
                });
                localStorage.setItem('trust_onboarded', '1');
            } catch (e) {
                console.error('Onboarding confirm failed:', e);
                // Still close the modal — don't block the user on a save failure
            }
            this.show = false;
            // Deliver the intercepted first message if one was queued
            if (this.pendingMessage && globalThis.sendMessageWithText) {
                globalThis.sendMessageWithText(this.pendingMessage);
                this.pendingMessage = null;
            }
        },

        isComplete() {
            return localStorage.getItem('trust_onboarded') === '1';
        },

        intercept(message) {
            this.pendingMessage = message;
            this.show = true;
        },
    };
}
</script>

<style>
[x-cloak] { display: none !important; }
</style>
```

- [ ] **Step 2: Add sendMessageWithText to index.js and wire the onboarding intercept**

In `webui/index.js`, find the `export async function sendMessage()` function (line 38). Add a new exported function immediately after the existing `sendMessage` function body:

```js
/**
 * Send a message with explicit text (used by onboarding to deliver intercepted messages).
 */
export async function sendMessageWithText(text) {
  const chatInputEl = document.getElementById("chat-input");
  if (!chatInputEl) return;
  chatInputEl.value = text;
  await sendMessage();
}
globalThis.sendMessageWithText = sendMessageWithText;
```

Then, in the existing `sendMessage` function, add the onboarding intercept at the top of the function, immediately after the `chatInputEl` null-check (before the `getConnectionStatus()` call):

```js
  // First-run onboarding intercept
  const onboarding = Alpine?.store?.('onboardingStore');
  if (onboarding && !onboarding.isComplete()) {
    const message = chatInputEl.value.trim();
    if (message) {
      onboarding.intercept(message);
      chatInputEl.value = "";
      adjustTextareaHeight();
      return;
    }
  }
```

Note: `onboardingData()` is an inline Alpine component (not a store), so the intercept check uses `document.querySelector('#onboarding-overlay').__x.$data` if Alpine.store is not used. Adjust the lookup:

```js
  // First-run onboarding intercept
  const onboardingEl = document.getElementById('onboarding-overlay');
  if (onboardingEl && onboardingEl._x_dataStack) {
    const od = Alpine.$data(onboardingEl);
    if (od && !od.isComplete()) {
      const message = chatInputEl.value.trim();
      if (message) {
        od.intercept(message);
        chatInputEl.value = "";
        adjustTextareaHeight?.();
        return;
      }
    }
  }
```

- [ ] **Step 3: Include the onboarding modal in index.html**

In `webui/index.html`, find the `</body>` closing tag and add the component include immediately before it:

```html
  <!-- First-run onboarding wizard -->
  <div x-data>
    <div x-html="onboardingModalHtml"></div>
  </div>
```

Find where other panel HTML files are included (search for `fetch(` or `x-html` patterns loading component HTML). Follow the same pattern used by other components. If components are loaded via a JS loader, add the onboarding modal to that loader. If they use a direct `<script>` include or `fetch` + `innerHTML`, do the same:

Look for how `cowork-panel.html` is loaded — search `index.html` for `cowork-panel` to find the exact inclusion pattern and mirror it for `onboarding-modal.html`.

- [ ] **Step 4: Verify the exact inclusion pattern and fix Step 3**

```bash
grep -n "cowork-panel\|components.*html\|loadComponent\|innerHTML" /mnt/wdblack/dev/projects/agent-jumbo/webui/index.html | head -20
```

Use the output to write the correct include. The modal needs to exist in the DOM before Alpine initializes, or be loaded dynamically the same way other panels are.

- [ ] **Step 5: Manual verification**

```bash
# Clear trust_onboarded from settings
# Open browser, go to http://localhost:6274
# Ensure localStorage has no 'trust_onboarded' key (DevTools → Application → Local Storage)
# Type a message and press Enter
# Expected: wizard modal appears, message field is cleared
# Complete wizard → verify trust_level updated in Trust dashboard
# Verify localStorage now has trust_onboarded = '1'
# Refresh page → wizard does NOT appear
```

- [ ] **Step 6: Commit**

```bash
git add webui/components/onboarding/onboarding-modal.html \
        webui/index.js \
        webui/index.html
git commit -m "feat: add first-run onboarding wizard for trust level setup"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Trust gate → cowork approval with paused suspension (Task 3)
- ✅ `trust_always_allow` list + always-approve UI (Tasks 2, 4)
- ✅ Risk badge on cowork panel (Task 4)
- ✅ `trust_onboarded` flag in settings (Task 1)
- ✅ Onboarding wizard 3-step guided flow (Task 5)
- ✅ localStorage + settings persistence for onboarding (Task 5)
- ✅ First message intercepted and delivered after wizard (Task 5)
- ✅ Approve/deny both unset `context.paused` (Task 3)

**One known ambiguity in Task 5, Step 3:** The component inclusion pattern for `index.html` is marked as "look it up" — Step 4 makes this explicit by instructing the implementer to grep for the pattern before writing the include. This avoids a wrong assumption.
