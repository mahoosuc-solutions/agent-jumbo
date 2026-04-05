"""
Integration tests for C-suite persona loading, tool resolution,
EXECUTIVE memory wiring, delegation paths, and peer coordination.

These tests validate runtime behavior without LLM calls — they exercise
AgentComposer, Memory.Area, manifest inheritance, tool file resolution,
and the shared EXECUTIVE memory contract between C-suite personas.

Usage:
    pytest tests/test_csuite_integration.py -v
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import pytest
import yaml

from python.helpers.agent_composer import AgentComposer, AgentProfileConfig
from python.helpers.memory import Memory

# ── Constants ────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent.parent
AGENTS_DIR = ROOT_DIR / "agents"
TOOLS_DIR = ROOT_DIR / "python" / "tools"

CSUITE_PERSONAS = ["cfo", "cmo", "cso", "coo"]
MOS_PERSONAS = ["solution-design", "devops", "data-ml", "analytics", "customer-support"]
ALL_PERSONAS = MOS_PERSONAS + CSUITE_PERSONAS

# Tools that are known to have environmental deps (not import-broken)
ENV_DEPENDENT_TOOLS = {
    "browser_agent",  # needs playwright
    "code_execution_tool",  # needs paramiko
    "browser_open",  # disabled (._py)
    "browser_do",  # disabled (._py)
    "browser",  # disabled (._py)
}

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def composer():
    c = AgentComposer()
    c.clear_cache()
    return c


@pytest.fixture(params=CSUITE_PERSONAS)
def csuite_persona(request):
    return request.param


@pytest.fixture(params=ALL_PERSONAS)
def any_persona(request):
    return request.param


# ── Phase 1: Persona Load & Tool Resolution ──────────────────────────────────


class TestPersonaLoad:
    """Verify AgentComposer loads and resolves all personas correctly."""

    def test_manifest_exists(self, any_persona):
        manifest_path = AGENTS_DIR / any_persona / "manifest.yaml"
        assert manifest_path.is_file(), f"Missing manifest for {any_persona}"

    def test_manifest_parses(self, any_persona):
        manifest_path = AGENTS_DIR / any_persona / "manifest.yaml"
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert data.get("name") == any_persona

    def test_composer_loads_manifest(self, composer, any_persona):
        manifest = composer.load_manifest(any_persona)
        assert manifest, f"Composer returned empty manifest for {any_persona}"
        assert manifest["name"] == any_persona

    def test_inheritance_resolves(self, composer, any_persona):
        chain = composer.resolve_inheritance(any_persona)
        assert len(chain) >= 1
        assert chain[-1] == any_persona
        # All C-suite and MOS personas inherit from default
        if any_persona in CSUITE_PERSONAS or any_persona in MOS_PERSONAS:
            assert "default" in chain

    def test_compose_produces_valid_config(self, composer, any_persona):
        cfg = composer.compose([any_persona])
        assert isinstance(cfg, AgentProfileConfig)
        assert cfg.name == any_persona
        warnings = composer.validate_config(cfg)
        assert warnings == [], f"Validation warnings for {any_persona}: {warnings}"

    def test_compose_has_capabilities(self, composer, any_persona):
        cfg = composer.compose([any_persona])
        assert len(cfg.capabilities) > 0, f"{any_persona} has no capabilities"

    def test_compose_has_tools(self, composer, any_persona):
        cfg = composer.compose([any_persona])
        includes = cfg.tools.get("include", [])
        assert len(includes) > 0, f"{any_persona} has no tool includes"

    def test_compose_has_memory_areas(self, composer, any_persona):
        cfg = composer.compose([any_persona])
        assert len(cfg.memory_areas) > 0, f"{any_persona} has no memory areas"


class TestToolResolution:
    """Verify every tool referenced in persona manifests has a backing file."""

    @staticmethod
    def _get_tool_files():
        """Return set of tool names from python/tools/ directory."""
        return {f.stem for f in TOOLS_DIR.iterdir() if f.suffix == ".py" and not f.name.startswith("_")}

    @staticmethod
    def _get_disabled_tool_files():
        """Return set of tool names from disabled (._py) files."""
        return {f.stem for f in TOOLS_DIR.iterdir() if f.name.endswith("._py")}

    def test_csuite_tools_resolve_to_files(self, composer, csuite_persona):
        """Every non-wildcard tool in C-suite includes has a python/tools/*.py file."""
        cfg = composer.compose([csuite_persona])
        available = self._get_tool_files()
        disabled = self._get_disabled_tool_files()

        missing = []
        for tool in cfg.tools.get("include", []):
            if "*" in tool or "?" in tool:
                continue  # wildcard patterns
            if tool in available:
                continue
            if tool in disabled:
                continue  # intentionally disabled
            missing.append(tool)

        assert missing == [], f"{csuite_persona} references tools with no backing file: {missing}"

    def test_csuite_excludes_do_not_overlap_includes(self, composer, csuite_persona):
        """No tool should match both include and exclude patterns."""
        cfg = composer.compose([csuite_persona])
        includes = cfg.tools.get("include", [])
        excludes = cfg.tools.get("exclude", [])

        overlapping = []
        for exc in excludes:
            for inc in includes:
                if fnmatch.fnmatch(exc, inc) or fnmatch.fnmatch(inc, exc):
                    # Only flag if the explicit name matches both
                    if not ("*" in exc or "?" in exc):
                        if any(fnmatch.fnmatch(exc, i) for i in includes):
                            overlapping.append(exc)

        assert overlapping == [], f"{csuite_persona} has tools in both include and exclude: {overlapping}"

    def test_tool_allowed_respects_excludes(self, composer):
        """CFO should NOT be allowed to use code_execution_tool."""
        cfg = composer.compose(["cfo"])
        assert not composer.tool_allowed(cfg, "code_execution_tool")
        assert not composer.tool_allowed(cfg, "deployment_execute")
        assert not composer.tool_allowed(cfg, "git_tool")

    def test_tool_allowed_permits_includes(self, composer):
        """CFO should be allowed to use stripe_payments and finance_manager."""
        cfg = composer.compose(["cfo"])
        assert composer.tool_allowed(cfg, "stripe_payments")
        assert composer.tool_allowed(cfg, "finance_manager")
        assert composer.tool_allowed(cfg, "payment_dunning")

    def test_coo_cannot_use_finance_tools(self, composer):
        """COO explicitly excludes finance tools — delegates to CFO."""
        cfg = composer.compose(["coo"])
        assert not composer.tool_allowed(cfg, "stripe_payments")
        assert not composer.tool_allowed(cfg, "payment_dunning")
        assert not composer.tool_allowed(cfg, "finance_manager")

    def test_coo_can_use_ops_tools(self, composer):
        """COO should have workflow, linear, scheduler."""
        cfg = composer.compose(["coo"])
        assert composer.tool_allowed(cfg, "workflow_engine")
        assert composer.tool_allowed(cfg, "linear_integration")
        assert composer.tool_allowed(cfg, "scheduler")

    def test_cmo_has_brand_voice(self, composer):
        """CMO should have brand_voice as a mandatory quality gate."""
        cfg = composer.compose(["cmo"])
        assert composer.tool_allowed(cfg, "brand_voice")

    def test_cso_has_sales_tools(self, composer):
        """CSO should have sales_generator and customer_lifecycle."""
        cfg = composer.compose(["cso"])
        assert composer.tool_allowed(cfg, "sales_generator")
        assert composer.tool_allowed(cfg, "customer_lifecycle")


# ── Phase 2: EXECUTIVE Memory Area ──────────────────────────────────────────


class TestExecutiveMemory:
    """Verify EXECUTIVE memory area is properly declared and accessible."""

    def test_executive_in_memory_area_enum(self):
        """Memory.Area enum must include EXECUTIVE."""
        assert hasattr(Memory.Area, "EXECUTIVE")
        assert Memory.Area.EXECUTIVE.value == "executive"

    def test_all_csuite_declare_executive(self, composer, csuite_persona):
        """Every C-suite persona must have EXECUTIVE in memory areas."""
        cfg = composer.compose([csuite_persona])
        assert "EXECUTIVE" in cfg.memory_areas, (
            f"{csuite_persona} missing EXECUTIVE in memory_areas: {cfg.memory_areas}"
        )

    def test_mos_personas_lack_executive(self, composer):
        """MOS specialist personas should NOT have EXECUTIVE memory area."""
        for persona in MOS_PERSONAS:
            cfg = composer.compose([persona])
            assert "EXECUTIVE" not in cfg.memory_areas, f"MOS persona {persona} should not have EXECUTIVE access"

    def test_all_enum_areas_valid(self):
        """Every Area enum value should be a non-empty lowercase string."""
        for area in Memory.Area:
            assert area.value
            assert area.value == area.value.lower()
            assert area.value.isalpha()


# ── Phase 3: Delegation Paths ────────────────────────────────────────────────


class TestDelegationPaths:
    """Verify auto_delegate targets are valid persona names and delegation is asymmetric."""

    def test_auto_delegate_targets_exist(self, composer, csuite_persona):
        """Every auto_delegate target must be a valid agent profile directory."""
        manifest = composer.load_manifest(csuite_persona)
        auto_delegate = manifest.get("behavior", {}).get("auto_delegate", {})

        invalid = []
        for task_type, target in auto_delegate.items():
            target_dir = AGENTS_DIR / target
            if not target_dir.is_dir():
                invalid.append(f"{task_type} → {target}")

        assert invalid == [], f"{csuite_persona} delegates to non-existent profiles: {invalid}"

    def test_csuite_have_call_subordinate(self, composer, csuite_persona):
        """Every C-suite persona must include call_subordinate tool."""
        cfg = composer.compose([csuite_persona])
        assert composer.tool_allowed(cfg, "call_subordinate"), f"{csuite_persona} lacks call_subordinate tool"

    def test_no_csuite_peer_delegation(self):
        """C-suite personas should NOT auto_delegate to each other."""
        composer = AgentComposer()
        csuite_set = set(CSUITE_PERSONAS)

        violations = []
        for persona in CSUITE_PERSONAS:
            manifest = composer.load_manifest(persona)
            auto_delegate = manifest.get("behavior", {}).get("auto_delegate", {})
            for task_type, target in auto_delegate.items():
                if target in csuite_set:
                    violations.append(f"{persona}.{task_type} → {target}")

        assert violations == [], f"C-suite peers should not auto_delegate to each other: {violations}"

    def test_coo_delegates_infra_to_devops(self, composer):
        """COO should delegate infrastructure tasks to devops."""
        manifest = composer.load_manifest("coo")
        ad = manifest.get("behavior", {}).get("auto_delegate", {})
        assert ad.get("infrastructure_tasks") == "devops"

    def test_cfo_delegates_analysis_to_analytics(self, composer):
        """CFO should delegate analysis tasks to analytics."""
        manifest = composer.load_manifest("cfo")
        ad = manifest.get("behavior", {}).get("auto_delegate", {})
        assert ad.get("analysis_tasks") == "analytics"


# ── Phase 4: C-Suite Peer Coordination ───────────────────────────────────────


class TestPeerCoordination:
    """Verify the shared EXECUTIVE memory contract between C-suite peers."""

    def test_all_csuite_share_executive_memory(self, composer):
        """All C-suite personas must have EXECUTIVE in their memory areas."""
        for persona in CSUITE_PERSONAS:
            cfg = composer.compose([persona])
            assert "EXECUTIVE" in cfg.memory_areas

    def test_csuite_shared_with_includes_peers(self, composer):
        """Each C-suite persona's shared_with should include other C-suite peers."""
        for persona in CSUITE_PERSONAS:
            manifest = composer.load_manifest(persona)
            shared_with = manifest.get("memory", {}).get("shared_with", [])
            peers = [p for p in CSUITE_PERSONAS if p != persona]
            missing_peers = [p for p in peers if p not in shared_with]
            assert missing_peers == [], f"{persona} missing C-suite peers in shared_with: {missing_peers}"

    def test_cfo_owns_financial_tools_exclusively(self, composer):
        """Only CFO should have stripe_payments, payment_dunning, finance_manager."""
        financial_tools = ["stripe_payments", "payment_dunning", "finance_manager"]
        for persona in CSUITE_PERSONAS:
            cfg = composer.compose([persona])
            for tool in financial_tools:
                if persona == "cfo":
                    assert composer.tool_allowed(cfg, tool), f"CFO should own {tool}"
                else:
                    assert not composer.tool_allowed(cfg, tool), f"{persona} should NOT have {tool} — CFO exclusive"

    def test_cmo_owns_brand_voice_exclusively(self, composer):
        """Only CMO should have brand_voice tool among C-suite."""
        for persona in CSUITE_PERSONAS:
            cfg = composer.compose([persona])
            if persona == "cmo":
                assert composer.tool_allowed(cfg, "brand_voice")
            else:
                assert not composer.tool_allowed(cfg, "brand_voice"), (
                    f"{persona} should NOT have brand_voice — CMO exclusive"
                )

    def test_tool_confirmation_required_for_cfo_mutations(self, composer):
        """CFO must require tool_confirmation for financial tools."""
        manifest = composer.load_manifest("cfo")
        confirmations = manifest.get("behavior", {}).get("tool_confirmation", [])
        for tool in ["stripe_payments", "payment_dunning", "finance_manager"]:
            assert tool in confirmations, f"CFO missing tool_confirmation for {tool}"

    def test_coo_tool_confirmation_for_comms(self, composer):
        """COO must require tool_confirmation for email and comms tools."""
        manifest = composer.load_manifest("coo")
        confirmations = manifest.get("behavior", {}).get("tool_confirmation", [])
        assert any("email" in c for c in confirmations), "COO missing email confirmation"

    def test_max_iterations_set(self, composer, csuite_persona):
        """Every C-suite persona must have a positive max_iterations."""
        cfg = composer.compose([csuite_persona])
        max_iter = cfg.behavior.get("max_iterations", 0)
        assert max_iter > 0, f"{csuite_persona} has invalid max_iterations: {max_iter}"

    def test_csuite_response_tool_available(self, composer, csuite_persona):
        """Every C-suite persona must have the response tool."""
        cfg = composer.compose([csuite_persona])
        assert composer.tool_allowed(cfg, "response")


# ── Phase 5: Cross-tier Consistency ──────────────────────────────────────────


class TestCrossTierConsistency:
    """Verify MOS and C-suite tiers compose consistently."""

    def test_all_personas_have_memory_tools(self, composer, any_persona):
        """Every persona should have memory_* wildcard access."""
        cfg = composer.compose([any_persona])
        assert composer.tool_allowed(cfg, "memory_save")
        assert composer.tool_allowed(cfg, "memory_load")

    def test_all_personas_have_response(self, composer, any_persona):
        """Every persona must have the response tool."""
        cfg = composer.compose([any_persona])
        assert composer.tool_allowed(cfg, "response")

    def test_mos_personas_inherit_from_default(self, composer):
        """All MOS personas should inherit from default."""
        for persona in MOS_PERSONAS:
            chain = composer.resolve_inheritance(persona)
            assert "default" in chain, f"{persona} does not inherit from default"

    def test_csuite_personas_inherit_from_default(self, composer):
        """All C-suite personas should inherit from default."""
        for persona in CSUITE_PERSONAS:
            chain = composer.resolve_inheritance(persona)
            assert "default" in chain, f"{persona} does not inherit from default"

    def test_no_circular_inheritance(self, composer):
        """No persona should have circular inheritance."""
        for persona in ALL_PERSONAS:
            chain = composer.resolve_inheritance(persona)
            assert len(chain) == len(set(chain)), f"{persona} has circular inheritance: {chain}"
