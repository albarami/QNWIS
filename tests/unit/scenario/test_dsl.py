"""
Unit tests for Scenario DSL parser and validator.

Tests cover:
- Transform validation
- ScenarioSpec validation
- parse_scenario function with YAML/JSON/dict
- Edge cases and error handling
"""

import pytest

from src.qnwis.scenario.dsl import (
    ScenarioSpec,
    Transform,
    parse_scenario,
    validate_scenario_file,
)


class TestTransform:
    """Test Transform model validation."""

    def test_valid_additive_transform(self):
        """Test valid additive transform."""
        t = Transform(type="additive", value=5.0, start_month=0)
        assert t.type == "additive"
        assert t.value == 5.0
        assert t.start_month == 0
        assert t.end_month is None

    def test_valid_multiplicative_transform(self):
        """Test valid multiplicative transform with rate in [0,1]."""
        t = Transform(type="multiplicative", value=0.10, start_month=3, end_month=12)
        assert t.type == "multiplicative"
        assert t.value == 0.10

    def test_multiplicative_rate_out_of_range(self):
        """Test multiplicative rate must be in [0,1]."""
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            Transform(type="multiplicative", value=1.5, start_month=0)

    def test_nan_value_rejected(self):
        """Test NaN value is rejected."""
        with pytest.raises(ValueError, match="must be finite"):
            Transform(type="additive", value=float("nan"), start_month=0)

    def test_inf_value_rejected(self):
        """Test Inf value is rejected."""
        with pytest.raises(ValueError, match="must be finite"):
            Transform(type="additive", value=float("inf"), start_month=0)

    def test_end_before_start_rejected(self):
        """Test end_month < start_month is rejected."""
        with pytest.raises(ValueError, match="must be >= start_month"):
            Transform(type="additive", value=5.0, start_month=10, end_month=5)

    def test_negative_start_month_rejected(self):
        """Test negative start_month is rejected."""
        with pytest.raises(ValueError):
            Transform(type="additive", value=5.0, start_month=-1)


class TestScenarioSpec:
    """Test ScenarioSpec model validation."""

    def test_valid_scenario_spec(self):
        """Test valid scenario specification."""
        spec = ScenarioSpec(
            name="Test Scenario",
            description="Test description",
            metric="retention",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.10, start_month=0)
            ],
        )
        assert spec.name == "Test Scenario"
        assert spec.metric == "retention"
        assert len(spec.transforms) == 1

    def test_empty_transforms_rejected(self):
        """Test scenario must have at least one transform."""
        with pytest.raises(ValueError, match="at least one transform"):
            ScenarioSpec(
                name="Test",
                description="Test",
                metric="retention",
                horizon_months=12,
                transforms=[],
            )

    def test_too_many_transforms_rejected(self):
        """Test limit on number of transforms."""
        transforms = [
            Transform(type="additive", value=1.0, start_month=i)
            for i in range(15)
        ]
        with pytest.raises(ValueError, match="Too many transforms"):
            ScenarioSpec(
                name="Test",
                description="Test",
                metric="retention",
                horizon_months=12,
                transforms=transforms,
            )

    def test_invalid_horizon_rejected(self):
        """Test horizon must be in valid range."""
        with pytest.raises(ValueError):
            ScenarioSpec(
                name="Test",
                description="Test",
                metric="retention",
                horizon_months=0,  # Too small
                transforms=[
                    Transform(type="additive", value=1.0, start_month=0)
                ],
            )

        with pytest.raises(ValueError):
            ScenarioSpec(
                name="Test",
                description="Test",
                metric="retention",
                horizon_months=120,  # Too large (>96)
                transforms=[
                    Transform(type="additive", value=1.0, start_month=0)
                ],
            )

    def test_clamp_min_greater_than_max_rejected(self):
        """Test clamp_min must be < clamp_max."""
        with pytest.raises(ValueError, match="clamp_min .* must be < clamp_max"):
            ScenarioSpec(
                name="Test",
                description="Test",
                metric="retention",
                horizon_months=12,
                transforms=[
                    Transform(type="additive", value=1.0, start_month=0)
                ],
                clamp_min=100.0,
                clamp_max=50.0,
            )

    def test_nan_clamp_rejected(self):
        """Test NaN clamp values are rejected."""
        with pytest.raises(ValueError, match="must be finite"):
            ScenarioSpec(
                name="Test",
                description="Test",
                metric="retention",
                horizon_months=12,
                transforms=[
                    Transform(type="additive", value=1.0, start_month=0)
                ],
                clamp_min=float("nan"),
            )


