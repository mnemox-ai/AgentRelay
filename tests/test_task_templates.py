"""Tests for task templates — ensure all 20 templates are valid and produce varied inputs."""

from __future__ import annotations

import jsonschema

from agentrelay.tasks.templates import (
    ALL_TEMPLATES,
    TEMPLATES_BY_TYPE,
    get_template,
)

REQUIRED_KEYS = {
    "id",
    "task_type",
    "difficulty",
    "reward",
    "deadline_seconds",
    "token_estimate",
    "validation_method",
    "generate_input",
    "output_schema",
}

VALID_TASK_TYPES = {
    "data_structuring",
    "research_extraction",
    "coding",
    "content_generation",
    "classification",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_VALIDATION_METHODS = {"schema", "rule"}


class TestTemplateStructure:
    def test_exactly_20_templates(self):
        assert len(ALL_TEMPLATES) == 20

    def test_five_types_four_each(self):
        assert len(TEMPLATES_BY_TYPE) == 5
        for task_type, templates in TEMPLATES_BY_TYPE.items():
            assert task_type in VALID_TASK_TYPES, f"Unknown type: {task_type}"
            assert len(templates) == 4, f"{task_type} has {len(templates)} templates, expected 4"

    def test_unique_ids(self):
        ids = [t["id"] for t in ALL_TEMPLATES]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

    def test_all_required_keys_present(self):
        for tmpl in ALL_TEMPLATES:
            missing = REQUIRED_KEYS - set(tmpl.keys())
            assert not missing, f"Template {tmpl['id']} missing keys: {missing}"

    def test_valid_task_types(self):
        for tmpl in ALL_TEMPLATES:
            assert tmpl["task_type"] in VALID_TASK_TYPES, f"{tmpl['id']}: bad type {tmpl['task_type']}"

    def test_valid_difficulties(self):
        for tmpl in ALL_TEMPLATES:
            assert tmpl["difficulty"] in VALID_DIFFICULTIES, f"{tmpl['id']}: bad difficulty {tmpl['difficulty']}"

    def test_valid_validation_methods(self):
        for tmpl in ALL_TEMPLATES:
            assert tmpl["validation_method"] in VALID_VALIDATION_METHODS, (
                f"{tmpl['id']}: bad validation_method {tmpl['validation_method']}"
            )

    def test_reward_positive(self):
        for tmpl in ALL_TEMPLATES:
            assert tmpl["reward"] > 0, f"{tmpl['id']}: reward must be positive"

    def test_deadline_positive(self):
        for tmpl in ALL_TEMPLATES:
            assert tmpl["deadline_seconds"] > 0, f"{tmpl['id']}: deadline must be positive"

    def test_token_estimate_positive(self):
        for tmpl in ALL_TEMPLATES:
            assert tmpl["token_estimate"] > 0, f"{tmpl['id']}: token_estimate must be positive"


class TestGenerateInput:
    def test_all_generate_input_callable(self):
        for tmpl in ALL_TEMPLATES:
            assert callable(tmpl["generate_input"]), f"{tmpl['id']}: generate_input not callable"

    def test_all_generate_input_returns_dict(self):
        for tmpl in ALL_TEMPLATES:
            result = tmpl["generate_input"]()
            assert isinstance(result, dict), f"{tmpl['id']}: generate_input returned {type(result)}"

    def test_generate_input_not_empty(self):
        for tmpl in ALL_TEMPLATES:
            result = tmpl["generate_input"]()
            assert len(result) > 0, f"{tmpl['id']}: generate_input returned empty dict"

    def test_generate_input_produces_variation(self):
        """Call generate_input() 10 times; at least 2 distinct results expected."""
        for tmpl in ALL_TEMPLATES:
            results = [str(tmpl["generate_input"]()) for _ in range(10)]
            unique = set(results)
            assert len(unique) >= 2, (
                f"{tmpl['id']}: generate_input produced no variation in 10 calls"
            )


class TestOutputSchema:
    def test_valid_json_schema(self):
        """Each output_schema must be a valid JSON Schema (Draft 7+)."""
        for tmpl in ALL_TEMPLATES:
            schema = tmpl["output_schema"]
            assert isinstance(schema, dict), f"{tmpl['id']}: output_schema not dict"
            assert "type" in schema, f"{tmpl['id']}: output_schema has no 'type'"
            # Validate it's a well-formed schema by checking it against metaschema
            jsonschema.Draft7Validator.check_schema(schema)

    def test_output_schema_has_required(self):
        for tmpl in ALL_TEMPLATES:
            schema = tmpl["output_schema"]
            assert "required" in schema, f"{tmpl['id']}: output_schema has no 'required'"
            assert len(schema["required"]) > 0, f"{tmpl['id']}: 'required' is empty"


class TestGetTemplate:
    def test_existing_template(self):
        tmpl = get_template("ds_earnings")
        assert tmpl is not None
        assert tmpl["id"] == "ds_earnings"

    def test_nonexistent_template(self):
        tmpl = get_template("nonexistent_xyz")
        assert tmpl is None

    def test_all_templates_gettable(self):
        for tmpl in ALL_TEMPLATES:
            found = get_template(tmpl["id"])
            assert found is not None
            assert found["id"] == tmpl["id"]
