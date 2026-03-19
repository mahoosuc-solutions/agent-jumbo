"""Unit tests for the priority_scorer pure-function module."""

import os
import sys

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instruments.custom.work_queue.priority_scorer import (
    score_item,
    score_linear_item,
    score_scanner_item,
)

# ── score_scanner_item ───────────────────────────────────────────────


class TestScannerItemScoring:
    def _item(self, **kwargs):
        base = {"source_type": "todo", "file_path": "", "title": "", "description": ""}
        base.update(kwargs)
        return base

    def test_base_score_fixme(self):
        score, breakdown = score_scanner_item(self._item(source_type="fixme"))
        assert breakdown["base_type"] == 35
        assert score == 35

    def test_base_score_todo(self):
        score, breakdown = score_scanner_item(self._item(source_type="todo"))
        assert breakdown["base_type"] == 15
        assert score == 15

    def test_base_score_failing_test(self):
        score, breakdown = score_scanner_item(self._item(source_type="failing_test"))
        assert breakdown["base_type"] == 40
        assert score == 40

    def test_file_importance_bonus_auth(self):
        score, breakdown = score_scanner_item(self._item(source_type="todo", file_path="app/auth/login.py"))
        assert breakdown["file_importance"] == 10
        assert score == 15 + 10

    def test_file_importance_takes_max_when_multiple_patterns_match(self):
        # "auth" (10) and "route" (8) both match; result should be 10
        score, breakdown = score_scanner_item(self._item(source_type="todo", file_path="app/auth/route_handler.py"))
        assert breakdown["file_importance"] == 10

    def test_security_keyword_bonus_vulnerability(self):
        score, breakdown = score_scanner_item(self._item(source_type="todo", title="Fix vulnerability in login flow"))
        assert breakdown["security"] == 15

    def test_security_keyword_bonus_xss(self):
        score, breakdown = score_scanner_item(self._item(source_type="todo", title="Escape xss in user input"))
        assert breakdown["security"] == 15

    def test_score_capped_at_100(self):
        # failing_test (40) + auth file (10) + security keyword (15) = 65, well under 100.
        # Use a very high custom weight to force a cap.
        custom_weights = {"todo": 90}
        score, breakdown = score_scanner_item(
            self._item(
                source_type="todo",
                file_path="auth/handler.py",
                title="Fix vulnerability",
            ),
            weights=custom_weights,
        )
        # 90 + 10 + 15 = 115 → capped at 100
        assert score == 100
        assert breakdown["total"] == 100

    def test_custom_weights_override_defaults(self):
        custom_weights = {"fixme": 99}
        score, breakdown = score_scanner_item(
            self._item(source_type="fixme"),
            weights=custom_weights,
        )
        assert breakdown["base_type"] == 99
        assert score == 99


# ── score_linear_item ────────────────────────────────────────────────


class TestLinearItemScoring:
    def _item(self, **kwargs):
        base = {
            "linear_priority": 0,
            "linear_state": "",
            "linear_labels": "[]",
        }
        base.update(kwargs)
        return base

    def test_priority_mapping_urgent(self):
        score, breakdown = score_linear_item(self._item(linear_priority=1))
        assert breakdown["priority_base"] == 40

    def test_priority_mapping_high(self):
        score, breakdown = score_linear_item(self._item(linear_priority=2))
        assert breakdown["priority_base"] == 30

    def test_priority_mapping_low(self):
        score, breakdown = score_linear_item(self._item(linear_priority=4))
        assert breakdown["priority_base"] == 10

    def test_priority_mapping_none(self):
        score, breakdown = score_linear_item(self._item(linear_priority=0))
        assert breakdown["priority_base"] == 5

    def test_state_bonus_in_progress(self):
        score, breakdown = score_linear_item(self._item(linear_priority=2, linear_state="In Progress"))
        assert breakdown["state_bonus"] == 10

    def test_state_bonus_review(self):
        score, breakdown = score_linear_item(self._item(linear_priority=2, linear_state="In Review"))
        assert breakdown["state_bonus"] == 15

    def test_label_bonus_bug(self):
        score, breakdown = score_linear_item(self._item(linear_priority=2, linear_labels='["bug", "ui"]'))
        assert breakdown["label_bonus"] == 10

    def test_label_bonus_critical(self):
        score, breakdown = score_linear_item(self._item(linear_priority=2, linear_labels='["critical"]'))
        assert breakdown["label_bonus"] == 10

    def test_age_bonus_key_exists_in_breakdown(self):
        # We don't pin the exact value (depends on datetime.now),
        # but the key must always be present in the breakdown dict.
        score, breakdown = score_linear_item(self._item())
        assert "age_bonus" in breakdown


# ── score_item (routing) ─────────────────────────────────────────────


class TestScoreItemRouting:
    def test_routes_to_scanner_for_source_scanner(self):
        item = {"source": "scanner", "source_type": "fixme", "file_path": "", "title": ""}
        score, breakdown = score_item(item)
        # Scanner breakdown has "base_type" key; linear uses "priority_base"
        assert "base_type" in breakdown
        assert score == 35

    def test_routes_to_linear_for_source_linear(self):
        item = {"source": "linear", "linear_priority": 1, "linear_state": "", "linear_labels": "[]"}
        score, breakdown = score_item(item)
        assert "priority_base" in breakdown
        assert score == 40

    def test_unknown_source_defaults_to_scanner(self):
        item = {"source": "unknown_system", "source_type": "todo", "file_path": "", "title": ""}
        score, breakdown = score_item(item)
        assert "base_type" in breakdown
        assert score == 15
