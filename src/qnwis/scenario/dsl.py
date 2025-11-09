"""
Scenario DSL - Typed schema and strict parser for scenario specifications.

Provides typed data structures and validation for scenario definitions with
guardrails to prevent invalid inputs (NaN/Inf, out-of-range rates, etc.).
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Type aliases for clarity
TransformType = Literal["additive", "multiplicative", "growth_override", "clamp"]
AggregationType = Literal["sector_to_national", "none"]


class Transform(BaseModel):
    """
    Single transformation to apply to a time series.

    Attributes:
        type: Transform type (additive, multiplicative, growth_override, clamp)
        value: Transform magnitude (rate for multiplicative, absolute for additive)
        start_month: Zero-indexed month to start applying (inclusive)
        end_month: Zero-indexed month to end applying (inclusive, None for all)
    """

    type: TransformType
    value: float
    start_month: int = Field(ge=0)
    end_month: int | None = Field(default=None, ge=0)

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float, info: Any) -> float:
        """Validate transform value is finite and in valid range."""
        if not math.isfinite(v):
            raise ValueError(f"Transform value must be finite, got {v}")

        # For multiplicative transforms, ensure rate is in [0, 1] range
        transform_type = info.data.get("type") if hasattr(info, "data") else None
        if transform_type == "multiplicative" and not (0.0 <= v <= 1.0):
            raise ValueError(
                f"Multiplicative transform rate must be in [0, 1], got {v}"
            )

        return v

    @field_validator("end_month")
    @classmethod
    def validate_end_month(cls, v: int | None, info: Any) -> int | None:
        """Validate end_month >= start_month if provided."""
        if v is not None:
            start = info.data.get("start_month", 0)
            if v < start:
                raise ValueError(
                    f"end_month ({v}) must be >= start_month ({start})"
                )
        return v


class ScenarioSpec(BaseModel):
    """
    Complete scenario specification with validation.

    Attributes:
        name: Human-readable scenario name
        description: Brief description of the scenario
        metric: Target metric to transform (e.g., "retention", "qatarization")
        sector: Optional sector filter (None for national)
        horizon_months: Forecast horizon in months
        transforms: List of transforms to apply sequentially
        aggregation: How to aggregate sector results to national level
        clamp_min: Minimum allowed value (None for no floor)
        clamp_max: Maximum allowed value (None for no ceiling)
    """

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=500)
    metric: str = Field(min_length=1)
    sector: str | None = None
    horizon_months: int = Field(ge=1, le=96)  # Max 8 years
    transforms: list[Transform] = Field(default_factory=list)
    aggregation: AggregationType = "none"
    clamp_min: float | None = None
    clamp_max: float | None = None

    @field_validator("clamp_min", "clamp_max")
    @classmethod
    def validate_clamps(cls, v: float | None) -> float | None:
        """Validate clamp values are finite."""
        if v is not None and not math.isfinite(v):
            raise ValueError(f"Clamp value must be finite, got {v}")
        return v

    @field_validator("transforms")
    @classmethod
    def validate_transforms(cls, v: list[Transform]) -> list[Transform]:
        """Validate transforms list is non-empty and within limits."""
        if not v:
            raise ValueError("Scenario must have at least one transform")
        if len(v) > 10:
            raise ValueError(f"Too many transforms: {len(v)} (max 10)")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation for cross-field constraints."""
        # Validate clamp_min < clamp_max if both provided
        if (
            self.clamp_min is not None
            and self.clamp_max is not None
            and self.clamp_min >= self.clamp_max
        ):
            raise ValueError(
                f"clamp_min ({self.clamp_min}) must be < clamp_max ({self.clamp_max})"
            )


def parse_scenario(source: str | dict[str, Any], format: Literal["yaml", "json", "dict"] = "yaml") -> ScenarioSpec:
    """
    Parse scenario specification from YAML, JSON, or dict with strict validation.

    Args:
        source: Scenario specification as YAML string, JSON string, or dict
        format: Source format ("yaml", "json", or "dict")

    Returns:
        Validated ScenarioSpec instance

    Raises:
        ValueError: If parsing fails or validation constraints are violated

    Examples:
        >>> spec = parse_scenario('''
        ... name: Retention Boost
        ... description: 10% retention improvement scenario
        ... metric: retention
        ... sector: Construction
        ... horizon_months: 12
        ... transforms:
        ...   - type: multiplicative
        ...     value: 0.10
        ...     start_month: 0
        ... ''', format="yaml")
        >>> spec.name
        'Retention Boost'
    """
    try:
        if format == "dict":
            if not isinstance(source, dict):
                raise ValueError("Source must be a dict when format='dict'")
            data = source
        elif format == "yaml":
            if not isinstance(source, str):
                raise ValueError("Source must be a string when format='yaml'")
            data = yaml.safe_load(source)
        elif format == "json":
            if not isinstance(source, str):
                raise ValueError("Source must be a string when format='json'")
            data = json.loads(source)
        else:
            raise ValueError(f"Invalid format: {format}")

        if not isinstance(data, dict):
            raise ValueError(f"Parsed data must be a dict, got {type(data)}")

        # Parse and validate with Pydantic
        spec = ScenarioSpec.model_validate(data)

        logger.info(
            "Parsed scenario: name=%s metric=%s horizon=%d transforms=%d",
            spec.name,
            spec.metric,
            spec.horizon_months,
            len(spec.transforms),
        )

        return spec

    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to parse {format}: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Scenario validation failed: {exc}") from exc


def validate_scenario_file(filepath: str) -> tuple[bool, str]:
    """
    Validate a scenario file without executing it.

    Args:
        filepath: Path to YAML or JSON scenario file

    Returns:
        Tuple of (is_valid, message)

    Examples:
        >>> is_valid, msg = validate_scenario_file("scenarios/retention_boost.yml")
        >>> print(msg)
        'Valid scenario: Retention Boost (12 months, 1 transforms)'
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Detect format from extension
        fmt = "json" if filepath.endswith(".json") else "yaml"

        spec = parse_scenario(content, format=fmt)

        msg = (
            f"Valid scenario: {spec.name} "
            f"({spec.horizon_months} months, {len(spec.transforms)} transforms)"
        )
        return True, msg

    except Exception as exc:
        return False, f"Validation failed: {exc}"
