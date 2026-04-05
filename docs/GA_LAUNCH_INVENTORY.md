---
title: GA Launch Inventory
description: Feature classification, validation ownership, evidence locations, and rollback paths for launch scope.
date: 2026-03-24
---

# GA Launch Inventory

Use this inventory with [Production GA Definition of Done](PRODUCTION_GA_DEFINITION_OF_DONE.md). It is the operator-facing control sheet for feature classification, validation, evidence capture, and rollback planning.

## Current Launch Target

- **Launch profile:** Production GA for self-serve customers
- **Feature freeze target:** 2026-04-03
- **GA decision target:** 2026-04-17

## Classification Rules

- `ga`: customer-visible, supported at launch, validated with evidence
- `beta`: customer-visible but explicitly not part of GA support commitment
- `internal`: hidden from public launch scope

If a row does not have an owner, validation path, evidence path, and rollback path, it is not ready for `ga`.

## Inventory

| Capability | Classification | Owner role | Validation path | Evidence artifact | Rollback or disable path | Status |
|---|---|---|---|---|---|---|
| Core startup and auth | ga | Engineering | `/health`, boot smoke, config load smoke | `artifacts/validation/validation-360-20260404-170924.log` | rollback deploy or disable release | ✅ Evidence captured 2026-04-04 — 10/10 pass |
| Chat create/message/poll lifecycle | ga | Engineering | `./scripts/validate_360.sh` and manual smoke | `artifacts/validation/validation-360-20260404-170924.log` | rollback deploy | ✅ Evidence captured 2026-04-04 — chat roundtrip pass |
| Skills discovery | ga | Engineering | `./scripts/validate_360.sh` | `artifacts/validation/validation-360-20260404-170924.log` | rollback deploy | ✅ Evidence captured 2026-04-04 — skills discovery pass |
| Trust gate enforcement | ga | Security | targeted pytest plus manual trust-level smoke | `artifacts/validation/deployment-validation-20260404-171147.log` | set stricter trust defaults or stop launch | ✅ Deployment 83/83 pass — refresh manual trust smoke before launch |
| Trust and Security dashboard | ga | Product | browser smoke on dashboard render and state | `artifacts/validation/manual-smoke-20260405.md` | hide dashboard link | ✅ Validated 2026-04-05 — 4 trust cards, 6 posture items |
| Dashboards sidebar navigation | ga | Product | browser smoke for sidebar registration and routing | `artifacts/validation/manual-smoke-20260405.md` | feature flag or hide section | ✅ Validated 2026-04-05 — Work Queue, Workflows, Tasks routes load |
| New chat auto-select | ga | Product | browser smoke after chat creation | `artifacts/validation/manual-smoke-20260405.md` | rollback deploy | ✅ Validated 2026-04-05 — new chat selected immediately |
| Ideas workspace | beta | Product | backend tests plus browser smoke for create, refine, and save brief | test report plus launch smoke record | hide sidebar link | Beta — no GA evidence required |
| Projects workspace | beta | Product | backend tests plus browser smoke for load and project chat activation | test report plus launch smoke record | hide sidebar link | Beta — no GA evidence required |
| Idea promotion to project/workflow/queue | beta | Engineering/Product | targeted integration tests plus manual promotion smoke | pytest output plus launch smoke record | disable promotion action | Beta — no GA evidence required |
| In-monologue task planner | beta | Product | targeted functional smoke | launch smoke record | hide or label beta | Beta — no GA evidence required |
| Graceful shutdown | ga | Operations | controlled shutdown and restart smoke | `artifacts/validation/deployment-validation-20260404-171147.log` | rollback deploy | ✅ Container health verified — refresh shutdown smoke before launch |
| Backup create and restore | ga | Operations | backup plus restore rehearsal | `artifacts/validation/backup-restore-20260405.md` | stop launch if restore fails | ✅ Full rehearsal 2026-04-05 — 241 files, zip integrity OK, 38 DBs captured, path translation verified — create and restore both pass |
| Public product page | ga | Product | `web` build plus manual content smoke | `artifacts/validation/web-build-20260405.md` | unpublish marketing route | ✅ TypeScript 0 errors 2026-04-05 — 16 public routes confirmed: home, pricing (5 tiers), /try demos (chat/summarize/workflow), /signup, solutions, install, docs, portfolio, platform |
| Platform status API | ga | Engineering | route smoke with backend up and down | `artifacts/validation/deployment-validation-20260404-171147.log` | fallback to static-only status | ✅ API health checks pass in deployment validation |
| Stripe pricing and payment path | ga | Product/Ops | Stripe test-mode end-to-end flow | `artifacts/validation/stripe-flow-20260405.md` | disable payment route and hold launch | ✅ Mock provider rehearsal 2026-04-05 — 8/8 pass: customer, product, price, checkout, subscription, invoice, finalize, cancel — real sk_test key needed before live launch |
| Square payment provider | beta | Engineering | `scripts/square_catalog_sync.py --mock --catalog both` — 7 created, 0 errors | mock sync log | disable `SQUARE_ACCESS_TOKEN` env var | Beta — mock rehearsal passes; real Square credentials and live end-to-end needed before ga promotion |
| PayPal payment provider | beta | Engineering | `scripts/paypal_catalog_sync.py --mock --catalog both` — 7 created, 0 errors | mock sync log | disable `PAYPAL_CLIENT_ID` env var | Beta — mock rehearsal passes; real PayPal credentials and live end-to-end needed before ga promotion |
| Customer billing portal (/billing) | beta | Product | load /billing in browser while authenticated — verify plan, invoices, subscription pages render | manual browser smoke | disable route in Next.js middleware or remove billing nav | Beta — UI built; requires live payment provider credentials for full validation |
| Payment dunning and retry | beta | Engineering | `payment_dunning` tool `run_cycle` action against test past_due invoices | dunning cycle log | disable `DunningManager` cron call — seeded by `dunning_scheduler_init.py` | Beta — cron wired 2026-04-05; agent-only surface; daily 03:00 task auto-seeded at boot |
| Browser-assisted payment account setup | beta | Engineering | `payment_account_setup` tool `start_setup` dry-run with mock browser | setup session log | tool is agent-only, no customer surface | Beta — 15-step Stripe + 15-step WBM workflows; `internal_shell` steps auto-execute; recovery/restart API endpoints wired; Playwright MCP needed for live browser automation |
| Self-serve onboarding docs | ga | Product | fresh install from docs | onboarding dry-run notes | remove self-serve claim | ✅ INSTALL.md created and validated — onboarding guide at /wbm-onboarding.html |
| Monitoring and alerting | ga | Operations | alert fire drill and dashboard checks | `artifacts/validation/monitoring-alerting-*.md` | hold launch | ✅ health_alerter wired, platform-health-monitor task running every 5 min |
| Privacy, terms, retention, deletion docs | ga | Product/Ops | doc publication review on customer-facing documentation and pricing surfaces | `artifacts/validation/compliance-links-20260405.md` | hold launch | ✅ Verified 2026-04-05 — docs routes and pricing surface link compliance + support paths |
| Security review | ga | Security | static analysis (Bandit, detect-secrets) + manual review of auth, webhooks, payment data | `artifacts/validation/security-review-20260405.md` | hold launch or remediate findings | ✅ Reviewed 2026-04-05 — 3 findings resolved, 2 accepted, 2 open (SEC-007/008 require real keys) |

## Freeze Review Checklist

- [ ] Every public feature has a row in this inventory.
- [ ] Every `ga` row has an owner role assigned.
- [ ] Every `ga` row has a runnable validation path.
- [ ] Every `ga` row has a known evidence artifact location.
- [ ] Every `ga` row has a rollback or disable path.
- [ ] Every `beta` or `internal` feature is labeled correctly in public-facing surfaces.

## Notes

- Update this inventory at feature freeze, not launch day.
- If a feature changes materially after 2026-04-03, refresh its validation and evidence.
- Do not promote `beta` to `ga` without updating this file and the public docs in the same change.
