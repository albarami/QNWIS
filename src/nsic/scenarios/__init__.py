"""NSIC Scenarios - External Factor Scenario Generation.

Key Components:
- NSICScenarioGenerator: Generates 6 EXTERNAL FACTOR scenarios from ANY user question
- ScenarioLoader: Loads pre-defined YAML templates (for reference/backward compat)
- ScenarioValidator: Validates scenario structure and content

NEW DESIGN (v2.0):
- Scenarios are EXTERNAL FACTORS, not policy variations
- 1 Base Case + 5 domain-relevant external factors
- Engine B runs FOR EACH scenario
- Makes recommendations ROBUST across multiple futures
"""

from .generator import (
    NSICScenarioGenerator,
    ScenarioSet,
    GeneratedScenario,
    create_scenario_generator,
    SCENARIO_CATEGORY_GUIDANCE,
)

from .loader import (
    ScenarioLoader,
    ScenarioDefinition,
    ScenarioInput,
    ValidationRule,
    RetryConfig,
    create_scenario_loader,
)

from .validator import (
    ScenarioValidator,
    ValidationResult,
    ValidationError,
    create_scenario_validator,
)

__all__ = [
    # Generator (External Factors Edition)
    "NSICScenarioGenerator",
    "ScenarioSet",
    "GeneratedScenario",
    "create_scenario_generator",
    "SCENARIO_CATEGORY_GUIDANCE",
    # Loader (for templates/backward compatibility)
    "ScenarioLoader",
    "ScenarioDefinition",
    "ScenarioInput",
    "ValidationRule",
    "RetryConfig",
    "create_scenario_loader",
    # Validator
    "ScenarioValidator",
    "ValidationResult",
    "ValidationError",
    "create_scenario_validator",
]
