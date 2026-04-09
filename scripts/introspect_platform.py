#!/usr/bin/env python3
"""Introspect the agent-mahoo codebase and emit a platform manifest JSON.

Scans commands, instruments, tools, API endpoints, integrations, helpers,
AG Mesh metadata, GitHub repos, and optional product/pricing catalogs.

Output: web/public/platform-manifest.json
"""

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_PUBLIC = ROOT / "web" / "public"
MANIFEST_PATH = WEB_PUBLIC / "platform-manifest.json"


# ---------------------------------------------------------------------------
# Counting helpers
# ---------------------------------------------------------------------------


def count_commands() -> dict:
    """Count .md command files and category subdirectories."""
    commands_dir = ROOT / ".claude" / "commands"
    if not commands_dir.is_dir():
        return {"total": 0, "categories": 0}
    md_files = list(commands_dir.rglob("*.md"))
    categories = [d for d in commands_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    return {"total": len(md_files), "categories": len(categories)}


def count_instruments() -> dict:
    """Count instrument subdirectories (excluding _TEMPLATE)."""
    instruments_dir = ROOT / "instruments" / "custom"
    if not instruments_dir.is_dir():
        return {"total": 0, "active": 0}
    dirs = [d for d in instruments_dir.iterdir() if d.is_dir() and d.name != "_TEMPLATE"]
    return {"total": len(dirs), "active": len(dirs)}


def count_tools() -> dict:
    """Count .py tool files (excluding __init__.py)."""
    tools_dir = ROOT / "python" / "tools"
    if not tools_dir.is_dir():
        return {"total": 0}
    py_files = [f for f in tools_dir.iterdir() if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"]
    return {"total": len(py_files)}


def count_api_endpoints() -> dict:
    """Count .py API endpoint files (excluding __init__.py)."""
    api_dir = ROOT / "python" / "api"
    if not api_dir.is_dir():
        return {"total": 0}
    py_files = [f for f in api_dir.iterdir() if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"]
    return {"total": len(py_files)}


def detect_integrations() -> list[str]:
    """Detect known integrations by directory/file presence."""
    instruments_dir = ROOT / "instruments" / "custom"
    helpers_dir = ROOT / "python" / "helpers"

    # Directory-based integrations
    dir_integrations = [
        "linear_integration",
        "stripe_payments",
        "google_voice",
        "twilio_voice",
        "notion_integration",
        "motion_integration",
        "calendar_hub",
        "pms_hub",
    ]
    found = []
    for name in dir_integrations:
        if (instruments_dir / name).is_dir():
            found.append(name)

    # File-based integrations in helpers
    file_integrations = {
        "telegram_orchestrator.py": "telegram_orchestrator",
        "gmail_api_client.py": "gmail_api_client",
    }
    for filename, label in file_integrations.items():
        if (helpers_dir / filename).is_file():
            found.append(label)

    return sorted(found)


def count_helper_modules() -> int:
    """Count .py helper modules (excluding __init__.py)."""
    helpers_dir = ROOT / "python" / "helpers"
    if not helpers_dir.is_dir():
        return 0
    py_files = [f for f in helpers_dir.iterdir() if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"]
    return len(py_files)


def extract_ag_mesh() -> dict:
    """Extract AG Mesh event types, risk levels, and agent profiles."""
    event_types: set[str] = set()
    risk_levels: list[str] = []
    agent_profiles = 0

    # Event types from bridge and task handler
    event_pattern = re.compile(r'"(task\.\w+)"')
    for filename in ("agentmesh_bridge.py", "agentmesh_task_handler.py"):
        filepath = ROOT / "python" / "helpers" / filename
        if filepath.is_file():
            text = filepath.read_text()
            event_types.update(event_pattern.findall(text))

    # Risk levels from risk module
    risk_file = ROOT / "python" / "helpers" / "agentmesh_risk.py"
    if risk_file.is_file():
        text = risk_file.read_text()
        risk_pattern = re.compile(r'"(LOW|MEDIUM|HIGH|CRITICAL)"')
        risk_levels = sorted(set(risk_pattern.findall(text)))

    # Agent profiles from CATEGORY_PROFILE_MAP values
    handler_file = ROOT / "python" / "helpers" / "agentmesh_task_handler.py"
    if handler_file.is_file():
        text = handler_file.read_text()
        # Extract the dict block
        map_match = re.search(r"CATEGORY_PROFILE_MAP[^{]*\{([^}]+)\}", text, re.DOTALL)
        if map_match:
            values = re.findall(r':\s*"([^"]+)"', map_match.group(1))
            agent_profiles = len(set(values))

    return {
        "event_types": sorted(event_types),
        "risk_levels": risk_levels,
        "agent_profiles": agent_profiles,
    }


def fetch_github_repos() -> dict:
    """Fetch GitHub repos for mahoosuc-solutions and classify by vertical."""
    vertical_keywords = {
        "hospitality": ["pms", "hotel", "hospitality", "booking", "property"],
        "finance": ["finance", "stripe", "billing", "payment", "accounting"],
        "ai-ops": ["agent", "ai", "llm", "mesh", "orchestrat"],
        "devops": ["deploy", "ci", "cd", "infra", "docker", "k8s"],
        "communications": ["telegram", "voice", "sms", "email", "twilio"],
        "productivity": ["notion", "linear", "motion", "calendar", "task"],
    }

    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                "mahoosuc-solutions",
                "--limit",
                "100",
                "--json",
                "name,description,isArchived",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return {"repos": 0, "verticals": []}

        repos = json.loads(result.stdout)
        active_repos = [r for r in repos if not r.get("isArchived", False)]

        verticals_found: set[str] = set()
        for repo in active_repos:
            searchable = ((repo.get("name") or "") + " " + (repo.get("description") or "")).lower()
            for vertical, keywords in vertical_keywords.items():
                if any(kw in searchable for kw in keywords):
                    verticals_found.add(vertical)

        return {
            "repos": len(active_repos),
            "verticals": sorted(verticals_found),
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"repos": 0, "verticals": []}


def load_optional_json(path: Path) -> dict | list | None:
    """Load a JSON file if it exists, otherwise return None."""
    if path.is_file():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_manifest() -> dict:
    """Assemble the full platform manifest."""
    products_data = load_optional_json(ROOT / "docs" / "product-page" / "product-catalog.json")
    pricing_data = load_optional_json(ROOT / "docs" / "product-page" / "pricing-model.json")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "commands": count_commands(),
            "instruments": count_instruments(),
            "tools": count_tools(),
            "api_endpoints": count_api_endpoints(),
            "integrations": detect_integrations(),
            "helper_modules": count_helper_modules(),
        },
        "github": fetch_github_repos(),
        "ag_mesh": extract_ag_mesh(),
        "products": products_data
        if isinstance(products_data, list)
        else (products_data.get("products", []) if isinstance(products_data, dict) else []),
        "pricing": pricing_data
        if isinstance(pricing_data, dict)
        else {
            "tiers": [],
            "cost_components": [],
            "competitive_reference": [],
            "assumptions": [],
        },
    }
    return manifest


def main() -> None:
    WEB_PUBLIC.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Platform manifest written to {MANIFEST_PATH}")
    # Summary
    p = manifest["platform"]
    print(f"  Commands:    {p['commands']['total']} across {p['commands']['categories']} categories")
    print(f"  Instruments: {p['instruments']['total']}")
    print(f"  Tools:       {p['tools']['total']}")
    print(f"  API endpoints: {p['api_endpoints']['total']}")
    print(f"  Integrations:  {len(p['integrations'])}")
    print(f"  Helpers:       {p['helper_modules']}")
    g = manifest["github"]
    print(f"  GitHub repos:  {g['repos']} ({len(g['verticals'])} verticals)")
    a = manifest["ag_mesh"]
    print(
        f"  AG Mesh:       {len(a['event_types'])} events, {len(a['risk_levels'])} risk levels, {a['agent_profiles']} profiles"
    )


if __name__ == "__main__":
    main()
