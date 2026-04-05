# ADR: Complexity Classifier — Keyword-Based Task Tier Routing

## Status

Accepted

## Context

Multi-LLM orchestration requires routing each task to the right model. Using a flagship model
(claude-opus) for every task is expensive and slow; using a fast/cheap model for architecture
work produces poor results. A routing layer is needed that maps task descriptions to an
appropriate model tier without requiring the agent to explicitly specify the model.

The existing `TaskClassifier` in `task_decomposer.py` classifies tasks by *type* (code,
research, creative, etc.) but not by *complexity*. Complexity drives model cost/quality
trade-offs more than task type — a simple code lookup can use a local model; a complex
architecture design needs claude-opus.

## Decision

Implement `ComplexityClassifier` (`python/helpers/complexity_classifier.py`) with four tiers:

| Tier | Token Budget | Model | Trigger Keywords |
|------|-------------|-------|-----------------|
| SIMPLE | 500 | ollama/llama3.2 | what is, list, show, read |
| EASY | 2,000 | google/gemini-2.0-flash | add, fix, update, rename |
| MEDIUM | 8,000 | anthropic/claude-sonnet-4-6 | implement, refactor, integrate |
| HARD | 32,000 | anthropic/claude-opus-4-6 | architect, rewrite, migrate entire |

**Scoring algorithm:** Count keyword pattern matches per tier across all pattern groups.
The tier with the **highest match count wins** (not first-match). Confidence = winner's
matches / total matches. Default fallback: MEDIUM at 0.3 confidence (safest non-destructive choice).

**Why count-wins over first-match:** A task like "implement and architect a full system"
matches both MEDIUM and HARD. Count-wins picks HARD (more specific, higher stakes). First-match
would pick whichever tier's patterns were evaluated first, which is order-dependent and fragile.

## Consequences

**Positive:**

- Prevents over-spending flagship tokens on trivial tasks
- Single source of truth for tier → model mapping (`TIER_MODEL_MAP` constant)
- Easily testable (pure function, no side effects)
- Confidence score enables downstream uncertainty handling

**Negative / Trade-offs:**

- Keyword heuristics can be fooled — "fix an architect's workflow" would incorrectly hit HARD
- No semantic understanding — "small change to the entire authentication system" hits HARD (correct-ish) but "update one line in the migration script" hits EASY (correct)
- The model map is a constant, not runtime-configurable — changing providers requires code edit
- `task_cycle.py` records the tier but dispatches all subtasks through `utility_model` (the agent's configured model) due to `call_llm` API design; tier affects planning documentation but not actual model selection in the current implementation

## Alternatives Considered

- **LLM-based classification** — ask a small model to rate complexity. Rejected: adds latency and cost to every task; bootstrap problem (need a model to pick a model).
- **Token counting** — count tokens in the task description. Rejected: short tasks can be hard (e.g., "rewrite auth"), long tasks can be easy (e.g., a verbose description of a simple CRUD change).
- **Manual tier selection** — let the agent specify tier. Rejected: defeats the purpose; agents tend to overestimate complexity.

---

*Recorded 2026-04-05 — Agent Jumbo agentic task cycle implementation*
