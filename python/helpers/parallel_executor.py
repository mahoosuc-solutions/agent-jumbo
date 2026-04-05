"""Parallel Executor — runs subtasks concurrently across LLM providers."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from python.helpers.task_decomposer import SubTask, SubTaskType

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    subtask_id: str
    result: str
    provider: str
    model: str
    latency_ms: float
    cost_cents: float
    status: str  # completed, failed, timeout


class ParallelExecutor:
    """Executes subtasks concurrently, respecting DAG dependencies."""

    def __init__(self, timeout_seconds: int = 120):
        self.timeout = timeout_seconds
        self._results: dict[str, ExecutionResult] = {}

    async def execute(self, subtasks: list[SubTask], call_fn) -> list[ExecutionResult]:
        """Execute subtasks with dependency-aware concurrency.

        call_fn: async function(prompt, provider, model) -> str
        """
        # Clear instance results so reused executors don't leak prior state
        self._results = {}

        # Build dependency graph
        pending = {st.id: st for st in subtasks}
        completed: set[str] = set()
        results: list[ExecutionResult] = []

        while pending:
            # Find ready tasks (no unresolved dependencies)
            ready = [st for st in pending.values() if all(dep in completed for dep in st.dependencies)]

            if not ready:
                pending_ids = list(pending.keys())
                raise RuntimeError(
                    f"ParallelExecutor deadlock: {len(pending)} task(s) have unresolvable "
                    f"dependencies and cannot execute. Pending: {pending_ids}"
                )

            # Execute ready tasks concurrently
            tasks = [self._execute_one(st, call_fn) for st in ready]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for st, result in zip(ready, batch_results):
                if isinstance(result, Exception):
                    exec_result = ExecutionResult(
                        subtask_id=st.id,
                        result=str(result),
                        provider=st.recommended_provider,
                        model=st.recommended_model or "unknown",
                        latency_ms=0,
                        cost_cents=0,
                        status="failed",
                    )
                else:
                    exec_result = result

                results.append(exec_result)
                self._results[st.id] = exec_result
                completed.add(st.id)
                del pending[st.id]

                # Inject result into synthesis context
                st.result = exec_result.result
                st.status = exec_result.status

        return results

    async def _execute_one(self, subtask: SubTask, call_fn) -> ExecutionResult:
        """Execute a single subtask with timeout and metrics."""
        start = time.time()

        # Build prompt with dependency context
        prompt = subtask.prompt
        if subtask.dependencies and subtask.type == SubTaskType.SYNTHESIZE:
            context_parts = []
            for dep_id in subtask.dependencies:
                if dep_id in self._results:
                    dep = self._results[dep_id]
                    context_parts.append(f"[Result from {dep_id}]:\n{dep.result}")
            if context_parts:
                prompt = "\n\n".join(context_parts) + f"\n\n---\nTask: {subtask.prompt}"

        try:
            result = await asyncio.wait_for(
                call_fn(
                    prompt,
                    subtask.recommended_provider,
                    subtask.recommended_model,
                ),
                timeout=self.timeout,
            )
            latency = (time.time() - start) * 1000

            return ExecutionResult(
                subtask_id=subtask.id,
                result=result,
                provider=subtask.recommended_provider,
                model=subtask.recommended_model or "auto",
                latency_ms=latency,
                cost_cents=0,  # TODO: extract from LLM response metadata
                status="completed",
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                subtask_id=subtask.id,
                result=f"Timeout after {self.timeout}s",
                provider=subtask.recommended_provider,
                model=subtask.recommended_model or "auto",
                latency_ms=self.timeout * 1000,
                cost_cents=0,
                status="timeout",
            )
        except Exception as e:
            return ExecutionResult(
                subtask_id=subtask.id,
                result=str(e),
                provider=subtask.recommended_provider,
                model=subtask.recommended_model or "auto",
                latency_ms=(time.time() - start) * 1000,
                cost_cents=0,
                status="failed",
            )
