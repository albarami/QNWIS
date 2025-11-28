"""
Phase 5 Tests: Deterministic Scenario Definitions

Tests:
- Scenario dataclasses
- YAML file loading
- Scenario validation
- Domain filtering
- Engine assignment
- Output validation
"""

import pytest
import tempfile
import os
from pathlib import Path
import yaml


class TestScenarioDataclasses:
    """Test scenario data structures."""
    
    def test_scenario_input_creation(self):
        """ScenarioInput should store input parameters."""
        from src.nsic.scenarios.loader import ScenarioInput
        
        inp = ScenarioInput(
            variable="oil_price",
            base_value=80.0,
            shock_value=120.0,
            shock_type="absolute",
            unit="USD/barrel",
        )
        
        assert inp.variable == "oil_price"
        assert inp.base_value == 80.0
        assert inp.shock_value == 120.0
        assert inp.shock_type == "absolute"
        assert inp.unit == "USD/barrel"
    
    def test_scenario_input_to_dict(self):
        """ScenarioInput.to_dict() should return all fields."""
        from src.nsic.scenarios.loader import ScenarioInput
        
        inp = ScenarioInput(
            variable="inflation",
            base_value=3.0,
            shock_value=8.0,
            shock_type="percentage",
        )
        
        d = inp.to_dict()
        
        assert d["variable"] == "inflation"
        assert d["base_value"] == 3.0
        assert d["shock_type"] == "percentage"
    
    def test_validation_rule_creation(self):
        """ValidationRule should store rule parameters."""
        from src.nsic.scenarios.loader import ValidationRule
        
        rule = ValidationRule(
            field="gdp_impact",
            rule_type="range",
            params={"min": -100, "max": 100},
            message="GDP impact must be reasonable",
        )
        
        assert rule.field == "gdp_impact"
        assert rule.rule_type == "range"
        assert rule.params["min"] == -100
        assert rule.params["max"] == 100
    
    def test_retry_config_defaults(self):
        """RetryConfig should have sensible defaults."""
        from src.nsic.scenarios.loader import RetryConfig
        
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 1.0
        assert config.exponential_backoff is True
        assert "timeout" in config.retry_on_errors
    
    def test_scenario_definition_creation(self):
        """ScenarioDefinition should store all scenario data."""
        from src.nsic.scenarios.loader import (
            ScenarioDefinition,
            ScenarioInput,
            ValidationRule,
            RetryConfig,
        )
        
        scenario = ScenarioDefinition(
            id="test_001",
            name="Test Scenario",
            domain="economic",
            description="Test description",
            inputs=[ScenarioInput("var1", 0, 10, "absolute")],
            expected_structure={"result": "str"},
            validation_rules=[ValidationRule("result", "required")],
            retry_config=RetryConfig(),
            priority=1,
            assigned_engine="engine_a",
            target_turns=100,
        )
        
        assert scenario.id == "test_001"
        assert scenario.domain == "economic"
        assert scenario.priority == 1
        assert scenario.assigned_engine == "engine_a"
        assert scenario.target_turns == 100


