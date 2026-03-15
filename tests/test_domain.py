"""Tests for domain layer objects."""

from datetime import datetime, timezone

from agentrelay.domain import (
    QuotaProfile,
    ReputationMetrics,
    TaskDifficulty,
    TaskSpec,
    TaskStatus,
    TaskType,
    ValidationResult,
    ValidatorType,
)


# --- TaskType ---

class TestTaskType:
    def test_values(self):
        assert TaskType.DATA_STRUCTURING.value == "data_structuring"
        assert TaskType.RESEARCH_EXTRACTION.value == "research_extraction"
        assert TaskType.CODING.value == "coding"
        assert TaskType.CONTENT_GENERATION.value == "content_generation"
        assert TaskType.CLASSIFICATION.value == "classification"

    def test_member_count(self):
        assert len(TaskType) == 5


# --- TaskStatus ---

class TestTaskStatus:
    def test_values(self):
        expected = ["open", "claimed", "submitted", "validating", "completed", "failed", "expired"]
        assert [s.value for s in TaskStatus] == expected

    def test_member_count(self):
        assert len(TaskStatus) == 7


# --- TaskDifficulty ---

class TestTaskDifficulty:
    def test_values(self):
        assert TaskDifficulty.EASY.value == "easy"
        assert TaskDifficulty.MEDIUM.value == "medium"
        assert TaskDifficulty.HARD.value == "hard"

    def test_member_count(self):
        assert len(TaskDifficulty) == 3


# --- TaskSpec ---

class TestTaskSpec:
    def test_creation(self):
        spec = TaskSpec(
            task_type=TaskType.CODING,
            input_data={"prompt": "write hello world"},
            output_schema={"type": "object"},
            validation_method="test",
            difficulty=TaskDifficulty.EASY,
            token_estimate=500,
            reward=0.01,
            deadline_seconds=300,
        )
        assert spec.task_type is TaskType.CODING
        assert spec.input_data == {"prompt": "write hello world"}
        assert spec.output_schema == {"type": "object"}
        assert spec.validation_method == "test"
        assert spec.difficulty is TaskDifficulty.EASY
        assert spec.token_estimate == 500
        assert spec.reward == 0.01
        assert spec.deadline_seconds == 300
        assert spec.allowed_models == []

    def test_allowed_models_default_empty(self):
        spec = TaskSpec(
            task_type=TaskType.DATA_STRUCTURING,
            input_data={},
            output_schema={},
            validation_method="schema",
            difficulty=TaskDifficulty.MEDIUM,
            token_estimate=1000,
            reward=0.05,
            deadline_seconds=600,
        )
        assert spec.allowed_models == []

    def test_allowed_models_specified(self):
        spec = TaskSpec(
            task_type=TaskType.RESEARCH_EXTRACTION,
            input_data={"query": "test"},
            output_schema={"type": "string"},
            validation_method="rule",
            difficulty=TaskDifficulty.HARD,
            token_estimate=2000,
            reward=0.10,
            deadline_seconds=900,
            allowed_models=["haiku", "sonnet"],
        )
        assert spec.allowed_models == ["haiku", "sonnet"]

    def test_equality(self):
        kwargs = dict(
            task_type=TaskType.CODING,
            input_data={"x": 1},
            output_schema={},
            validation_method="test",
            difficulty=TaskDifficulty.EASY,
            token_estimate=100,
            reward=0.01,
            deadline_seconds=60,
        )
        assert TaskSpec(**kwargs) == TaskSpec(**kwargs)


# --- ValidatorType ---

class TestValidatorType:
    def test_values(self):
        expected = ["schema", "rule", "test", "consensus", "llm_judge"]
        assert [v.value for v in ValidatorType] == expected

    def test_member_count(self):
        assert len(ValidatorType) == 5


# --- ValidationResult ---

class TestValidationResult:
    def test_creation(self):
        result = ValidationResult(
            passed=True,
            score=0.95,
            validator_type=ValidatorType.SCHEMA,
            details="All fields valid",
        )
        assert result.passed is True
        assert result.score == 0.95
        assert result.validator_type is ValidatorType.SCHEMA
        assert result.details == "All fields valid"
        assert isinstance(result.validated_at, datetime)

    def test_validated_at_defaults_to_utc(self):
        result = ValidationResult(
            passed=False,
            score=0.0,
            validator_type=ValidatorType.RULE,
            details="missing field",
        )
        assert result.validated_at.tzinfo is not None
        assert result.validated_at.tzinfo == timezone.utc

    def test_validated_at_explicit(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = ValidationResult(
            passed=True,
            score=1.0,
            validator_type=ValidatorType.LLM_JUDGE,
            details="ok",
            validated_at=ts,
        )
        assert result.validated_at == ts

    def test_failed_result(self):
        result = ValidationResult(
            passed=False,
            score=0.3,
            validator_type=ValidatorType.TEST,
            details="2/5 tests failed",
        )
        assert result.passed is False
        assert result.score == 0.3


# --- ReputationMetrics ---

class TestReputationMetrics:
    def test_creation(self):
        metrics = ReputationMetrics(
            completion_rate=0.95,
            pass_rate=0.90,
            avg_latency_seconds=12.5,
            token_efficiency=0.85,
            rework_rate=0.05,
            quality_score=0.88,
        )
        assert metrics.completion_rate == 0.95
        assert metrics.pass_rate == 0.90
        assert metrics.avg_latency_seconds == 12.5
        assert metrics.token_efficiency == 0.85
        assert metrics.rework_rate == 0.05
        assert metrics.quality_score == 0.88

    def test_equality(self):
        kwargs = dict(
            completion_rate=1.0,
            pass_rate=1.0,
            avg_latency_seconds=5.0,
            token_efficiency=1.0,
            rework_rate=0.0,
            quality_score=1.0,
        )
        assert ReputationMetrics(**kwargs) == ReputationMetrics(**kwargs)


# --- QuotaProfile ---

class TestQuotaProfile:
    def test_creation(self):
        profile = QuotaProfile(
            provider="anthropic",
            model="haiku",
            executor_type="free_tier",
            plan_type="basic",
            daily_task_budget=100,
            safe_token_cap=50000,
        )
        assert profile.provider == "anthropic"
        assert profile.model == "haiku"
        assert profile.executor_type == "free_tier"
        assert profile.plan_type == "basic"
        assert profile.daily_task_budget == 100
        assert profile.safe_token_cap == 50000

    def test_equality(self):
        kwargs = dict(
            provider="openai",
            model="gpt-4o-mini",
            executor_type="paid",
            plan_type="pro",
            daily_task_budget=500,
            safe_token_cap=200000,
        )
        assert QuotaProfile(**kwargs) == QuotaProfile(**kwargs)
