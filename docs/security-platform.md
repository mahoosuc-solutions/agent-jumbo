# Mahoosuc OS Security Architecture

## Overview

Mahoosuc OS is a security-first AI operating system built on Kali Linux and hardened through defense-in-depth principles. This document describes the security architecture, controls, and design decisions that protect agent operations, data integrity, and system access across every layer of the platform.

This is not a compliance checklist retrofitted onto a shipping product. Security is the architectural foundation — every component, from webhook ingestion to agent execution to data persistence, was designed with explicit threat modeling and fail-closed defaults.

---

## 1. Security Foundation: Kali Linux

### Why Kali Linux

Mahoosuc OS runs on Kali Linux — the industry-standard operating system used by penetration testers, red teams, and security researchers worldwide. This is a deliberate architectural choice with three strategic benefits:

**Self-auditing capability.** Kali Linux provides access to 600+ security tools out of the box. The same toolchain that professionals use to break into systems is available to continuously audit, test, and harden the platform. Network scanning, vulnerability assessment, password auditing, wireless analysis, and forensic investigation tools are all native to the environment.

**Rolling security updates.** Kali follows a rolling release model, meaning security patches and tool updates are delivered continuously rather than on fixed release cycles. There is no waiting for quarterly patch windows. When a vulnerability is disclosed, the fix flows through the update pipeline immediately.

**Container isolation via Docker.** The entire Mahoosuc OS runtime operates inside Docker containers, providing process-level isolation, controlled volume mounts, and a well-defined boundary between the host system and agent execution. The Kali base image ensures that the container itself carries forward the security-first posture of the host.

**Not a toy.** Kali Linux is not a novelty distribution chosen for aesthetics. It is the OS used by professional security teams to test enterprise defenses. By building on it, Mahoosuc OS inherits the operational assumptions of a platform designed to operate in adversarial environments — exactly where AI agents need to function safely.

---

## 2. Authentication & Authorization

### Passkey Enforcement

High-risk tools — code execution, email dispatch, deployment operations, and other sensitive actions — require passkey authentication before execution. This is enforced at the platform level through the `SECURITY_ENFORCE_PASSKEY` configuration.

- **Enforcement is on by default.** Passkey gates are active unless explicitly overridden.
- **Environment variable override.** Setting `SECURITY_ENFORCE_PASSKEY=false` disables enforcement for development and testing environments. This override is logged and surfaced in health checks.
- **Auth window.** A successful passkey authentication creates a 3600-second (1-hour) session window during which subsequent high-risk tool calls proceed without re-authentication. This balances security with usability for interactive sessions.
- **Automated context exemption.** Scheduled tasks, cron-triggered workflows, and subordinate agents spawned by an already-authenticated parent process are exempt from interactive passkey prompts. These contexts operate under the trust level established by the initiating process, preventing deadlocks in automated pipelines.

### Progressive Trust System

Authorization follows a four-level progressive trust model:

| Level | Name | Description |
|-------|------|-------------|
| 1 | **Observer** | Read-only access. Agent can query data and generate recommendations but cannot execute any actions. |
| 2 | **Supervised** | Agent can execute low-risk tools autonomously. Medium and high-risk tools require explicit approval. |
| 3 | **Trusted** | Agent can execute low and medium-risk tools autonomously. High-risk and critical tools require approval. |
| 4 | **Autonomous** | Full execution authority. All tool risk levels execute without interactive approval. Audit logging remains active. |

Trust levels are configurable per agent, per workflow, and per operational context. New deployments default to the Supervised level.

### Tool Risk Classification

Every tool in the platform carries an explicit risk classification:

| Risk Level | Examples | Authorization Requirement |
|------------|----------|--------------------------|
| **LOW** | Data queries, status checks, list operations | No additional auth |
| **MEDIUM** | Content generation, scheduling, notifications | Trust Level 2+ |
| **HIGH** | Code execution, email dispatch, financial operations | Passkey or Trust Level 3+ |
| **CRITICAL** | Deployment, infrastructure changes, credential management | Passkey required regardless of trust level |

The security gate in `process_tools()` checks authorization before every tool call. There is no bypass path — the gate sits in the critical execution path, and tool calls that fail authorization are rejected with a structured error that includes the required authorization method.

---

## 3. Network Security

### WireGuard VPN

Remote access to the Mahoosuc OS instance is secured through a WireGuard VPN tunnel. WireGuard provides:

- Modern cryptographic primitives (Curve25519, ChaCha20-Poly1305, BLAKE2s)
- Minimal attack surface (approximately 4,000 lines of code in the kernel module)
- Roaming support for agents operating across network boundaries
- No listening ports exposed to the public internet beyond the VPN endpoint

