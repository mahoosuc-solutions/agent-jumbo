"""Tests for TelegramOrchestrator."""

from python.helpers.telegram_orchestrator import (
    HELP_TEXT,
    build_orchestrator_context,
    format_for_telegram,
    parse_slash_command,
    slash_command_to_prompt,
)


class TestParseSlashCommand:
    def test_status_command(self):
        cmd, args = parse_slash_command("/status")
        assert cmd == "status"
        assert args == ""

    def test_project_command_with_name(self):
        cmd, args = parse_slash_command("/project agent-jumbo")
        assert cmd == "project"
        assert args == "agent-jumbo"

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
        prompt = slash_command_to_prompt("project", "agent-jumbo")
        assert "agent-jumbo" in prompt

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
            active_project="agent-jumbo",
        )
        assert "agent-jumbo" in ctx

    def test_minimal_context_without_extras(self):
        ctx = build_orchestrator_context(chat_id="123")
        assert "Telegram" in ctx


class TestHelpText:
    def test_contains_all_commands(self):
        assert "/status" in HELP_TEXT
        assert "/project" in HELP_TEXT
        assert "/tasks" in HELP_TEXT
        assert "/help" in HELP_TEXT
