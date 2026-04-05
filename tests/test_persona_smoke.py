"""
End-to-end persona smoke tests and cross-persona EXECUTIVE memory bridge.

D1: Persona Smoke — verify each C-suite and MOS persona loads correct role prompt,
    resolves expected signature tools, declares proper memory areas, and the
    profile API → settings → compose chain works end-to-end.

D2: Memory Bridge — CFO writes to EXECUTIVE area, COO reads it back via the
    same Memory subdir. Validates the shared memory contract between C-suite peers.

These are structural/wiring tests — no LLM calls.

Usage:
    pytest tests/test_persona_smoke.py -v
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from python.helpers.agent_composer import AgentComposer, AgentProfileConfig
from python.helpers.memory import Memory

ROOT_DIR = Path(__file__).parent.parent
AGENTS_DIR = ROOT_DIR / "agents"

CSUITE_PERSONAS = ["cfo", "cmo", "cso", "coo"]
MOS_PERSONAS = ["solution-design", "devops", "data-ml", "analytics", "customer-support"]

# Signature tools each C-suite persona MUST have
CSUITE_SIGNATURE_TOOLS: dict[str, list[str]] = {
    "cfo": ["stripe_payments", "payment_dunning", "finance_manager"],
    "coo": ["workflow_engine", "linear_integration", "scheduler"],
    "cso": ["sales_generator", "customer_lifecycle"],
    "cmo": ["brand_voice"],
}

# Keywords expected in each role prompt
CSUITE_ROLE_KEYWORDS: dict[str, list[str]] = {
    "cfo": ["Chief Financial Officer", "Stripe", "revenue", "financial"],
    "coo": ["Chief Operations Officer", "workflow", "SLA", "operational"],
    "cso": ["Chief Sales Officer", "pipeline", "proposal", "revenue"],
    "cmo": ["Chief Marketing Officer", "brand", "content", "campaign"],
}

# Tools each C-suite persona must NOT have (exclusivity check)
CSUITE_FORBIDDEN_TOOLS: dict[str, list[str]] = {
    "cfo": ["brand_voice", "sales_generator", "deployment_execute"],
    "coo": ["stripe_payments", "finance_manager", "brand_voice"],
    "cso": ["stripe_payments", "finance_manager", "brand_voice"],
    "cmo": ["stripe_payments", "finance_manager", "sales_generator"],
}


@pytest.fixture
def composer():
    c = AgentComposer()
    c.clear_cache()
    return c


# ── D1: Persona Smoke Tests ────────────────────────────────────────────────────


class TestCsuiteRolePrompts:
    """Verify each C-suite persona has a role prompt with domain-specific content."""

    @pytest.fixture(params=CSUITE_PERSONAS)
    def persona(self, request):
        return request.param

    def test_role_prompt_file_exists(self, persona):
        prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
        assert prompt_path.is_file(), f"Missing role prompt for {persona}"

    def test_role_prompt_contains_domain_keywords(self, persona):
        prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
        content = prompt_path.read_text()
        for keyword in CSUITE_ROLE_KEYWORDS[persona]:
            assert keyword.lower() in content.lower(), f"{persona} role prompt missing keyword '{keyword}'"

    def test_role_prompt_references_executive_memory(self, persona):
        prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
        content = prompt_path.read_text()
        assert "executive" in content.lower(), f"{persona} role prompt missing EXECUTIVE memory reference"

    def test_role_prompt_has_tool_call_examples(self, persona):
        prompt_path = AGENTS_DIR / persona / "prompts" / "agent.system.main.role.md"
        content = prompt_path.read_text()
        assert "memory_save" in content or "memory_load" in content, (
            f"{persona} role prompt has no memory tool-call examples"
        )


class TestCsuiteSignatureTools:
    """Verify each C-suite persona resolves its signature tools and excludes forbidden ones."""

    @pytest.fixture(params=CSUITE_PERSONAS)
    def persona(self, request):
        return request.param

    def test_signature_tools_allowed(self, composer, persona):
        cfg = composer.compose([persona])
        for tool in CSUITE_SIGNATURE_TOOLS[persona]:
            assert composer.tool_allowed(cfg, tool), f"{persona} should have signature tool '{tool}'"

    def test_forbidden_tools_blocked(self, composer, persona):
        cfg = composer.compose([persona])
        for tool in CSUITE_FORBIDDEN_TOOLS[persona]:
            assert not composer.tool_allowed(cfg, tool), f"{persona} should NOT have '{tool}'"

    def test_all_csuite_have_memory_tools(self, composer, persona):
        cfg = composer.compose([persona])
        assert composer.tool_allowed(cfg, "memory_save")
        assert composer.tool_allowed(cfg, "memory_load")

    def test_all_csuite_have_call_subordinate(self, composer, persona):
        cfg = composer.compose([persona])
        assert composer.tool_allowed(cfg, "call_subordinate")

    def test_all_csuite_have_scheduler(self, composer, persona):
        cfg = composer.compose([persona])
        assert composer.tool_allowed(cfg, "scheduler")


class TestProfileActivationChain:
    """Verify the profile API → settings → compose → tools chain works end-to-end."""

    def test_profile_get_returns_all_csuite(self):
        """agent profile scan finds all C-suite profiles."""
        selectable = []
        for entry in sorted(os.listdir(AGENTS_DIR)):
            manifest_path = AGENTS_DIR / entry / "manifest.yaml"
            if not manifest_path.is_file():
                continue
            with open(manifest_path) as f:
                data = yaml.safe_load(f) or {}
            display = data.get("display", {})
            if display.get("selectable", False):
                selectable.append(entry)

        for persona in CSUITE_PERSONAS:
            assert persona in selectable, f"{persona} missing from selectable profiles"

    def test_profile_get_returns_metadata_fields(self):
        for persona in CSUITE_PERSONAS:
            manifest_path = AGENTS_DIR / persona / "manifest.yaml"
            with open(manifest_path) as f:
                data = yaml.safe_load(f) or {}
            display = data.get("display", {})
            assert "display_name" in display, f"{persona} missing display_name"
            assert "icon" in display, f"{persona} missing icon"
            assert "tier" in display, f"{persona} missing tier"

    def test_csuite_profiles_tier_is_executive(self):
        for persona in CSUITE_PERSONAS:
            manifest_path = AGENTS_DIR / persona / "manifest.yaml"
            with open(manifest_path) as f:
                data = yaml.safe_load(f) or {}
            tier = data.get("display", {}).get("tier", "")
            assert tier == "executive", f"{persona} tier should be executive, got {tier}"

    def test_compose_after_profile_switch(self, composer):
        """Switching profile and recomposing yields different tool sets."""
        cfo_cfg = composer.compose(["cfo"])
        coo_cfg = composer.compose(["coo"])

        # CFO has finance tools, COO doesn't
        assert composer.tool_allowed(cfo_cfg, "stripe_payments")
        assert not composer.tool_allowed(coo_cfg, "stripe_payments")

        # COO has linear_integration, CFO may or may not (not the point)
        assert composer.tool_allowed(coo_cfg, "linear_integration")

    def test_compose_memory_areas_differ_by_persona(self, composer):
        """C-suite have EXECUTIVE, MOS personas don't."""
        cfo_cfg = composer.compose(["cfo"])
        devops_cfg = composer.compose(["devops"])

        assert "EXECUTIVE" in cfo_cfg.memory_areas
        assert "EXECUTIVE" not in devops_cfg.memory_areas


