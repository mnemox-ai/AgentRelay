"""Tests for task generator — generate_task() and generate_tasks()."""

from __future__ import annotations

import uuid

import pytest

from agentrelay.tasks.generator import generate_task, generate_tasks
from agentrelay.tasks.templates import ALL_TEMPLATES, TEMPLATES_BY_TYPE


PUBLISHER_ID = str(uuid.uuid4())


class TestGenerateTask:
    def test_basic(self):
        task = generate_task("ds_earnings", PUBLISHER_ID)
        assert task["publisher_id"] == PUBLISHER_ID
        assert task["task_spec"]["task_type"] == "data_structuring"
        assert task["reward"] > 0
        assert task["deadline_seconds"] > 0

    def test_task_spec_keys(self):
        task = generate_task("code_utility", PUBLISHER_ID)
        spec = task["task_spec"]
        assert "task_type" in spec
        assert "difficulty" in spec
        assert "input_data" in spec
        assert "output_schema" in spec
        assert "validation_method" in spec
        assert "token_estimate" in spec

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            generate_task("does_not_exist", PUBLISHER_ID)

    def test_deadline_override(self):
        task = generate_task("ds_earnings", PUBLISHER_ID, deadline_override=9999)
        assert task["deadline_seconds"] == 9999

    def test_reward_override(self):
        task = generate_task("ds_earnings", PUBLISHER_ID, reward_override=1.23)
        assert task["reward"] == 1.23

    def test_all_templates_generate_valid_task(self):
        for tmpl in ALL_TEMPLATES:
            task = generate_task(tmpl["id"], PUBLISHER_ID)
            assert task["task_spec"]["task_type"] == tmpl["task_type"]
            assert task["task_spec"]["difficulty"] == tmpl["difficulty"]
            assert isinstance(task["task_spec"]["input_data"], dict)

    def test_input_data_varies_between_calls(self):
        results = [generate_task("ds_earnings", PUBLISHER_ID) for _ in range(10)]
        inputs = [str(r["task_spec"]["input_data"]) for r in results]
        assert len(set(inputs)) >= 2, "No variation in 10 calls"


class TestGenerateTasks:
    def test_all_templates_no_args(self):
        """No count, no type → one per template (20)."""
        tasks = generate_tasks(PUBLISHER_ID)
        assert len(tasks) == 20

    def test_count_only(self):
        """count=5, no type → 5 random from all."""
        tasks = generate_tasks(PUBLISHER_ID, count=5)
        assert len(tasks) == 5

    def test_type_only(self):
        """No count, type='coding' → all coding templates (4)."""
        tasks = generate_tasks(PUBLISHER_ID, task_type="coding")
        assert len(tasks) == 4
        for t in tasks:
            assert t["task_spec"]["task_type"] == "coding"

    def test_count_and_type(self):
        """count=3, type='classification' → 3 random classification tasks."""
        tasks = generate_tasks(PUBLISHER_ID, count=3, task_type="classification")
        assert len(tasks) == 3
        for t in tasks:
            assert t["task_spec"]["task_type"] == "classification"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="No templates for type"):
            generate_tasks(PUBLISHER_ID, task_type="nonexistent_type")

    def test_deadline_override_propagates(self):
        tasks = generate_tasks(PUBLISHER_ID, count=3, deadline_override=7200)
        for t in tasks:
            assert t["deadline_seconds"] == 7200

    def test_count_zero(self):
        tasks = generate_tasks(PUBLISHER_ID, count=0)
        assert tasks == []

    def test_all_types_present_when_no_filter(self):
        tasks = generate_tasks(PUBLISHER_ID)
        types = {t["task_spec"]["task_type"] for t in tasks}
        assert types == set(TEMPLATES_BY_TYPE.keys())
