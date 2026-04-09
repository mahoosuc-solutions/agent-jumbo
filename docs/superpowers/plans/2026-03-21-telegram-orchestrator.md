# Telegram Orchestrator — Full Agentic Platform Access via Telegram

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Telegram bot from a simple chat pipe into a full agentic workflow orchestrator that exposes Agent Mahoo's top 15 tools — portfolio, projects, workflows, Linear, knowledge, memory, vision, calendar, email, finance, diagrams, search, work queue, notifications, and digests — through natural conversation, with vision-powered context persistence and complete work product generation.

**Architecture:** The Telegram webhook handler (`python/api/telegram_webhook.py`) currently receives messages, creates an agent context, and sends back the LLM's text response. We enhance this by: (1) adding a Telegram-aware system prompt that teaches the agent about available orchestration tools, (2) building a `TelegramOrchestrator` layer that enriches context with vision analysis and persistent state, (3) adding structured output formatting that adapts rich tool responses for Telegram's Markdown constraints, and (4) creating a `/status` and `/help` command system for quick access. The existing tool infrastructure (`agent.get_tool()` at `agent.py:1516`) already supports all tools — the agent just needs the right system prompt and context to use them.

**Tech Stack:** Python 3.12, Flask (existing), LangChain (existing agent framework), Telegram Bot API, existing tool classes in `python/tools/`, existing prompt system in `prompts/`, Extension class pattern in `python/helpers/extension.py`

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `python/helpers/telegram_orchestrator.py` | Orchestration layer: slash commands, tool result formatting, context enrichment | Create |
| `python/api/telegram_webhook.py` | Webhook handler — delegates to orchestrator for commands and formatting | Modify |
| `python/helpers/telegram_bridge.py` | Add session metadata (last tool used, active project, vision context) | Modify |
| `python/helpers/telegram_client.py` | Add `chunk_message()` and `send_long_message()` for chunked responses | Modify |
| `prompts/agent.system.telegram_orchestrator.md` | System prompt teaching agent about Telegram orchestration tools | Create |
| `prompts/agent.system.tool.telegram_commands.md` | Telegram slash command reference for the agent | Create |
| `python/extensions/system_prompt/_85_telegram_orchestrator.py` | Extension that injects orchestrator prompt for Telegram contexts | Create |
| `tests/test_telegram_client_chunking.py` | Unit tests for message chunking | Create |
| `tests/test_telegram_bridge_session.py` | Unit tests for session metadata including vision context | Create |
| `tests/test_telegram_orchestrator.py` | Unit tests for orchestrator logic | Create |
| `tests/test_telegram_orchestration_e2e.py` | Integration tests for full orchestration flow | Create |

---

## Task 1: Message Chunking for Telegram Client

Telegram limits messages to 4096 characters. Tool responses (dashboards, lists, analyses) regularly exceed this.

**Files:**

- Modify: `python/helpers/telegram_client.py`
- Test: `tests/test_telegram_client_chunking.py`

- [ ] **Step 1: Write failing tests for message chunking**

