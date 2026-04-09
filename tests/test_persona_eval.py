"""
Local training and evaluation harness for MOS and C-suite persona profiles.

Purpose:
    Validate that each persona profile is correctly configured — manifests load,
    capabilities are declared, tool lists are non-empty, and delegation targets
    are valid persona names.

    Covers two tiers:
    - MOS specialist personas: solution-design, devops, data-ml, analytics, customer-support
    - C-suite executive personas: coo, cso, cmo, cfo

Usage:
    # Run all personas
    pytest tests/test_persona_eval.py -v

    # Run a specific persona or tier
    pytest tests/test_persona_eval.py -v -k "cfo"
    pytest tests/test_persona_eval.py -v -k "solution_design"

    # Run fixture coverage check only
    pytest tests/test_persona_eval.py -v -k "fixture"

These are structural/configuration tests only. They do not invoke LLM calls.
For live response quality evaluation, use the PERSONA_TASK_FIXTURES dict below
as a reference for manual or automated prompt injection tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ── Constants ────────────────────────────────────────────────────────────────

AGENTS_DIR = Path(__file__).parent.parent / "agents"

PERSONAS = [
    # MOS specialist personas
    "solution-design",
    "devops",
    "data-ml",
    "analytics",
    "customer-support",
    # C-suite executive personas
    "coo",
    "cso",
    "cmo",
    "cfo",
]

KNOWN_PERSONA_NAMES = {
    "developer",
    "researcher",
    "actor-research",
    "actor-ops",
    "ghost-writer",
    "solution-design",
    "devops",
    "data-ml",
    "analytics",
    "customer-support",
    "coo",
    "cso",
    "cmo",
    "cfo",
}

# Representative MOS task fixtures for manual / LLM evaluation.
# Feed each fixture to the corresponding persona and verify:
#   - Response stays within role boundaries (no hallucinated tools)
#   - Delegation targets match expected profiles
#   - Structured MOS output format is present (metric, value, trend, status fields)
PERSONA_TASK_FIXTURES: dict[str, list[str]] = {
    "solution-design": [
        "Design a multi-tenant data isolation architecture for Mahoosuc.ai.",
        "Evaluate switching from REST to GraphQL for the solutions API — produce a scored decision matrix.",
        "Review the current work queue instrument architecture and propose a scaling roadmap for 10x throughput.",
    ],
    "devops": [
        "Deploy the latest agent-mahoo build to production — run pre-flight checks and post-deploy smoke tests.",
        "Investigate high latency reported in the MOS work queue scanner and produce a root cause analysis.",
        "Design a GitHub Actions CI/CD pipeline for the Mahoosuc.ai web application.",
    ],
    "data-ml": [
        "Build a churn prediction pipeline using Linear issue history and platform usage signals.",
        "Design a feature store for customer engagement signals — define entity definitions, feature groups, and serving tiers.",
        "Implement real-time anomaly detection on work queue throughput metrics.",
    ],
    "analytics": [
        "Generate the daily MOS operations digest covering work queue, Linear velocity, and Stripe events.",
        "Calculate ROI for the StayHive hospitality add-on and produce an executive summary.",
        "Produce a weekly KPI summary comparing this week's metrics against the prior four-week average.",
    ],
    "customer-support": [
        "A customer reports their Stripe payment failed on checkout — triage the issue and provide resolution steps.",
        "Onboard a new Mahoosuc.ai customer to the solutions catalog and configure their first workflow.",
        "A customer reports the work queue dashboard shows stale data — escalate to the appropriate technical team.",
    ],
    # C-suite executive personas
    "coo": [
        "Run the daily operations digest — collect platform health signals and produce the morning briefing.",
        "Identify work queue items aging beyond SLA thresholds and escalate to responsible personas.",
        "Coordinate incident response for a P1 workflow engine failure across devops and data-ml.",
    ],
    "cso": [
        "Run the weekly pipeline review — sweep customer_lifecycle for stage movements and produce an action list.",
        "Coordinate an enterprise proposal for a new customer — ROI model, technical review, and narrative.",
        "Process a batch of new signup leads and classify by tier for operator follow-up.",
    ],
    "cmo": [
        "Review this week's marketing content queue and brief ghost-writer on the top-priority items.",
        "Run a brand voice audit on recently produced solution briefs and flag any brand drift.",
        "Update the solution positioning framework based on a new competitive research report.",
    ],
    "cfo": [
        "Run the daily financial snapshot — collect Stripe revenue state and write to EXECUTIVE memory.",
        "Review the dunning queue and prepare a human confirmation package for next-stage actions.",
        "Produce the weekly financial digest combining Stripe actuals with the CSO pipeline forecast.",
    ],
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _load_manifest(persona: str) -> dict:
    """Load and parse a persona's manifest.yaml."""
    manifest_path = AGENTS_DIR / persona / "manifest.yaml"
    assert manifest_path.exists(), f"manifest.yaml missing for persona '{persona}' at {manifest_path}"
    with manifest_path.open() as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"manifest.yaml for '{persona}' did not parse to a dict"
    return data


