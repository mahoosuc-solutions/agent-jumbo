---
title: Production GA Definition of Done
description: Source of truth for self-serve launch readiness, release gates, and go-live decision criteria.
date: 2026-03-24
---

# Production GA Definition of Done

**Platform:** Agent Jumbo AI Architect Platform
**Launch profile:** Production GA for self-serve customers
**Last reviewed:** 2026-03-24
**Feature freeze target:** 2026-04-03
**GA decision target:** 2026-04-17
**Decision rule:** Do not launch before 2026-04-17 unless every gate in this document is green with evidence attached.

## Why This Document Exists

Recent work shipped meaningful platform improvements across trust enforcement, web UI dashboards, multi-LLM orchestration, task planning, backup and shutdown hardening, Stripe-backed commerce, and the public product page. The repo also contains older "production ready" and beta-launch claims that were written for different phases of the project.

This document is the current source of truth for launch readiness. It replaces ad hoc launch claims with one explicit go/no-go gate tied to the current platform state.

Related execution documents:

- [GA Launch Inventory](GA_LAUNCH_INVENTORY.md)
- [GA Evidence Package](GA_EVIDENCE_PACKAGE.md)
- [Self-Serve GA Onboarding](SELF_SERVE_GA_ONBOARDING.md)
- [GA Launch Runbook](GA_LAUNCH_RUNBOOK.md)

## Recent Work Reviewed

The go-live target in this document is based on work shipped between 2026-03-22 and 2026-03-24, including:

- Progressive Trust System and trust-level configuration
- Trust and Security dashboard plus sidebar navigation
- Multi-LLM meta-orchestration and shared context dispatch
- In-monologue task planner for complex work
- Graceful shutdown, backup command, and database backup support
- WAL mode, dead-letter limits, alerting, and reliability fixes
- Stripe payment foundation and full pipeline work
- Public product page, pricing model, product catalog, and platform status API
- Web UI reliability fixes for chat send, new chat selection, and dashboard behavior

## Launch Targets

### Milestone 1: Feature Freeze by 2026-04-03

By 2026-04-03:

- No new GA-scope features merge without launch-owner approval.
- Every launchable feature is classified as `ga`, `beta`, or `internal`.
- All public claims are reconciled against actual code and validation evidence.
- Remaining work is limited to bug fixes, launch-doc cleanup, validation, deployment hardening, and release operations.

### Milestone 2: GA Decision on 2026-04-17

On 2026-04-17, the platform is eligible for production GA only if:

- Every required gate below is green.
- No unresolved Sev-1 or Sev-2 issues exist in GA scope.
- Launch evidence has been collected within 72 hours of go-live.
- Engineering, product, security, and operations have signed off.

## GA Scope Policy

### Included in GA

- Core app startup, auth, and settings persistence
- Chat creation, async message flow, and poll lifecycle
- Trust-gated tool execution and trust-level UX
- Dashboard navigation and current dashboard surfaces
- Public product page and platform status API
- Backup, graceful shutdown, and restore workflow
- Documented self-serve deployment path
- Stripe-backed commercial path that matches published pricing and fulfillment flow

### Not GA by default

Any feature is not GA by default if it meets any of these conditions:

- It is labeled "POC", "deferred", or "pending manual smoke" in current docs.
- It exists only in historical launch summaries or legacy README claims.
- It lacks an automated check or a documented manual smoke script.
- It requires operator intervention that is not documented for self-serve users.

Mark non-GA features as `beta` or `internal`, hide them, or remove the claim from public docs before launch.

## Definition of Done

### 1. Product and documentation gate

- Root `README.md`, `web/README.md`, pricing data, product-page content, and launch docs describe the same launch scope.
- Every public feature claim is traceable to code, configuration, or measured evidence.
- A launch inventory exists with:
  - feature name
  - classification (`ga`, `beta`, `internal`)
  - owner role
  - validation command or smoke script
  - evidence artifact path
  - rollback or disable path
- Self-serve onboarding docs exist as one canonical path with no conflicting setup instructions.

### 2. Core technical gate

- `./scripts/validate_360.sh` passes in the intended GA environment and archives output under `artifacts/validation/`.
- Release validation and deployment validation scripts are current and do not depend on stale paths or obsolete repo assumptions.
- The following flows pass end-to-end on the GA environment:
  - `GET /health`
  - `GET /chat_readiness`
  - `POST /chat_create`
  - `POST /message_async`
  - `GET /poll`
  - skills discovery
