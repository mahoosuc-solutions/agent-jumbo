---
title: Customer Support
description: Canonical support, incident, billing, and remediation paths for the self-serve Agent Mahoo platform.
date: 2026-04-05
---

# Customer Support

Last updated: 2026-04-05

This is the canonical customer-facing support and escalation path for the current self-serve Agent Mahoo platform. If another document conflicts with this one, this document wins for launch.

## Standard Support

Use these channels for normal product questions, onboarding help, and reproducible bugs:

- Product issues and bug reports: GitHub Issues
  - <https://github.com/agent-mahoo-deploy/agent-mahoo/issues>
- Product questions and non-urgent discussion: GitHub Discussions
  - <https://github.com/agent-mahoo-deploy/agent-mahoo/discussions>
- Community support: Discord
  - <https://discord.gg/B8KZKNsPpj>

## Incident Path

Treat an issue as an incident if the service is unavailable, core chat flows are failing, backups cannot be trusted, or the payment path is materially broken.

- First response path: open a GitHub issue with reproduction details and mark the operational impact
- Public documentation and runbook source of truth:
  - [GA Launch Runbook](GA_LAUNCH_RUNBOOK.md)
  - [Production GA Definition of Done](PRODUCTION_GA_DEFINITION_OF_DONE.md)

For launch and self-serve readiness, the customer-facing incident path is the GitHub issue tracker until a separate staffed incident contact is published.

## Billing And Payment Support

Use GitHub Issues for payment-path defects, failed checkout flows, incorrect subscription state, or invoice disputes discovered during self-serve operation.

Launch gating note:

- A real Stripe `sk_test_*` key must be configured and validated before live GA launch.
- Until that validation exists, Stripe remains launch-blocking for self-serve commercial activation.

## Refund And Remediation

If a paid workflow fails because of a platform defect, use the billing support path above and include:

- checkout or invoice identifier if available
- timestamp and environment
- screenshots or request logs when possible
- whether the issue is ongoing or already resolved

Refunds, credits, or remediation steps are handled case by case after the payment-path validation record is reviewed.

## Related Customer Policies

- [Privacy Policy](PRIVACY_POLICY.md)
- [Terms Of Use](TERMS_OF_USE.md)
- [Data Retention Policy](DATA_RETENTION_POLICY.md)
- [Data Deletion Policy](DATA_DELETION_POLICY.md)
- [Self-Serve GA Onboarding](SELF_SERVE_GA_ONBOARDING.md)
