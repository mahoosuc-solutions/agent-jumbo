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
| Core startup and auth | ga | Engineering | `/health`, boot smoke, config load smoke | `artifacts/validation/` health run | rollback deploy or disable release | Pending evidence refresh |
| Chat create/message/poll lifecycle | ga | Engineering | `./scripts/validate_360.sh` and manual smoke | `artifacts/validation/validation-360-*.log` | rollback deploy | Pending evidence refresh |
| Skills discovery | ga | Engineering | `./scripts/validate_360.sh` | `artifacts/validation/validation-360-*.log` | rollback deploy | Pending evidence refresh |
| Trust gate enforcement | ga | Security | targeted pytest plus manual trust-level smoke | test report plus launch smoke record | set stricter trust defaults or stop launch | Pending evidence refresh |
| Trust and Security dashboard | ga | Product | browser smoke on dashboard render and state | launch smoke record | hide dashboard link | Pending evidence refresh |
| Dashboards sidebar navigation | ga | Product | browser smoke for sidebar registration and routing | launch smoke record | feature flag or hide section | Pending evidence refresh |
| New chat auto-select | ga | Product | browser smoke after chat creation | launch smoke record | rollback deploy | Pending evidence refresh |
| Ideas workspace | beta | Product | backend tests plus browser smoke for create, refine, and save brief | test report plus launch smoke record | hide sidebar link | Needs classification follow-up |
| Projects workspace | beta | Product | backend tests plus browser smoke for load and project chat activation | test report plus launch smoke record | hide sidebar link | Needs classification follow-up |
| Idea promotion to project/workflow/queue | beta | Engineering/Product | targeted integration tests plus manual promotion smoke | pytest output plus launch smoke record | disable promotion action | Needs validation bundle |
| In-monologue task planner | beta | Product | targeted functional smoke | launch smoke record | hide or label beta | Needs GA decision |
| Graceful shutdown | ga | Operations | controlled shutdown and restart smoke | ops run log | rollback deploy | Pending evidence refresh |
| Backup create and restore | ga | Operations | backup plus restore rehearsal | backup and restore log | stop launch if restore fails | Pending evidence refresh |
| Public product page | ga | Product | `web` build plus manual content smoke | build log plus smoke record | unpublish marketing route | Pending evidence refresh |
| Platform status API | ga | Engineering | route smoke with backend up and down | API smoke log | fallback to static-only status | Pending evidence refresh |
| Stripe pricing and payment path | ga | Product/Ops | Stripe test-mode end-to-end flow | payment validation record | disable payment route and hold launch | Pending evidence refresh |
| Self-serve onboarding docs | ga | Product | fresh install from docs | onboarding dry-run notes | remove self-serve claim | Pending evidence refresh |
| Monitoring and alerting | ga | Operations | alert fire drill and dashboard checks | `artifacts/validation/monitoring-alerting-*.md` | hold launch | Local evidence captured; refresh in target env |
| Privacy, terms, retention, deletion docs | ga | Product/Ops | doc publication review | `artifacts/validation/compliance-links-*.md` | hold launch | Local publication package prepared |

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
