"""
J-series validation tests.

J1: C-Suite persona live smoke tests — manifest, role prompt, tool lists, AgentMesh routing
J2: EXECUTIVE memory bridge — shared memory area, cross-persona access
J3: Scheduler task execution — MOS 5-task + WBM 9-task registration and structure
J4: StayHive hospitality workflow — WBM scheduler, tenant gating, task uniqueness
J5: Progressive trust gate — TrustLevel/ToolRisk matrix, gate extension, always-allow
J6: Full E2E suite measurement — file count, function count, fixture coverage
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"

CSUITE_PERSONAS = ["coo", "cso", "cmo", "cfo"]

# Expected C-suite → profile mapping from agentmesh_task_handler.py
EXPECTED_CSUITE_CATEGORIES = {
    "financial_report": "cfo",
    "revenue_analysis": "cfo",
    "payment_dunning": "cfo",
    "ops_digest": "coo",
    "sla_enforcement": "coo",
    "devops": "coo",
    "sales_pipeline": "cso",
    "proposal_generation": "cso",
    "brand_review": "cmo",
    "content_calendar": "cmo",
    "marketing": "cmo",
}


def _load_manifest(persona: str) -> dict:
    path = AGENTS_DIR / persona / "manifest.yaml"
    assert path.exists(), f"Missing manifest for {persona}"
    with path.open() as f:
        return yaml.safe_load(f)


# ── J1: C-Suite Persona Live Smoke Tests ───────────────────────────────────


class TestCSuitePersonas:
    """Validate all 4 C-suite persona manifests and role prompts."""

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_exists_and_parses(self, persona: str):
        manifest = _load_manifest(persona)
        assert manifest["name"] == persona

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_tier_is_executive(self, persona: str):
        """C-suite personas must be marked as executive tier."""
        manifest = _load_manifest(persona)
        display = manifest.get("display", {})
        assert display.get("tier") == "executive", f"{persona} not marked as executive tier"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_inherits_default(self, persona: str):
        manifest = _load_manifest(persona)
        assert manifest.get("inherits") == "default"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_has_min_5_capabilities(self, persona: str):
        manifest = _load_manifest(persona)
        caps = manifest.get("capabilities", [])
        assert len(caps) >= 5, f"{persona} has only {len(caps)} capabilities"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_has_tool_include_list(self, persona: str):
        manifest = _load_manifest(persona)
        include = manifest.get("tools", {}).get("include", [])
        assert len(include) >= 5, f"{persona} tools.include has only {len(include)} entries"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_has_tool_exclude_list(self, persona: str):
        """C-suite personas must exclude tools outside their domain."""
        manifest = _load_manifest(persona)
        exclude = manifest.get("tools", {}).get("exclude", [])
        assert len(exclude) >= 1, f"{persona} has no tool exclusions"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_declares_executive_memory(self, persona: str):
        """C-suite personas must have EXECUTIVE in their memory areas."""
        manifest = _load_manifest(persona)
        areas = manifest.get("memory", {}).get("areas", [])
        assert "EXECUTIVE" in areas, f"{persona} missing EXECUTIVE memory area"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_manifest_has_auto_delegate(self, persona: str):
        """C-suite personas should delegate to specialist personas."""
        manifest = _load_manifest(persona)
        delegates = manifest.get("behavior", {}).get("auto_delegate", {})
        assert len(delegates) >= 1, f"{persona} has no auto_delegate entries"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_role_prompt_exists_and_substantive(self, persona: str):
        prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
        assert prompt_path.exists(), f"Missing role prompt for {persona}"
        content = prompt_path.read_text()
        assert len(content) >= 3000, f"{persona} role prompt too short: {len(content)} chars"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_context_md_exists(self, persona: str):
        ctx = AGENTS_DIR / persona / "_context.md"
        assert ctx.exists(), f"Missing _context.md for {persona}"

    def test_agentmesh_routes_all_csuite_categories(self):
        """CATEGORY_PROFILE_MAP must route all expected C-suite categories."""
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        for category, expected_profile in EXPECTED_CSUITE_CATEGORIES.items():
            actual = CATEGORY_PROFILE_MAP.get(category)
            assert actual == expected_profile, (
                f"Category '{category}' routes to '{actual}', expected '{expected_profile}'"
            )

    def test_agentmesh_registers_executive_event_handlers(self):
        """register_task_handlers must register executive.* event handlers."""
        src = (ROOT / "python" / "helpers" / "agentmesh_task_handler.py").read_text()
        for event in [
            "executive.financial_report",
            "executive.ops_digest",
            "executive.sales_update",
            "executive.brand_review",
        ]:
            assert event in src, f"Missing event handler registration for '{event}'"

    def test_coo_excludes_stripe(self):
        """COO must not have access to stripe_payments (CFO domain)."""
        manifest = _load_manifest("coo")
        exclude = manifest.get("tools", {}).get("exclude", [])
        assert "stripe_payments" in exclude, "COO should exclude stripe_payments"

    def test_cfo_includes_finance(self):
        """CFO must include finance_manager tool."""
        manifest = _load_manifest("cfo")
        include = manifest.get("tools", {}).get("include", [])
        assert "finance_manager" in include, "CFO should include finance_manager"

    def test_cmo_excludes_deployment(self):
        """CMO must not have access to deployment tools."""
        manifest = _load_manifest("cmo")
        exclude = manifest.get("tools", {}).get("exclude", [])
        has_deploy_exclusion = any("deploy" in e.lower() for e in exclude)
        assert has_deploy_exclusion, "CMO should exclude deployment tools"


# ── J2: EXECUTIVE Memory Bridge Validation ─────────────────────────────────


class TestExecutiveMemoryBridge:
    """Validate EXECUTIVE memory area and cross-persona sharing."""

    def test_executive_area_enum_exists(self):
        from python.helpers.memory import Memory

        assert hasattr(Memory.Area, "EXECUTIVE")
        assert Memory.Area.EXECUTIVE.value == "executive"

    def test_all_memory_areas_present(self):
        """Memory.Area should have MAIN, FRAGMENTS, SOLUTIONS, INSTRUMENTS, EXECUTIVE."""
        from python.helpers.memory import Memory

        expected = {"main", "fragments", "solutions", "instruments", "executive"}
        actual = {a.value for a in Memory.Area}
        assert expected.issubset(actual), f"Missing areas: {expected - actual}"

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_persona_declares_executive_area(self, persona: str):
        manifest = _load_manifest(persona)
        areas = manifest.get("memory", {}).get("areas", [])
        assert "EXECUTIVE" in areas

    @pytest.mark.parametrize("persona", CSUITE_PERSONAS)
    def test_persona_shares_memory_with_peers(self, persona: str):
        """Each C-suite persona should share memory with at least 2 other personas."""
        manifest = _load_manifest(persona)
        shared = manifest.get("memory", {}).get("shared_with", [])
        assert len(shared) >= 2, f"{persona} shares with only {len(shared)} peers"

    def test_csuite_shared_memory_is_bidirectional(self):
        """If COO shares with CFO, CFO should share with COO."""
        manifests = {p: _load_manifest(p) for p in CSUITE_PERSONAS}
        for persona_a in CSUITE_PERSONAS:
            shared_a = set(manifests[persona_a].get("memory", {}).get("shared_with", []))
            for persona_b in CSUITE_PERSONAS:
                if persona_a == persona_b:
                    continue
                if persona_b in shared_a:
                    shared_b = set(manifests[persona_b].get("memory", {}).get("shared_with", []))
                    assert persona_a in shared_b, f"{persona_a} shares with {persona_b} but not vice versa"

    def test_memory_consolidation_references_executive(self):
        """The weekly memory consolidation task must target the executive area."""
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        consolidation = [t for t in _MOS_TASKS if "consolidation" in t["name"]]
        assert len(consolidation) == 1
        assert "executive" in consolidation[0]["prompt"].lower()


# ── J3: Scheduler Task Execution Validation ────────────────────────────────


class TestSchedulerTaskExecution:
    """Validate all MOS and WBM scheduled tasks."""

    def test_mos_has_exactly_5_tasks(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        assert len(_MOS_TASKS) == 5

    def test_mos_task_names_unique(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        names = [t["name"] for t in _MOS_TASKS]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_mos_tasks_have_valid_cron_fields(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        for task in _MOS_TASKS:
            sched = task["schedule"]
            for field in ("minute", "hour", "day", "month", "weekday"):
                assert field in sched, f"Task '{task['name']}' missing schedule field '{field}'"
                assert isinstance(sched[field], str), f"Schedule field '{field}' must be a string"

    def test_mos_tasks_have_prompts(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        for task in _MOS_TASKS:
            assert "prompt" in task, f"Task '{task['name']}' missing prompt"
            assert len(task["prompt"]) > 30, f"Task '{task['name']}' prompt too short"

    def test_mos_seed_function_importable(self):
        from python.helpers.mos_scheduler_init import seed_mos_tasks

        assert callable(seed_mos_tasks)

    def test_mos_expected_task_names(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        expected = {
            "mos-linear-to-motion",
            "mos-linear-activity-digest",
            "mos-analytics-daily-digest",
            "mos-support-queue-check",
            "mos-memory-consolidation",
        }
        actual = {t["name"] for t in _MOS_TASKS}
        assert actual == expected, f"Unexpected tasks: {actual.symmetric_difference(expected)}"

    def test_mos_linear_to_motion_runs_3x_daily_weekdays(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-linear-to-motion")
        assert task["schedule"]["hour"] == "8,12,17"
        assert task["schedule"]["weekday"] == "1-5"

    def test_mos_memory_consolidation_runs_weekly(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-memory-consolidation")
        assert task["schedule"]["weekday"] == "0"  # Sunday


# ── J4: StayHive Hospitality Workflow Validation ───────────────────────────


class TestStayHiveHospitality:
    """Validate WBM hospitality scheduler, tenant gating, and workflows."""

    def test_wbm_has_exactly_9_tasks(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        assert len(_WBM_TASKS) == 9

    def test_wbm_task_names_unique(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        names = [t["name"] for t in _WBM_TASKS]
        assert len(names) == len(set(names))

    def test_wbm_tasks_have_valid_cron_fields(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        for task in _WBM_TASKS:
            sched = task["schedule"]
            for field in ("minute", "hour", "day", "month", "weekday"):
                assert field in sched, f"Task '{task['name']}' missing '{field}'"

    def test_wbm_daily_tasks_count(self):
        """3 daily tasks: ops brief, checkin scan, occupancy check."""
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        daily = [
            t
            for t in _WBM_TASKS
            if t["schedule"]["day"] == "*" and t["schedule"]["month"] == "*" and t["schedule"]["weekday"] == "*"
        ]
        assert len(daily) == 3, f"Expected 3 daily tasks, got {len(daily)}"

    def test_wbm_weekly_tasks_count(self):
        """2 weekly tasks: revenue review, competitor intel."""
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        weekly = [t for t in _WBM_TASKS if t["schedule"]["weekday"] not in ("*",)]
        # Filter out the ones that aren't daily (which have weekday=*)
        assert len(weekly) == 2

    def test_wbm_seasonal_task_runs_quarterly(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        seasonal = next(t for t in _WBM_TASKS if "seasonal" in t["name"])
        assert seasonal["schedule"]["month"] == "3,6,9,12"

    def test_wbm_yearly_task_runs_january(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        yearly = next(t for t in _WBM_TASKS if "yearly" in t["name"])
        assert yearly["schedule"]["month"] == "1"
        assert yearly["schedule"]["day"] == "1"

    def test_wbm_seed_function_requires_tenant_id(self):
        """seed_wbm_tasks should skip when WBM_TENANT_ID is not set."""
        import asyncio

        from python.helpers.wbm_scheduler_init import seed_wbm_tasks

        # Without WBM_TENANT_ID, should return skipped status
        result = asyncio.run(seed_wbm_tasks())
        assert result["status"] == "skipped"
        assert "WBM_TENANT_ID" in result.get("reason", "")

    def test_wbm_all_prompts_reference_wbm_embedded_workflow(self):
        """All WBM task prompts should reference wbm_embedded_workflow tool."""
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        for task in _WBM_TASKS:
            assert "wbm_embedded_workflow" in task["prompt"], (
                f"Task '{task['name']}' doesn't reference wbm_embedded_workflow"
            )

    def test_wbm_scheduler_test_file_exists(self):
        assert (ROOT / "tests" / "test_wbm_scheduler_init.py").exists()


# ── J5: Progressive Trust Gate Testing ─────────────────────────────────────


class TestProgressiveTrustGate:
    """Validate trust level system, risk registry, and gate extension."""

    def test_trust_level_enum_has_4_levels(self):
        from python.helpers.trust_system import TrustLevel

        assert len(TrustLevel) == 4
        assert TrustLevel.OBSERVER == 1
        assert TrustLevel.GUIDED == 2
        assert TrustLevel.COLLABORATIVE == 3
        assert TrustLevel.AUTONOMOUS == 4

    def test_tool_risk_enum_has_4_levels(self):
        from python.helpers.trust_system import ToolRisk

        assert len(ToolRisk) == 4
        assert ToolRisk.LOW == 1
        assert ToolRisk.CRITICAL == 4

    def test_risk_registry_covers_critical_tools(self):
        """TOOL_RISK_REGISTRY must classify all critical tools."""
        from python.helpers.trust_system import TOOL_RISK_REGISTRY, ToolRisk

        critical_tools = ["memory_delete", "memory_forget", "deployment_orchestrator", "stripe_payments"]
        for tool in critical_tools:
            assert TOOL_RISK_REGISTRY.get(tool) == ToolRisk.CRITICAL, f"Tool '{tool}' should be CRITICAL"

    def test_risk_registry_covers_low_risk_tools(self):
        from python.helpers.trust_system import TOOL_RISK_REGISTRY, ToolRisk

        low_tools = ["response", "input", "memory_load", "search_engine"]
        for tool in low_tools:
            assert TOOL_RISK_REGISTRY.get(tool) == ToolRisk.LOW, f"Tool '{tool}' should be LOW risk"

    def test_observer_requires_approval_for_everything(self):
        from python.helpers.trust_system import TrustLevel, requires_approval

        for tool in ["response", "memory_save", "email", "stripe_payments"]:
            # Observer requires approval for everything (except gate bypass)
            assert requires_approval(tool, TrustLevel.OBSERVER) is True

    def test_autonomous_only_blocks_critical(self):
        from python.helpers.trust_system import TrustLevel, requires_approval

        # LOW and MEDIUM should be auto-approved
        assert requires_approval("memory_load", TrustLevel.AUTONOMOUS) is False
        assert requires_approval("memory_save", TrustLevel.AUTONOMOUS) is False
        # HIGH should be auto-approved at AUTONOMOUS
        assert requires_approval("email", TrustLevel.AUTONOMOUS) is False
        # CRITICAL should still require approval
        assert requires_approval("stripe_payments", TrustLevel.AUTONOMOUS) is True

    def test_guided_blocks_medium_and_above(self):
        from python.helpers.trust_system import TrustLevel, requires_approval

        assert requires_approval("memory_load", TrustLevel.GUIDED) is False  # LOW
        assert requires_approval("memory_save", TrustLevel.GUIDED) is True  # MEDIUM
        assert requires_approval("email", TrustLevel.GUIDED) is True  # HIGH

    def test_collaborative_blocks_high_and_above(self):
        from python.helpers.trust_system import TrustLevel, requires_approval

        assert requires_approval("memory_load", TrustLevel.COLLABORATIVE) is False
        assert requires_approval("memory_save", TrustLevel.COLLABORATIVE) is False
        assert requires_approval("email", TrustLevel.COLLABORATIVE) is True  # HIGH
        assert requires_approval("stripe_payments", TrustLevel.COLLABORATIVE) is True

    def test_trust_gate_extension_exists(self):
        path = ROOT / "python" / "extensions" / "tool_execute_before" / "_25_trust_gate.py"
        assert path.exists()

    def test_trust_gate_has_bypass_list(self):
        """Trust gate must bypass essential tools (response, input, wait)."""
        content = (ROOT / "python" / "extensions" / "tool_execute_before" / "_25_trust_gate.py").read_text()
        for tool in ["response", "input", "wait"]:
            assert tool in content, f"Trust gate missing bypass for '{tool}'"

    def test_trust_level_info_has_all_levels(self):
        from python.helpers.trust_system import TRUST_LEVEL_INFO, TrustLevel

        for level in TrustLevel:
            assert level in TRUST_LEVEL_INFO, f"Missing info for {level.name}"
            info = TRUST_LEVEL_INFO[level]
            assert "name" in info
            assert "description" in info

    def test_always_allow_system_works(self):
        from python.helpers.trust_system import is_always_allowed

        settings = {"trust_always_allow": ["email", "code_execution_tool"]}
        assert is_always_allowed("email", settings) is True
        assert is_always_allowed("stripe_payments", settings) is False

    def test_default_settings_has_trust_fields(self):
        from python.helpers.settings_core import get_default_settings

        s = get_default_settings()
        assert "trust_always_allow" in s
        assert "trust_onboarded" in s

    def test_approval_fingerprint_stable(self):
        from python.helpers.trust_system import get_approval_fingerprint

        fp1 = get_approval_fingerprint("email", {"to": "a@b.com"})
        fp2 = get_approval_fingerprint("email", {"to": "a@b.com"})
        assert fp1 == fp2
        assert fp1 == "email:a@b.com"

    def test_e2e_trust_gate_tests_exist(self):
        """E2E trust gate tests must exist."""
        assert (ROOT / "tests" / "e2e" / "test_trust_gate_approval.py").exists()

    def test_e2e_trust_gate_has_sufficient_coverage(self):
        content = (ROOT / "tests" / "e2e" / "test_trust_gate_approval.py").read_text()
        test_count = content.count("def test_")
        assert test_count >= 4, f"Only {test_count} trust gate E2E tests"


# ── J6: Full E2E Suite Measurement ─────────────────────────────────────────


class TestE2ESuiteMeasurement:
    """Measure the E2E test suite size and infrastructure quality."""

    _E2E_DIR = ROOT / "tests" / "e2e"

    def test_at_least_40_e2e_test_files(self):
        count = len(list(self._E2E_DIR.glob("test_*.py")))
        assert count >= 40, f"Only {count} E2E test files (expected ≥40)"

    def test_at_least_200_e2e_test_functions(self):
        """Total test functions across all E2E files should be ≥200."""
        total = 0
        for f in self._E2E_DIR.glob("test_*.py"):
            content = f.read_text()
            total += content.count("def test_")
        assert total >= 200, f"Only {total} E2E test functions (expected ≥200)"

    def test_conftest_provides_core_fixtures(self):
        content = (self._E2E_DIR / "conftest.py").read_text()
        for fixture in ["app_server", "auth_cookies", "page", "authenticated_page", "warmup"]:
            assert fixture in content, f"conftest.py missing fixture: {fixture}"

    def test_helpers_module_complete(self):
        from tests.e2e.helpers import (
            api_get,
            api_get_tolerant,
            api_post,
            api_post_tolerant,
            cookie_header,
            get_csrf_token_and_cookies,
            with_retry,
        )

        for fn in [
            api_get,
            api_get_tolerant,
            api_post,
            api_post_tolerant,
            cookie_header,
            get_csrf_token_and_cookies,
            with_retry,
        ]:
            assert callable(fn)

    def test_e2e_covers_major_subsystems(self):
        """E2E suite should cover auth, chat, upload, settings, calendar, memory, trust."""
        filenames = {f.name for f in self._E2E_DIR.glob("test_*.py")}
        required_coverage = [
            "test_functional.py",  # auth, chat, upload
            "test_performance.py",  # load times, API SLA
            "test_calendar_e2e_api.py",  # calendar subsystem
            "test_memory_api.py",  # memory dashboard
            "test_trust_gate_approval.py",  # progressive trust
        ]
        for required in required_coverage:
            assert required in filenames, f"E2E suite missing: {required}"

    def test_unit_tests_exist_for_trust_system(self):
        assert (ROOT / "tests" / "unit" / "test_trust_system.py").exists()

    def test_persona_eval_tests_exist(self):
        assert (ROOT / "tests" / "test_persona_eval.py").exists()

    def test_integration_tests_cover_agentmesh(self):
        assert (ROOT / "tests" / "integration" / "test_agentmesh_bridge_integration.py").exists()

    def test_series_validation_chain_complete(self):
        """Validation test files E through J must all exist."""
        for series in ["e", "f", "g", "h", "i", "j"]:
            path = ROOT / "tests" / f"test_{series}_series_validation.py"
            assert path.exists(), f"Missing: {path.name}"
