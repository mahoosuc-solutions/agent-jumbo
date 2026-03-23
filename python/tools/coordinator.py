"""
Coordinator Tool for Agent Jumbo
Multi-LLM task coordination: decompose, dispatch, classify, and monitor.
"""

import asyncio
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum

from python.helpers.tool import Response, Tool

# ---------------------------------------------------------------------------
# Task classification
# ---------------------------------------------------------------------------


class TaskType(Enum):
    CODE = "code"
    REASONING = "reasoning"
    CREATIVE = "creative"
    DATA = "data"
    VISION = "vision"
    SIMPLE = "simple"
    GENERAL = "general"


# Keyword heuristics for classification
_TYPE_KEYWORDS: dict[TaskType, list[str]] = {
    TaskType.CODE: [
        "code",
        "function",
        "class",
        "implement",
        "debug",
        "refactor",
        "python",
        "javascript",
        "typescript",
        "rust",
        "sql",
        "api",
        "endpoint",
        "test",
        "bug",
        "fix",
        "compile",
        "build",
    ],
    TaskType.REASONING: [
        "analyze",
        "compare",
        "evaluate",
        "reason",
        "logic",
        "proof",
        "explain why",
        "trade-off",
        "pros and cons",
        "architecture",
        "design decision",
        "strategy",
    ],
    TaskType.CREATIVE: [
        "write",
        "draft",
        "compose",
        "story",
        "poem",
        "blog",
        "email",
        "copy",
        "marketing",
        "describe",
        "narrative",
    ],
    TaskType.DATA: [
        "extract",
        "parse",
        "csv",
        "json",
        "table",
        "data",
        "summarize",
        "aggregate",
        "statistics",
        "report",
        "numbers",
    ],
    TaskType.VISION: [
        "image",
        "screenshot",
        "photo",
        "picture",
        "diagram",
        "chart",
        "visual",
        "ocr",
        "describe the image",
    ],
    TaskType.SIMPLE: [
        "hello",
        "hi",
        "thanks",
        "yes",
        "no",
        "ok",
        "what time",
        "date",
        "weather",
    ],
}

# Provider affinities per task type
_PROVIDER_AFFINITY: dict[TaskType, list[str]] = {
    TaskType.CODE: ["anthropic", "openai", "ollama"],
    TaskType.REASONING: ["anthropic", "openai", "google"],
    TaskType.CREATIVE: ["anthropic", "openai", "google"],
    TaskType.DATA: ["google", "openai", "anthropic"],
    TaskType.VISION: ["google", "anthropic", "openai"],
    TaskType.SIMPLE: ["ollama", "google", "openai"],
    TaskType.GENERAL: ["anthropic", "openai", "google"],
}


@dataclass
class ClassificationResult:
    task_type: TaskType
    confidence: float
    preferred_providers: list[str]
    reasoning: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["task_type"] = self.task_type.value
        return d


class TaskClassifier:
    """Classify prompts by task type using keyword heuristics."""

    def classify(self, prompt: str) -> ClassificationResult:
        prompt_lower = prompt.lower()
        scores: dict[TaskType, int] = dict.fromkeys(TaskType, 0)

        for task_type, keywords in _TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in prompt_lower:
                    scores[task_type] += 1

        best_type = max(scores, key=lambda t: scores[t])
        best_score = scores[best_type]

        if best_score == 0:
            best_type = TaskType.GENERAL

        total_keywords = sum(scores.values()) or 1
        confidence = min(best_score / max(total_keywords, 1) + 0.3, 1.0)

        return ClassificationResult(
            task_type=best_type,
            confidence=round(confidence, 2),
            preferred_providers=_PROVIDER_AFFINITY.get(best_type, ["anthropic"]),
            reasoning=f"Matched {best_score} keyword(s) for '{best_type.value}' type",
        )


# ---------------------------------------------------------------------------
# Task decomposition
# ---------------------------------------------------------------------------


@dataclass
class Subtask:
    id: str
    task_type: TaskType
    prompt: str
    provider: str
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["task_type"] = self.task_type.value
        return d


