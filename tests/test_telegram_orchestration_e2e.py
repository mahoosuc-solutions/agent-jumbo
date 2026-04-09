# tests/test_telegram_orchestration_e2e.py
"""Integration tests for Telegram orchestration flow."""

from python.helpers.telegram_client import chunk_message
from python.helpers.telegram_orchestrator import (
    build_orchestrator_context,
    format_for_telegram,
    parse_slash_command,
    slash_command_to_prompt,
)


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