class TestParseScenario:
    """Test parse_scenario function."""

    def test_parse_yaml_string(self):
        """Test parsing YAML string."""
        yaml_spec = """
name: Retention Boost
description: 10% improvement scenario
metric: retention
sector: Construction
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.10
    start_month: 0
"""
        spec = parse_scenario(yaml_spec, format="yaml")
        assert spec.name == "Retention Boost"
        assert spec.metric == "retention"
        assert spec.sector == "Construction"
        assert len(spec.transforms) == 1

    def test_parse_json_string(self):
        """Test parsing JSON string."""
        json_spec = """
{
  "name": "Retention Boost",
  "description": "10% improvement",
  "metric": "retention",
  "horizon_months": 12,
  "transforms": [
    {"type": "multiplicative", "value": 0.10, "start_month": 0}
  ]
}
"""
        spec = parse_scenario(json_spec, format="json")
        assert spec.name == "Retention Boost"
        assert spec.metric == "retention"

    def test_parse_dict(self):
        """Test parsing dict."""
        dict_spec = {
            "name": "Retention Boost",
            "description": "10% improvement",
            "metric": "retention",
            "horizon_months": 12,
            "transforms": [
                {"type": "multiplicative", "value": 0.10, "start_month": 0}
            ],
        }
        spec = parse_scenario(dict_spec, format="dict")
        assert spec.name == "Retention Boost"
        assert spec.metric == "retention"

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML raises error."""
        invalid_yaml = "name: [unclosed bracket"
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_scenario(invalid_yaml, format="yaml")

    def test_parse_missing_required_field(self):
        """Test parsing with missing required field raises error."""
        incomplete_yaml = """
name: Test
description: Test
# Missing metric and horizon_months
transforms:
  - type: additive
    value: 1.0
    start_month: 0
"""
        with pytest.raises(ValueError, match="validation failed"):
            parse_scenario(incomplete_yaml, format="yaml")

    def test_parse_invalid_transform_in_spec(self):
        """Test parsing spec with invalid transform."""
        invalid_spec = """
name: Test
description: Test
metric: retention
horizon_months: 12
transforms:
  - type: multiplicative
    value: 2.0
    start_month: 0
"""
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            parse_scenario(invalid_spec, format="yaml")


class TestValidateScenarioFile:
    """Test validate_scenario_file function."""

    def test_validate_nonexistent_file(self, tmp_path):
        """Test validating non-existent file."""
        filepath = tmp_path / "nonexistent.yml"
        is_valid, msg = validate_scenario_file(str(filepath))
        assert not is_valid
        assert "Validation failed" in msg

    def test_validate_valid_file(self, tmp_path):
        """Test validating valid scenario file."""
        spec_content = """
name: Test Scenario
description: Test
metric: retention
horizon_months: 12
transforms:
  - type: additive
    value: 5.0
    start_month: 0
"""
        spec_file = tmp_path / "valid_scenario.yml"
        spec_file.write_text(spec_content, encoding="utf-8")

        is_valid, msg = validate_scenario_file(str(spec_file))
        assert is_valid
        assert "Valid scenario" in msg
        assert "Test Scenario" in msg

    def test_validate_invalid_file(self, tmp_path):
        """Test validating invalid scenario file."""
        spec_content = """
name: Test
description: Test
metric: retention
horizon_months: 12
transforms: []
"""
        spec_file = tmp_path / "invalid_scenario.yml"
        spec_file.write_text(spec_content, encoding="utf-8")

        is_valid, msg = validate_scenario_file(str(spec_file))
        assert not is_valid
        assert "Validation failed" in msg