class TestScenarioLoader:
    """Test scenario loading from YAML files."""
    
    def test_loader_initialization(self):
        """ScenarioLoader should initialize with directory."""
        from src.nsic.scenarios.loader import ScenarioLoader
        
        loader = ScenarioLoader("scenarios")
        
        assert loader.scenarios_dir == Path("scenarios")
    
    def test_load_from_project_scenarios(self):
        """Should load scenarios from project scenarios directory."""
        from src.nsic.scenarios.loader import ScenarioLoader
        
        loader = ScenarioLoader("scenarios")
        count = loader.load_all()
        
        # We created at least 4 scenarios
        assert count >= 4
    
    def test_get_scenario_by_id(self):
        """Should retrieve scenario by ID."""
        from src.nsic.scenarios.loader import ScenarioLoader
        
        loader = ScenarioLoader("scenarios")
        loader.load_all()
        
        scenario = loader.get("econ_001_oil_shock_50")
        
        assert scenario is not None
        assert scenario.name == "Oil Price Shock - 50% Increase"
        assert scenario.domain == "economic"
    
    def test_get_by_domain(self):
        """Should filter scenarios by domain."""
        from src.nsic.scenarios.loader import ScenarioLoader
        
        loader = ScenarioLoader("scenarios")
        loader.load_all()
        
        economic_scenarios = loader.get_by_domain("economic")
        
        assert len(economic_scenarios) >= 2
        for s in economic_scenarios:
            assert s.domain == "economic"
    
    def test_get_by_engine(self):
        """Should filter scenarios by assigned engine."""
        from src.nsic.scenarios.loader import ScenarioLoader
        
        loader = ScenarioLoader("scenarios")
        loader.load_all()
        
        engine_a_scenarios = loader.get_by_engine("engine_a")
        
        assert len(engine_a_scenarios) >= 1
        for s in engine_a_scenarios:
            assert s.assigned_engine in ["engine_a", "auto"]
    
    def test_get_stats(self):
        """Should return statistics about loaded scenarios."""
        from src.nsic.scenarios.loader import ScenarioLoader
        
        loader = ScenarioLoader("scenarios")
        loader.load_all()
        
        stats = loader.get_stats()
        
        assert stats["total_scenarios"] >= 4
        assert "by_domain" in stats
        assert "by_engine" in stats
    
    def test_load_yaml_with_all_fields(self):
        """Should parse all YAML fields correctly."""
        from src.nsic.scenarios.loader import ScenarioLoader
        
        loader = ScenarioLoader("scenarios")
        loader.load_all()
        
        scenario = loader.get("econ_001_oil_shock_50")
        
        assert scenario is not None
        assert len(scenario.inputs) >= 1
        assert len(scenario.validation_rules) >= 1
        assert scenario.retry_config.max_retries == 3
        assert "oil" in scenario.tags


