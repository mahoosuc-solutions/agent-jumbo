# tests/test_work_mode_wizard.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python.helpers.work_mode.wizard import FirstRunWizard


@pytest.mark.asyncio
async def test_wizard_triggers_when_no_llm_configured():
    wizard = FirstRunWizard()
    mock_router = MagicMock()
    mock_router.discover_models = AsyncMock(return_value=[])

    with patch("python.helpers.work_mode.wizard._get_router", return_value=mock_router):
        with patch("python.helpers.work_mode.wizard._has_cloud_api_key", return_value=False):
            result = await wizard.check()

    assert result is True  # wizard should show


@pytest.mark.asyncio
async def test_wizard_does_not_trigger_when_ollama_available():
    wizard = FirstRunWizard()
    mock_router = MagicMock()
    mock_model = MagicMock()
    mock_model.provider = "ollama"
    mock_router.discover_models = AsyncMock(return_value=[mock_model])

    with patch("python.helpers.work_mode.wizard._get_router", return_value=mock_router):
        with patch("python.helpers.work_mode.wizard._has_cloud_api_key", return_value=False):
            result = await wizard.check()

    assert result is False  # no wizard needed


@pytest.mark.asyncio
async def test_wizard_does_not_trigger_when_cloud_key_present():
    wizard = FirstRunWizard()
    mock_router = MagicMock()
    mock_router.discover_models = AsyncMock(return_value=[])

    with patch("python.helpers.work_mode.wizard._get_router", return_value=mock_router):
        with patch("python.helpers.work_mode.wizard._has_cloud_api_key", return_value=True):
            result = await wizard.check()

    assert result is False  # cloud key available, no wizard


@pytest.mark.asyncio
async def test_wizard_triggers_after_ollama_goes_offline():
    wizard = FirstRunWizard()
    mock_router = MagicMock()
    mock_router.discover_models = AsyncMock(
        side_effect=[
            [MagicMock(provider="ollama")],
            [],
        ]
    )

    with patch("python.helpers.work_mode.wizard._get_router", return_value=mock_router):
        with patch("python.helpers.work_mode.wizard._has_cloud_api_key", return_value=False):
            first = await wizard.check()
            second = await wizard.check()

    assert first is False
    assert second is True
