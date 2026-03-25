from unittest.mock import patch


def test_register_mos_schedules_skips_incompatible_scheduler():
    from python.helpers.mos_scheduler_init import register_mos_schedules

    result = register_mos_schedules()

    assert result == {"registered": [], "count": 0}


def test_initialize_keys_skips_missing_ecdsa_without_warning():
    from python.helpers.security import SecurityVaultManager

    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "ecdsa":
            raise ImportError("ecdsa unavailable")
        return original_import(name, *args, **kwargs)

    with patch.object(SecurityVaultManager, "get_secret", return_value=None):
        with patch("builtins.__import__", side_effect=fake_import):
            with patch("builtins.print") as mock_print:
                SecurityVaultManager.initialize_keys()

    mock_print.assert_not_called()
