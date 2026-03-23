"""Result Synthesizer — combines multi-LLM subtask results into a unified response."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.parallel_executor import ExecutionResult


class ResultSynthesizer:
    """Combines results from multiple LLM providers into a coherent response."""

    def format_results_for_synthesis(self, results: list[ExecutionResult], original_prompt: str) -> str:
        """Build a synthesis prompt from execution results."""
        sections = [f"Original request: {original_prompt}\n"]

        for r in results:
            status_icon = "OK" if r.status == "completed" else "FAIL"
            sections.append(
                f"[{status_icon} {r.subtask_id} via {r.provider}/{r.model} ({r.latency_ms:.0f}ms)]:\n{r.result}"
            )

        sections.append(
            "\n---\nSynthesize these results into a single coherent response. "
            "Resolve any contradictions. Do not mention the subtask structure."
        )
        return "\n\n".join(sections)

    def build_execution_report(self, results: list[ExecutionResult]) -> dict:
        """Build a structured report of the execution."""
        total_latency = max((r.latency_ms for r in results), default=0)
        total_cost = sum(r.cost_cents for r in results)
        providers_used = list({r.provider for r in results})

        return {
            "subtasks": len(results),
            "completed": sum(1 for r in results if r.status == "completed"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "total_latency_ms": round(total_latency),
            "total_cost_cents": round(total_cost, 2),
            "providers_used": providers_used,
            "breakdown": [
                {
                    "id": r.subtask_id,
                    "provider": r.provider,
                    "model": r.model,
                    "status": r.status,
                    "latency_ms": round(r.latency_ms),
                }
                for r in results
            ],
        }