- The following March platform additions have explicit validation evidence:
  - trust gate is authoritative
  - Trust and Security dashboard renders
  - new chat auto-select works
  - dashboard sidebar registration works
  - task planner runs for complex tasks
  - graceful shutdown completes cleanly
  - backup command creates a recoverable backup
  - product-page status API fails gracefully when backend is unavailable
- No Sev-1 or Sev-2 defects remain in GA scope.

### 3. Self-serve customer gate

- A new user can complete setup from published docs without operator help.
- Required environment variables, paid integrations, and BYOK responsibilities are documented in one place.
- The customer can understand pricing, payment flow, and what becomes active after purchase.
- Failure states are explicit for:
  - missing API keys
  - invalid credentials
  - unreachable backend
  - Stripe/payment failure
  - degraded status API
- Support contact path, incident contact path, and refund or remediation path are visible to customers.

### 4. Security and compliance gate

- Secret handling is verified across logs, settings, test fixtures, and examples.
- Trust enforcement has no known bypass in GA scope.
- Privacy policy, terms, retention policy, and deletion policy exist and are linked from customer-facing surfaces.
- A canonical customer-facing support path exists and is linked from customer-facing surfaces.
- Data collected through chat, billing, email, and integrations has documented retention and deletion behavior.
- Only launch integrations whose auth model, permissions, and failure behavior are documented for self-serve use.
- Security review sign-off exists with owner, date, and any accepted residual risks.

### 5. Operations gate

- Production deployment is repeatable from clean state using the documented deployment path.
- Monitoring and alerting exist for:
  - service health
  - chat readiness
  - async message or poll failures
  - payment failures
  - backup failures
  - restart or shutdown anomalies
- Backup, restore, and rollback are tested, not only documented.
- A launch-day runbook exists with:
  - deployment order
  - smoke tests
  - rollback triggers
  - owner roles
  - communication steps
- A 24-hour post-launch observation plan exists with clear stay-live versus rollback criteria.

## Required Evidence Package

Collect this package no earlier than 2026-04-14 for the 2026-04-17 GA decision:

| Evidence | Minimum requirement | Owner role |
|---|---|---|
| Validation 360 report | Latest run passes | Engineering |
| Release validation output | Latest run passes | Engineering |
| Deployment validation output | Latest run passes on target environment | Engineering |
| Web build evidence | Production build passes for `web/` | Engineering |
| Manual smoke record | Product page, dashboards, trust UX, backup/restore, Stripe flow | Product |
| Security review | Open issues triaged, no launch-blocking findings | Security |
| Legal/compliance packet | Privacy, terms, retention, deletion, and support path published | Product/Ops |
| Launch runbook | Final version linked and reviewed | Operations |

## Go/No-Go Checklist

Use this checklist in the final launch review:

- [ ] Feature freeze held since 2026-04-03
- [ ] Launch inventory complete and current
- [ ] Public claims reconciled across README, web docs, and product page
- [ ] Validation 360 green
- [ ] Release validation green
- [ ] Deployment validation green
- [ ] Web production build green
- [ ] Core chat and readiness flows manually smoked
- [ ] Backup, restore, and rollback exercised successfully
- [ ] Stripe and customer commercial flow validated
- [ ] Privacy, terms, retention, deletion, and support docs published
- [ ] Monitoring and alerting checked in production
- [ ] No open Sev-1 or Sev-2 GA issues
- [ ] Final sign-off from Engineering, Product, Security, Operations

## Immediate Gaps To Close Before Feature Freeze

Based on the current repo state, these are the highest-priority launch gaps:

1. Reconcile legacy "production ready" claims with the actual current platform scope.
2. Update validation scripts and release docs that still assume older repository structure or release process.
3. Create one canonical self-serve onboarding path for backend, web, billing, and integrations.
4. Convert manual or deferred validations into explicit smoke scripts and evidence artifacts.
5. Publish customer-facing privacy, terms, retention, deletion, and support paths.

## Ownership Model

Use role-based ownership for launch tracking:

- **Engineering:** validation scripts, runtime health, deployment, backup, rollback, defects
- **Product:** GA scope classification, public claims, onboarding, pricing, launch inventory
- **Security:** secrets review, trust enforcement review, residual risk sign-off
- **Operations:** monitoring, alerting, runbook, launch-day execution, observation window

## Exit Criteria

The platform is ready for production GA only when this document can be reviewed line by line with linked evidence and no unchecked launch blockers remain.
