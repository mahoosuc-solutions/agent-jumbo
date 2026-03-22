# Observability Patterns for AI Agent Systems

## Overview

AI agents are harder to observe than traditional software. They make non-deterministic decisions, consume variable resources, interact with external systems in unpredictable patterns, and can fail in subtle ways that look like success (hallucinated answers that seem plausible). This document covers the observability patterns needed to operate AI agents in production with confidence.

## The Three Pillars, Extended for AI

Traditional observability has three pillars: logs, metrics, and traces. AI agents add two more: **token economics** and **quality signals**.

```
Traditional              AI-Specific
-----------              -----------
Logs                     Token usage & cost
Metrics                  Quality/accuracy signals
Traces                   Decision audit trails
```

## 1. Request Tracing

Every agent session should produce a trace that captures the full execution flow: LLM calls, tool invocations, decision points, and results.

### Trace Structure

```python
@dataclass
class AgentTrace:
    trace_id: str
    session_id: str
    user_id: str
    started_at: datetime
    ended_at: datetime | None
    status: str  # "running", "completed", "failed", "timeout"
    spans: list[TraceSpan]
    total_tokens: int
    total_cost_usd: float
    tool_calls: int
    llm_calls: int

@dataclass
class TraceSpan:
    span_id: str
    parent_span_id: str | None
    operation: str      # "llm_call", "tool_call", "decision", "wait_human"
    started_at: datetime
    duration_ms: float
    attributes: dict    # Operation-specific data
    status: str
    error: str | None
```

### Instrumentation

```python
class TracedAgent:
    async def run(self, task: Task) -> Result:
        with self.tracer.start_span("agent_session") as session_span:
            session_span.set_attribute("task_type", task.type)
            session_span.set_attribute("user_id", task.user_id)

            while not task.is_complete():
                # Trace LLM call
                with self.tracer.start_span("llm_call") as llm_span:
                    response = await self.llm.complete(self.messages, tools=self.tools)
                    llm_span.set_attribute("model", response.model)
                    llm_span.set_attribute("input_tokens", response.usage.prompt_tokens)
                    llm_span.set_attribute("output_tokens", response.usage.completion_tokens)
                    llm_span.set_attribute("latency_ms", response.latency_ms)

                # Trace tool calls
                for tool_call in response.tool_calls:
                    with self.tracer.start_span("tool_call") as tool_span:
                        tool_span.set_attribute("tool_name", tool_call.name)
                        tool_span.set_attribute("args_hash", hash_args(tool_call.args))
                        result = await self.execute_tool(tool_call)
                        tool_span.set_attribute("result_size", len(str(result)))
                        tool_span.set_attribute("success", result.success)
```

### Trace Visualization

Agent traces are best visualized as flame charts showing the nesting and timing of operations:

```
[===== Agent Session (45s) =======================================]
  [== LLM Call #1 (3s) ==]
  [= Tool: search_kb (1.2s) =]
  [==== LLM Call #2 (4s) ====]
  [= Tool: get_customer (0.8s) =]
  [= Tool: update_record (0.5s) =]
  [====== LLM Call #3 (5s) ======]
  [= Tool: send_email (1.1s) =]
  [== LLM Call #4 (2s) ==]
```

## 2. Token Budget Monitoring

Token usage directly maps to cost. Monitor it like you monitor cloud spend.

### Real-Time Token Tracking

```python
class TokenBudgetMonitor:
    def __init__(self):
        self.metrics = MetricsClient()

    def record_usage(self, session_id: str, model: str, usage: TokenUsage):
        cost = self.calculate_cost(model, usage)

        self.metrics.gauge("agent.tokens.input", usage.prompt_tokens, tags={
            "model": model, "session": session_id,
        })
        self.metrics.gauge("agent.tokens.output", usage.completion_tokens, tags={
            "model": model, "session": session_id,
        })
        self.metrics.increment("agent.cost.usd", cost, tags={
            "model": model, "session": session_id,
        })

    def calculate_cost(self, model: str, usage: TokenUsage) -> float:
        prices = MODEL_PRICES[model]  # {"input": 0.003, "output": 0.015} per 1K
        return (
            (usage.prompt_tokens / 1000) * prices["input"]
            + (usage.completion_tokens / 1000) * prices["output"]
        )
```

### Budget Alerts

```python
BUDGET_ALERTS = {
    "session_warning": {
        "condition": lambda s: s.tokens_used > s.budget * 0.8,
        "action": "log_warning",
    },
    "session_limit": {
        "condition": lambda s: s.tokens_used >= s.budget,
        "action": "stop_agent",
    },
    "daily_tenant_warning": {
        "condition": lambda t: t.daily_tokens > t.daily_limit * 0.9,
        "action": "notify_admin",
    },
    "monthly_spike": {
        "condition": lambda t: t.daily_tokens > t.avg_daily * 3,
        "action": "alert_oncall",
    },
}
```

### Cost Dashboard Metrics

| Metric | Aggregation | Alert Threshold |
|--------|-------------|-----------------|
| Cost per session | P50, P95, P99 | P95 > $2.00 |
| Cost per tenant per day | Sum | > 120% of forecast |
| Input/output token ratio | Average | > 10:1 (possible prompt bloat) |
| Cache hit rate | Percentage | < 30% (caching may be broken) |
| Cost per successful resolution | Average | > $1.50 |

## 3. Tool Execution Metrics

Track tool reliability and performance to catch degradation early.

