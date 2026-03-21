"""Minimal Telegram API helper."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

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
        chunks = [f"{c}\n({i + 1}/{total})" for i, c in enumerate(chunks)]

    return chunks


def send_long_message(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> list[dict[str, Any]]:
    """Send a message, automatically chunking if it exceeds Telegram's limit."""
    chunks = chunk_message(text, add_part_numbers=True)
    results = []
    for chunk in chunks:
        results.append(send_message(token, chat_id, chunk, parse_mode))
    return results


def get_file_path(token: str, file_id: str) -> str | None:
    endpoint = f"https://api.telegram.org/bot{token}/getFile"
    data = json.dumps({"file_id": file_id}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            result = json.loads(response.read().decode("utf-8", errors="ignore"))
        if result.get("ok"):
            return result["result"].get("file_path")
    except Exception:
        pass
    return None


def download_file(token: str, file_id: str, max_bytes: int = 20 * 1024 * 1024) -> bytes | None:
    file_path = get_file_path(token, file_id)
    if not file_path:
        return None
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    request = urllib.request.Request(url)  # nosec B310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None
            return data
    except Exception:
        return None


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> dict[str, Any]:
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"

    def _send(mode: str | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if mode:
            payload["parse_mode"] = mode
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310 - configured Telegram API URL
            raw = response.read().decode("utf-8", errors="ignore")
        return {"raw": raw}

    # Try with requested parse_mode; fall back to plain text on 400
    try:
        return _send(parse_mode)
    except urllib.error.HTTPError as e:
        if e.code == 400 and parse_mode:
            return _send(None)
        raise
