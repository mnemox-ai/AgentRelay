"""Token budget limiter — prevent agents from exceeding token caps."""

from __future__ import annotations


def check_token_budget(task_estimate: int, agent_cap: int) -> bool:
    """Check whether a task's estimated token usage fits within the agent's cap.

    Args:
        task_estimate: Estimated tokens the task will consume.
        agent_cap: Maximum tokens the agent is allowed to use.

    Returns:
        True if the task fits within budget, False otherwise.
    """
    if task_estimate < 0 or agent_cap < 0:
        return False
    return task_estimate <= agent_cap
