# python/helpers/work_mode/wizard.py
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_CLOUD_KEY_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "TOGETHER_API_KEY",
)


def _get_router():
    from python.helpers.llm_router import get_router

    return get_router()


def _has_cloud_api_key() -> bool:
    from python.helpers import dotenv

    return any(dotenv.get_dotenv_value(k) for k in _CLOUD_KEY_ENV_VARS)


class FirstRunWizard:
    """Detects when no usable LLM is configured and signals the UI to show setup."""

    async def check(self) -> bool:
        """Return True if the setup wizard should be shown.

        Triggers when: no models discovered AND no cloud API key present.
        Reuses LLMRouter.discover_models() — does not duplicate logic.
        """
        try:
            router = _get_router()
            models = await router.discover_models(force=False)
            has_models = bool(models)
        except Exception as e:
            log.warning("FirstRunWizard: model discovery failed: %s", e)
            has_models = False

        if has_models:
            return False

        if _has_cloud_api_key():
            return False

        log.info("FirstRunWizard: no usable LLM configured — wizard should show")
        return True