```python
class ToolMetrics:
    def record(self, tool_name: str, duration_ms: float, success: bool, error: str = None):
        self.metrics.histogram("tool.duration_ms", duration_ms, tags={"tool": tool_name})
        self.metrics.increment("tool.calls", tags={"tool": tool_name, "success": str(success)})

        if not success:
            self.metrics.increment("tool.errors", tags={
                "tool": tool_name,
                "error_type": error or "unknown",
            })
```

### Key Tool Metrics

| Metric | What It Tells You |
|--------|------------------|
| Call rate per tool | Which tools agents rely on most |
| Error rate per tool | Which integrations are unreliable |
| P95 latency per tool | Which tools are slow (and slow down agents) |
| Retry rate per tool | Which tools need better error handling |
| Calls per session | Whether agents are over-using certain tools |

## 4. Health Checks

### Agent System Health

```python
class AgentHealthCheck:
    async def check(self) -> HealthStatus:
        checks = {
            "llm_provider": self.check_llm(),
            "tool_servers": self.check_tools(),
            "queue": self.check_queue(),
            "database": self.check_database(),
            "token_budget_service": self.check_budget(),
        }

        results = await asyncio.gather(*checks.values(), return_exceptions=True)
        status = {}
        for name, result in zip(checks.keys(), results):
            if isinstance(result, Exception):
                status[name] = HealthResult(healthy=False, error=str(result))
            else:
                status[name] = result

        overall = all(s.healthy for s in status.values())
        return HealthStatus(healthy=overall, components=status)

    async def check_llm(self) -> HealthResult:
        """Verify LLM provider is responding."""
        try:
            start = time.monotonic()
            response = await self.llm.complete(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            latency = (time.monotonic() - start) * 1000
            return HealthResult(healthy=True, latency_ms=latency)
        except Exception as e:
            return HealthResult(healthy=False, error=str(e))
```

### Canary Queries

Run synthetic agent tasks periodically to detect issues before users do.

```python
class CanaryMonitor:
    CANARY_TASKS = [
        CanaryTask(
            name="basic_query",
            input="What is 2 + 2?",
            expected_contains="4",
            timeout=timedelta(seconds=30),
        ),
        CanaryTask(
            name="tool_usage",
            input="Look up customer ID CANARY-001",
            expected_tool_calls=["get_customer"],
            timeout=timedelta(seconds=60),
        ),
    ]

    async def run_canaries(self):
        for task in self.CANARY_TASKS:
            result = await self.execute_canary(task)
            self.metrics.gauge("canary.success", 1 if result.passed else 0, tags={
                "canary": task.name,
            })
            self.metrics.histogram("canary.latency_ms", result.latency_ms, tags={
                "canary": task.name,
            })
```

## 5. Dead Letter Monitoring

Failed agent tasks should not disappear. Route them to a dead letter queue for investigation.

```python
class DeadLetterMonitor:
    async def process_dead_letters(self):
        while True:
            dead = await self.dlq.dequeue(batch_size=10)
            for item in dead:
                # Classify the failure
                failure_type = self.classify_failure(item.error)
                self.metrics.increment("dlq.items", tags={"type": failure_type})

                # Auto-retry transient failures
                if failure_type == "transient" and item.retry_count < 3:
                    await self.task_queue.reenqueue(item, delay=timedelta(minutes=5))
                # Alert on persistent failures
                elif failure_type == "persistent":
                    await self.alert(f"Persistent failure: {item.task_id}: {item.error}")
                # Log and archive
                else:
                    await self.archive(item)

            await asyncio.sleep(30)
```

### Dead Letter Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| DLQ depth | > 50 items |
| DLQ growth rate | > 10 items/hour |
| Failure type distribution | Any single type > 80% of failures |
| Time in DLQ | > 4 hours without processing |

## 6. Quality Signals

AI-specific: track whether agent outputs are actually good, not just whether the system is running.

```python
class QualityMetrics:
    def record_session_quality(self, session: AgentSession):
        # Task completion rate
        self.metrics.increment("quality.tasks", tags={
            "completed": str(session.task_completed),
        })

        # User satisfaction (if available)
        if session.csat_score is not None:
            self.metrics.histogram("quality.csat", session.csat_score)

        # Tool call efficiency
        useful_calls = session.tool_calls - session.redundant_tool_calls
        efficiency = useful_calls / max(session.tool_calls, 1)
        self.metrics.histogram("quality.tool_efficiency", efficiency)

        # Turns to resolution
        self.metrics.histogram("quality.turns_to_resolve", session.turn_count, tags={
            "task_type": session.task_type,
        })
```

## Agent Jumbo Observability

Agent Jumbo implements these patterns through:

- **Structured event logging**: Every agent action emits a structured JSON event to the event log, enabling trace reconstruction and audit analysis
- **Token budget tracking**: Per-session and per-tenant budgets with real-time enforcement and alerting
- **Tool execution metrics**: MCP server calls are instrumented with latency, error rate, and retry tracking
- **Health checks**: The scheduler runs periodic health probes against LLM providers and tool servers
- **Dead letter queue**: Failed workflow steps route to the DLQ with automatic retry for transient errors and alerting for persistent failures

## Observability Maturity Model

| Level | Capabilities |
|-------|-------------|
| **L1: Basic** | Structured logging, error tracking, uptime monitoring |
| **L2: Operational** | Request tracing, token cost tracking, tool metrics, health checks |
| **L3: Proactive** | Canary queries, anomaly detection, quality metrics, DLQ monitoring |
| **L4: Predictive** | Cost forecasting, capacity planning, quality trend analysis, auto-scaling |

Start at L1. Most teams should target L2-L3 within the first quarter of production operation.
