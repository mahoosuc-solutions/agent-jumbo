"""Reusable input validation utilities for API handlers."""

from __future__ import annotations

MAX_MESSAGE_LENGTH = 100_000  # 100KB text
MAX_ATTACHMENTS = 20


def validate_message_input(text: str, attachments: list | None = None) -> None:
    """Validate chat message input."""
    if not isinstance(text, str):
        raise ValueError("Message text must be a string")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message too long ({len(text)} chars). Maximum is {MAX_MESSAGE_LENGTH}.")
    if attachments and len(attachments) > MAX_ATTACHMENTS:
        raise ValueError(f"Too many attachments ({len(attachments)}). Maximum is {MAX_ATTACHMENTS}.")


def validate_settings_input(data: dict) -> None:
    """Validate settings update input."""
    if not isinstance(data, dict):
        raise ValueError("Settings input must be a dictionary")
    sections = data.get("sections")
    if sections is not None and not isinstance(sections, list):
        raise ValueError("Settings sections must be a list")
    if sections:
        for section in sections:
            if not isinstance(section, dict):
                raise ValueError("Each settings section must be a dictionary")
            fields = section.get("fields")
            if fields is not None:
                if not isinstance(fields, list):
                    raise ValueError("Section fields must be a list")
                for field in fields:
                    if not isinstance(field, dict) or "id" not in field or "value" not in field:
                        raise ValueError("Each field must have 'id' and 'value' keys")
