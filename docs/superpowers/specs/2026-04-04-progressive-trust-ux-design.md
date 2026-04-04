# Progressive Trust UX — Approval Modal & First-Run Onboarding

## Goal

Complete the Progressive Trust system by wiring trust gate approvals into the existing cowork approval sidebar (replacing the text-only `RepairableException` path) and adding a guided first-run onboarding wizard that sets the user's trust level before their first conversation.

## Architecture

Two independent, self-contained features that share the existing settings infrastructure:

1. **Trust Gate → Cowork Approval** — backend gate uses `context.paused` + `cowork.add_approval()` to suspend the agent and surface a structured approval record to the existing cowork panel
2. **First-Run Onboarding Wizard** — frontend-only guided wizard (3 steps) that intercepts the first message sent, captures trust level preference, persists to settings + localStorage, then delivers the intercepted message

No new API endpoints. Both features reuse existing infrastructure.

---

## Feature 1: Trust Gate → Cowork Approval Integration

### How the current system works

`_25_trust_gate.py` raises `RepairableException` when a tool requires approval. The monologue loop at `agent.py:699` catches this, adds it as a warning to history, and continues — the LLM sees a text warning and tries to self-repair. This is a soft block, not a hard suspension.

### How the new system works

1. Trust gate stores an approval record via `cowork.add_approval()` with `source: "trust_gate"`
2. Trust gate sets `context.paused = True` — this causes `handle_intervention()` at `agent.py:1387` to spin-wait
3. Trust gate raises `RepairableException` with a brief message ("Waiting for user approval — check the Approvals panel")
4. The monologue loop adds the message to history but the agent cannot proceed because `context.paused` is `True`
5. The user sees the approval record in the cowork sidebar (already rendered by existing `cowork_approvals_list` polling)
6. User clicks Approve → `cowork_approvals_update.py` sets `status: "approved"`, calls `context.communicate(UserMessage(...))` to inject a retry message, and calls `context.paused = False` via `pause.py` to unblock the agent
7. User clicks Deny → same flow but injects a "user denied {tool_name}" message; agent continues with that context

### Approval record schema

Extends the existing cowork approval schema:

```json
{
  "id": "trust-<uuid4>",
  "source": "trust_gate",
  "tool_name": "email_advanced",
  "tool_args": { "to": "client@acme.com", "subject": "Project Proposal" },
  "risk": "HIGH",
  "risk_label": "High risk (external communication or code execution)",
  "trust_level_name": "Collaborative",
  "status": "pending",
  "created_at": "2026-04-04T12:00:00Z",
  "agent_number": 0,
  "fingerprint": "email_advanced:client@acme.com"
}
```

`fingerprint` is `tool_name + ":" + first meaningful arg value` — used by `find_matching_approval()` in `cowork.py` for the "always approve" flow.

### Always-approve shortcut

The cowork panel gets an "Always approve this tool →" link for trust gate records. Clicking it saves the tool name to `settings.trust_always_allow` (a list). The trust gate checks this list before deciding to block.

### Files to modify

| File | Change |
|------|--------|
| `python/extensions/tool_execute_before/_25_trust_gate.py` | Replace `RepairableException` raise with: build approval record, `cowork.add_approval()`, `context.paused = True`, raise `RepairableException("Waiting for user approval")` |
| `python/api/cowork_approvals_update.py` | On `approve`/`approve_and_retry`: call `pause.py` logic to set `context.paused = False`; on `deny`: set paused=False, inject denial message |
| `python/helpers/trust_system.py` | Add `get_approval_fingerprint(tool_name, tool_args) -> str`; add `TRUST_ALWAYS_ALLOW_KEY = "trust_always_allow"` and `is_always_allowed(tool_name, settings) -> bool` |
| `python/helpers/settings_core.py` | Add `trust_always_allow: list[str]` field, default `[]` |
| `python/helpers/settings_ui.py` | No change needed — `trust_always_allow` is managed programmatically |

### Frontend (cowork panel)

The existing cowork approvals panel already renders pending records. The only addition is:
- Display `risk` badge (color-coded: LOW=green, MEDIUM=yellow, HIGH=orange, CRITICAL=red) when `source === "trust_gate"`
- Show "Always approve this tool →" link for trust gate records that calls a new `alwaysApprove(toolName)` method in the cowork store, which POSTs to `settings_set` with the updated `trust_always_allow` list

