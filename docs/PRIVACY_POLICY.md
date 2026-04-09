---
title: Privacy Policy
description: Customer-facing summary of how Agent Mahoo handles platform data, integrations, and operational telemetry.
date: 2026-03-24
---

# Privacy Policy

Last updated: 2026-03-24

This policy describes how Agent Mahoo handles customer data for the self-serve platform described in the current launch package.

## Scope

This policy applies to:

- chat content submitted through the platform
- account and configuration data stored in platform settings
- uploaded files and generated artifacts
- telemetry and runtime diagnostics
- billing metadata handled through Stripe or equivalent payment providers
- integration metadata for connected services

## What We Collect

Agent Mahoo may store:

- chat prompts, responses, and thread metadata
- project, workflow, and work-queue records
- uploaded files and generated outputs
- configuration values needed to run enabled features
- masked telemetry about tool use, latency, and failure states
- payment and subscription identifiers returned by billing providers

Agent Mahoo is not intended to collect unnecessary sensitive data. Operators are responsible for not placing secrets, credentials, or regulated data into chat or file uploads unless the deployment is explicitly configured and reviewed for that use case.

## How Data Is Used

Agent Mahoo uses stored data to:

- operate chat, workflow, queue, and project features
- persist user settings and connected integrations
- support backups, restores, and troubleshooting
- measure runtime health, reliability, and feature usage
- process billing and account lifecycle actions

## Third-Party Services

Depending on configuration, Agent Mahoo may send data to third-party providers, including:

- model providers
- Stripe
- email, messaging, calendar, finance, or CRM integrations
- observability providers explicitly enabled by the operator

Operators are responsible for reviewing the privacy and data-processing terms of any enabled third-party service.

## Security Practices

Agent Mahoo uses risk-gated tool execution, secret masking, audit-oriented runtime logs, and encrypted handling for sensitive fields where supported by the configured deployment.

No security control is a guarantee against all misuse. Operators remain responsible for environment hardening, credential management, and limiting access to authorized users.

## Data Sharing

Agent Mahoo does not treat customer content as public. Data may be disclosed only:

- to the customer or authorized operators
- to subprocessors needed to provide configured services
- when required by law
- to investigate abuse, fraud, or security incidents

## Data Retention and Deletion

Retention and deletion behavior are governed by:

- [Data Retention Policy](DATA_RETENTION_POLICY.md)
- [Data Deletion Policy](DATA_DELETION_POLICY.md)

## Customer Responsibilities

Customers are responsible for:

- choosing which integrations and providers are enabled
- supplying only data they are authorized to process
- configuring backups, monitoring, and secrets safely
- meeting any legal or regulatory obligations specific to their data

## Changes

Customer support and deletion-request routing follow [Customer Support](CUSTOMER_SUPPORT.md).

If this policy changes materially, update the launch docs and evidence package in the same release.
