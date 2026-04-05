"""
Tests for WBM step definitions and internal_shell auto-execution.

Recovery API endpoint integration is covered in test_billing_setup_api.py.
"""

from unittest.mock import patch

# ---------------------------------------------------------------------------
# WBM step definitions
# ---------------------------------------------------------------------------


class TestWbmStepDefinitions:
    def test_step_count(self):
        from instruments.custom.payment_account_setup.step_definitions.wbm_steps import get_wbm_steps

        steps = get_wbm_steps("test_session")
        assert len(steps) == 15

    def test_all_steps_have_required_fields(self):
        from instruments.custom.payment_account_setup.step_definitions.wbm_steps import get_wbm_steps

        steps = get_wbm_steps("sess")
        required = {"step_id", "step_index", "title", "description", "automation_type", "human_instructions"}
        for step in steps:
            missing = required - set(step.keys())
            assert not missing, f"Step '{step.get('title')}' missing: {missing}"

    def test_step_ids_are_namespaced_by_session(self):
        from instruments.custom.payment_account_setup.step_definitions.wbm_steps import get_wbm_steps

        steps_a = get_wbm_steps("session_a")
        steps_b = get_wbm_steps("session_b")
        ids_a = {s["step_id"] for s in steps_a}
        ids_b = {s["step_id"] for s in steps_b}
        assert ids_a.isdisjoint(ids_b), "Step IDs from different sessions should not overlap"

    def test_all_steps_are_human_required(self):
        """WBM steps all require operator interaction (embedded workflow)."""
        from instruments.custom.payment_account_setup.step_definitions.wbm_steps import get_wbm_steps

        steps = get_wbm_steps("test")
        for step in steps:
            assert step["automation_type"] == "human_required", (
                f"Step '{step['title']}' has automation_type '{step['automation_type']}'; expected 'human_required'"
            )

    def test_step_indices_are_sequential(self):
        from instruments.custom.payment_account_setup.step_definitions.wbm_steps import get_wbm_steps

        steps = get_wbm_steps("test")
        for i, step in enumerate(steps):
            assert step["step_index"] == i

    def test_first_and_last_steps(self):
        from instruments.custom.payment_account_setup.step_definitions.wbm_steps import get_wbm_steps

        steps = get_wbm_steps("test")
        assert steps[0]["title"] == "Verify MCP Bridge"
        assert steps[-1]["title"] == "Final Validation"

    def test_wbm_provider_wires_steps(self, monkeypatch, tmp_path):
        """start_setup('wbm', ...) loads WBM steps via the setup manager."""
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        monkeypatch.setenv("PAYMENT_ACCOUNT_SETUP_DB_PATH", str(tmp_path / "wbm.db"))
        manager = PaymentAccountSetupManager()
        result = manager.start_setup(
            provider="wbm",
            business_name="StayHive Inn",
            email="ops@stayhive.example",
            country="us",
        )
        steps = result["session"]["total_steps"]
        assert steps == 15


# ---------------------------------------------------------------------------
# internal_shell execution in advance_step
# ---------------------------------------------------------------------------


class TestInternalShellExecution:
    def test_shell_step_auto_executes(self, monkeypatch, tmp_path):
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        monkeypatch.setenv("PAYMENT_ACCOUNT_SETUP_DB_PATH", str(tmp_path / "shell_test.db"))
        manager = PaymentAccountSetupManager()

        session_id = "test_shell_sess"
        manager.db.create_session(
            session_id=session_id,
            tenant_id="default",
            provider="stripe",
            business_name="Test",
            email="t@t.com",
            country="us",
            phase="test",
        )
        manager.db.insert_step(
            step_id=f"{session_id}_s00",
            session_id=session_id,
            step_index=0,
            title="Run catalog dry-run",
            description="",
            automation_type="automated",
            human_instructions="",
            action={"tool": "internal_shell", "args": {"command": "echo shellok"}},
            completion_check="",
            extract_fields=[],
        )
        manager.db.update_session(session_id, status="in_progress", total_steps=1)

        with patch.object(
            manager, "_run_internal_shell", return_value={"ok": True, "output": "shellok", "returncode": 0}
        ) as mock_shell:
            result = manager.advance_step(session_id=session_id, step_result=None, human_confirmed=False)

        mock_shell.assert_called_once()
        assert result.get("next_step") is None  # last step, session complete

    def test_run_internal_shell_success(self, tmp_path):
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager(db_path=str(tmp_path / "tmp.db"))
        step = {"action": {"tool": "internal_shell", "args": {"command": "echo hello"}}}
        result = manager._run_internal_shell(step)
        assert result["ok"] is True
        assert result["returncode"] == 0
        assert "hello" in result["output"]

    def test_run_internal_shell_failure(self, tmp_path):
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager(db_path=str(tmp_path / "tmp.db"))
        step = {"action": {"tool": "internal_shell", "args": {"command": "exit 1"}}}
        result = manager._run_internal_shell(step)
        assert result["ok"] is False
        assert result["returncode"] == 1

    def test_run_internal_shell_no_command(self, tmp_path):
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager(db_path=str(tmp_path / "tmp.db"))
        step = {"action": {"tool": "internal_shell", "args": {}}}
        result = manager._run_internal_shell(step)
        assert "error" in result