### Webhook Verification

Mahoosuc OS operates 16 channel adapters for receiving external events — Telegram, Slack, Discord, Microsoft Teams, WhatsApp, Signal, Mattermost, and nine additional channels. Every adapter implements fail-closed webhook verification:

**No secret configured = no access.** If a channel adapter does not have its verification secret set, the adapter rejects all incoming requests. There is no "open by default" mode. Each adapter requires its own dedicated secret — there is no shared secret across channels.

**Verification methods by channel type:**

| Verification Method | Channels |
|---------------------|----------|
| **Ed25519 signature verification** | Discord |
| **HMAC-SHA256 signature verification** | Slack, Mattermost, Signal, and others |
| **Verification token validation** | Meta (WhatsApp, Facebook Messenger) |
| **Bot token + update validation** | Telegram |

Every webhook endpoint validates the cryptographic signature or verification token before processing the payload. Invalid signatures result in immediate rejection with no further processing. This is enforced at the adapter layer, before the event reaches the AG Mesh event bus or any agent logic.

---

## 4. Agent Safety Controls

### Monologue Iteration Limit

Agent monologues — the internal reasoning loops where an agent processes information and generates tool calls — are hard-limited to **25 iterations** by default. This prevents runaway loops, infinite recursion, and cost escalation from unconstrained agent reasoning.

- Configurable via environment variable for workflows that legitimately require extended reasoning
- When the limit is reached, the agent terminates its current monologue with a structured summary of progress and remaining work
- The limit applies per monologue invocation, not per session

### Wall-Clock Timeout

Every agent execution is subject to a **30-minute wall-clock timeout** by default. This is independent of the iteration limit and provides a hard boundary on elapsed time regardless of how many iterations have been consumed.

- Configurable via environment variable
- Timeout triggers graceful shutdown with state preservation where possible
- Prevents abandoned or stuck agent processes from consuming resources indefinitely

### Security Gate in process_tools()

The `process_tools()` function — the central dispatch point for all tool execution — includes an inline security gate that evaluates every tool call against the current authorization context before execution. This gate checks:

1. The tool's risk classification
2. The agent's current trust level
3. Whether a valid passkey session exists (for high-risk and critical tools)
4. Whether the execution context qualifies for automated exemption

No tool call bypasses this gate. The check is synchronous and blocking — the tool does not begin execution until authorization is confirmed.

---

## 5. Data Security

### Database Architecture

Mahoosuc OS operates **35 instrument databases**, each implemented as a dedicated SQLite database with the following security-relevant configuration:

- **WAL (Write-Ahead Logging) mode** is enabled on every database. WAL mode allows concurrent readers and a single writer without blocking, eliminating the class of bugs where concurrent agent operations corrupt data through lock contention.
- **busy_timeout=5000ms** is set on every connection. If a write lock cannot be acquired immediately, the connection retries for up to 5 seconds before failing. This prevents both silent data loss and indefinite blocking.

### Encryption

Sensitive data fields are encrypted using **AES-256-GCM** (Galois/Counter Mode), which provides both confidentiality and authenticated integrity verification.

**No plaintext fallback.** If encryption fails for any reason — missing key, corrupted key material, library error — the operation returns `None` rather than falling back to storing or returning plaintext. This is a deliberate design decision: it is better to surface an error than to silently degrade security.

### Dead-Letter Queue

Events that fail processing are persisted to a dead-letter queue rather than being silently dropped. This provides:

- A complete audit trail of failed operations
- The ability to replay failed events after root cause resolution
- Visibility into systematic failures that might indicate an attack or misconfiguration

---

## 6. Observability & Audit

### End-to-End Request Tracing

Every request entering the system receives a `request_id` that propagates through all downstream operations — agent execution, tool calls, database writes, external API calls, and event emissions. This correlation ID enables:

- Full reconstruction of any request's execution path
- Latency attribution across component boundaries
- Forensic investigation of security incidents

### Token Budget Monitoring

LLM token consumption is monitored in real time. When a single operation exceeds **30,000 tokens**, the system emits a warning. This serves dual purposes:

- **Cost control**: Prevents runaway inference costs from unconstrained prompts
- **Security signal**: Anomalous token consumption can indicate prompt injection or data exfiltration attempts

### Structured Health Check

The platform exposes a structured health check endpoint that validates:

| Component | Check |
|-----------|-------|
| Databases | Connection availability and WAL mode verification for all 35 instruments |
| Redis | Connection and pub/sub functionality for AG Mesh event bus |
| Disk | Available storage capacity |
| Dead-letters | Count and age of unprocessed dead-letter events |

### Tool Execution Telemetry

Every tool execution is logged with:

