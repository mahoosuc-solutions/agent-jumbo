# Monitoring And Alerting Evidence — 2026-03-24

- Environment: local repo plus running Docker target `agent-jumbo`
- Prepared by: Codex

## Evidence Collected

1. Live health signal
   Source: `GET http://localhost:50080/health`
   Result: passed
   Notes:
   - service reported `status=healthy`
   - runtime metrics exposed for poll duration and tool execution duration
   - disk and memory checks returned healthy

2. Live readiness signal
   Source: `GET http://localhost:50080/chat_readiness`
   Result: passed
   Notes:
   - readiness checks passed for provider, model, API key, and backend

3. Monitoring tool coverage
   Command:
   - `python3.11 -m pytest tests/test_devops_monitor.py tests/integration/test_observability_integration.py -q`
   Result: `16 passed`

4. Platform documentation
   Linked sources:
   - [Observability](../../docs/OBSERVABILITY.md)
   - [GA Launch Runbook](../../docs/GA_LAUNCH_RUNBOOK.md)
   - [Security Platform](../../docs/security-platform.md)

## Current Monitoring Surface

- `/health` for platform health
- `/chat_readiness` for chat runtime readiness
- runtime metrics embedded in health payload
- telemetry and external observability settings documented in the observability guide
- launch runbook requires monitoring checks before and after deployment

## Remaining Operational Note

This artifact closes the local evidence gap for monitoring and alerting. Production GA still requires a target-environment fire drill and final 72-hour refresh before launch.
