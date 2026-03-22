# Agent Orchestration Patterns

## Overview

Agent orchestration determines how multiple AI agents coordinate to accomplish complex tasks. The choice of pattern affects reliability, latency, cost, and the complexity of failure handling. There is no single best pattern -- the right choice depends on task structure, latency requirements, and how much autonomy each agent needs.

## Pattern 1: Supervisor (Centralized Control)

A single supervisor agent receives the task, decomposes it, dispatches subtasks to worker agents, and synthesizes results. The supervisor holds all context and makes routing decisions.

```
Supervisor
  |-- Worker A (research)
  |-- Worker B (code generation)
  |-- Worker C (validation)
```

**When to use:**
- Tasks with clear decomposition into independent subtasks
- When a single agent needs full visibility to make routing decisions
- When you need deterministic control flow with clear accountability

**Implementation sketch (Python):**

```python
class Supervisor:
    def __init__(self, workers: dict[str, Worker]):
        self.workers = workers

    async def execute(self, task: Task) -> Result:
        plan = await self.plan(task)
        results = {}
        for step in plan.steps:
            worker = self.workers[step.worker_id]
            result = await worker.execute(step.subtask, context=results)
            results[step.id] = result
            if result.needs_replanning:
                plan = await self.replan(task, results)
        return self.synthesize(results)
```

**Pitfalls:**
- Supervisor becomes a bottleneck and single point of failure
- Context window pressure: the supervisor must track all worker outputs
- Over-planning: supervisors tend to create overly detailed plans that break when reality diverges

## Pattern 2: Swarm (Decentralized)

Agents operate as peers with shared state. Each agent picks up work, executes it, and publishes results to a shared context. No central coordinator.

**When to use:**
- Exploratory tasks where the work structure is not known upfront
- When agents have overlapping capabilities and can self-organize
- High availability requirements where no single point of failure is acceptable

**Implementation sketch:**

```python
class SwarmAgent:
    def __init__(self, shared_state: SharedState, capabilities: list[str]):
        self.state = shared_state
        self.capabilities = capabilities

    async def run(self):
        while not self.state.is_complete():
            task = await self.state.claim_next(self.capabilities)
            if task is None:
                await asyncio.sleep(0.1)
                continue
            result = await self.execute(task)
            await self.state.publish(task.id, result)
            # Agents can spawn new tasks
            for follow_up in result.follow_up_tasks:
                await self.state.enqueue(follow_up)
```

**Pitfalls:**
- Coordination overhead: shared state becomes a contention point
- Duplicate work: two agents may claim overlapping tasks
- Convergence: without a supervisor, it is hard to know when the swarm has "finished"
- Debugging is significantly harder -- trace every agent's decision path

## Pattern 3: Pipeline (Sequential)

Agents are arranged in a fixed sequence. Each agent's output feeds the next agent's input. Classic assembly line.

```
Intake --> Classify --> Extract --> Validate --> Route
```

**When to use:**
- Well-understood, repeatable processes (document processing, content moderation)
- When each stage has a clearly different skill requirement
- When you need predictable latency and throughput

**Pitfalls:**
- Rigid: adding or removing stages requires pipeline reconfiguration
- Error propagation: a bad output from stage 2 corrupts everything downstream
- Latency is the sum of all stages -- no parallelism

**Mitigation:** Add validation gates between stages. If stage N output fails validation, retry stage N or route to a human review queue rather than passing garbage downstream.

## Pattern 4: Fan-Out / Fan-In

A coordinator dispatches the same task (or related subtasks) to multiple agents in parallel, then aggregates results.

```
              /--> Agent A --\
Coordinator --+--> Agent B --+--> Aggregator
              \--> Agent C --/
```

**When to use:**
- Tasks that benefit from multiple perspectives (code review, research)
- When you want consensus or voting-based confidence
- Search problems where parallel exploration reduces time-to-answer

**Implementation sketch:**

```python
async def fan_out_fan_in(task: Task, agents: list[Agent]) -> Result:
    # Fan out
    coros = [agent.execute(task) for agent in agents]
    results = await asyncio.gather(*coros, return_exceptions=True)

    # Filter failures
    successes = [r for r in results if not isinstance(r, Exception)]
    if len(successes) < len(agents) // 2:
        raise InsufficientConsensusError()

    # Fan in: aggregate
    return aggregate(successes, strategy="majority_vote")
```

**Pitfalls:**
- Cost multiplier: N agents means N times the token spend
- Aggregation is hard: reconciling conflicting outputs requires its own logic
- Diminishing returns beyond 3-5 parallel agents for most tasks

## Pattern 5: Hierarchical (Multi-Level Supervision)

Supervisors manage sub-supervisors, which manage workers. Used for very large task decompositions.

```
Executive Supervisor
  |-- Team Lead A
  |     |-- Worker A1
  |     |-- Worker A2
  |-- Team Lead B
        |-- Worker B1
        |-- Worker B2
```

**When to use:**
- Enterprise-scale workflows with dozens of agents
- When different teams have different domain expertise
- When you need delegation with bounded context at each level

**Pitfalls:**
- Communication overhead grows with depth
- Context loss: information gets summarized (and potentially distorted) at each level
- Over-engineering for most use cases -- start with a flat supervisor first

## Choosing a Pattern

| Factor | Supervisor | Swarm | Pipeline | Fan-Out |
|--------|-----------|-------|----------|---------|
| Task structure known upfront | Required | Not required | Required | Partially |
| Latency sensitivity | Medium | Variable | High (sequential) | Low (parallel) |
| Failure isolation | Good | Poor | Good | Good |
| Cost predictability | High | Low | High | Medium |
| Debugging ease | High | Low | High | Medium |
| Scalability | Limited by supervisor | High | Limited by slowest stage | Linear cost |

## Anti-Patterns

1. **Agent sprawl**: Creating an agent for every small task. If a task can be handled by a tool call, it does not need its own agent.

2. **Premature orchestration**: Building multi-agent systems before validating that a single agent cannot handle the workload. Always start with one agent and split only when you hit concrete limits.

3. **Shared mutable state without coordination**: Multiple agents writing to the same data store without locks or versioning leads to race conditions and data corruption.

4. **Ignoring token economics**: A 5-agent fan-out with GPT-4 class models costs 5x. Budget for it or use smaller models for parallel exploration.

5. **No circuit breakers**: If a worker agent enters an infinite loop or hallucinates extensively, the supervisor must have a timeout and fallback strategy.

## Key Takeaway

Start simple. A single agent with good tools will outperform a poorly orchestrated multi-agent system. Add orchestration complexity only when you have evidence that a single agent cannot meet your requirements for quality, latency, or scope.