# ── Manifest presence tests ──────────────────────────────────────────────────


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_exists(persona: str) -> None:
    """Each persona must have a manifest.yaml."""
    manifest_path = AGENTS_DIR / persona / "manifest.yaml"
    assert manifest_path.exists(), f"Missing: {manifest_path}"


@pytest.mark.parametrize("persona", PERSONAS)
def test_context_md_exists(persona: str) -> None:
    """Each persona must have a _context.md description file."""
    context_path = AGENTS_DIR / persona / "_context.md"
    assert context_path.exists(), f"Missing: {context_path}"


@pytest.mark.parametrize("persona", PERSONAS)
def test_role_prompt_exists(persona: str) -> None:
    """Each persona must have a role prompt."""
    prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
    assert prompt_path.exists(), f"Missing: {prompt_path}"


# ── Manifest schema tests ─────────────────────────────────────────────────────


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_has_required_fields(persona: str) -> None:
    """Each manifest must have name, version, description, and inherits."""
    manifest = _load_manifest(persona)
    for field in ("name", "version", "description", "inherits"):
        assert field in manifest, f"'{persona}' manifest missing required field: '{field}'"


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_name_matches_directory(persona: str) -> None:
    """The name field in the manifest must match the directory name."""
    manifest = _load_manifest(persona)
    assert manifest["name"] == persona, f"Manifest name '{manifest['name']}' does not match directory '{persona}'"


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_inherits_valid_profile(persona: str) -> None:
    """Each persona must inherit from 'default' or another valid base."""
    manifest = _load_manifest(persona)
    valid_bases = {"default", "base", "developer", "researcher"}
    inherits = manifest.get("inherits", "")
    assert inherits in valid_bases, f"'{persona}' inherits from unknown profile: '{inherits}'"


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_has_capabilities(persona: str) -> None:
    """Each manifest must declare at least 3 capabilities."""
    manifest = _load_manifest(persona)
    caps = manifest.get("capabilities", [])
    assert isinstance(caps, list), f"'{persona}' capabilities must be a list"
    assert len(caps) >= 3, f"'{persona}' declares only {len(caps)} capability/ies — expected at least 3"


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_tools_section(persona: str) -> None:
    """Each manifest must have a tools section with at least one include entry."""
    manifest = _load_manifest(persona)
    tools = manifest.get("tools", {})
    assert isinstance(tools, dict), f"'{persona}' tools must be a dict"
    include = tools.get("include", [])
    assert isinstance(include, list), f"'{persona}' tools.include must be a list"
    assert len(include) >= 1, f"'{persona}' tools.include is empty"


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_behavior_section(persona: str) -> None:
    """Each manifest must define behavior with max_iterations."""
    manifest = _load_manifest(persona)
    behavior = manifest.get("behavior", {})
    assert isinstance(behavior, dict), f"'{persona}' behavior must be a dict"
    assert "max_iterations" in behavior, f"'{persona}' behavior missing 'max_iterations'"
    assert isinstance(behavior["max_iterations"], int), f"'{persona}' behavior.max_iterations must be an int"
    assert behavior["max_iterations"] > 0, f"'{persona}' behavior.max_iterations must be positive"


