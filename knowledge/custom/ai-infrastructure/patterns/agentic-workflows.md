# Agentic Workflow Patterns

## Overview

Agentic workflows are long-running, multi-step processes driven by AI agents. Unlike simple request-response interactions, these workflows must survive process crashes, handle retries gracefully, maintain state across steps, and deal with operations that take minutes or hours. This document covers the patterns that make agentic workflows production-ready.

## Durable Execution

The fundamental challenge: an agent is midway through a 10-step workflow when the process crashes. Durable execution ensures the workflow can resume from the last completed step rather than starting over.

### Event Sourcing for Agent State

Store every state transition as an immutable event. The current state is derived by replaying events.

```python
@dataclass
class WorkflowEvent:
    workflow_id: str
    sequence: int
    timestamp: datetime
    event_type: str  # "step_started", "step_completed", "step_failed", "input_received"
    step_id: str
    data: dict

class DurableWorkflow:
    def __init__(self, workflow_id: str, event_store: EventStore):
        self.workflow_id = workflow_id
        self.store = event_store
        self.completed_steps: set[str] = set()

    async def recover(self):
        """Rebuild state from stored events."""
        events = await self.store.get_events(self.workflow_id)
        for event in events:
            if event.event_type == "step_completed":
                self.completed_steps.add(event.step_id)

    async def execute_step(self, step: WorkflowStep) -> StepResult:
        # Skip already-completed steps on recovery
        if step.id in self.completed_steps:
            return await self.store.get_step_result(self.workflow_id, step.id)

        await self.store.append(WorkflowEvent(
            workflow_id=self.workflow_id,
            event_type="step_started",
            step_id=step.id,
            data={"input": step.input},
        ))

        result = await step.execute()

        await self.store.append(WorkflowEvent(
            workflow_id=self.workflow_id,
            event_type="step_completed",
            step_id=step.id,
            data={"output": result.to_dict()},
        ))
        self.completed_steps.add(step.id)
        return result
```

### Checkpoint-Based Recovery

Simpler than full event sourcing. Serialize the entire workflow state at defined checkpoints.

```python
class CheckpointedWorkflow:
    async def run(self, steps: list[WorkflowStep]):
        # Try to resume from checkpoint
        checkpoint = await self.load_checkpoint()
        start_index = checkpoint.last_completed_step + 1 if checkpoint else 0

        for i, step in enumerate(steps[start_index:], start=start_index):
            result = await self.execute_with_retry(step)
            await self.save_checkpoint(CheckpointData(
                last_completed_step=i,
                accumulated_results=self.results,
                agent_context=self.context.serialize(),
            ))
        return self.finalize()
```

## Step-Based Workflow Design

### Defining Steps

Each step should be a self-contained unit with clear inputs, outputs, and failure modes.

```python
@dataclass
class WorkflowStep:
    id: str
    name: str
    handler: Callable
    input_schema: dict
    output_schema: dict
    retry_policy: RetryPolicy
    timeout: timedelta
    idempotency_key: str | None = None
    requires_approval: bool = False
    rollback_handler: Callable | None = None

class RetryPolicy:
    max_attempts: int = 3
    backoff: str = "exponential"  # "fixed", "exponential", "linear"
    base_delay: float = 1.0
    max_delay: float = 60.0
    retryable_errors: list[str] = field(default_factory=lambda: [
        "timeout", "rate_limited", "transient_error"
    ])
```

### Step Dependencies

Model step dependencies as a DAG (directed acyclic graph) to enable parallel execution of independent steps.

```python
class WorkflowDAG:
    def __init__(self):
        self.steps: dict[str, WorkflowStep] = {}
        self.dependencies: dict[str, set[str]] = {}  # step_id -> set of dependency step_ids

    def add_step(self, step: WorkflowStep, depends_on: list[str] = None):
        self.steps[step.id] = step
        self.dependencies[step.id] = set(depends_on or [])

    async def execute(self):
        completed: dict[str, StepResult] = {}
        while len(completed) < len(self.steps):
            # Find steps whose dependencies are all met
            ready = [
                sid for sid, deps in self.dependencies.items()
                if sid not in completed and deps.issubset(completed.keys())
            ]
            # Execute ready steps in parallel
            results = await asyncio.gather(*[
                self.run_step(self.steps[sid], completed) for sid in ready
            ])
            for sid, result in zip(ready, results):
                completed[sid] = result
        return completed
```

## Idempotency

Agent workflows must be idempotent: running the same step twice with the same input produces the same result without side effects. This is critical for safe retries.

### Idempotency Key Pattern

```python
class IdempotentExecutor:
    def __init__(self, result_store: ResultStore):
        self.store = result_store

    async def execute(self, step: WorkflowStep, input_data: dict) -> StepResult:
        # Generate deterministic key from step ID + input
        idem_key = self.compute_key(step.id, input_data)

        # Check if already executed
        existing = await self.store.get(idem_key)
        if existing is not None:
            return existing

        # Execute and store result atomically
        result = await step.handler(input_data)
        await self.store.put(idem_key, result, ttl=timedelta(hours=24))
        return result

    def compute_key(self, step_id: str, input_data: dict) -> str:
        content = json.dumps({"step": step_id, "input": input_data}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
```

