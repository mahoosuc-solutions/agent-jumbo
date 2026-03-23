"""Shared Context Store — serializes context for multi-LLM subtask dispatch.

When the coordinator dispatches subtasks to different LLM providers, each
provider has a different context window limit. This module builds a
minimal-but-sufficient context package for each subtask, respecting the
target model's window size.

Context priority (highest first):
1. Subtask prompt (always included)
2. Project context (active project files, structure)
3. Dependency results (outputs from completed subtasks)
4. Conversation summary (compressed recent history)
5. Memory recalls (relevant memories)
6. System instructions (coordinator role)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default chars-per-token ratio for prose (used as fallback)
CHARS_PER_TOKEN = 4

# Default context budgets per provider (in tokens)
PROVIDER_CONTEXT_LIMITS = {
    "anthropic": 200_000,  # Claude: 200K
    "google": 1_000_000,  # Gemini 1.5 Pro: 1M, Flash: 1M
    "openai": 128_000,  # GPT-4o: 128K
    "ollama": 32_000,  # Qwen 2.5 7B: 32K context
}

# Reserve tokens for the model's response
RESPONSE_RESERVE_RATIO = 0.25  # 25% of window for output


@dataclass
class ContextBudget:
    """Token budget allocation for a subtask's context."""

    total_tokens: int
    prompt_tokens: int = 0
    project_tokens: int = 0
    dependency_tokens: int = 0
    history_tokens: int = 0
    memory_tokens: int = 0
    system_tokens: int = 0
    remaining: int = 0

    def __post_init__(self):
        self.remaining = self.total_tokens


@dataclass
class ContextPackage:
    """Serialized context for a single subtask dispatch."""

    subtask_id: str
    provider: str
    model: str | None
    budget: ContextBudget
    system_prompt: str = ""
    prompt: str = ""
    project_context: str = ""
    dependency_context: str = ""
    history_summary: str = ""
    memory_context: str = ""

    def to_messages(self) -> list[dict]:
        """Convert to LLM message format."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # Build user content with all context sections
        parts = []
        if self.project_context:
            parts.append(f"[Project Context]\n{self.project_context}")
        if self.dependency_context:
            parts.append(f"[Previous Results]\n{self.dependency_context}")
        if self.history_summary:
            parts.append(f"[Conversation Context]\n{self.history_summary}")
        if self.memory_context:
            parts.append(f"[Relevant Knowledge]\n{self.memory_context}")
        parts.append(self.prompt)

        messages.append({"role": "user", "content": "\n\n".join(parts)})
        return messages

    @property
    def total_chars(self) -> int:
        return sum(
            len(s)
            for s in [
                self.system_prompt,
                self.prompt,
                self.project_context,
                self.dependency_context,
                self.history_summary,
                self.memory_context,
            ]
        )

    @property
    def estimated_tokens(self) -> int:
        return self.total_chars // CHARS_PER_TOKEN


def _estimate_tokens(text: str) -> int:
    """Content-aware token estimation."""
    if not text:
        return 0
    # Detect content type and adjust ratio
    code_indicators = text.count("{") + text.count("}") + text.count("def ") + text.count("class ")
    json_indicators = text.count('":') + text.count('","')

    chars = len(text)
    if json_indicators > 5:
        return chars // 3  # JSON: ~3 chars/token
    if code_indicators > 5:
        return int(chars / 3.5)  # Code: ~3.5 chars/token
    return chars // 4  # Prose: ~4 chars/token


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget."""
    # Reserve 5 tokens for the truncation marker
    marker = "\n[...truncated]"
    effective_tokens = max(max_tokens - 5, 0)
    max_chars = effective_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    # Truncate at a sentence or newline boundary
    truncated = text[:max_chars]
    last_nl = truncated.rfind("\n")
    last_period = truncated.rfind(". ")
    cut_at = max(last_nl, last_period)
    if cut_at > max_chars * 0.5:
        truncated = truncated[: cut_at + 1]
    return truncated + marker