@pytest.mark.parametrize("persona", PERSONAS)
def test_manifest_auto_delegate_targets_are_known(persona: str) -> None:
    """Any auto_delegate targets must reference known persona names."""
    manifest = _load_manifest(persona)
    auto_delegate = manifest.get("behavior", {}).get("auto_delegate", {})
    for task_type, target in auto_delegate.items():
        assert target in KNOWN_PERSONA_NAMES, (
            f"'{persona}' auto_delegate['{task_type}'] = '{target}' is not a known persona"
        )


# ── Role prompt content tests ─────────────────────────────────────────────────


@pytest.mark.parametrize("persona", PERSONAS)
def test_role_prompt_has_core_sections(persona: str) -> None:
    """Role prompts must contain the required structural sections."""
    prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
    content = prompt_path.read_text()
    required_phrases = [
        "## Your Role",
        "Core Identity",
        "Operational Directives",
        "MOS",
    ]
    for phrase in required_phrases:
        assert phrase in content, f"'{persona}' role prompt missing expected section/phrase: '{phrase}'"


@pytest.mark.parametrize("persona", PERSONAS)
def test_role_prompt_minimum_length(persona: str) -> None:
    """Role prompts must be substantive (at least 3000 characters)."""
    prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
    content = prompt_path.read_text()
    assert len(content) >= 3000, f"'{persona}' role prompt is too short: {len(content)} chars (expected ≥3000)"


@pytest.mark.parametrize("persona", PERSONAS)
def test_role_prompt_references_mos(persona: str) -> None:
    """Each role prompt must reference MOS task sources (work queue or scheduler)."""
    prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
    content = prompt_path.read_text()
    mos_references = ["work queue", "MOS work queue", "MOS scheduler", "workflow"]
    assert any(ref.lower() in content.lower() for ref in mos_references), (
        f"'{persona}' role prompt does not reference any MOS task sources"
    )


# ── Fixture coverage test ─────────────────────────────────────────────────────


def test_all_personas_have_task_fixtures() -> None:
    """Every persona must have at least 2 task fixtures for manual evaluation."""
    for persona in PERSONAS:
        fixtures = PERSONA_TASK_FIXTURES.get(persona, [])
        assert len(fixtures) >= 2, f"Persona '{persona}' has {len(fixtures)} fixture(s) — expected at least 2"


def test_no_extra_fixtures_for_unknown_personas() -> None:
    """PERSONA_TASK_FIXTURES must not reference undefined personas."""
    for persona in PERSONA_TASK_FIXTURES:
        assert persona in PERSONAS, f"PERSONA_TASK_FIXTURES contains unknown persona: '{persona}'"


# ── MOS scheduler registration smoke test ────────────────────────────────────


def test_scheduler_init_imports_cleanly() -> None:
    """mos_scheduler_init.py must be importable without raising."""
    try:
        import python.helpers.mos_scheduler_init  # noqa: F401
    except ImportError as e:
        pytest.skip(f"Scheduler dependencies not available: {e}")


def test_seed_mos_tasks_returns_dict() -> None:
    """seed_mos_tasks() must return a dict with required keys."""
    import asyncio

    try:
        from python.helpers.mos_scheduler_init import seed_mos_tasks

        result = asyncio.run(seed_mos_tasks())
        assert isinstance(result, dict), "seed_mos_tasks() did not return a dict"
        assert "status" in result, "seed_mos_tasks() result missing key: 'status'"
    except ImportError as e:
        pytest.skip(f"Scheduler dependencies not available: {e}")
