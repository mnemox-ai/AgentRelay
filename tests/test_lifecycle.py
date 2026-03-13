"""Tests for task state machine lifecycle transitions."""

from __future__ import annotations

import pytest

from agentrelay.domain.task_lifecycle import InvalidTransitionError, TaskStateMachine
from agentrelay.domain.task_spec import TaskStatus


# ---------------------------------------------------------------------------
# All legal transitions should pass
# ---------------------------------------------------------------------------

class TestLegalTransitions:
    @pytest.mark.parametrize(
        "current, target",
        [
            ("open", "claimed"),
            ("open", "expired"),
            ("claimed", "submitted"),
            ("claimed", "expired"),
            ("submitted", "validating"),
            ("validating", "completed"),
            ("validating", "failed"),
        ],
    )
    def test_legal_transition(self, current: str, target: str):
        # Should not raise
        TaskStateMachine.transition(current, target)


# ---------------------------------------------------------------------------
# All illegal transitions should raise InvalidTransitionError
# ---------------------------------------------------------------------------

class TestIllegalTransitions:
    @pytest.mark.parametrize(
        "current, target",
        [
            # open — cannot skip to submitted/validating/completed/failed
            ("open", "submitted"),
            ("open", "validating"),
            ("open", "completed"),
            ("open", "failed"),
            ("open", "open"),
            # claimed — cannot go back to open or skip ahead
            ("claimed", "open"),
            ("claimed", "validating"),
            ("claimed", "completed"),
            ("claimed", "failed"),
            ("claimed", "claimed"),
            # submitted — only validating is allowed
            ("submitted", "open"),
            ("submitted", "claimed"),
            ("submitted", "completed"),
            ("submitted", "failed"),
            ("submitted", "expired"),
            ("submitted", "submitted"),
            # validating — only completed or failed
            ("validating", "open"),
            ("validating", "claimed"),
            ("validating", "submitted"),
            ("validating", "expired"),
            ("validating", "validating"),
            # terminal states — no transitions allowed
            ("completed", "open"),
            ("completed", "claimed"),
            ("completed", "submitted"),
            ("completed", "validating"),
            ("completed", "failed"),
            ("completed", "expired"),
            ("completed", "completed"),
            ("failed", "open"),
            ("failed", "claimed"),
            ("failed", "submitted"),
            ("failed", "validating"),
            ("failed", "completed"),
            ("failed", "expired"),
            ("failed", "failed"),
            ("expired", "open"),
            ("expired", "claimed"),
            ("expired", "submitted"),
            ("expired", "validating"),
            ("expired", "completed"),
            ("expired", "failed"),
            ("expired", "expired"),
        ],
    )
    def test_illegal_transition(self, current: str, target: str):
        with pytest.raises(InvalidTransitionError) as exc_info:
            TaskStateMachine.transition(current, target)
        assert exc_info.value.current == current
        assert exc_info.value.target == target


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_invalid_current_status(self):
        with pytest.raises(InvalidTransitionError):
            TaskStateMachine.transition("bogus", "open")

    def test_invalid_target_status(self):
        with pytest.raises(InvalidTransitionError):
            TaskStateMachine.transition("open", "bogus")

    def test_both_invalid(self):
        with pytest.raises(InvalidTransitionError):
            TaskStateMachine.transition("foo", "bar")

    def test_error_message_format(self):
        with pytest.raises(InvalidTransitionError, match="Invalid transition: open -> completed"):
            TaskStateMachine.transition("open", "completed")

    def test_all_statuses_covered_in_transitions(self):
        """Every non-terminal TaskStatus should appear as a key in allowed transitions."""
        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.EXPIRED}
        from agentrelay.domain.task_lifecycle import _TRANSITIONS

        for status in TaskStatus:
            if status not in terminal:
                assert status in _TRANSITIONS, f"{status} missing from transition table"