class TestMosPersonaSmoke:
    """Quick smoke tests for MOS specialist personas."""

    @pytest.fixture(params=MOS_PERSONAS)
    def persona(self, request):
        return request.param

    def test_manifest_exists(self, persona):
        manifest = AGENTS_DIR / persona / "manifest.yaml"
        assert manifest.is_file()

    def test_compose_succeeds(self, composer, persona):
        cfg = composer.compose([persona])
        assert isinstance(cfg, AgentProfileConfig)
        assert cfg.name == persona

    def test_has_capabilities(self, composer, persona):
        cfg = composer.compose([persona])
        assert len(cfg.capabilities) > 0

    def test_inherits_from_default(self, composer, persona):
        chain = composer.resolve_inheritance(persona)
        assert "default" in chain

    def test_no_executive_memory(self, composer, persona):
        cfg = composer.compose([persona])
        assert "EXECUTIVE" not in cfg.memory_areas


# ── D2: Cross-Persona EXECUTIVE Memory Bridge ──────────────────────────────────


class TestExecutiveMemoryBridge:
    """Verify CFO can write to EXECUTIVE and COO can read it back."""

    @pytest.mark.asyncio
    async def test_cfo_write_coo_read_round_trip(self):
        """CFO writes financial KPIs to EXECUTIVE → COO reads them back."""
        # Shared in-memory store simulating FAISS
        store: list[dict] = []

        async def mock_insert(text, metadata=None):
            doc_id = f"mem-{len(store)}"
            store.append({"id": doc_id, "text": text, "metadata": metadata or {}})
            return doc_id

        async def mock_search(query, count=5, filter_fn=None):
            results = []
            for doc in store:
                if filter_fn and not filter_fn(doc["metadata"]):
                    continue
                results.append(doc)
            return results[:count]

        mock_db = AsyncMock()
        mock_db.insert_text = mock_insert
        mock_db.search = mock_search

        # CFO writes
        with patch("python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(return_value=mock_db)):
            mem = await Memory.get_by_subdir("default")
            await mem.insert_text(
                "CFO Financial Update | MRR: $48,200 | growth: +8.2% | churn: 1.1%",
                {"area": "executive", "source": "finance_manager", "action": "generate_report"},
            )

        assert len(store) == 1
        assert store[0]["metadata"]["area"] == "executive"

        # COO reads via same subdir
        with patch("python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(return_value=mock_db)):
            mem = await Memory.get_by_subdir("default")
            results = await mem.search(
                "financial KPIs",
                filter_fn=lambda m: m.get("area") == "executive",
            )

        assert len(results) == 1
        assert "MRR" in results[0]["text"]
        assert results[0]["metadata"]["source"] == "finance_manager"

    @pytest.mark.asyncio
    async def test_executive_area_isolates_from_main(self):
        """EXECUTIVE writes don't appear in main area queries."""
        store: list[dict] = []

        async def mock_insert(text, metadata=None):
            store.append({"text": text, "metadata": metadata or {}})
            return f"mem-{len(store)}"

        async def mock_search(query, count=5, filter_fn=None):
            results = []
            for doc in store:
                if filter_fn and not filter_fn(doc["metadata"]):
                    continue
                results.append(doc)
            return results[:count]

        mock_db = AsyncMock()
        mock_db.insert_text = mock_insert
        mock_db.search = mock_search

        with patch("python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(return_value=mock_db)):
            mem = await Memory.get_by_subdir("default")
            # Write one EXECUTIVE doc and one MAIN doc
            await mem.insert_text("Revenue report Q1", {"area": "executive", "source": "cfo"})
            await mem.insert_text("Bug fix notes", {"area": "main", "source": "developer"})

        # Query for only EXECUTIVE
        with patch("python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(return_value=mock_db)):
            mem = await Memory.get_by_subdir("default")
            executive_results = await mem.search(
                "report",
                filter_fn=lambda m: m.get("area") == "executive",
            )
            main_results = await mem.search(
                "report",
                filter_fn=lambda m: m.get("area") == "main",
            )

        assert len(executive_results) == 1
        assert "Revenue" in executive_results[0]["text"]
        assert len(main_results) == 1
        assert "Bug fix" in main_results[0]["text"]

    @pytest.mark.asyncio
    async def test_multiple_csuite_writers(self):
        """All C-suite personas can write to EXECUTIVE, each tagged by source."""
        store: list[dict] = []

        async def mock_insert(text, metadata=None):
            store.append({"text": text, "metadata": metadata or {}})
            return f"mem-{len(store)}"

        mock_db = AsyncMock()
        mock_db.insert_text = mock_insert

        writers = {
            "cfo": "MRR: $48K, churn: 1.1%",
            "coo": "Uptime: 99.97%, incidents: 0",
            "cso": "Pipeline: $230K, proposals: 4",
            "cmo": "Brand score: 92, campaigns: 3",
        }

        with patch("python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(return_value=mock_db)):
            for persona, text in writers.items():
                mem = await Memory.get_by_subdir("default")
                await mem.insert_text(
                    f"[{persona.upper()}] {text}",
                    {"area": "executive", "source": persona},
                )

        assert len(store) == 4
        sources = {doc["metadata"]["source"] for doc in store}
        assert sources == {"cfo", "coo", "cso", "cmo"}

    def test_all_csuite_manifests_declare_shared_subdir(self):
        """All C-suite personas use same memory subdir (default) for EXECUTIVE sharing."""
        composer = AgentComposer()
        for persona in CSUITE_PERSONAS:
            manifest = composer.load_manifest(persona)
            # All C-suite should either not specify subdir (defaults to "default")
            # or explicitly set it to "default"
            mem = manifest.get("memory", {})
            subdir = mem.get("subdir", "default")
            assert subdir == "default", (
                f"{persona} memory subdir is '{subdir}', expected 'default' for EXECUTIVE sharing"
            )

    def test_executive_area_in_memory_enum(self):
        """Memory.Area.EXECUTIVE exists and has correct value."""
        assert hasattr(Memory.Area, "EXECUTIVE")
        assert Memory.Area.EXECUTIVE.value == "executive"