class SharedContextStore:
    """Builds context packages for multi-LLM subtask dispatch."""

    def __init__(
        self,
        project_context: str = "",
        conversation_history: str = "",
        memory_recalls: str = "",
        system_instructions: str = "",
    ):
        self.project_context = project_context
        self.conversation_history = conversation_history
        self.memory_recalls = memory_recalls
        self.system_instructions = system_instructions

    def build_context_package(
        self,
        subtask_id: str,
        prompt: str,
        provider: str,
        model: str | None = None,
        dependency_results: dict[str, str] | None = None,
        context_limit_override: int | None = None,
    ) -> ContextPackage:
        """Build a context package for a subtask, respecting the provider's window.

        Args:
            subtask_id: Unique subtask identifier
            prompt: The subtask's prompt
            provider: Target LLM provider (anthropic, google, openai, ollama)
            model: Optional specific model name
            dependency_results: Results from completed dependency subtasks
            context_limit_override: Override the provider's default context limit
        """
        # Determine total budget
        total_limit = context_limit_override or PROVIDER_CONTEXT_LIMITS.get(provider, 8000)
        usable_tokens = int(total_limit * (1 - RESPONSE_RESERVE_RATIO))
        budget = ContextBudget(total_tokens=usable_tokens)

        package = ContextPackage(
            subtask_id=subtask_id,
            provider=provider,
            model=model,
            budget=budget,
        )

        # 1. Prompt (always included, never truncated)
        package.prompt = prompt
        budget.prompt_tokens = _estimate_tokens(prompt)
        budget.remaining -= budget.prompt_tokens

        # 2. System instructions (high priority, small)
        if self.system_instructions and budget.remaining > 200:
            sys_tokens = min(_estimate_tokens(self.system_instructions), budget.remaining // 4)
            package.system_prompt = _truncate_to_tokens(self.system_instructions, sys_tokens)
            budget.system_tokens = _estimate_tokens(package.system_prompt)
            budget.remaining -= budget.system_tokens

        # 3. Dependency results (critical for synthesis tasks)
        if dependency_results and budget.remaining > 500:
            dep_parts = []
            dep_budget = min(budget.remaining // 2, 50_000)  # Up to half remaining, max 50K
            for dep_id, dep_result in dependency_results.items():
                dep_text = f"[{dep_id}]: {dep_result}"
                dep_parts.append(dep_text)
            dep_combined = "\n\n".join(dep_parts)
            package.dependency_context = _truncate_to_tokens(dep_combined, dep_budget)
            budget.dependency_tokens = _estimate_tokens(package.dependency_context)
            budget.remaining -= budget.dependency_tokens

        # 4. Project context (important for code tasks)
        if self.project_context and budget.remaining > 500:
            proj_budget = min(budget.remaining // 3, 20_000)  # Up to 1/3 remaining, max 20K
            package.project_context = _truncate_to_tokens(self.project_context, proj_budget)
            budget.project_tokens = _estimate_tokens(package.project_context)
            budget.remaining -= budget.project_tokens

        # 5. Conversation history (compressed summary)
        if self.conversation_history and budget.remaining > 300:
            hist_budget = min(budget.remaining // 2, 10_000)  # Up to half remaining, max 10K
            package.history_summary = _truncate_to_tokens(self.conversation_history, hist_budget)
            budget.history_tokens = _estimate_tokens(package.history_summary)
            budget.remaining -= budget.history_tokens

        # 6. Memory recalls (lowest priority)
        if self.memory_recalls and budget.remaining > 200:
            mem_budget = min(budget.remaining, 5_000)  # Whatever's left, max 5K
            package.memory_context = _truncate_to_tokens(self.memory_recalls, mem_budget)
            budget.memory_tokens = _estimate_tokens(package.memory_context)
            budget.remaining -= budget.memory_tokens

        logger.info(
            "Context package for %s (%s): %d tokens used of %d budget "
            "(prompt=%d, system=%d, deps=%d, project=%d, history=%d, memory=%d)",
            subtask_id,
            provider,
            package.estimated_tokens,
            usable_tokens,
            budget.prompt_tokens,
            budget.system_tokens,
            budget.dependency_tokens,
            budget.project_tokens,
            budget.history_tokens,
            budget.memory_tokens,
        )

        return package

    @classmethod
    def from_agent_context(cls, agent) -> SharedContextStore:
        """Build a SharedContextStore from the current agent's context.

        Extracts project context, conversation history summary, and
        memory recalls from the running agent.
        """
        project_context = ""
        conversation_history = ""
        memory_recalls = ""
        system_instructions = ""

        try:
            # Extract project context from agent data
            project_data = agent.data.get("project")
            if project_data:
                project_context = (
                    f"Active project: {project_data.get('title', 'Unknown')}\n"
                    f"Description: {project_data.get('description', '')}\n"
                )
                file_structure = project_data.get("file_structure", "")
                if file_structure:
                    project_context += f"Files:\n{file_structure}\n"
        except Exception:
            pass

        try:
            # Extract conversation summary from history
            history = agent.history
            if history:
                # Take last N messages and summarize
                recent = history[-10:] if len(history) > 10 else history
                summary_parts = []
                for msg in recent:
                    role = getattr(msg, "type", "unknown")
                    content = str(msg.content)[:200] if hasattr(msg, "content") else ""
                    if content:
                        summary_parts.append(f"[{role}]: {content}")
                conversation_history = "\n".join(summary_parts)
        except Exception:
            pass

        try:
            # Extract system prompt excerpt
            if hasattr(agent, "config") and agent.config:
                system_instructions = "You are Agent Jumbo, an AI assistant with tool access."
        except Exception:
            pass

        return cls(
            project_context=project_context,
            conversation_history=conversation_history,
            memory_recalls=memory_recalls,
            system_instructions=system_instructions,
        )
