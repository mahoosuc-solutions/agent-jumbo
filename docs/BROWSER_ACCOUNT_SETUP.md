# Browser-Assisted Payment Account Setup

Agent Mahoo can guide you through setting up accounts on Stripe, Square, and PayPal using
browser automation. The agent handles all navigation and form-filling, but pauses at checkpoints
where human action is required (CAPTCHA, 2FA, email verification, document upload).

For the full tenant-owned Stripe journey and operating model, see `docs/BILLING_SETUP_JOURNEY.md`.

## How It Works

The setup instrument uses Playwright browser automation (via the MCP plugin) to:

1. Open the provider's registration page
2. Fill in your business details
3. Navigate to the API keys / developer dashboard
4. Extract credentials and store them in tenant-scoped billing setup storage
5. Run a dry-run catalog sync and readiness verification

At each **human-required** checkpoint, the agent stops, shows you a screenshot, gives you
clear instructions, and waits for you to press **Continue** before proceeding.

## Starting a Setup Session

Tell the agent what you want:

```
"Help me set up Stripe payments for Mahoosuc"
"Walk me through creating a Square developer account"
"Set up PayPal billing"
```

Or use the tool directly:

```json
{"action": "start_setup", "provider": "stripe", "business_name": "Mahoosuc Solutions", "email": "billing@mahoosuc.com", "country": "US"}
```

Available providers: `stripe`, `square`, `paypal`, `wbm`

## Setup Steps by Provider

### Stripe (15 steps)

| # | Type | Action |
|---|------|--------|
| 0 | automated | Navigate to stripe.com/register |
| 1 | automated | Take screenshot for review |
| 2 | automated | Fill email and password |
| 3 | automated | Submit registration |
| 4 | **human** | Check email, click verification link, press Continue |
| 5 | **human** | Complete CAPTCHA if shown, press Continue |
| 6 | **human** | Set up 2FA if prompted, press Continue |
| 7 | automated | Navigate to API keys page |
| 8 | automated | Screenshot API keys page |
| 9 | automated | Reveal and extract test secret key |
| 10 | automated | Navigate to webhooks page |
| 11 | automated | Register webhook endpoint |
| 12 | automated | Extract webhook signing secret |
| 13 | automated | Store credentials in .env |
| 14 | automated | Run catalog dry-run to verify |

### Square (13 steps)

| # | Type | Action |
|---|------|--------|
| 0 | automated | Navigate to squareup.com/signup |
| 1 | automated | Take screenshot |
| 2 | automated | Fill business details |
| 3 | automated | Submit registration |
| 4 | **human** | Confirm email, press Continue |
| 5 | **human** | Complete identity verification if required, press Continue |
| 6 | automated | Navigate to Developer Dashboard |
| 7 | automated | Create application |
| 8 | automated | Extract sandbox credentials |
| 9 | automated | Navigate to webhooks |
| 10 | automated | Register webhook subscription |
| 11 | automated | Extract webhook signature key |
| 12 | automated | Store credentials and run dry-run |

### PayPal (13 steps)

| # | Type | Action |
|---|------|--------|
| 0 | automated | Navigate to paypal.com/bizsignup |
| 1 | automated | Take screenshot |
| 2 | automated | Fill business details |
| 3 | automated | Submit registration |
| 4 | **human** | Confirm email, press Continue |
| 5 | **human** | Complete phone verification if required, press Continue |
| 6 | automated | Navigate to developer.paypal.com |
| 7 | automated | Create REST API application |
| 8 | automated | Extract sandbox credentials |
| 9 | automated | Navigate to webhooks |
| 10 | automated | Create webhook subscription |
| 11 | automated | Extract webhook ID |
| 12 | automated | Store credentials and run dry-run |

### WBM (15 steps — all human-required)

The WBM provider runs an operator-guided onboarding across 15 phases. The agent tracks each
phase, captures evidence, and creates a safe checkpoint after each one. All steps are
`human_required` — the agent prompts you through each phase and waits for confirmation.

| # | Phase | Goal |
|---|-------|------|
| 0 | Verify MCP Bridge | Confirm bridge health before changing tenant state |
| 1 | Bootstrap Tenant | Run onboarding summary and tenant bootstrap |
| 2 | Property Configuration | Set identity, contact, timezone, guest-facing defaults |
| 3 | Room Inventory | Create and validate room inventory |
| 4 | Staff Access | Configure staff roles and operator permissions |
| 5 | Email | Configure guest communication flows |
| 6 | Voice AI | Configure voice assistant path |
| 7 | SMS | Enable SMS messaging |
| 8 | Door Codes | Wire code issuance with check-in settings |
| 9 | Payments | Confirm billing integration points |
| 10 | Occupancy & Rates | Configure occupancy baselines and rate inputs |
| 11 | Competitor Intel | Set up competitive monitoring |
| 12 | Dynamic Pricing | Configure pricing automation guardrails |
| 13 | SEO & Web Presence | Set listing and discoverability details |
| 14 | Final Validation | Run validation suite and capture evidence |

