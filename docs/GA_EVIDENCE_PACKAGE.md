# GA Evidence Package

This document defines the minimum evidence bundle required for the 2026-04-17 production GA decision. Store artifacts in stable locations and link them from the launch review.

## Collection Window

- Collect final evidence no earlier than **2026-04-14**.
- Any artifact older than 72 hours at the time of the GA review must be refreshed.

## Required Artifacts

| Area | Required artifact | Suggested location | Owner role |
|---|---|---|---|
| Validation 360 | Passing report from `./scripts/validate_360.sh` | `artifacts/validation/validation-360-*.log` | Engineering |
| Release validation | Passing output from `./scripts/validate_release.sh` | `artifacts/validation/release-validation-*.log` | Engineering |
| Deployment validation | Passing output from `./scripts/validate_deployment.sh` on target env | `artifacts/validation/deployment-validation-*.log` | Engineering |
| Web build | Successful `npm run build` and `npm run type-check` in `web/` | CI run link or saved build log | Engineering |
| Core smoke | Manual record for health, readiness, chat flow, dashboards, trust UX | `artifacts/validation/manual-smoke-*.md` | Product |
| Backup and restore | Successful rehearsal notes with timestamps | `artifacts/validation/backup-restore-*.md` | Operations |
| Stripe flow | Test-mode or production-safe validation of pricing and payment path | `artifacts/validation/stripe-flow-*.md` | Product/Ops |
| Security review | Signed review with open findings disposition | `artifacts/validation/security-review-*.md` | Security |
| Compliance packet | Published links for privacy, terms, retention, deletion | `artifacts/validation/compliance-links-*.md` | Product/Ops |
| Launch runbook | Final reviewed go-live runbook | `docs/` or `artifacts/validation/` | Operations |

## Evidence Standards

- Prefer machine-generated logs where possible.
- Manual smoke notes must include date, environment, tester, exact path exercised, and result.
- If an artifact references a dashboard, screenshot, or external system, include the link or file path.
- If a check fails and is later fixed, keep both the failing artifact and the passing artifact for auditability.

## Launch Review Packet

Prepare one final launch packet with:

1. Link to [Production GA Definition of Done](PRODUCTION_GA_DEFINITION_OF_DONE.md)
2. Link to [GA Launch Inventory](GA_LAUNCH_INVENTORY.md)
3. Links to the latest artifacts for every required area
4. List of open risks accepted for launch
5. Final go/no-go sign-off names and timestamps

Current branch snapshot:

- [GA Evidence Record — 2026-03-24](GA_EVIDENCE_RECORD_2026-03-24.md)

## Open Gaps As Of 2026-03-24

- Privacy, terms, retention, and deletion publication package is still missing
- Several March features need fresh manual smoke evidence
- Monitoring and alerting evidence is not yet bundled for launch review
- Ideas/projects beta slice needs explicit smoke evidence and launch classification
