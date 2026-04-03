# tests/test_work_mode_drain.py
import logging
import threading
import time
from unittest.mock import MagicMock, patch

from python.helpers.work_mode.drain import DrainCoordinator


def test_drain_returns_true_when_no_tasks():
    coord = DrainCoordinator()
    result = coord.drain(timeout=1.0)
    assert result is True


def test_drain_blocks_new_tasks_during_drain():
    coord = DrainCoordinator()
    coord._draining = True
    assert coord.is_draining() is True
    coord._draining = False
    assert coord.is_draining() is False


def test_drain_waits_for_contexts_to_clear():
    coord = DrainCoordinator()

    mock_ctx = MagicMock()
    mock_ctx.id = "test-ctx-1"

    contexts_store = {"test-ctx-1": mock_ctx}

    def clear_after_delay():
        time.sleep(0.1)
        contexts_store.clear()

    t = threading.Thread(target=clear_after_delay)
    t.start()

    with patch("agent.AgentContext.all", side_effect=lambda: list(contexts_store.values())):
        result = coord.drain(timeout=2.0)

    t.join()
    assert result is True


def test_drain_returns_false_on_timeout():
    coord = DrainCoordinator()
    mock_ctx = MagicMock()

    # Context never clears
    with patch("agent.AgentContext.all", return_value=[mock_ctx]):
        result = coord.drain(timeout=0.2)

    assert result is False


def test_drain_logs_warning_on_timeout(caplog):
    coord = DrainCoordinator()
    mock_ctx = MagicMock()
    mock_ctx.id = "stuck-task"

    with patch("agent.AgentContext.all", return_value=[mock_ctx]):
        with caplog.at_level(logging.WARNING, logger="python.helpers.work_mode.drain"):
            coord.drain(timeout=0.1)

    assert any("stuck-task" in r.message or "drain" in r.message.lower() for r in caplog.records)
