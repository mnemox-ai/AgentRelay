"""Task state machine — enforces valid lifecycle transitions."""

from __future__ import annotations

from .task_spec import TaskStatus


class InvalidTransitionError(Exception):
    """Raised when a task status transition is not allowed."""

    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid transition: {current} -> {target}"
        )


# Allowed transitions: {current_status: {allowed_target_statuses}}
_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.OPEN: {TaskStatus.CLAIMED, TaskStatus.EXPIRED},
    TaskStatus.CLAIMED: {TaskStatus.SUBMITTED, TaskStatus.EXPIRED},
    TaskStatus.SUBMITTED: {TaskStatus.VALIDATING},
    TaskStatus.VALIDATING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
}


class TaskStateMachine:
    """Validates task status transitions against the allowed lifecycle graph."""

    @staticmethod
    def transition(current: str, target: str) -> None:
        """Check if *current* -> *target* is a legal transition.

        Raises ``InvalidTransitionError`` if not.
        """
        try:
            current_status = TaskStatus(current)
        except ValueError:
            raise InvalidTransitionError(current, target)

        try:
            target_status = TaskStatus(target)
        except ValueError:
            raise InvalidTransitionError(current, target)

        allowed = _TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidTransitionError(current, target)
