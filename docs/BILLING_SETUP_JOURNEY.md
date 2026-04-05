# Tenant Billing Setup Journey

This document is the canonical process for guided, tenant-owned onboarding workflows inside Mahoosuc OS.

Stripe billing setup is the primary billing implementation today. WBM onboarding uses the same embedded workflow shell, evidence model, recovery states, and safe-checkpoint behavior.

## Goal

Help a tenant connect and operate their own Stripe account without making Mahoosuc the merchant of record.

The product should:

1. Guide the tenant through the right Stripe dashboard tasks at the right time.
2. Track readiness and blockers as structured capabilities.
3. Keep catalog intent and operational status visible inside billing admin.
4. Let each tenant activate, deactivate, and reprice offers before syncing them to Stripe.
5. Preserve full workflow context across interruptions and recover safely without replaying regulated steps.

## Shared Recovery Model

All embedded onboarding workflows should expose the same recovery vocabulary:

- `recoverable_in_place`
- `recoverable_from_checkpoint`
- `needs_user_reauth`
- `not_recoverable`
- `completed`

The operator experience should:

1. resume in place when the browser/session state is still valid
2. fall back to the nearest safe checkpoint when exact resume is no longer safe
3. never auto-replay regulated steps such as CAPTCHA, 2FA, KYC, password entry, or secret reveal

Every workflow run should keep:

- current phase and current step
- structured evidence
- pending human gate details
- browser/session metadata when relevant
- safe checkpoints that can be restarted intentionally

## Journey Stages

### 1. Discover

Purpose:

- explain what Stripe setup involves
- show why KYC, payouts, webhooks, and catalog sync matter
- tell the operator what the next recommended action is

Exit criteria:

- the operator can open the billing setup assistant
- next actions and guidance are visible

### 2. Connect

Purpose:

- capture tenant-owned Stripe credentials
- establish the webhook endpoint that Mahoosuc expects

Exit criteria:

- test-mode secret key stored for the tenant
- webhook signing secret stored for the tenant

### 3. Configure

Purpose:

- guide the operator through Stripe dashboard setup
- surface human-required checkpoints such as email verification, 2FA, KYC, and payout setup

Exit criteria:

- business profile submitted
- webhook endpoint registered
- pending Stripe requirements are visible

### 4. Catalog

Purpose:

- start from Mahoosuc templates where useful
- let the tenant decide which offers should exist in their Stripe account
- avoid unsafe price editing patterns

Exit criteria:

- required products and prices exist in Stripe
- at least one billable offer is ready for checkout testing

### 5. Validate

Purpose:

- prove the account is operational, not just connected
- verify API auth, payouts, charges, webhooks, and catalog presence

Exit criteria:

- readiness checks pass
- the tenant has a viable test checkout path

### 6. Operate

Purpose:

- make the setup assistant an ongoing copilot for billing operations
- support day-2 work like price changes, new offers, and webhook recovery

Exit criteria:

- billing admin remains healthy after dashboard or catalog changes
- the operator knows which process to run for common changes

## Defined Processes

### New Tenant Onboarding

Trigger:

- a tenant is connecting Stripe for the first time

Process:

1. Start a guided setup session.
2. Capture the tenant’s Stripe API key and webhook secret.
3. Run health verification to expose missing KYC, payouts, or webhook work.
4. Review starter catalog offers before syncing them.
5. Disable offers that should stay out of the tenant account and save any tenant-specific price overrides.
6. Re-run readiness until the tenant reaches `ready`.

### Catalog Change

Trigger:

- a tenant wants to add, remove, or reprice offers

Process:

1. Refresh the catalog diff.
2. Review recommended actions rather than editing active prices in place.
3. Save tenant-specific price overrides or deactivate offers in billing admin.
4. Sync the intended offers.
5. Re-run readiness checks.
6. Confirm at least one valid test checkout path still exists.

### Billing Recovery

Trigger:

- readiness regresses after a dashboard change or credential rotation

Process:

1. Run health verification.
2. Identify the failing capability.
3. Resume the setup journey or store updated credentials.
4. Re-run verification until readiness returns to `ready`.

### Embedded Workflow Recovery

Trigger:

- an onboarding workflow is interrupted mid-run

Process:

1. Open the workflow workspace, not a standalone document.
2. Review the recovery panel and last safe checkpoint.
3. Resume in place when possible.
4. Restart from a safe checkpoint when exact recovery is not safe.
5. Re-run validation after recovery.

### WBM Onboarding

Trigger:

- a property is being onboarded through the embedded WBM workspace

Process:

1. Verify WBM bridge health.
2. Start or resume the embedded workflow.
3. Complete each onboarding phase from the workspace and confirm progress there.
4. Use recovery and checkpoints rather than skipping ahead after interruptions.
5. Finish with the final validation phase and keep the evidence trail intact.

## Product Responsibilities

Mahoosuc should:

- store tenant-scoped provider connection state
- store tenant-scoped secrets
- guide the operator through Stripe-hosted tasks
- track structured readiness
- let tenants manage offer activation and pricing safely before sync
- sync catalog intent into Stripe when asked

Mahoosuc should not:

- become merchant of record
- silently complete regulated identity steps
- hide Stripe ownership from the tenant

## Operator Notes

- Human-regulated steps remain in Stripe Dashboard.
- Browser-assisted setup should navigate, explain, and pause cleanly when human action is required.
- The billing setup assistant and embedded onboarding workspaces are the canonical homes for these journeys; chat can launch or resume them, but should not replace them.
