"""Agent capability domain object."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentrelay.domain.task_spec import TaskDifficulty, TaskType

# Difficulty ordering for comparison
_DIFFICULTY_ORDER = {
    TaskDifficulty.EASY: 1,
    TaskDifficulty.MEDIUM: 2,
    TaskDifficulty.HARD: 3,
}


@dataclass
class AgentCapability:
    supported_task_types: list[TaskType] = field(default_factory=lambda: list(TaskType))
    supported_models: list[str] = field(default_factory=list)
    max_difficulty: TaskDifficulty = TaskDifficulty.HARD

    def supports_task_type(self, task_type: TaskType) -> bool:
        return task_type in self.supported_task_types

    def supports_difficulty(self, difficulty: TaskDifficulty) -> bool:
        return _DIFFICULTY_ORDER[difficulty] <= _DIFFICULTY_ORDER[self.max_difficulty]

    @classmethod
    def from_dict(cls, data: dict) -> AgentCapability:
        """Parse a capabilities dict (from JSONB) into AgentCapability.

        Empty dict = agent can do everything (defaults).
        """
        if not data:
            return cls()

        task_types = [TaskType(t) for t in data["supported_task_types"]] if "supported_task_types" in data else list(TaskType)
        models = data.get("supported_models", [])
        max_diff = TaskDifficulty(data["max_difficulty"]) if "max_difficulty" in data else TaskDifficulty.HARD

        return cls(
            supported_task_types=task_types,
            supported_models=models,
            max_difficulty=max_diff,
        )
