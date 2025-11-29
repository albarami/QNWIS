"""
NSIC Scenario Validator

Validates scenario definitions and outputs against rules.

Features:
- Schema validation for scenario definitions
- Output validation against expected structure
- Rule-based validation (required, range, format, contains)
- Detailed error reporting
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from .loader import ScenarioDefinition, ValidationRule

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    rule_type: str
    message: str
    actual_value: Any = None
    expected: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "rule_type": self.rule_type,
            "message": self.message,
            "actual_value": str(self.actual_value)[:100] if self.actual_value else None,
            "expected": self.expected,
        }


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
        }


class ScenarioValidator:
    """
    Validates scenario definitions and outputs.
    
    Validation types:
    - required: Field must exist and be non-empty
    - range: Numeric value within bounds
    - format: String matches pattern
    - contains: Field contains specified value
    - type: Field is of expected type
    """
    
    # Required fields in scenario definition
    REQUIRED_DEFINITION_FIELDS = [
        "id", "name", "domain", "description", "inputs"
    ]
    
    VALID_DOMAINS = {"economic", "policy", "competitive", "timing", "social", "deep"}
    VALID_ENGINES = {"engine_a", "engine_b", "auto"}
    VALID_PRIORITIES = {1, 2, 3}
    
    def __init__(self):
        """Initialize validator."""
        self._validation_count = 0
        self._error_count = 0
    
    def validate_definition(
        self,
        scenario: ScenarioDefinition,
    ) -> ValidationResult:
        """
        Validate a scenario definition.
        
        Args:
            scenario: ScenarioDefinition to validate
            
        Returns:
            ValidationResult with any errors found
        """
        errors = []
        warnings = []
        
        # Check required fields
        if not scenario.id or not scenario.id.strip():
            errors.append(ValidationError(
                field="id",
                rule_type="required",
                message="Scenario ID is required",
            ))
        
        if not scenario.name or not scenario.name.strip():
            errors.append(ValidationError(
                field="name",
                rule_type="required",
                message="Scenario name is required",
            ))
        
        if not scenario.description:
            warnings.append("Scenario description is empty")
        
        # Validate domain
        if scenario.domain not in self.VALID_DOMAINS:
            errors.append(ValidationError(
                field="domain",
                rule_type="enum",
                message=f"Invalid domain: {scenario.domain}",
                actual_value=scenario.domain,
                expected=list(self.VALID_DOMAINS),
            ))
        
        # Validate assigned engine
        if scenario.assigned_engine not in self.VALID_ENGINES:
            errors.append(ValidationError(
                field="assigned_engine",
                rule_type="enum",
                message=f"Invalid engine: {scenario.assigned_engine}",
                actual_value=scenario.assigned_engine,
                expected=list(self.VALID_ENGINES),
            ))
        
        # Validate priority
        if scenario.priority not in self.VALID_PRIORITIES:
            errors.append(ValidationError(
                field="priority",
                rule_type="enum",
                message=f"Invalid priority: {scenario.priority}",
                actual_value=scenario.priority,
                expected=list(self.VALID_PRIORITIES),
            ))
        
        # Validate inputs
        if not scenario.inputs:
            errors.append(ValidationError(
                field="inputs",
                rule_type="required",
                message="At least one input is required",
            ))
        else:
            for i, inp in enumerate(scenario.inputs):
                if not inp.variable:
                    errors.append(ValidationError(
                        field=f"inputs[{i}].variable",
                        rule_type="required",
                        message=f"Input {i} missing variable name",
                    ))
                if inp.shock_type not in ["absolute", "percentage"]:
                    errors.append(ValidationError(
                        field=f"inputs[{i}].shock_type",
                        rule_type="enum",
                        message=f"Invalid shock_type: {inp.shock_type}",
                        expected=["absolute", "percentage"],
                    ))
        
        # Validate target turns
        if scenario.target_turns < 1 or scenario.target_turns > 200:
            errors.append(ValidationError(
                field="target_turns",
                rule_type="range",
                message=f"target_turns must be 1-200, got {scenario.target_turns}",
                actual_value=scenario.target_turns,
                expected={"min": 1, "max": 200},
            ))
        
        # Update stats
        self._validation_count += 1
        self._error_count += len(errors)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def validate_output(
        self,
        output: Dict[str, Any],
        scenario: ScenarioDefinition,
    ) -> ValidationResult:
        """
        Validate scenario output against rules.
        
        Args:
            output: Output data to validate
            scenario: ScenarioDefinition with validation rules
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # Validate against expected structure
        if scenario.expected_structure:
            structure_errors = self._validate_structure(
                output,
                scenario.expected_structure,
            )
            errors.extend(structure_errors)
        
        # Apply validation rules
        for rule in scenario.validation_rules:
            rule_errors = self._apply_rule(output, rule)
            errors.extend(rule_errors)
        
        # Update stats
        self._validation_count += 1
        self._error_count += len(errors)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def _validate_structure(
        self,
        data: Dict[str, Any],
        expected: Dict[str, Any],
        path: str = "",
    ) -> List[ValidationError]:
        """Validate data structure against expected schema."""
        errors = []
        
        for key, expected_type in expected.items():
            full_path = f"{path}.{key}" if path else key
            
            if key not in data:
                errors.append(ValidationError(
                    field=full_path,
                    rule_type="required",
                    message=f"Missing required field: {full_path}",
                ))
                continue
            
            actual_value = data[key]
            
            # Check type
            if isinstance(expected_type, dict):
                # Nested structure
                if not isinstance(actual_value, dict):
                    errors.append(ValidationError(
                        field=full_path,
                        rule_type="type",
                        message=f"Expected dict at {full_path}",
                        actual_value=type(actual_value).__name__,
                        expected="dict",
                    ))
                else:
                    nested_errors = self._validate_structure(
                        actual_value,
                        expected_type,
                        full_path,
                    )
                    errors.extend(nested_errors)
            elif isinstance(expected_type, str):
                # Type name
                if expected_type == "str" and not isinstance(actual_value, str):
                    errors.append(ValidationError(
                        field=full_path,
                        rule_type="type",
                        message=f"Expected string at {full_path}",
                        actual_value=type(actual_value).__name__,
                        expected="str",
                    ))
                elif expected_type == "int" and not isinstance(actual_value, int):
                    errors.append(ValidationError(
                        field=full_path,
                        rule_type="type",
                        message=f"Expected int at {full_path}",
                        actual_value=type(actual_value).__name__,
                        expected="int",
                    ))
                elif expected_type == "float" and not isinstance(actual_value, (int, float)):
                    errors.append(ValidationError(
                        field=full_path,
                        rule_type="type",
                        message=f"Expected float at {full_path}",
                        actual_value=type(actual_value).__name__,
                        expected="float",
                    ))
                elif expected_type == "list" and not isinstance(actual_value, list):
                    errors.append(ValidationError(
                        field=full_path,
                        rule_type="type",
                        message=f"Expected list at {full_path}",
                        actual_value=type(actual_value).__name__,
                        expected="list",
                    ))
                elif expected_type == "bool" and not isinstance(actual_value, bool):
                    errors.append(ValidationError(
                        field=full_path,
                        rule_type="type",
                        message=f"Expected bool at {full_path}",
                        actual_value=type(actual_value).__name__,
                        expected="bool",
                    ))
        
        return errors
    
    def _apply_rule(
        self,
        data: Dict[str, Any],
        rule: ValidationRule,
    ) -> List[ValidationError]:
        """Apply a single validation rule."""
        errors = []
        
        # Get field value (supports nested paths like "output.metrics.value")
        value = self._get_nested_value(data, rule.field)
        
        if rule.rule_type == "required":
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(ValidationError(
                    field=rule.field,
                    rule_type="required",
                    message=rule.message or f"{rule.field} is required",
                ))
        
        elif rule.rule_type == "range":
            if value is not None:
                min_val = rule.params.get("min")
                max_val = rule.params.get("max")
                
                if min_val is not None and value < min_val:
                    errors.append(ValidationError(
                        field=rule.field,
                        rule_type="range",
                        message=rule.message or f"{rule.field} below minimum",
                        actual_value=value,
                        expected={"min": min_val},
                    ))
                
                if max_val is not None and value > max_val:
                    errors.append(ValidationError(
                        field=rule.field,
                        rule_type="range",
                        message=rule.message or f"{rule.field} above maximum",
                        actual_value=value,
                        expected={"max": max_val},
                    ))
        
        elif rule.rule_type == "format":
            if value is not None and isinstance(value, str):
                pattern = rule.params.get("pattern", "")
                if pattern and not re.match(pattern, value):
                    errors.append(ValidationError(
                        field=rule.field,
                        rule_type="format",
                        message=rule.message or f"{rule.field} doesn't match pattern",
                        actual_value=value,
                        expected={"pattern": pattern},
                    ))
        
        elif rule.rule_type == "contains":
            if value is not None:
                expected_value = rule.params.get("value")
                if isinstance(value, str) and expected_value not in value:
                    errors.append(ValidationError(
                        field=rule.field,
                        rule_type="contains",
                        message=rule.message or f"{rule.field} doesn't contain expected value",
                        actual_value=value,
                        expected={"contains": expected_value},
                    ))
                elif isinstance(value, (list, dict)) and expected_value not in value:
                    errors.append(ValidationError(
                        field=rule.field,
                        rule_type="contains",
                        message=rule.message or f"{rule.field} doesn't contain expected item",
                        actual_value=value,
                        expected={"contains": expected_value},
                    ))
        
        return errors
    
    def _get_nested_value(
        self,
        data: Dict[str, Any],
        path: str,
    ) -> Any:
        """Get a nested value from a dict using dot notation."""
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "total_validations": self._validation_count,
            "total_errors": self._error_count,
        }


def create_scenario_validator() -> ScenarioValidator:
    """Factory function to create a ScenarioValidator."""
    return ScenarioValidator()

