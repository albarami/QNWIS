"""NSIC Scenarios - Dynamic scenario generation and validation.

Key Components:
- NSICScenarioGenerator: Generates 30 scenarios (1+5+24) from ANY user question
- ScenarioLoader: Loads pre-defined YAML templates (for reference/backward compat)
- ScenarioValidator: Validates scenario structure and content
"""

from .generator import (
    NSICScenarioGenerator,
    ScenarioSet,
    GeneratedScenario,
    create_scenario_generator,
    DEEP_SCENARIO_TYPES,
    BROAD_CATEGORIES,
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
    # Generator (NEW - primary interface)
    "NSICScenarioGenerator",
    "ScenarioSet",
    "GeneratedScenario",
    "create_scenario_generator",
    "DEEP_SCENARIO_TYPES",
    "BROAD_CATEGORIES",
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
