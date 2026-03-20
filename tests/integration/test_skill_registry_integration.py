"""Integration tests for SkillRegistry — pure in-memory, no DB or server needed."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


def _make_manifest(name: str = "test-skill", **kwargs):
    """Build a minimal SkillManifest for testing."""
    from python.helpers.skill_registry import SkillManifest

    defaults = {
        "name": name,
        "version": "1.0.0",
        "author": "tester",
        "tier": 1,
        "trust_level": "local",
        "categories": ["testing"],
        "dependencies": [],
        "capabilities": ["demo"],
        "path": Path("/tmp/fake-skills") / name,
        "enabled": True,
        "installed_at": datetime.now(timezone.utc),
        "description": "Test skill",
    }
    defaults.update(kwargs)
    return SkillManifest(**defaults)


def test_skill_registry_register(fresh_registry):
    """install() adds the skill and get() returns it."""
    manifest = _make_manifest("hello-world")
    fresh_registry.install(manifest)

    retrieved = fresh_registry.get("hello-world")
    assert retrieved is not None
    assert retrieved.name == "hello-world"
    assert retrieved.version == "1.0.0"


def test_skill_registry_get_registered(fresh_registry):
    """list() returns all installed skills; category filter narrows results."""
    fresh_registry.install(_make_manifest("skill-a", categories=["ai"]))
    fresh_registry.install(_make_manifest("skill-b", categories=["util"]))
    fresh_registry.install(_make_manifest("skill-c", categories=["ai"]))

    all_skills = fresh_registry.list()
    assert len(all_skills) == 3

    ai_skills = fresh_registry.list(category="ai")
    assert len(ai_skills) == 2
    assert all(s.categories == ["ai"] for s in ai_skills)


def test_skill_registry_uninstall(fresh_registry):
    """uninstall() removes the skill; subsequent get() returns None."""
    fresh_registry.install(_make_manifest("removable"))
    assert fresh_registry.get("removable") is not None

    fresh_registry.uninstall("removable")
    assert fresh_registry.get("removable") is None
    assert len(fresh_registry.list()) == 0


# ---------------------------------------------------------------------------
# Fixture — isolated registry per test (avoids global singleton pollution)
# ---------------------------------------------------------------------------


@pytest.fixture()
def fresh_registry():
    from python.helpers.skill_registry import SkillRegistry

    return SkillRegistry()
