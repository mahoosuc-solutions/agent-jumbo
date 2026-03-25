# GA Launch Runbook

Use this runbook for the final production GA decision and launch execution on **2026-04-17**.

## Preconditions

Do not start launch-day execution unless all are true:

- Feature freeze has held since **2026-04-03**
- [Production GA Definition of Done](PRODUCTION_GA_DEFINITION_OF_DONE.md) is fully reviewed
- [GA Launch Inventory](GA_LAUNCH_INVENTORY.md) is current
- [GA Evidence Package](GA_EVIDENCE_PACKAGE.md) has fresh artifacts from the last 72 hours

## Owner Roles

| Role | Responsibility |
|---|---|
| Engineering | deployment, validation logs, runtime verification |
| Product | scope confirmation, public claims, customer comms |
| Security | trust review, secret handling review, risk acceptance |
| Operations | runbook execution, monitoring, rollback coordination |

## T-24 Hours

- Freeze public-facing copy except launch-critical fixes
- Confirm deployment target and rollback target are both available
- Refresh evidence artifacts
- Confirm monitoring and alerting are enabled
- Confirm support, incident, and payment contacts are staffed

## T-2 Hours

- Re-run `./scripts/validate_release.sh`
- Re-run `./scripts/validate_360.sh`
- Re-run `./scripts/validate_deployment.sh` on the target environment if applicable
- Verify `web/` production build still succeeds
- Confirm no new Sev-1 or Sev-2 defects have opened

## Go/No-Go Review

The review meeting must cover:

1. Current commit or deploy target
2. Evidence links for all required checks
3. Open risks accepted for launch
4. Rollback trigger conditions
5. Named approvers from Engineering, Product, Security, and Operations

If any approver blocks launch, hold the release.

## Launch Sequence

1. Confirm backup exists for the target environment
2. Deploy backend changes
3. Verify `/health`
4. Verify `/chat_readiness`
5. Deploy or promote frontend
6. Verify public product page
7. Run chat smoke:
   - create chat
   - send message
   - poll to completion
8. Verify dashboard navigation and trust UX
9. Verify Stripe or sales conversion path
10. Start observation window

## Rollback Triggers

Rollback immediately if any of the following occur:

- `/health` goes red after deployment
- `/chat_readiness` does not settle ready
- chat create/message/poll flow fails
- customer login is broken
- product page or platform status API is materially broken
- backup or restore confidence is lost
- Stripe payment path is broken for the launch scope

## Rollback Procedure

1. Halt customer-facing announcements
2. Roll back to the last known good deployment target
3. Verify `/health`
4. Verify `/chat_readiness`
5. Run one chat smoke
6. Post incident update to the launch channel
7. Preserve failing logs and screenshots in `artifacts/validation/`

## Observation Window

Minimum observation window: **24 hours**

During the observation window, check:

- health endpoint stability
- readiness stability
- chat completion success
- payment or support incidents
- restart and shutdown anomalies

If launch remains stable for 24 hours with no Sev-1 or Sev-2 issues, mark GA complete.

## Launch Artifacts

Capture and link:

- release validation log
- validation 360 log
- deployment validation log
- manual smoke record
- backup/restore record
- security sign-off
- final launch decision record