class TestScenarioValidator:
    """Test scenario validation."""
    
    def test_validator_initialization(self):
        """ScenarioValidator should initialize."""
        from src.nsic.scenarios.validator import ScenarioValidator
        
        validator = ScenarioValidator()
        
        assert validator._validation_count == 0
    
    def test_validate_valid_definition(self):
        """Should validate correct scenario definition."""
        from src.nsic.scenarios.loader import (
            ScenarioDefinition,
            ScenarioInput,
            ValidationRule,
            RetryConfig,
        )
        from src.nsic.scenarios.validator import ScenarioValidator
        
        validator = ScenarioValidator()
        
        scenario = ScenarioDefinition(
            id="valid_001",
            name="Valid Scenario",
            domain="economic",
            description="A valid scenario",
            inputs=[ScenarioInput("var1", 0, 10, "absolute")],
            expected_structure={},
            validation_rules=[],
            retry_config=RetryConfig(),
        )
        
        result = validator.validate_definition(scenario)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_validate_missing_required_fields(self):
        """Should catch missing required fields."""
        from src.nsic.scenarios.loader import (
            ScenarioDefinition,
            ValidationRule,
            RetryConfig,
        )
        from src.nsic.scenarios.validator import ScenarioValidator
        
        validator = ScenarioValidator()
        
        # Missing ID and name
        scenario = ScenarioDefinition(
            id="",
            name="",
            domain="economic",
            description="",
            inputs=[],  # Also missing inputs
            expected_structure={},
            validation_rules=[],
            retry_config=RetryConfig(),
        )
        
        result = validator.validate_definition(scenario)
        
        assert result.valid is False
        assert len(result.errors) >= 3  # id, name, inputs
    
    def test_validate_invalid_domain(self):
        """Should catch invalid domain."""
        from src.nsic.scenarios.loader import (
            ScenarioDefinition,
            ScenarioInput,
            RetryConfig,
        )
        from src.nsic.scenarios.validator import ScenarioValidator
        
        validator = ScenarioValidator()
        
        scenario = ScenarioDefinition(
            id="test",
            name="Test",
            domain="invalid_domain",  # Invalid
            description="",
            inputs=[ScenarioInput("var", 0, 1, "absolute")],
            expected_structure={},
            validation_rules=[],
            retry_config=RetryConfig(),
        )
        
        result = validator.validate_definition(scenario)
        
        assert result.valid is False
        assert any(e.field == "domain" for e in result.errors)
    
    def test_validate_output_against_rules(self):
        """Should validate output against rules."""
        from src.nsic.scenarios.loader import (
            ScenarioDefinition,
            ScenarioInput,
            ValidationRule,
            RetryConfig,
        )
        from src.nsic.scenarios.validator import ScenarioValidator
        
        validator = ScenarioValidator()
        
        scenario = ScenarioDefinition(
            id="test",
            name="Test",
            domain="economic",
            description="",
            inputs=[ScenarioInput("var", 0, 1, "absolute")],
            expected_structure={},
            validation_rules=[
                ValidationRule("summary", "required"),
                ValidationRule("score", "range", {"min": 0, "max": 1}),
            ],
            retry_config=RetryConfig(),
        )
        
        # Valid output
        output = {"summary": "Test summary", "score": 0.85}
        result = validator.validate_output(output, scenario)
        assert result.valid is True
        
        # Invalid output - missing summary
        output = {"score": 0.5}
        result = validator.validate_output(output, scenario)
        assert result.valid is False
        
        # Invalid output - score out of range
        output = {"summary": "Test", "score": 1.5}
        result = validator.validate_output(output, scenario)
        assert result.valid is False
    
    def test_validate_nested_structure(self):
        """Should validate nested expected structure."""
        from src.nsic.scenarios.loader import (
            ScenarioDefinition,
            ScenarioInput,
            RetryConfig,
        )
        from src.nsic.scenarios.validator import ScenarioValidator
        
        validator = ScenarioValidator()
        
        scenario = ScenarioDefinition(
            id="test",
            name="Test",
            domain="economic",
            description="",
            inputs=[ScenarioInput("var", 0, 1, "absolute")],
            expected_structure={
                "analysis": {
                    "value": "float",
                    "description": "str",
                }
            },
            validation_rules=[],
            retry_config=RetryConfig(),
        )
        
        # Valid nested output
        output = {
            "analysis": {
                "value": 1.5,
                "description": "Test",
            }
        }
        result = validator.validate_output(output, scenario)
        assert result.valid is True
        
        # Invalid - missing nested field
        output = {"analysis": {"value": 1.5}}
        result = validator.validate_output(output, scenario)
        assert result.valid is False


class TestValidationResult:
    """Test validation result structure."""
    
    def test_validation_result_creation(self):
        """ValidationResult should store validation state."""
        from src.nsic.scenarios.validator import ValidationResult, ValidationError
        
        error = ValidationError(
            field="test_field",
            rule_type="required",
            message="Field is required",
        )
        
        result = ValidationResult(
            valid=False,
            errors=[error],
            warnings=["A warning"],
        )
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
    
    def test_validation_result_to_dict(self):
        """ValidationResult.to_dict() should include all data."""
        from src.nsic.scenarios.validator import ValidationResult
        
        result = ValidationResult(valid=True)
        d = result.to_dict()
        
        assert d["valid"] is True
        assert d["error_count"] == 0
        assert d["warning_count"] == 0


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_scenario_loader(self):
        """create_scenario_loader should return loader."""
        from src.nsic.scenarios import create_scenario_loader
        
        loader = create_scenario_loader("scenarios")
        
        assert loader is not None
    
    def test_create_scenario_validator(self):
        """create_scenario_validator should return validator."""
        from src.nsic.scenarios import create_scenario_validator
        
        validator = create_scenario_validator()
        
        assert validator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