### Making LLM Calls Idempotent

LLM calls are inherently non-deterministic. For idempotency, cache the first successful response and return it on retry.

```python
class CachedLLMCall:
    async def complete(self, prompt: str, cache_key: str) -> str:
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        response = await self.llm.complete(prompt, temperature=0)
        await self.cache.set(cache_key, response, ttl=3600)
        return response
```

## Retry Semantics

```python
async def execute_with_retry(step: WorkflowStep, input_data: dict) -> StepResult:
    policy = step.retry_policy
    last_error = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await asyncio.wait_for(
                step.handler(input_data),
                timeout=step.timeout.total_seconds(),
            )
        except RetryableError as e:
            last_error = e
            if attempt < policy.max_attempts:
                delay = compute_backoff(attempt, policy)
                logger.warning(f"Step {step.id} failed (attempt {attempt}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Step {step.id} exhausted retries after {attempt} attempts")

    raise StepFailedError(step.id, last_error)

def compute_backoff(attempt: int, policy: RetryPolicy) -> float:
    if policy.backoff == "exponential":
        delay = policy.base_delay * (2 ** (attempt - 1))
    elif policy.backoff == "linear":
        delay = policy.base_delay * attempt
    else:
        delay = policy.base_delay
    # Add jitter to prevent thundering herd
    delay *= (0.5 + random.random())
    return min(delay, policy.max_delay)
```

## Compensation and Rollback

When a workflow fails midway, previously completed steps may need to be undone. The saga pattern handles this.

```python
class SagaWorkflow:
    async def execute(self, steps: list[WorkflowStep]) -> dict:
        completed: list[tuple[WorkflowStep, StepResult]] = []

        try:
            for step in steps:
                result = await self.execute_with_retry(step)
                completed.append((step, result))
            return {s.id: r for s, r in completed}
        except StepFailedError as e:
            # Compensate in reverse order
            logger.error(f"Workflow failed at step {e.step_id}, compensating...")
            for step, result in reversed(completed):
                if step.rollback_handler:
                    try:
                        await step.rollback_handler(result)
                    except Exception as rollback_error:
                        logger.critical(
                            f"Rollback failed for step {step.id}: {rollback_error}. "
                            "Manual intervention required."
                        )
            raise
```

## Long-Running Workflow Patterns

### Heartbeat Pattern

For steps that take minutes or hours, use heartbeats to detect stuck workflows.

```python
class HeartbeatMonitor:
    def __init__(self, timeout: timedelta = timedelta(minutes=5)):
        self.timeout = timeout
        self.last_heartbeat: dict[str, datetime] = {}

    async def heartbeat(self, workflow_id: str):
        self.last_heartbeat[workflow_id] = datetime.utcnow()

    async def check_stale(self) -> list[str]:
        now = datetime.utcnow()
        stale = []
        for wf_id, last in self.last_heartbeat.items():
            if now - last > self.timeout:
                stale.append(wf_id)
        return stale
```

### Pause and Resume

Workflows that require external input (human approval, external system callback) need to pause cleanly and resume when the input arrives.

```python
class PausableWorkflow:
    async def execute(self, steps: list[WorkflowStep]):
        for step in steps:
            if step.requires_approval:
                await self.save_state()
                approval = await self.request_approval(step)
                if not approval.granted:
                    return WorkflowResult(status="rejected", step=step.id)

            result = await step.handler(self.context)
            self.context.add_result(step.id, result)
```

## Workflow Observability

Every workflow should emit structured events for monitoring:

```python
class WorkflowTelemetry:
    def emit(self, event: str, workflow_id: str, step_id: str, **kwargs):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_id": workflow_id,
            "step_id": step_id,
            "event": event,
            **kwargs,
        }
        self.logger.info(json.dumps(log_entry))
        self.metrics.increment(f"workflow.{event}", tags={
            "step": step_id,
            "workflow_type": kwargs.get("workflow_type", "unknown"),
        })
```

Key metrics to track:
- **Workflow completion rate**: percentage of workflows that finish successfully
- **Step failure rate**: which steps fail most often
- **End-to-end latency**: total time from start to completion
- **Retry frequency**: how often steps need retries (indicator of upstream instability)
- **Recovery success rate**: how often crashed workflows resume successfully

## Anti-Patterns

1. **Storing state only in memory**: One process restart and all in-flight workflows are lost. Always persist state externally.

2. **Non-idempotent side effects**: Sending an email on every retry creates duplicate messages. Use idempotency keys for all external side effects.

3. **Unbounded retries**: Retrying forever on a permanently broken step wastes resources and can cascade failures. Always have a max retry count with dead-letter routing.

4. **Monolithic steps**: A single step that "does everything" cannot be partially retried. Break complex operations into smaller, independently retryable steps.

5. **Ignoring partial completion**: If step 3 of 5 fails, the workflow should know exactly what was completed and what was not, enabling targeted recovery rather than full restart.
