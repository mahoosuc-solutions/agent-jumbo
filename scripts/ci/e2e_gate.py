#!/usr/bin/env python3
"""E2E test gate script for CI.

Reads pytest-json-report output and applies tiered pass/fail logic:
- security + e2e (functional): hard block, never overridable
- performance: soft block (20% tolerance built into tests), overridable via [force-merge] label
- a11y: advisory, always passes

Usage:
    python scripts/ci/e2e_gate.py e2e-results.json --labels '["force-merge"]'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TIERS = {
    "hard": {"markers": {"security", "e2e"}, "label": "Security + Functional"},
    "soft": {"markers": {"performance"}, "label": "Performance"},
    "advisory": {"markers": {"a11y"}, "label": "Accessibility"},
}


def categorize_tests(report: dict) -> dict[str, dict]:
    """Categorize test results by gate tier."""
    results: dict[str, dict] = {
        "hard": {"passed": 0, "failed": 0, "failures": []},
        "soft": {"passed": 0, "failed": 0, "failures": []},
        "advisory": {"passed": 0, "failed": 0, "failures": []},
    }

    for test in report.get("tests", []):
        markers = {m["name"] for m in test.get("markers", [])} if "markers" in test else set()
        # Also extract markers from keywords (pytest-json-report stores them differently)
        keywords = set(test.get("keywords", []))
        all_tags = markers | keywords

        outcome = test.get("outcome", "passed")
        name = test.get("nodeid", "unknown")

        # Determine tier — check in priority order
        tier = None
        if all_tags & TIERS["hard"]["markers"]:
            tier = "hard"
        if all_tags & TIERS["soft"]["markers"]:
            tier = "soft"
        if all_tags & TIERS["advisory"]["markers"]:
            tier = "advisory"

        if tier is None:
            # Untagged tests go to hard block (functional)
            tier = "hard"

        if outcome == "passed":
            results[tier]["passed"] += 1
        else:
            results[tier]["failed"] += 1
            results[tier]["failures"].append(name)

    return results


def format_summary(results: dict[str, dict], override: bool) -> str:
    """Format PR-comment-friendly summary."""
    lines = ["## E2E Test Results", ""]

    for tier_key, tier_info in TIERS.items():
        r = results[tier_key]
        total = r["passed"] + r["failed"]
        if total == 0:
            continue

        if r["failed"] == 0:
            icon = "[check]"
        elif tier_key == "advisory":
            icon = "[info]"
        elif tier_key == "soft" and override:
            icon = "[warn]"
        else:
            icon = "[fail]"

        label = tier_info["label"]
        line = f"{icon} {label}: {r['passed']}/{total} passed"

        if r["failed"] > 0 and tier_key == "soft" and override:
            line += " (override: force-merge label present)"
        elif r["failed"] > 0 and tier_key == "advisory":
            line += f" ({r['failed']} violations, see report)"

        lines.append(line)

        if r["failures"] and tier_key != "advisory":
            for f in r["failures"]:
                lines.append(f"  - {f}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E test gate")
    parser.add_argument("report", type=Path, help="pytest-json-report JSON file")
    parser.add_argument("--labels", default="[]", help="JSON array of PR labels")
    args = parser.parse_args()

    if not args.report.exists():
        print(f"Error: report file not found: {args.report}", file=sys.stderr)
        return 1

    report = json.loads(args.report.read_text())
    try:
        labels = json.loads(args.labels) if args.labels.strip() else []
    except (json.JSONDecodeError, AttributeError):
        labels = []
    override = "force-merge" in labels

    results = categorize_tests(report)
    summary = format_summary(results, override)
    print(summary)

    # Hard block: security + functional failures always fail
    if results["hard"]["failed"] > 0:
        print(f"\nGate: FAIL — {results['hard']['failed']} hard-block failure(s)", file=sys.stderr)
        return 1

    # Soft block: performance failures fail unless overridden
    if results["soft"]["failed"] > 0 and not override:
        print(
            f"\nGate: FAIL — {results['soft']['failed']} performance failure(s) (add [force-merge] label to override)",
            file=sys.stderr,
        )
        return 1

    if results["soft"]["failed"] > 0 and override:
        print("\nGate: PASS (performance failures overridden by force-merge label)", file=sys.stderr)
    else:
        print("\nGate: PASS", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
