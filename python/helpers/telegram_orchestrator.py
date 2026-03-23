"""Telegram orchestration layer — enriches agent context for platform-wide tool access."""

from __future__ import annotations

import re
from typing import Any

ORCHESTRATOR_COMMANDS = {
    "status",
    "project",
    "tasks",
    "newtask",
    "help",
    "digest",
    "sync",
    "deadletters",
    "payments",
    "revenue",
    "invoices",
    "solutions",
    "solution",
    "coordinate",
    "providers",
    "routing",
}

HELP_TEXT = """*Agent Jumbo — Telegram Commands*

/status — Cross-system status (portfolio + tasks + workflows)
/project <name> — Project details and lifecycle
/tasks — Active Linear issues
/newtask <title> — Create a new task in Linear
/digest — Today's digest
/sync — Sync projects from platform into portfolio
/deadletters — Dead-letter queue summary
/payments — Stripe payments dashboard
/revenue — Revenue report (MRR, ARR, growth)
/invoices — Recent Stripe invoices
/solutions — List available AI solutions with pricing
/solution <name> — Solution details and architecture
/coordinate <task> — Multi-LLM coordinated execution
/providers — Show LLM provider health and availability
/routing — Show active LLM routing configuration
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
    if cmd == "newtask":
        if not args.strip():
            return "I need a title for the new task. Ask me what I'd like to create."
        return (
            f"Create a new issue in Linear with the title: '{args.strip()}'. "
            f"Use the default team. Set priority to medium unless the title suggests urgency. "
            f"After creating it, confirm the issue ID and title."
        )
    if cmd == "digest":
        return "Build me a digest of today's activity across all systems."
    if cmd == "sync":
        return (
            "Sync projects from the platform into the portfolio. "
            "Run the portfolio sync to pull in any new or updated projects, "
            "then show me the portfolio dashboard."
        )
    if cmd == "deadletters":
        return (
            "Check the dead-letter queue at logs/dead_letters.jsonl. "
            "Read the file and summarize: how many dead letters, most recent errors, "
            "and which channels are affected. If the file doesn't exist or is empty, "
            "report that the queue is clear."
        )
    if cmd == "payments":
        return (
            "Check the Stripe payments dashboard. Show MRR, recent payments, "
            "active subscriptions count, and any failed payments."
        )
    if cmd == "revenue":
        return (
            "Generate a revenue report from Stripe. Show MRR, ARR, total revenue "
            "for the last 30 days, customer count, and growth trend."
        )
    if cmd == "invoices":
        return "List recent Stripe invoices. Show status (draft, open, paid, void), amounts, and customer names."
    if cmd == "solutions":
        return (
            "List all AI infrastructure solutions from the solution catalog. "
            "Show name, category, pricing, and status for each."
        )
    if cmd == "solution":
        return (
            f"Get details for the AI solution '{args}'. Show the architecture, "
            f"pricing, included agents, integrations, and deployment timeline."
        )
    if cmd == "coordinate":
        if not args.strip():
            return "I need a task description to coordinate. Ask me what I'd like to run."
        return (
            f"Use the coordinator tool with action 'dispatch' to execute this task "
            f"with multi-LLM coordination: {args.strip()}"
        )
    if cmd == "providers":
        return (
            "Use the coordinator tool with action 'provider_health' to show the "
            "current status of all available LLM providers."
        )
    if cmd == "routing":
        return (
            "Show the current LLM routing configuration. Which models are configured "
            "for chat, utility, browser, and embedding roles? What routing rules are active?"
        )
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
