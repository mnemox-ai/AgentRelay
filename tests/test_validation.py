from agentrelay.validation import SchemaValidator, RuleValidator, ValidationResult, ValidatorType
from agentrelay.validation.rule_validator import (
    required_fields_present,
    no_empty_values,
    type_check,
)


# ---------- Shared fixtures ----------

SCHEMA = {
    "type": "object",
    "required": ["name", "score"],
    "properties": {
        "name": {"type": "string"},
        "score": {"type": "integer"},
        "tags": {"type": "array"},
    },
}

VALID_OUTPUT = {"name": "test", "score": 42, "tags": ["a"]}


# ========== SchemaValidator ==========


class TestSchemaValidatorHappyPath:
    def test_valid_output(self):
        result = SchemaValidator().validate({}, VALID_OUTPUT, SCHEMA)
        assert result.passed is True
        assert result.errors == []

    def test_extra_fields_allowed(self):
        output = {**VALID_OUTPUT, "extra": True}
        result = SchemaValidator().validate({}, output, SCHEMA)
        assert result.passed is True


class TestSchemaValidatorMissingFields:
    def test_missing_required_field(self):
        output = {"name": "test"}  # missing score
        result = SchemaValidator().validate({}, output, SCHEMA)
        assert result.passed is False
        assert any("score" in e for e in result.errors)

    def test_missing_all_required(self):
        result = SchemaValidator().validate({}, {}, SCHEMA)
        assert result.passed is False
        assert len(result.errors) >= 2


class TestSchemaValidatorWrongTypes:
    def test_wrong_type_string(self):
        output = {"name": 123, "score": 42}
        result = SchemaValidator().validate({}, output, SCHEMA)
        assert result.passed is False
        assert any("name" in e for e in result.errors)

    def test_wrong_type_integer(self):
        output = {"name": "test", "score": "not_a_number"}
        result = SchemaValidator().validate({}, output, SCHEMA)
        assert result.passed is False
        assert any("score" in e for e in result.errors)

    def test_wrong_type_array(self):
        output = {"name": "test", "score": 42, "tags": "not_an_array"}
        result = SchemaValidator().validate({}, output, SCHEMA)
        assert result.passed is False
        assert any("tags" in e for e in result.errors)


# ========== RuleValidator ==========


class TestRuleValidatorHappyPath:
    def test_valid_output(self):
        result = RuleValidator().validate({}, VALID_OUTPUT, SCHEMA)
        assert result.passed is True
        assert result.errors == []


class TestRuleValidatorRequiredFields:
    def test_missing_required(self):
        errors = required_fields_present({}, {"name": "test"}, SCHEMA)
        assert any("score" in e for e in errors)

    def test_all_present(self):
        errors = required_fields_present({}, VALID_OUTPUT, SCHEMA)
        assert errors == []


class TestRuleValidatorNoEmptyValues:
    def test_none_value(self):
        errors = no_empty_values({}, {"name": None}, SCHEMA)
        assert any("name" in e for e in errors)

    def test_empty_string(self):
        errors = no_empty_values({}, {"name": ""}, SCHEMA)
        assert any("name" in e for e in errors)

    def test_empty_list(self):
        errors = no_empty_values({}, {"tags": []}, SCHEMA)
        assert any("tags" in e for e in errors)

    def test_empty_dict(self):
        errors = no_empty_values({}, {"meta": {}}, SCHEMA)
        assert any("meta" in e for e in errors)

    def test_valid_values(self):
        errors = no_empty_values({}, VALID_OUTPUT, SCHEMA)
        assert errors == []


class TestRuleValidatorTypeCheck:
    def test_wrong_type(self):
        errors = type_check({}, {"name": 123, "score": 42}, SCHEMA)
        assert any("name" in e for e in errors)

    def test_correct_types(self):
        errors = type_check({}, VALID_OUTPUT, SCHEMA)
        assert errors == []

    def test_number_accepts_int_and_float(self):
        schema = {"properties": {"value": {"type": "number"}}}
        assert type_check({}, {"value": 1}, schema) == []
        assert type_check({}, {"value": 1.5}, schema) == []

    def test_missing_field_skipped(self):
        errors = type_check({}, {}, SCHEMA)
        assert errors == []


class TestRuleValidatorCustomRule:
    def test_add_custom_rule(self):
        def no_negative_score(input_data, output_data, schema):
            score = output_data.get("score")
            if isinstance(score, (int, float)) and score < 0:
                return ["score must not be negative"]
            return []

        validator = RuleValidator()
        validator.add_rule(no_negative_score)
        result = validator.validate({}, {"name": "x", "score": -1}, SCHEMA)
        assert result.passed is False
        assert any("negative" in e for e in result.errors)


class TestRuleValidatorCombined:
    def test_multiple_failures(self):
        """Missing field + empty value + wrong type all at once."""
        output = {"name": "", "tags": "bad"}  # missing score, empty name, wrong type tags
        result = RuleValidator().validate({}, output, SCHEMA)
        assert result.passed is False
        assert len(result.errors) >= 3


# ========== ValidationResult ==========


class TestValidationResult:
    def test_merge_both_valid(self):
        a = ValidationResult(passed=True, score=1.0, validator_type=ValidatorType.SCHEMA, details="")
        b = ValidationResult(passed=True, score=1.0, validator_type=ValidatorType.RULE, details="")
        merged = ValidationResult.merge(a, b)
        assert merged.passed is True
        assert merged.errors == []

    def test_merge_one_invalid(self):
        a = ValidationResult(passed=True, score=1.0, validator_type=ValidatorType.SCHEMA, details="")
        b = ValidationResult(passed=False, score=0.0, validator_type=ValidatorType.RULE, details="fail", errors=["fail"])
        merged = ValidationResult.merge(a, b)
        assert merged.passed is False
        assert merged.errors == ["fail"]

    def test_merge_combines_errors(self):
        a = ValidationResult(passed=False, score=0.0, validator_type=ValidatorType.SCHEMA, details="a", errors=["a"])
        b = ValidationResult(passed=False, score=0.0, validator_type=ValidatorType.RULE, details="b", errors=["b"])
        merged = ValidationResult.merge(a, b)
        assert merged.passed is False
        assert merged.errors == ["a", "b"]
