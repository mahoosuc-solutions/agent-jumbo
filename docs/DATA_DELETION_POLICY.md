---
title: Data Deletion Policy
description: Expected deletion behavior for customer content, integrations, workspaces, and backup expiration.
date: 2026-03-24
---

# Data Deletion Policy

Last updated: 2026-03-24

This policy defines how Agent Mahoo platform data should be deleted when customers remove content, disconnect integrations, or close an environment.

## Customer-Initiated Deletion

Customers should be able to remove or request removal of:

- chat threads
- uploaded files
- project and workflow data
- work-queue records
- integration credentials and connection metadata

Deletion should remove active references from the live environment. If a deployment keeps backups, deleted data may continue to exist in backup media until the retention window expires.

## Integration Disconnects

When an integration is removed:

- revoke or delete stored tokens where supported
- stop future sync or webhook processing for that integration
- remove configuration values no longer required

## Workspace Or Environment Deletion

When a customer workspace or deployment is decommissioned:

- remove live databases and associated files from the active environment
- revoke active credentials and secrets
- remove scheduled jobs, webhooks, and background tasks tied to that environment
- let backup copies expire according to the configured retention policy

## Incident Or Abuse Exceptions

Data may be preserved longer when needed for:

- security investigations
- fraud or abuse review
- legal hold
- billing disputes

## Verification

Deletion workflows should be tested during launch readiness and documented in the final evidence package.

## Related Policies

- [Privacy Policy](PRIVACY_POLICY.md)
- [Data Retention Policy](DATA_RETENTION_POLICY.md)
- [Customer Support](CUSTOMER_SUPPORT.md)