class TaskDecomposer:
    """Decompose a complex prompt into independent subtasks."""

    _SPLIT_PATTERNS = [
        r"(?:^|\n)\s*\d+[\.\)]\s+",  # numbered lists
        r"(?:^|\n)\s*[-*]\s+",  # bullet lists
        r"\.\s+(?:Also|Then|Next|Finally|Additionally|After that)",  # transition words
    ]

    def __init__(self):
        self.classifier = TaskClassifier()

    def decompose_simple(self, prompt: str) -> list[Subtask]:
        """Split prompt into subtasks using structural cues."""
        parts = self._split(prompt)
        subtasks: list[Subtask] = []

        for idx, part in enumerate(parts):
            part = part.strip()
            if not part or len(part) < 10:
                continue
            classification = self.classifier.classify(part)
            provider = classification.preferred_providers[0] if classification.preferred_providers else "anthropic"
            subtasks.append(
                Subtask(
                    id=f"sub_{idx}",
                    task_type=classification.task_type,
                    prompt=part,
                    provider=provider,
                )
            )

        # If nothing was split, treat the whole prompt as a single task
        if not subtasks:
            classification = self.classifier.classify(prompt)
            provider = classification.preferred_providers[0] if classification.preferred_providers else "anthropic"
            subtasks.append(
                Subtask(
                    id="sub_0",
                    task_type=classification.task_type,
                    prompt=prompt,
                    provider=provider,
                )
            )

        return subtasks

    # ------------------------------------------------------------------
    def _split(self, prompt: str) -> list[str]:
        """Try to split the prompt on structural boundaries."""
        for pattern in self._SPLIT_PATTERNS:
            parts = re.split(pattern, prompt)
            parts = [p.strip() for p in parts if p and p.strip()]
            if len(parts) > 1:
                return parts
        # Fallback: split on double-newline paragraphs
        paragraphs = [p.strip() for p in prompt.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            return paragraphs
        return [prompt]


# ---------------------------------------------------------------------------
# Parallel executor
# ---------------------------------------------------------------------------


@dataclass
class SubtaskResult:
    subtask_id: str
    provider: str
    result: str
    elapsed_ms: int
    success: bool
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ParallelExecutor:
    """Execute subtasks concurrently via a caller-supplied LLM function."""

    async def execute(
        self,
        subtasks: list[Subtask],
        call_fn,
        timeout: float = 120.0,
    ) -> list[SubtaskResult]:
        """Run all independent subtasks concurrently.

        Args:
            subtasks: List of Subtask objects.
            call_fn: async (prompt, provider, model) -> str
            timeout: Per-subtask timeout in seconds.
        """

        async def _run(st: Subtask) -> SubtaskResult:
            t0 = time.monotonic()
            try:
                result = await asyncio.wait_for(
                    call_fn(st.prompt, st.provider, None),
                    timeout=timeout,
                )
                elapsed = int((time.monotonic() - t0) * 1000)
                return SubtaskResult(
                    subtask_id=st.id,
                    provider=st.provider,
                    result=str(result),
                    elapsed_ms=elapsed,
                    success=True,
                )
            except Exception as e:
                elapsed = int((time.monotonic() - t0) * 1000)
                return SubtaskResult(
                    subtask_id=st.id,
                    provider=st.provider,
                    result="",
                    elapsed_ms=elapsed,
                    success=False,
                    error=str(e),
                )

        results = await asyncio.gather(*[_run(st) for st in subtasks])
        return list(results)


def _synthesize(subtask_results: list[SubtaskResult]) -> str:
    """Merge subtask results into a single coherent answer."""
    parts: list[str] = []
    for r in subtask_results:
        if r.success and r.result:
            parts.append(r.result.strip())
        elif r.error:
            parts.append(f"[Subtask {r.subtask_id} failed: {r.error}]")
    return "\n\n---\n\n".join(parts) if parts else "(no results)"


# ---------------------------------------------------------------------------
# Coordinator Tool
# ---------------------------------------------------------------------------


class Coordinator(Tool):
    """Multi-LLM task coordination tool.

    Decomposes complex tasks, dispatches to optimal providers,
    and synthesizes results.
    """

    def __init__(self, agent, name: str, method: str | None, args: dict, message: str, loop_data=None, **kwargs):
        super().__init__(agent, name, method, args, message, loop_data, **kwargs)
        self.classifier = TaskClassifier()
        self.decomposer = TaskDecomposer()
        self.executor = ParallelExecutor()

    async def execute(self, **kwargs):
        action = self.args.get("action", "").lower()
        action_map = {
            "decompose": self._decompose,
            "dispatch": self._dispatch,
            "provider_health": self._provider_health,
            "cost_report": self._cost_report,
            "classify": self._classify,
        }
        handler = action_map.get(action)
        if handler:
            return await handler()
        return Response(message=self._format_help(), break_loop=False)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _decompose(self) -> Response:
        """Decompose a prompt into subtasks and show the plan."""
        prompt = self.args.get("prompt", "")
        if not prompt:
            return Response(message="Missing `prompt` argument for decompose.", break_loop=False)

        subtasks = self.decomposer.decompose_simple(prompt)
        table = self._format_subtask_table(subtasks)
        return Response(message=f"**Task Decomposition Plan**\n\n{table}", break_loop=False)

    async def _dispatch(self) -> Response:
        """Decompose AND execute with parallel multi-LLM coordination."""
        prompt = self.args.get("prompt", "")
        if not prompt:
            return Response(message="Missing `prompt` argument for dispatch.", break_loop=False)

        subtasks = self.decomposer.decompose_simple(prompt)

        async def call_fn(sub_prompt: str, provider: str, model: str | None) -> str:
            from python.helpers.call_llm import call_llm

            # Use the agent's utility model for sub-calls
            llm = self.agent.config.utility_model.create_model()
            return await call_llm(
                system="You are a helpful assistant. Complete the following task concisely.",
                model=llm,
                message=sub_prompt,
            )

        results = await self.executor.execute(subtasks, call_fn)
        synthesized = _synthesize(results)

        # Build execution report
        report_lines = ["**Multi-LLM Execution Report**\n"]
        total_ms = 0
        success_count = 0
        for r in results:
            status = "OK" if r.success else "FAIL"
            report_lines.append(f"- `{r.subtask_id}` [{r.provider}] {status} ({r.elapsed_ms}ms)")
            total_ms += r.elapsed_ms
            if r.success:
                success_count += 1

        report_lines.append(f"\nCompleted {success_count}/{len(results)} subtasks in {total_ms}ms total\n")
        report_lines.append("---\n")
        report_lines.append("**Synthesized Result**\n")
        report_lines.append(synthesized)

        return Response(message="\n".join(report_lines), break_loop=False)

    async def _provider_health(self) -> Response:
        """Show provider health and availability."""
        try:
            from python.helpers.llm_router import get_router

            router = get_router()
            health = await router.health_check_models()
            models = router.db.get_models(available_only=False)

            lines = ["**LLM Provider Health**\n"]

            if health.get("healthy"):
                lines.append(f"Healthy: {', '.join(health['healthy'])}")
            if health.get("degraded"):
                lines.append(f"Degraded: {', '.join(health['degraded'])}")
            if health.get("unavailable"):
                lines.append(f"Unavailable: {', '.join(health['unavailable'])}")
            lines.append(f"Baseline available: {'Yes' if health.get('baseline_available') else 'No'}")

            if models:
                lines.append(f"\nRegistered models: {len(models)}")
                for m in models[:15]:
                    status = "available" if m.is_available else "offline"
                    lines.append(f"  - `{m.provider}/{m.name}` ({status}) ctx={m.context_length}")

            if health.get("recommendations"):
                lines.append("\nRecommendations:")
                for rec in health["recommendations"]:
                    lines.append(f"  - {rec}")

            return Response(message="\n".join(lines), break_loop=False)
        except Exception as e:
            return Response(
                message=f"**Provider Health** — Could not query router: {e}",
                break_loop=False,
            )

    async def _cost_report(self) -> Response:
        """Show token usage / cost breakdown from the router."""
        try:
            from python.helpers.llm_router import get_router

            router = get_router()
            stats = router.get_usage_stats(hours=24)

            lines = ["**LLM Cost Report (last 24 h)**\n"]
            lines.append(f"Total calls: {stats.get('totalCalls', 0)}")
            lines.append(f"Total cost:  ${stats.get('totalCost', 0):.4f}\n")

            by_model = stats.get("byModel", [])
            if by_model:
                lines.append("| Provider | Model | Calls | In Tokens | Out Tokens | Cost | Avg Latency |")
                lines.append("|----------|-------|------:|----------:|-----------:|-----:|------------:|")
                for row in by_model:
                    lines.append(
                        f"| {row['provider']} | {row['modelName']} | {row['callCount']} "
                        f"| {row['totalInputTokens'] or 0} | {row['totalOutputTokens'] or 0} "
                        f"| ${row['totalCost'] or 0:.4f} | {row['avgLatency'] or 0:.0f}ms |"
                    )
            else:
                lines.append("No usage data recorded yet.")

            return Response(message="\n".join(lines), break_loop=False)
        except Exception as e:
            return Response(
                message=f"**Cost Report** — Could not query router: {e}",
                break_loop=False,
            )

    async def _classify(self) -> Response:
        """Classify a prompt and show the result."""
        prompt = self.args.get("prompt", "")
        if not prompt:
            return Response(message="Missing `prompt` argument for classify.", break_loop=False)

        result = self.classifier.classify(prompt)

        lines = ["**Task Classification**\n"]
        lines.append(f"Type: `{result.task_type.value}`")
        lines.append(f"Confidence: {result.confidence:.0%}")
        lines.append(f"Preferred providers: {', '.join(result.preferred_providers)}")
        lines.append(f"Reasoning: {result.reasoning}")

        return Response(message="\n".join(lines), break_loop=False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_subtask_table(self, subtasks: list[Subtask]) -> str:
        lines = ["| ID | Type | Provider | Prompt Preview | Dependencies |"]
        lines.append("|-----|------|----------|----------------|--------------|")
        for st in subtasks:
            preview = st.prompt[:60].replace("\n", " ")
            if len(st.prompt) > 60:
                preview += "..."
            deps = ", ".join(st.dependencies) if st.dependencies else "-"
            lines.append(f"| {st.id} | {st.task_type.value} | {st.provider} | {preview} | {deps} |")
        return "\n".join(lines)

    def _format_help(self) -> str:
        return (
            "**Coordinator Tool — Multi-LLM Coordination**\n\n"
            "Available actions:\n"
            "- `decompose` — Preview how a task splits into subtasks (requires `prompt`)\n"
            "- `dispatch` — Decompose and execute with multi-LLM coordination (requires `prompt`)\n"
            "- `classify` — Classify a prompt by task type (requires `prompt`)\n"
            "- `provider_health` — Show LLM provider status and availability\n"
            "- `cost_report` — Show token usage and cost breakdown (last 24h)\n\n"
            'Example: `coordinator` with args `{"action": "classify", "prompt": "Write a Python function"}`'
        )
