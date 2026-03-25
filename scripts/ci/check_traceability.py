#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LINEAR_PATTERNS = [
    re.compile(r"Linear issue:\s*(.+)", re.IGNORECASE),
    re.compile(r"Linear:\s*(.+)", re.IGNORECASE),
]
GITHUB_PATTERNS = [
    re.compile(r"GitHub issue/PR:\s*(.+)", re.IGNORECASE),
    re.compile(r"GitHub issue:\s*(.+)", re.IGNORECASE),
    re.compile(r"Related Issues\s+(.+)", re.IGNORECASE | re.DOTALL),
]


def extract_value(patterns: list[re.Pattern[str]], text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return ""


def looks_populated(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    placeholders = {
        "(issue number)",
        "<linear-id-or-url>",
        "<github-issue-or-pr>",
        "n/a",
        "none",
        "tbd",
    }
    return stripped.lower() not in placeholders


def validate_pr_body(body: str) -> list[str]:
    errors: list[str] = []
    linear_value = extract_value(LINEAR_PATTERNS, body)
    github_value = extract_value(GITHUB_PATTERNS, body)

    if not looks_populated(linear_value):
        errors.append("PR body must include a populated `Linear issue:` field.")
    if not looks_populated(github_value):
        errors.append("PR body must include a populated `GitHub issue/PR:` field.")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PR traceability fields.")
    parser.add_argument("--event-path", default="", help="GitHub event payload path")
    parser.add_argument("--body", default="", help="Explicit PR body override")
    args = parser.parse_args()

    body = args.body
    if not body:
        event_path = args.event_path or ""
        if not event_path:
            print("Traceability check skipped: no pull request body available.")
            return 0
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
        if "pull_request" not in payload:
            print("Traceability check skipped: event has no pull_request payload.")
            return 0
        body = str(((payload.get("pull_request") or {}).get("body")) or "")

    errors = validate_pr_body(body)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("Traceability check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
