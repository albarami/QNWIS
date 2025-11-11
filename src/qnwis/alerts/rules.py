"""
Pydantic DSL for alert rule definitions.

Provides type-safe rule specifications with built-in validation guardrails.
"""

from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class TriggerType(str, Enum):
    """Supported trigger types for alert evaluation."""

    THRESHOLD = "threshold"
    YOY_DELTA_PCT = "yoy_delta_pct"
    SLOPE_WINDOW = "slope_window"
    BREAK_EVENT = "break_event"
    BURN_RATE = "burn_rate"


class TriggerOperator(str, Enum):
    """Comparison operators for threshold-based triggers."""

    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    EQ = "eq"


class Severity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScopeConfig(BaseModel):
    """
    Scope definition for alert evaluation.

    Attributes:
        level: Aggregation level (sector, nationality, etc.)
        code: Optional specific code to filter (e.g., 'construction')
    """

    level: str = Field(..., description="Aggregation level (sector, nationality, etc.)")
    code: str | None = Field(None, description="Optional filter code")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate level is non-empty."""
        if not v or not v.strip():
            raise ValueError("Scope level cannot be empty")
        return v.strip()


class WindowConfig(BaseModel):
    """
    Time window configuration for alert evaluation.

    Attributes:
        months: Number of months in evaluation window (≥3)
    """

    months: int = Field(..., ge=3, description="Number of months (≥3)")

    @field_validator("months")
    @classmethod
    def validate_months(cls, v: int) -> int:
        """Ensure months is at least 3."""
        if v < 3:
            raise ValueError("Window must be at least 3 months")
        return v


class TriggerConfig(BaseModel):
    """
    Trigger configuration defining alert conditions.

    Attributes:
        type: Type of trigger (threshold, yoy_delta_pct, etc.)
        op: Comparison operator for threshold-based triggers
        value: Threshold or comparison value
    """

    type: TriggerType = Field(..., description="Trigger type")
    op: TriggerOperator | None = Field(None, description="Comparison operator")
    value: float = Field(0.0, description="Threshold or comparison value")
    fast_threshold: float | None = Field(
        None, description="Fast-window burn-rate threshold (burn_rate)"
    )
    slow_threshold: float | None = Field(
        None, description="Slow-window burn-rate threshold (burn_rate)"
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Reject NaN/Inf values."""
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Trigger value cannot be NaN or Inf")
        return v

    @field_validator("fast_threshold", "slow_threshold")
    @classmethod
    def validate_burn_thresholds(cls, v: float | None) -> float | None:
        """Reject NaN/Inf values for burn thresholds if provided."""
        if v is None:
            return v
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Burn threshold cannot be NaN or Inf")
        return v

    @model_validator(mode="after")
    def validate_operator(self) -> TriggerConfig:
        """Ensure operator is provided for threshold-based triggers."""
        if self.type == TriggerType.THRESHOLD and self.op is None:
            raise ValueError("Operator required for threshold trigger")
        return self

    @model_validator(mode="after")
    def validate_burn_rate(self) -> TriggerConfig:
        """Ensure required fields for burn-rate triggers are present."""
        if self.type == TriggerType.BURN_RATE:
            if self.fast_threshold is None or self.slow_threshold is None:
                raise ValueError(
                    "fast_threshold and slow_threshold are required for burn_rate trigger"
                )
            if self.fast_threshold < 0 or self.slow_threshold < 0:
                raise ValueError("Burn thresholds must be non-negative")
        return self


class AlertRule(BaseModel):
    """
    Production-grade alert rule specification.

    Example YAML:
        rule_id: retention_drop_construction
        metric: retention
        scope:
          level: sector
          code: construction
        window:
          months: 6
        trigger:
          type: yoy_delta_pct
          op: lte
          value: -5.0
        horizon: 12
        severity: high

    Attributes:
        rule_id: Unique identifier for this rule
        metric: Metric name to evaluate (e.g., 'retention')
        scope: Scope configuration (level, code)
        window: Time window configuration
        trigger: Trigger condition specification
        horizon: Forecast horizon in months (≤96)
        severity: Alert severity level
        enabled: Whether this rule is active
        description: Optional human-readable description
    """

    rule_id: str = Field(..., description="Unique rule identifier")
    metric: str = Field(..., description="Metric name")
    scope: ScopeConfig = Field(..., description="Scope configuration")
    window: WindowConfig = Field(..., description="Window configuration")
    trigger: TriggerConfig = Field(..., description="Trigger specification")
    horizon: int = Field(..., ge=1, le=96, description="Forecast horizon (1-96 months)")
    severity: Severity = Field(..., description="Alert severity")
    enabled: bool = Field(True, description="Rule enabled flag")
    description: str | None = Field(None, description="Optional description")

    @field_validator("rule_id", "metric")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure identifiers are non-empty."""
        if not v or not v.strip():
            raise ValueError("Identifier cannot be empty")
        return v.strip()

    @field_validator("horizon")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        """Ensure horizon is within bounds."""
        if v < 1 or v > 96:
            raise ValueError("Horizon must be between 1 and 96 months")
        return v

    def clamp_rate(self, value: float) -> float:
        """
        Clamp rate values to [0, 1] range.

        Args:
            value: Raw rate value

        Returns:
            Clamped value between 0.0 and 1.0
        """
        return max(0.0, min(1.0, value))

    def is_rate_metric(self) -> bool:
        """
        Check if metric represents a rate/percentage.

        Returns:
            True if metric name suggests a rate
        """
        rate_indicators = ["rate", "ratio", "pct", "percent", "retention"]
        return any(ind in self.metric.lower() for ind in rate_indicators)