- Tool name and risk classification
- Authorization method used (passkey, trust level, automated exemption)
- Execution duration
- Success or failure status
- The request_id of the originating request

### Webhook Event Logging

All incoming webhook events are logged with idempotent deduplication. Duplicate events (identified by platform-specific event IDs) are detected and discarded, preventing replay attacks and duplicate processing.

---

## 7. Code Execution Sandboxing

All code execution — whether triggered by agent tool calls, DevFlow build operations, or interactive commands — runs inside the Docker container. The sandboxing model provides:

- **No host filesystem escape.** Volume mounts are explicitly defined at container creation time. There are no bind mounts to sensitive host directories.
- **Passkey-gated access.** Code execution tools carry a HIGH risk classification, requiring passkey authentication or Trust Level 3+ authorization.
- **Process isolation.** Code execution runs in the container's process namespace, with no visibility into host processes.
- **Controlled resource limits.** Container resource constraints (CPU, memory) prevent code execution from consuming unbounded host resources.

---

## 8. Zero Bare Excepts Policy

The entire Mahoosuc OS codebase enforces a strict policy: **zero bare `except:` clauses**. Every exception handler uses explicit exception types (e.g., `except Exception:`, `except ValueError:`, `except OSError:`).

This matters because bare `except:` catches `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit` — exceptions that should almost never be caught in application code. Catching these silently can:

- Prevent clean process shutdown
- Mask critical failures
- Create zombie processes that consume resources without producing useful work
- Hide security-relevant errors from monitoring

The zero-bare-excepts policy is enforced codebase-wide, with **0 bare except clauses remaining** across the entire platform. This is verified as part of the code quality pipeline.

---

## Compliance Mapping

The following table maps Mahoosuc OS security controls to common compliance framework requirements. This mapping is provided as a reference for security evaluation and is not a certification claim.

| Security Control | SOC 2 (Trust Services Criteria) | HIPAA Security Rule | OWASP Top 10 (2021) |
|-----------------|-------------------------------|--------------------|--------------------|
| Passkey enforcement for high-risk tools | CC6.1 (Logical Access) | 164.312(d) Person or Entity Authentication | A07: Identification and Authentication Failures |
| Progressive Trust System (4 levels) | CC6.3 (Role-Based Access) | 164.312(a)(1) Access Control | A01: Broken Access Control |
| Fail-closed webhook verification (HMAC/Ed25519) | CC6.6 (System Boundaries) | 164.312(e)(1) Transmission Security | A02: Cryptographic Failures |
| AES-256-GCM encryption, no plaintext fallback | CC6.7 (Data-in-Transit/At-Rest) | 164.312(a)(2)(iv) Encryption and Decryption | A02: Cryptographic Failures |
| WireGuard VPN for remote access | CC6.6 (System Boundaries) | 164.312(e)(1) Transmission Security | A05: Security Misconfiguration |
| End-to-end request tracing (request_id) | CC7.2 (System Monitoring) | 164.312(b) Audit Controls | A09: Security Logging and Monitoring Failures |
| Tool execution telemetry | CC7.2 (System Monitoring) | 164.312(b) Audit Controls | A09: Security Logging and Monitoring Failures |
| Webhook idempotent dedup | CC7.1 (Anomaly Detection) | 164.306(a) Security Standards General | A08: Software and Data Integrity Failures |
| Agent iteration + timeout limits | CC7.5 (Incident Response) | 164.308(a)(6) Security Incident Procedures | A05: Security Misconfiguration |
| Docker container isolation | CC6.4 (Physical/Logical Access) | 164.310(c) Workstation Security | A05: Security Misconfiguration |
| Zero bare excepts policy | CC8.1 (Change Management) | 164.308(a)(8) Evaluation | A05: Security Misconfiguration |
| Dead-letter queue persistence | CC7.3 (Evaluation of Events) | 164.312(b) Audit Controls | A09: Security Logging and Monitoring Failures |
| SQLite WAL mode + busy_timeout | CC6.1 (Logical Access) | 164.312(c)(2) Integrity Controls | A08: Software and Data Integrity Failures |
| Token budget monitoring (30K+ warning) | CC7.2 (System Monitoring) | 164.308(a)(5) Security Awareness | A09: Security Logging and Monitoring Failures |
| Security gate in process_tools() | CC6.1 (Logical Access) | 164.312(a)(1) Access Control | A01: Broken Access Control |
| Kali Linux rolling security updates | CC7.1 (Anomaly Detection) | 164.308(a)(1) Security Management Process | A06: Vulnerable and Outdated Components |

---

*This document describes the security architecture of Mahoosuc OS as of March 2026. Security controls are subject to continuous improvement. For questions about specific controls or compliance requirements, contact the security team.*