Access the WBM onboarding UI at `/billing/wbm-onboarding`.

## Workflow Recovery and Restart

If a setup session is interrupted (network drop, browser crash, provider timeout), you can
resume without starting over.

### Resume In Place

Resume where the workflow left off:

```json
{"action": "recover_workflow", "run_id": "stripe_workflow_abc123"}
```

Use this when:

- The browser session is still open or can be restored
- The interrupted step was a human gate (you can just confirm it)
- The provider's state matches where the workflow paused

### Restart From Checkpoint

Restart from the last safe checkpoint if exact recovery is no longer safe:

```json
{"action": "restart_workflow_from_checkpoint", "run_id": "stripe_workflow_abc123", "checkpoint_id": "cp_abc"}
```

Use this when:

- The browser session is gone and the provider may have partial state
- A form submission partially completed and you need a clean retry
- The workflow advanced past a non-idempotent step that failed midway

### Choosing Between Resume and Restart

| Situation | Recommendation |
|-----------|---------------|
| Human gate interrupted — just confirm it | Resume in place |
| Automated step partially completed | Restart from last checkpoint |
| Provider shows partial account creation | Restart from last checkpoint |
| Only a heartbeat gap — no real failure | Resume in place |
| Webhook registration step failed | Restart from last checkpoint |

### Viewing Checkpoints

```json
{"action": "get_workflow_checkpoints", "run_id": "stripe_workflow_abc123"}
```

The UI at `/billing/wbm-onboarding` also surfaces checkpoints and recovery controls in
the Recovery panel that appears when a run is interrupted.

### When to Redo Manually

If neither resume nor restart succeeds (e.g., the provider locked the account after repeated
attempts), complete the affected step manually in the provider's dashboard, then:

1. Call `confirm_human_step` to advance the session past the failed step
2. Provide any extracted values (API key, webhook secret) as `credentials`
3. Continue with `next_step` or let the agent proceed

## Human-in-the-Loop Checkpoints

When the agent reaches a human-required step, it will:

1. Print the step description clearly
2. Show a browser screenshot (if using a visual interface)
3. Wait for your confirmation

To advance, tell the agent:

```
"Done, continue"
"I've completed the email verification"
```

Or call the tool:

```json
{"action": "confirm_human_step", "session_id": "your-session-id"}
```

## Viewing Session Status

```json
{"action": "get_session", "session_id": "your-session-id"}
```

Response includes:

- Current step number and description
- Steps completed vs total
- Provider name and status (`in_progress`, `completed`, `failed`)

List all sessions:

```json
{"action": "list_sessions"}
```

## Manually Storing Credentials

If you've already set up an account and just need to store credentials:

```json
{
  "action": "store_credentials",
  "provider": "stripe",
  "credentials": {
    "api_key": "sk_test_...",
    "webhook_secret": "whsec_..."
  }
}
```

This stores credentials in tenant billing setup state by default. For local/dev workflows,
credentials can still be written to `.env`, and optionally pushed via `vercel env add`.

## Verifying an Existing Setup

Check that credentials are configured and working:

```json
{"action": "verify_setup", "provider": "stripe"}
```

The agent will:

1. Check that required tenant credentials are present
2. Verify Stripe API auth
3. Check webhook registration, KYC/payout readiness, and catalog presence
4. Report success or the next required actions

## Screenshot Archive

All browser screenshots taken during setup sessions are stored in:

```
instruments/custom/payment_account_setup/data/screenshots/
```

Filenames follow the pattern `{provider}_{session_id}_step{N}.png`.

## Security Notes

- Tenant secrets are stored in local billing setup SQLite state for the current environment and returned redacted
- Session and connection data is stored in a local SQLite database at:
  `instruments/custom/payment_account_setup/data/payment_account_setup.db`
- Browser automation only fills forms — it never reads your passwords back after entry
- At human-required steps, the agent cannot see what you type in the browser

## Troubleshooting

**"No browser available"** — ensure the Playwright or Chrome DevTools MCP server is running.
In Claude Code, enable the plugin via `/plugin install playwright`.

**Step stuck at CAPTCHA** — complete the CAPTCHA manually and tell the agent to continue.
The agent cannot solve CAPTCHAs by design.

**Session `failed` status** — try recovery first (`recover_workflow`). If the provider's
state is inconsistent, restart from the last safe checkpoint (`restart_workflow_from_checkpoint`).
If both fail, start a new session:

```json
{"action": "start_setup", "provider": "stripe", "business_name": "...", "email": "..."}
```

Each `start_setup` creates a new independent session.

**`internal_shell` step fails** — steps with `automation_type: automated` and `action.tool: internal_shell`
run a subprocess automatically. If the command fails (non-zero exit), the step is still marked
complete with the error captured in evidence. Check the `output` field in step evidence to diagnose.