```python
# tests/test_telegram_client_chunking.py
"""Tests for Telegram message chunking."""

from python.helpers.telegram_client import chunk_message, MAX_TELEGRAM_LENGTH


class TestChunkMessage:
    def test_short_message_returns_single_chunk(self):
        msg = "Hello, world!"
        chunks = chunk_message(msg)
        assert chunks == ["Hello, world!"]

    def test_empty_message_returns_empty_list(self):
        assert chunk_message("") == []

    def test_long_message_splits_at_newlines(self):
        line = "x" * 100 + "\n"
        msg = line * 50  # 5050 chars > 4096
        chunks = chunk_message(msg)
        assert len(chunks) >= 2
        assert all(len(c) <= MAX_TELEGRAM_LENGTH for c in chunks)

    def test_preserves_markdown_code_blocks(self):
        code = "```\n" + "a" * 200 + "\n```"
        msg = "Before\n" + code + "\n" + "x" * 4000
        chunks = chunk_message(msg)
        assert "```" in chunks[0]
        block_count = chunks[0].count("```")
        assert block_count % 2 == 0  # balanced fences

    def test_single_line_exceeding_limit_force_splits(self):
        msg = "x" * 5000  # no newlines
        chunks = chunk_message(msg)
        assert len(chunks) >= 2
        assert all(len(c) <= MAX_TELEGRAM_LENGTH for c in chunks)
        assert "".join(chunks) == msg

    def test_chunk_numbering_when_multiple(self):
        msg = ("line\n") * 2000  # well over limit
        chunks = chunk_message(msg, add_part_numbers=True)
        assert len(chunks) > 1
        assert chunks[0].endswith("(1/" + str(len(chunks)) + ")")

    def test_no_numbering_for_single_chunk(self):
        msg = "short message"
        chunks = chunk_message(msg, add_part_numbers=True)
        assert len(chunks) == 1
        assert "(1/1)" not in chunks[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_client_chunking.py -v`
Expected: FAIL — `chunk_message` and `MAX_TELEGRAM_LENGTH` don't exist yet

- [ ] **Step 3: Implement chunk_message in telegram_client.py**

Add at the top of `python/helpers/telegram_client.py` (after the existing imports):

```python
MAX_TELEGRAM_LENGTH = 4096


def chunk_message(text: str, max_len: int = MAX_TELEGRAM_LENGTH, add_part_numbers: bool = False) -> list[str]:
    """Split text into Telegram-safe chunks, preferring newline boundaries."""
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break

        # Find best split point: last newline within limit
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at <= 0:
            split_at = max_len

        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")

    if add_part_numbers and len(chunks) > 1:
        total = len(chunks)
        chunks = [f"{c}\n({i+1}/{total})" for i, c in enumerate(chunks)]

    return chunks


def send_long_message(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> list[dict[str, Any]]:
    """Send a message, automatically chunking if it exceeds Telegram's limit."""
    chunks = chunk_message(text, add_part_numbers=True)
    results = []
    for chunk in chunks:
        results.append(send_message(token, chat_id, chunk, parse_mode))
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_client_chunking.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add python/helpers/telegram_client.py tests/test_telegram_client_chunking.py
git commit -m "feat(telegram): add message chunking for long tool responses"
```

---

## Task 2: Enhanced Session State in telegram_bridge.py

The bridge currently tracks `chat_contexts` and `last_update`. For orchestration, we need session metadata: active project, last tool used, and vision context from images.

**Files:**

- Modify: `python/helpers/telegram_bridge.py`
- Test: `tests/test_telegram_bridge_session.py`

- [ ] **Step 1: Write failing tests for session metadata (including vision context)**

```python
# tests/test_telegram_bridge_session.py
"""Tests for enhanced Telegram session state."""

from unittest.mock import patch
from python.helpers.telegram_bridge import (
    get_session_meta,
    set_session_meta,
    clear_session_meta,
)


@pytest.fixture(autouse=True)
def mock_state(tmp_path):
    state_file = tmp_path / "telegram_state.json"
    state_file.write_text("{}")
    with patch("python.helpers.telegram_bridge.STATE_PATH", state_file):
        yield state_file


import pytest


class TestSessionMeta:
    def test_set_and_get_meta(self):
        set_session_meta("chat123", "active_project", "agent-mahoo")
        assert get_session_meta("chat123", "active_project") == "agent-mahoo"

    def test_get_missing_key_returns_none(self):
        assert get_session_meta("chat123", "nonexistent") is None

    def test_clear_session_meta(self):
        set_session_meta("chat123", "last_tool", "portfolio")
        clear_session_meta("chat123")
        assert get_session_meta("chat123", "last_tool") is None

    def test_multiple_keys_per_chat(self):
        set_session_meta("chat123", "active_project", "proj-a")
        set_session_meta("chat123", "last_tool", "workflow_engine")
        assert get_session_meta("chat123", "active_project") == "proj-a"
        assert get_session_meta("chat123", "last_tool") == "workflow_engine"

    def test_vision_context_stored(self):
        set_session_meta("chat123", "vision_context", {
            "description": "A kanban board showing 3 columns",
            "extracted_items": ["task-1", "task-2"],
        })
        ctx = get_session_meta("chat123", "vision_context")
        assert ctx["description"] == "A kanban board showing 3 columns"
        assert len(ctx["extracted_items"]) == 2

    def test_vision_context_overwrites_on_new_image(self):
        set_session_meta("chat123", "vision_context", {"description": "Old image"})
        set_session_meta("chat123", "vision_context", {"description": "New image"})
        stored = get_session_meta("chat123", "vision_context")
        assert stored["description"] == "New image"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_bridge_session.py -v`
Expected: FAIL — functions don't exist

- [ ] **Step 3: Implement session metadata functions**

Add to the end of `python/helpers/telegram_bridge.py`:

```python
def get_session_meta(chat_id: str, key: str) -> Any:
    """Get a session metadata value for a chat."""
    state = load_state()
    return state.get("session_meta", {}).get(chat_id, {}).get(key)


def set_session_meta(chat_id: str, key: str, value: Any) -> None:
    """Set a session metadata value for a chat."""
    state = load_state()
    meta = state.setdefault("session_meta", {}).setdefault(chat_id, {})
    meta[key] = value
    save_state(state)


def clear_session_meta(chat_id: str) -> None:
    """Clear all session metadata for a chat."""
    state = load_state()
    state.get("session_meta", {}).pop(chat_id, None)
    save_state(state)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_bridge_session.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add python/helpers/telegram_bridge.py tests/test_telegram_bridge_session.py
git commit -m "feat(telegram): add session metadata for orchestration state"
```

---

## Task 3: Telegram Orchestrator System Prompt

The key prompt that teaches the agent how to orchestrate tools when responding to Telegram messages.

**Files:**

- Create: `prompts/agent.system.telegram_orchestrator.md`

- [ ] **Step 1: Create the orchestrator system prompt**

Create `prompts/agent.system.telegram_orchestrator.md` with this content:

```markdown
# Telegram Orchestrator Mode

You are Agent Mahoo responding via Telegram. You have full access to the platform's tools and should use them proactively to help the user manage their projects, workflows, and business operations.

## Available Tools (use by name in your tool calls)

### Project & Portfolio Management
- **portfolio_manager_tool**: Scan, list, analyze, search projects. Actions: `scan`, `list`, `get`, `add`, `update`, `analyze`, `export`, `search`, `pipeline`, `dashboard`, `create_product`, `pricing`
- **project_lifecycle**: Manage project phases (design/development/testing/validation). Actions: `get`, `upsert`, `set_phase`, `run_phase`, `list_phase_runs`

### Task & Workflow Management
- **workflow_engine**: Create and run structured workflows with stages and gates. Actions: `create_workflow`, `start_workflow`, `get_status`, `advance_stage`, `complete_task`, `list_workflows`
- **linear_integration**: Create/update/search Linear issues, sync pipeline. Actions: `create_issue`, `update_issue`, `search_issues`, `get_project_issues`, `sync_pipeline`, `get_dashboard`

### Knowledge & Memory
- **memory_save**: Save important information to long-term memory. Args: `text`, `area`
- **memory_load**: Recall information from memory. Args: `query`, `area`
- **knowledge_ingest**: Ingest knowledge from sources. Actions: `register_source`, `list_sources`, `ingest_source`, `ingest_text`

### Communication & Scheduling
- **calendar_hub**: Manage calendar events. Actions: `list_events`, `create_event`, `update_event`
- **email**: Send and manage emails
- **telegram_send**: Send messages to Telegram chats

### Analysis & Visualization
- **diagram_tool**: Generate Mermaid diagrams for architecture, flows, etc.
- **search_engine**: Search the web for information
- **digest_builder**: Build daily/weekly digest reports

### Business Operations
- **finance_manager**: Track revenue, expenses, invoicing
- **customer_lifecycle**: Manage customer relationships and lifecycle stages

## Response Formatting for Telegram

Telegram supports a limited Markdown subset. Follow these rules:
- Use **bold** for emphasis (surround with *)
- Use `code` for inline code (surround with `)
- Use ``` for code blocks
- Use bullet lists with - prefix
- Keep responses concise — Telegram is a mobile-first interface
- For complex outputs (dashboards, tables), summarize key metrics first, then offer "Want the full details?"
- When a tool produces a long result, extract the 3-5 most important points
- Never send raw JSON — always format for human readability

## Interaction Patterns

### When user sends an image:
1. The image has been processed by the vision system and its description is in the message context
2. Look for actionable items: tasks, project states, architecture decisions, bugs
3. Offer to persist extracted context: "I see [description]. Should I create tasks/update the project?"

### When user asks about a project:
1. Use `portfolio_manager_tool` with action `get` or `search` to find it
2. Use `project_lifecycle` to check its current phase
3. Summarize: name, phase, readiness, next actions

### When user wants to create work:
1. Create a Linear issue with `linear_integration` action `create_issue`
2. Optionally link to a workflow with `workflow_engine` action `create_workflow`
3. Update project lifecycle phase if relevant
4. Confirm what was created with links/IDs

### When user asks for a status update:
1. Check `portfolio_manager_tool` dashboard
2. Check `linear_integration` dashboard
3. Check `workflow_engine` for active workflows
4. Summarize: what's in progress, what's blocked, what's completed

## Slash Commands

Users may send these Telegram commands:
- `/new` or `/reset` — Reset conversation context (handled by webhook, not you)
- `/status` — Run a cross-system status check (portfolio + linear + workflows)
- `/project <name>` — Get project details and lifecycle
- `/tasks` — List active Linear issues
- `/help` — Show available commands

When you see these, execute the appropriate tool calls to fulfill the command.
```

- [ ] **Step 2: Verify the prompt file was created and contains expected tool names**

Run: `grep -c "portfolio_manager_tool\|workflow_engine\|linear_integration\|project_lifecycle\|memory_save\|calendar_hub\|diagram_tool\|finance_manager" /mnt/wdblack/dev/projects/agent-mahoo/prompts/agent.system.telegram_orchestrator.md`
Expected: 8 or more matches (all tool names present)

- [ ] **Step 3: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add prompts/agent.system.telegram_orchestrator.md
git commit -m "feat(telegram): add orchestrator system prompt with tool catalog"
```

---

## Task 4: Telegram Orchestrator Module

The core orchestration layer: slash command parsing, tool result formatting, and context enrichment.

**Files:**

- Create: `python/helpers/telegram_orchestrator.py`
- Test: `tests/test_telegram_orchestrator.py`

- [ ] **Step 1: Write failing tests for the orchestrator**

```python
# tests/test_telegram_orchestrator.py
"""Tests for TelegramOrchestrator."""

from python.helpers.telegram_orchestrator import (
    parse_slash_command,
    slash_command_to_prompt,
    format_for_telegram,
    build_orchestrator_context,
    HELP_TEXT,
)


class TestParseSlashCommand:
    def test_status_command(self):
        cmd, args = parse_slash_command("/status")
        assert cmd == "status"
        assert args == ""

    def test_project_command_with_name(self):
        cmd, args = parse_slash_command("/project agent-mahoo")
        assert cmd == "project"
        assert args == "agent-mahoo"

    def test_not_a_command(self):
        cmd, args = parse_slash_command("hello world")
        assert cmd is None
        assert args == "hello world"

    def test_help_command(self):
        cmd, args = parse_slash_command("/help")
        assert cmd == "help"

    def test_tasks_command(self):
        cmd, args = parse_slash_command("/tasks")
        assert cmd == "tasks"

    def test_unknown_command_passes_through(self):
        cmd, args = parse_slash_command("/unknown_cmd")
        assert cmd is None
        assert args == "/unknown_cmd"


class TestSlashCommandToPrompt:
    def test_status_mentions_portfolio_and_linear(self):
        prompt = slash_command_to_prompt("status", "")
        assert "portfolio" in prompt.lower()
        assert "linear" in prompt.lower()

    def test_project_includes_name(self):
        prompt = slash_command_to_prompt("project", "agent-mahoo")
        assert "agent-mahoo" in prompt

    def test_tasks_mentions_linear(self):
        prompt = slash_command_to_prompt("tasks", "")
        assert "linear" in prompt.lower()


class TestFormatForTelegram:
    def test_strips_html_tags(self):
        result = format_for_telegram("<b>bold</b> text")
        assert "<b>" not in result

    def test_truncates_long_tables(self):
        table = "| Col1 | Col2 |\n|------|------|\n"
        table += "| val | val |\n" * 50
        result = format_for_telegram(table)
        assert len(result) < len(table)

    def test_preserves_short_messages(self):
        msg = "Project updated successfully."
        assert format_for_telegram(msg) == msg

    def test_converts_markdown_headers_to_bold(self):
        msg = "## Portfolio Dashboard\n\nSome content"
        result = format_for_telegram(msg)
        assert "*Portfolio Dashboard*" in result


class TestBuildOrchestratorContext:
    def test_includes_vision_context(self):
        ctx = build_orchestrator_context(
            chat_id="123",
            vision_context={"description": "A kanban board with tasks"},
        )
        assert "kanban board" in ctx

    def test_includes_active_project(self):
        ctx = build_orchestrator_context(
            chat_id="123",
            active_project="agent-mahoo",
        )
        assert "agent-mahoo" in ctx

    def test_minimal_context_without_extras(self):
        ctx = build_orchestrator_context(chat_id="123")
        assert "Telegram" in ctx


class TestHelpText:
    def test_contains_all_commands(self):
        assert "/status" in HELP_TEXT
        assert "/project" in HELP_TEXT
        assert "/tasks" in HELP_TEXT
        assert "/help" in HELP_TEXT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_orchestrator.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement the orchestrator module**

```python
# python/helpers/telegram_orchestrator.py
"""Telegram orchestration layer — enriches agent context for platform-wide tool access."""

from __future__ import annotations

import re
from typing import Any


ORCHESTRATOR_COMMANDS = {"status", "project", "tasks", "help", "digest"}

HELP_TEXT = """*Agent Mahoo — Telegram Commands*

/status — Cross-system status (portfolio + tasks + workflows)
/project <name> — Project details and lifecycle
/tasks — Active Linear issues
/digest — Today's digest
/help — This message
/new — Reset conversation

Or just chat naturally — I can manage projects, create tasks, run workflows, analyze code, and more."""


def parse_slash_command(text: str) -> tuple[str | None, str]:
    """Parse a Telegram slash command. Returns (command, args) or (None, original_text)."""
    text = text.strip()
    if not text.startswith("/"):
        return None, text

    parts = text[1:].split(None, 1)
    cmd = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    if cmd in ORCHESTRATOR_COMMANDS:
        return cmd, args
    return None, text


def slash_command_to_prompt(cmd: str, args: str) -> str:
    """Convert a slash command into a natural language prompt for the agent."""
    if cmd == "status":
        return (
            "Give me a cross-system status update. Check the portfolio dashboard, "
            "Linear dashboard, and any active workflows. Summarize what's in progress, "
            "what's blocked, and what's been completed recently."
        )
    if cmd == "project":
        return (
            f"Look up the project '{args}'. Get its portfolio details and project lifecycle status. "
            f"Tell me its current phase, readiness score, and what needs to happen next."
        )
    if cmd == "tasks":
        return (
            "Search Linear for my active issues. Show me what's in progress, "
            "what's upcoming, and anything that's blocked or overdue."
        )
    if cmd == "digest":
        return "Build me a digest of today's activity across all systems."
    return ""


def format_for_telegram(text: str) -> str:
    """Format tool output for Telegram's limited Markdown support."""
    if not text:
        return ""

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Convert ## headers to bold
    text = re.sub(r"^#{1,3}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # Truncate tables with many rows (keep header + first 10 data rows)
    lines = text.split("\n")
    table_start = None
    filtered_lines: list[str] = []
    table_data_count = 0

    for line in lines:
        if "|" in line and line.strip().startswith("|"):
            if table_start is None:
                table_start = True
                table_data_count = 0
            elif re.match(r"^\|[-| ]+\|$", line.strip()):
                pass  # separator row
            else:
                table_data_count += 1
                if table_data_count > 10:
                    if table_data_count == 11:
                        filtered_lines.append("| ... | _and more_ |")
                    continue
        else:
            table_start = None
            table_data_count = 0
        filtered_lines.append(line)

    return "\n".join(filtered_lines)


def build_orchestrator_context(
    chat_id: str,
    vision_context: dict[str, Any] | None = None,
    active_project: str | None = None,
    last_tool: str | None = None,
) -> str:
    """Build additional context string to inject into the agent's conversation."""
    parts = ["[Telegram Orchestrator Context]"]

    if active_project:
        parts.append(f"Active project: {active_project}")

    if last_tool:
        parts.append(f"Last tool used: {last_tool}")

    if vision_context:
        desc = vision_context.get("description", "")
        items = vision_context.get("extracted_items", [])
        parts.append(f"Vision context from image: {desc}")
        if items:
            parts.append(f"Extracted items: {', '.join(str(i) for i in items)}")

    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_orchestrator.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add python/helpers/telegram_orchestrator.py tests/test_telegram_orchestrator.py
git commit -m "feat(telegram): add orchestrator module with command parsing and formatting"
```

---

## Task 5: System Prompt Extension for Telegram Contexts

Inject the orchestrator system prompt when the agent is responding to a Telegram-originated conversation. Uses the `system_prompt` extension point (same pattern as `_10_system_prompt.py`).

**Files:**

- Create: `python/extensions/system_prompt/_85_telegram_orchestrator.py`

- [ ] **Step 1: Create the extension file**

Follow the exact Extension class pattern from `python/extensions/system_prompt/_10_system_prompt.py`:

```python
# python/extensions/system_prompt/_85_telegram_orchestrator.py
"""Inject Telegram orchestrator system prompt for Telegram-originated conversations."""

import os
from typing import Any

from agent import LoopData
from python.helpers.extension import Extension


class TelegramOrchestratorPrompt(Extension):
    async def execute(self, system_prompt: list[str] | None = None, loop_data: LoopData = LoopData(), **kwargs: Any):
        if system_prompt is None:
            return

        context = self.agent.context
        if not context:
            return

        # Check if this is a Telegram context
        ctx_id = context.id or ""
        is_telegram = ctx_id.startswith("telegram-")

        # Also check shared context mode
        if not is_telegram:
            shared = os.getenv("TELEGRAM_AGENT_CONTEXT", "")
            if shared and ctx_id == shared:
                is_telegram = True

        if not is_telegram:
            return

        # Inject the orchestrator prompt
        try:
            prompt_content = self.agent.read_prompt("agent.system.telegram_orchestrator.md")
            if prompt_content:
                system_prompt.append(prompt_content)
        except Exception:
            pass
```

- [ ] **Step 2: Verify the file exists and slot number doesn't conflict**

Run: `ls /mnt/wdblack/dev/projects/agent-mahoo/python/extensions/system_prompt/ | sort`
Expected: `_85_telegram_orchestrator.py` present, no conflicts with `_10`, `_20`, `_30` (existing), or any other slots

- [ ] **Step 3: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add python/extensions/system_prompt/_85_telegram_orchestrator.py
git commit -m "feat(telegram): add system prompt extension for Telegram orchestrator"
```

---

## Task 6: Wire Orchestrator into Telegram Webhook

Connect the orchestrator to the existing webhook handler: slash command handling, vision context persistence, and formatted response output.

**Files:**

- Modify: `python/api/telegram_webhook.py`

- [ ] **Step 1: Add orchestrator imports to the webhook**

Add these imports after the existing imports at the top of `python/api/telegram_webhook.py`:

```python
from python.helpers.telegram_orchestrator import (
    HELP_TEXT,
    build_orchestrator_context,
    format_for_telegram,
    parse_slash_command,
    slash_command_to_prompt,
)
from python.helpers.telegram_bridge import get_session_meta, set_session_meta
from python.helpers.telegram_client import send_long_message
```

- [ ] **Step 2: Add slash command handling after the /new|/reset block**

After the `return {"status": "reset"}` line (the existing /new and /reset handler), add:

```python
        # Handle orchestrator slash commands
        cmd, cmd_args = parse_slash_command(raw_text)
        if cmd == "help":
            if token:
                send_message(token, chat_id_str, HELP_TEXT)
            return {"status": "ok"}
        if cmd is not None:
            # Translate slash command to natural language for the agent
            raw_text = slash_command_to_prompt(cmd, cmd_args)
```

- [ ] **Step 3: Add vision context persistence after media extraction**

After the `media = await extract_media(message, token)` block and before `text = media.text`, add:

```python
        # Persist vision context for follow-up messages
        if media and media.attachment_paths:
            vision_summary = {
                "description": f"Image received with message: {(media.text or 'no caption')[:200]}",
                "attachment_count": len(media.attachment_paths),
                "has_image": any(
                    p.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
                    for p in media.attachment_paths
                ),
            }
            set_session_meta(chat_id_str, "vision_context", vision_summary)
```

- [ ] **Step 4: Inject orchestrator context before sending to agent**

Before `task = context.communicate(UserMessage(...))`, add:

```python
        # Inject orchestrator context
        orch_context = build_orchestrator_context(
            chat_id=chat_id_str,
            vision_context=get_session_meta(chat_id_str, "vision_context"),
            active_project=get_session_meta(chat_id_str, "active_project"),
            last_tool=get_session_meta(chat_id_str, "last_tool"),
        )
        if orch_context:
            text = f"{orch_context}\n\n{text}"
```

- [ ] **Step 5: Replace response sending with formatted long message**

Replace the existing response send line (`send_message(token, chat_id_str, result)`) with:

```python
                formatted = format_for_telegram(result)
                send_long_message(token, chat_id_str, formatted)
```

- [ ] **Step 6: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add python/api/telegram_webhook.py
git commit -m "feat(telegram): wire orchestrator into webhook with commands, vision, and formatting"
```

---

## Task 7: Integration Tests — End-to-End Orchestration Flow

Verify the full flow: Telegram message → orchestrator → formatted response.

**Files:**

- Create: `tests/test_telegram_orchestration_e2e.py`

- [ ] **Step 1: Write the integration tests**

```python
# tests/test_telegram_orchestration_e2e.py
"""Integration tests for Telegram orchestration flow."""

from python.helpers.telegram_orchestrator import (
    parse_slash_command,
    slash_command_to_prompt,
    format_for_telegram,
    build_orchestrator_context,
    HELP_TEXT,
)
from python.helpers.telegram_client import chunk_message


class TestFullOrchestrationFlow:
    """Test the complete orchestration pipeline."""

    def test_status_flow(self):
        """Slash command -> prompt -> formatted response."""
        cmd, args = parse_slash_command("/status")
        assert cmd == "status"

        prompt = slash_command_to_prompt(cmd, args)
        assert "portfolio" in prompt.lower()

        # Simulate a tool response
        mock_response = """## Portfolio Dashboard

### Overview
- **Total Projects**: 15
- **Products Listed**: 8
- **Average Sale Readiness**: 67.5%

### By Status
| Status | Count |
|--------|-------|
| Production | 8 |
| Development | 5 |
| Draft | 2 |
"""
        formatted = format_for_telegram(mock_response)
        chunks = chunk_message(formatted)
        assert len(chunks) >= 1
        assert all(len(c) <= 4096 for c in chunks)

    def test_project_flow(self):
        """Project lookup -> context enrichment."""
        cmd, args = parse_slash_command("/project agent-mahoo")
        assert cmd == "project"
        assert args == "agent-mahoo"

        prompt = slash_command_to_prompt(cmd, args)
        assert "agent-mahoo" in prompt

    def test_vision_enrichment_flow(self):
        """Image context -> enriched prompt."""
        context = build_orchestrator_context(
            chat_id="123",
            vision_context={
                "description": "A screenshot of a project board with 5 tasks",
                "extracted_items": ["Fix login bug", "Add search", "Deploy v2"],
            },
            active_project="web-app",
        )
        assert "project board" in context
        assert "web-app" in context
        assert "Fix login bug" in context

    def test_natural_message_bypasses_commands(self):
        """Regular messages should not be treated as commands."""
        cmd, text = parse_slash_command("Can you check the portfolio?")
        assert cmd is None
        assert text == "Can you check the portfolio?"

    def test_long_tool_response_chunks_correctly(self):
        """Long tool output should be split into Telegram-safe chunks."""
        long_response = "Status line\n" * 1000
        formatted = format_for_telegram(long_response)
        chunks = chunk_message(formatted)
        assert len(chunks) > 1
        assert all(len(c) <= 4096 for c in chunks)
```

- [ ] **Step 2: Run the integration tests**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_orchestration_e2e.py -v`
Expected: All PASS

- [ ] **Step 3: Run the full Telegram test suite**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_*.py -v --tb=short`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add tests/test_telegram_orchestration_e2e.py
git commit -m "test(telegram): add integration tests for orchestration flow"
```

---

## Task 8: Telegram Commands Prompt and Final Verification

Add the commands reference prompt and verify everything is wired together.

**Files:**

- Create: `prompts/agent.system.tool.telegram_commands.md`

- [ ] **Step 1: Create Telegram commands tool prompt**

```markdown
# Telegram Commands

When responding to Telegram users, you can suggest these slash commands:

- `/status` - Cross-system status update
- `/project <name>` - Project details and lifecycle
- `/tasks` - Active Linear issues
- `/digest` - Daily activity digest
- `/help` - Available commands
- `/new` - Reset conversation context

These commands are shortcuts. Users can also describe what they want in natural language and you should use the appropriate tools to fulfill their request.
```

- [ ] **Step 2: Verify all new files exist**

Run: `ls -la /mnt/wdblack/dev/projects/agent-mahoo/prompts/agent.system.telegram_orchestrator.md /mnt/wdblack/dev/projects/agent-mahoo/prompts/agent.system.tool.telegram_commands.md /mnt/wdblack/dev/projects/agent-mahoo/python/helpers/telegram_orchestrator.py /mnt/wdblack/dev/projects/agent-mahoo/python/extensions/system_prompt/_85_telegram_orchestrator.py`
Expected: All 4 files exist

- [ ] **Step 3: Run the complete test suite**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && python -m pytest tests/test_telegram_*.py -v --tb=short`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
git add prompts/agent.system.tool.telegram_commands.md
git commit -m "docs(telegram): add Telegram commands tool prompt"
```

- [ ] **Step 5: Verify commit history**

Run: `cd /mnt/wdblack/dev/projects/agent-mahoo && git log --oneline -10`
Expected: 8 discrete commits for this feature