| File | Change |
|------|--------|
| `webui/components/panels/cowork-panel.html` | Add risk badge + always-approve link for `source === "trust_gate"` records |
| `webui/components/panels/cowork-panel.html` | Add `alwaysApprove(toolName)` method to `coworkPanelData()` inline Alpine component |

---

## Feature 2: First-Run Onboarding Wizard

### Trigger logic

On chat message submit (in the existing send handler):

```js
async function handleSend(message) {
    const alreadyOnboarded =
        localStorage.getItem('trust_onboarded') === '1' ||
        (await loadSettings()).trust_onboarded === true;

    if (!alreadyOnboarded) {
        $store.onboarding.pendingMessage = message;
        $store.onboarding.show = true;
        return; // intercept — do not send yet
    }
    // normal send path
    sendMessage(message);
}
```

### Wizard steps

**Step 1 — Experience question**

> "How would you describe your experience with AI assistants?"

| Choice | Maps to |
|--------|---------|
| I'm new — I want to understand what it's doing | `experienceScore = 1` |
| Some experience — I like reviewing important actions | `experienceScore = 2` |
| Experienced — let it run, I'll step in when needed | `experienceScore = 3` |

**Step 2 — Comfort question**

> "How comfortable are you with the agent sending messages or running code without asking first?"

| Choice | Maps to |
|--------|---------|
| I want to review everything first | `comfortScore = 1` |
| Fine for most things, but ask for emails/code | `comfortScore = 2` |
| Go ahead, I trust it | `comfortScore = 3` |

**Step 3 — Confirmation screen**

Shows the recommended level (computed below) with:
- Level name, icon, and description from `TRUST_LEVELS`
- "What it handles automatically" and "What it asks about" — pulled from existing `TRUST_LEVEL_INFO`
- Full 4-level override picker (same selector as trust dashboard)
- "Start using Agent Jumbo →" button

### Recommendation logic

```js
function recommendLevel(experienceScore, comfortScore) {
    const total = experienceScore + comfortScore;
    if (total <= 2) return 1; // Observer
    if (total <= 4) return 2; // Guided
    if (total <= 5) return 3; // Collaborative
    return 4;                 // Autonomous
}
```

### Persistence on confirm

```js
async function confirmOnboarding(trustLevel) {
    await saveSettings({ trust_level: trustLevel, trust_onboarded: true });
    localStorage.setItem('trust_onboarded', '1');
    $store.onboarding.show = false;
    sendMessage($store.onboarding.pendingMessage); // deliver intercepted message
    $store.onboarding.pendingMessage = null;
}
```

### New files

| File | Purpose |
|------|---------|
| `webui/components/onboarding/onboarding-modal.html` | Alpine.js wizard — 3 steps, progress dots, level picker on step 3 |
| `webui/components/onboarding/onboarding-store.js` | State: `show`, `step`, `experienceScore`, `comfortScore`, `recommendedLevel`, `selectedLevel`, `pendingMessage` |

### Modified files

| File | Change |
|------|--------|
| `webui/index.html` | Include `onboarding-modal.html` component; wire `handleSend` to check `$store.onboarding` |
| `python/helpers/settings_core.py` | Add `trust_onboarded: bool`, default `False` |

---

## Settings additions summary

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `trust_always_allow` | `list[str]` | `[]` | Tools permanently exempted from trust gate |
| `trust_onboarded` | `bool` | `False` | Whether first-run wizard has been completed |

---

## What is NOT in scope

- Telegram approval flow (already exists via inline keyboard; trust gate records will appear there automatically once stored as cowork approvals)
- Trust level changes via onboarding affecting performance profiles (already handled by `apply_profile_to_settings()` — `saveSettings({ trust_level: N })` triggers this automatically)
- Approval history dashboard (the existing cowork approvals panel already shows history)

---

## Verification

1. Set `trust_level = 3` (Collaborative), send "email the client" → agent pauses, cowork panel shows HIGH risk approval record → approve → agent sends email → done
2. Set `trust_level = 3`, send "email the client" → approve → click "Always approve this tool" → send again → agent sends without pausing
3. Clear `localStorage` and set `trust_onboarded = false` in settings → send first message → onboarding wizard appears, message is intercepted → complete wizard → message is delivered, trust level saved
4. Refresh browser after completing onboarding → wizard does not appear (localStorage check)
5. Clear localStorage but keep `trust_onboarded = true` in settings → wizard does not appear (settings fallback check)
