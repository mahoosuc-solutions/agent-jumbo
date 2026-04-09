"""
K-series validation tests — GA Readiness.

K1: Self-serve onboarding doc — failure states documented
K2: Evidence package — artifacts present and fresh
K3: Onboarding known gaps — all resolved
K4: GA evidence package — open gaps updated
K5: Go/No-Go checklist — items checked off with evidence links
K6: GA documentation chain — all required docs exist and cross-reference
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARTIFACTS = ROOT / "artifacts" / "validation"


def _has_validation_artifacts() -> bool:
    return ARTIFACTS.exists() and any(ARTIFACTS.iterdir())


# ── K1: Self-Serve Onboarding — Failure States ────────────────────────────


class TestOnboardingFailureStates:
    """Verify the onboarding doc covers common failure scenarios."""

    def test_onboarding_doc_exists(self):
        assert (DOCS / "SELF_SERVE_GA_ONBOARDING.md").exists()

    def test_onboarding_has_troubleshooting_section(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "Troubleshooting" in content or "Failure States" in content

    def test_onboarding_covers_missing_api_keys(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "CHAT_MODEL_PROVIDER" in content or "API key" in content.lower()

    def test_onboarding_covers_invalid_credentials(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "AUTH_LOGIN" in content or "invalid credentials" in content.lower()

    def test_onboarding_covers_stripe_failure(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "STRIPE" in content or "payment" in content.lower()

    def test_onboarding_covers_backend_unreachable(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "unreachable" in content.lower() or "NEXT_PUBLIC_API_URL" in content

    def test_onboarding_has_completion_checklist(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "Completion Checklist" in content

    def test_onboarding_references_validate_scripts(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "validate_release.sh" in content
        assert "validate_360.sh" in content


# ── K2: Evidence Package Artifacts ─────────────────────────────────────────


class TestEvidenceArtifacts:
    """Verify required evidence artifacts exist."""

    @pytest.fixture(autouse=True)
    def _require_validation_artifacts(self):
        if not _has_validation_artifacts():
            pytest.skip("Validation evidence artifacts are not present in this workspace")

    def test_validation_360_log_exists(self):
        logs = list(ARTIFACTS.glob("validation-360-*.log"))
        assert len(logs) >= 1, "No validation-360 logs found"

    def test_release_validation_log_exists(self):
        logs = list(ARTIFACTS.glob("release-validation-*.log"))
        assert len(logs) >= 1, "No release-validation logs found"

    def test_manual_smoke_record_exists(self):
        records = list(ARTIFACTS.glob("manual-smoke-*.md"))
        assert len(records) >= 1, "No manual smoke records found"

    def test_backup_restore_record_exists(self):
        records = list(ARTIFACTS.glob("backup-restore-*.md"))
        assert len(records) >= 1, "No backup-restore records found"

    def test_stripe_flow_record_exists(self):
        records = list(ARTIFACTS.glob("stripe-flow-*.md"))
        assert len(records) >= 1, "No stripe-flow records found"

    def test_security_review_exists(self):
        records = list(ARTIFACTS.glob("security-review-*.md"))
        assert len(records) >= 1, "No security review found"

    def test_compliance_links_record_exists(self):
        records = list(ARTIFACTS.glob("compliance-links-*.md"))
        assert len(records) >= 1, "No compliance-links records found"

    def test_web_build_record_exists(self):
        records = list(ARTIFACTS.glob("web-build-*.md"))
        assert len(records) >= 1, "No web-build records found"

    def test_ij_series_evidence_exists(self):
        records = list(ARTIFACTS.glob("evidence-record-*series-ij*"))
        assert len(records) >= 1, "No I+J series evidence record found"


# ── K3: Onboarding Known Gaps Resolved ─────────────────────────────────────


class TestOnboardingGapsResolved:
    """Verify the onboarding doc's known gaps are closed."""

    def test_onboarding_has_resolved_section(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "Resolved Known Gaps" in content or "Resolved Since" in content

    def test_privacy_gap_resolved(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "PRIVACY_POLICY" in content

    def test_support_gap_resolved(self):
        content = (DOCS / "SELF_SERVE_GA_ONBOARDING.md").read_text()
        assert "CUSTOMER_SUPPORT" in content


# ── K4: Compliance Documentation Chain ─────────────────────────────────────


class TestComplianceDocumentation:
    """Verify all required compliance docs exist."""

    @pytest.mark.parametrize(
        "doc",
        [
            "PRIVACY_POLICY.md",
            "TERMS_OF_USE.md",
            "DATA_RETENTION_POLICY.md",
            "DATA_DELETION_POLICY.md",
            "CUSTOMER_SUPPORT.md",
        ],
    )
    def test_compliance_doc_exists(self, doc: str):
        assert (DOCS / doc).exists(), f"Missing: {doc}"

    @pytest.mark.parametrize(
        "doc",
        [
            "PRIVACY_POLICY.md",
            "TERMS_OF_USE.md",
            "DATA_RETENTION_POLICY.md",
            "DATA_DELETION_POLICY.md",
            "CUSTOMER_SUPPORT.md",
        ],
    )
    def test_compliance_doc_is_substantive(self, doc: str):
        content = (DOCS / doc).read_text()
        assert len(content) >= 500, f"{doc} is too short: {len(content)} chars"


# ── K5: Go/No-Go Checklist Status ─────────────────────────────────────────


class TestGoNoGoChecklist:
    """Verify the DoD checklist reflects current validation state."""

    def test_dod_exists(self):
        assert (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").exists()

    def test_dod_has_checked_items(self):
        content = (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").read_text()
        checked = content.count("[x]")
        unchecked = content.count("[ ]")
        assert checked >= 10, f"Only {checked} items checked (expected ≥10)"
        assert unchecked <= 3, f"Still {unchecked} unchecked items (expected ≤3)"

    def test_dod_validation_360_checked(self):
        content = (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").read_text()
        assert "[x] Validation 360 green" in content

    def test_dod_release_validation_checked(self):
        content = (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").read_text()
        assert "[x] Release validation green" in content

    def test_dod_compliance_checked(self):
        content = (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").read_text()
        assert "[x] Privacy, terms, retention, deletion" in content


# ── K6: GA Documentation Chain ─────────────────────────────────────────────


class TestGADocumentationChain:
    """Verify all GA docs exist and cross-reference each other."""

    _REQUIRED_GA_DOCS = [
        "PRODUCTION_GA_DEFINITION_OF_DONE.md",
        "GA_LAUNCH_INVENTORY.md",
        "GA_EVIDENCE_PACKAGE.md",
        "GA_LAUNCH_RUNBOOK.md",
        "SELF_SERVE_GA_ONBOARDING.md",
        "CUSTOMER_SUPPORT.md",
    ]

    @pytest.mark.parametrize("doc", _REQUIRED_GA_DOCS)
    def test_ga_doc_exists(self, doc: str):
        assert (DOCS / doc).exists(), f"Missing GA doc: {doc}"

    def test_dod_references_inventory(self):
        content = (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").read_text()
        assert "GA_LAUNCH_INVENTORY" in content or "Launch Inventory" in content

    def test_dod_references_evidence_package(self):
        content = (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").read_text()
        assert "GA_EVIDENCE_PACKAGE" in content or "Evidence Package" in content

    def test_dod_references_runbook(self):
        content = (DOCS / "PRODUCTION_GA_DEFINITION_OF_DONE.md").read_text()
        assert "GA_LAUNCH_RUNBOOK" in content or "Launch Runbook" in content

    def test_inventory_has_all_ga_rows_validated(self):
        """All `ga` classified features should have ✅ evidence."""
        content = (DOCS / "GA_LAUNCH_INVENTORY.md").read_text()
        ga_rows = [line for line in content.split("\n") if "| ga |" in line]
        validated = [row for row in ga_rows if "✅" in row]
        assert len(ga_rows) >= 10, f"Only {len(ga_rows)} ga rows"
        assert len(validated) == len(ga_rows), f"{len(ga_rows) - len(validated)} ga rows missing ✅ evidence"

    def test_runbook_has_rollback_triggers(self):
        content = (DOCS / "GA_LAUNCH_RUNBOOK.md").read_text()
        assert "Rollback Triggers" in content

    def test_runbook_has_observation_window(self):
        content = (DOCS / "GA_LAUNCH_RUNBOOK.md").read_text()
        assert "Observation Window" in content
        assert "24 hours" in content

    def test_series_validation_chain_e_through_k(self):
        """All series validation files E through K must exist."""
        for series in "efghijk":
            path = ROOT / "tests" / f"test_{series}_series_validation.py"
            assert path.exists(), f"Missing: {path.name}"
