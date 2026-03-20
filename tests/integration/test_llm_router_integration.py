"""Integration tests for LLMRouter / LLMRouterDatabase — uses a temp SQLite DB."""

import os
import tempfile

import pytest

pytestmark = [pytest.mark.integration]


@pytest.fixture()
def router_db_path():
    """Yield a temp path for the router SQLite database, cleaned up after the test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture()
def router(router_db_path):
    """LLMRouter backed by a fresh temp database (no Ollama or cloud needed)."""
    from python.helpers.llm_router import LLMRouter

    return LLMRouter(db_path=router_db_path)


def _register_model(router, provider="test", name="model-a", capabilities=None, is_local=True, priority_score=50.0):
    """Helper: save a ModelInfo into the router DB."""
    from python.helpers.llm_router import ModelInfo

    model = ModelInfo(
        provider=provider,
        name=name,
        display_name=f"{provider}/{name}",
        capabilities=capabilities or ["chat"],
        is_local=is_local,
        is_available=True,
        priority_score=priority_score,
    )
    router.db.save_model(model)
    return model


def test_llm_router_select_model_with_registered_model(router):
    """select_model() returns the only registered available model."""
    _register_model(router, name="my-chat-model", capabilities=["chat"])

    selected = router.select_model(role="chat")
    assert selected is not None
    assert selected.name == "my-chat-model"


def test_llm_router_select_model_filters_by_capability(router):
    """select_model() with required_capabilities filters out models lacking them."""
    _register_model(router, name="basic-chat", capabilities=["chat"])
    _register_model(router, name="vision-model", capabilities=["chat", "vision"])

    selected = router.select_model(required_capabilities=["vision"])
    assert selected is not None
    assert selected.name == "vision-model"


def test_llm_router_fallback_when_no_models(router):
    """select_model() returns None gracefully when no models are registered."""
    # DB is empty — no models registered
    selected = router.select_model(role="chat")
    assert selected is None


def test_llm_router_routing_rule_exclusion(router):
    """A routing rule with excluded_models prevents a model from being selected."""
    from python.helpers.llm_router import RoutingRule

    _register_model(router, name="bad-model", capabilities=["chat"])
    _register_model(router, name="good-model", capabilities=["chat"], priority_score=10.0)

    rule = RoutingRule(
        name="exclude-bad",
        priority=100,
        condition="",
        excluded_models=["test/bad-model"],
        enabled=True,
    )
    router.db.save_routing_rule(rule)

    selected = router.select_model(role="chat")
    assert selected is not None
    assert selected.name == "good-model"
