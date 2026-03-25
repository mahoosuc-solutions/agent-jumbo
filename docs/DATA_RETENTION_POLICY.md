# Data Retention Policy

Last updated: 2026-03-24

This policy defines the default retention expectations for Agent Jumbo platform data.

## General Rule

Keep only the data needed to operate the platform, support troubleshooting, satisfy billing records, and honor customer deletion requests.

## Data Categories

| Category | Default retention guidance |
|---|---|
| Chat logs and thread metadata | Retain until customer deletes the thread or the workspace is removed |
| Projects, workflows, and work-queue records | Retain while the workspace is active |
| Uploaded files and generated artifacts | Retain while referenced by an active workflow, project, or chat |
| Runtime telemetry and observability data | Retain only as long as needed for troubleshooting and performance review |
| Backup archives | Retain according to operator-defined backup cadence and recovery objectives |
| Payment and subscription metadata | Retain as needed for billing records, audits, and dispute handling |
| Integration metadata and tokens | Retain only while the integration remains connected and authorized |

## Backup Retention

Backup retention is deployment-specific. Operators must define:

- backup frequency
- retention window
- storage location
- restoration test cadence

If no explicit retention schedule is configured, the deployment is not launch-ready for self-serve GA.

## Log Minimization

Secrets and sensitive values should not be stored in logs. Logs and telemetry should be limited to operational data needed for debugging, health checks, and incident review.

## Customer Overrides

Enterprise or regulated customers may require stricter retention windows. Those overrides must be documented in deployment or account-specific controls.

## Related Policies

- [Privacy Policy](PRIVACY_POLICY.md)
- [Data Deletion Policy](DATA_DELETION_POLICY.md)
